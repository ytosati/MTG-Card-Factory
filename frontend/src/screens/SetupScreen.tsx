// Setup screen container: reads what the build needs, starts and follows it, and hands each state to the view.
// Details: specs/spec.md, RN-28 and "Screens" (First-run setup); specs/plan.md, section 6.
import { useCallback, useEffect, useRef, useState } from "react";
import type { RefObject } from "react";

import { ApiError, getSetup, startBuild } from "../api/client";
import type { JobResponse, SetupResponse } from "../api/types";
import { useJob } from "../hooks/useJob";
import { setupCopy } from "./setup/copy";
import { formatSize } from "./setup/formatSize";
import { SetupView } from "./setup/SetupView";
import type { SetupAction } from "./setup/SetupView";

interface SetupScreenProps {
  /** Called once the database is ready, so the shell moves to the normal screens. */
  onReady: () => void;
}

type Load =
  | { kind: "loading" }
  | { kind: "failed"; message: string }
  | { kind: "loaded"; setup: SetupResponse };

/** One build followed on this screen; a new attempt remounts its follower, even when the job id repeats. */
interface BuildRun {
  attempt: number;
  /** Null when the job is already finished, so it is shown without polling. */
  pollId: string | null;
  known: JobResponse;
}

/** What the follower of a run last saw. */
interface Followed {
  attempt: number;
  job: JobResponse | null;
  lost: boolean;
}

interface Problem {
  code: string | null;
  message: string;
}

/** What the action area shows; a change of it may move focus (see useMoveFocus). */
type View = SetupAction;

function isActive(job: JobResponse): boolean {
  return job.status === "queued" || job.status === "running";
}

function runFromSetup(setup: SetupResponse, attempt: number): BuildRun | null {
  const job = setup.job;
  if (job === null) return null;
  if (isActive(job)) return { attempt, pollId: job.id, known: job };
  if (job.status === "failed") return { attempt, pollId: null, known: job };
  return null;
}

function problemOf(reason: unknown): Problem {
  if (reason instanceof ApiError) return { code: reason.code, message: reason.message };
  if (reason instanceof Error) return { code: null, message: reason.message };
  return { code: null, message: setupCopy.unknownFailure };
}

function viewOf(
  load: Load,
  run: BuildRun | null,
  followed: Followed | null,
  starting: boolean,
  startError: Problem | null,
): View {
  if (load.kind === "loading") return { kind: "loading" };
  if (load.kind === "failed") return { kind: "load-failed", message: load.message };
  if (load.setup.database_ready) return { kind: "ready" };
  if (starting) return { kind: "starting" };
  if (run !== null) {
    const seen = followed !== null && followed.attempt === run.attempt ? followed : null;
    if (seen?.lost) return { kind: "build-failed", message: setupCopy.lost };
    const job = seen?.job ?? run.known;
    if (job.status === "failed") return { kind: "build-failed", message: job.error?.error.message ?? setupCopy.failed };
    return { kind: "building", job };
  }
  // A refused start is newer than the listing error of the snapshot read on open.
  if (startError !== null) return { kind: "start", problem: startError };
  if (load.setup.listing_error !== null) return { kind: "listing-failed", message: load.setup.listing_error.error.message };
  const { free_space: free, space_needed: needed } = load.setup;
  // See spec RN-28: the build would be refused, so the screen asks for space instead of offering it.
  if (free !== null && needed !== null && free < needed) return { kind: "short", missing: formatSize(needed - free) };
  return { kind: "start", problem: null };
}

/** The Setup screen. */
export function SetupScreen({ onReady }: SetupScreenProps) {
  const [load, setLoad] = useState<Load>({ kind: "loading" });
  const [reads, setReads] = useState(0);
  const [run, setRun] = useState<BuildRun | null>(null);
  const [followed, setFollowed] = useState<Followed | null>(null);
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<Problem | null>(null);

  // A ref, not state: two clicks in the same frame must not both send the start.
  const startingRef = useRef(false);
  // Attempts only grow, so what a previous follower saw never counts for a new run.
  const attemptsRef = useRef(0);
  const mountedRef = useRef(true);
  const readyRef = useRef(false);
  const engagedRef = useRef(false);
  const actionRef = useRef<HTMLDivElement>(null);
  const onReadyRef = useRef(onReady);
  onReadyRef.current = onReady;

  const reportReady = useCallback(() => {
    if (readyRef.current) return;
    readyRef.current = true;
    onReadyRef.current();
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    getSetup().then(
      (setup) => {
        if (!active) return;
        setLoad({ kind: "loaded", setup });
        attemptsRef.current += 1;
        setRun(runFromSetup(setup, attemptsRef.current));
        if (setup.database_ready) reportReady();
      },
      (reason: unknown) => {
        if (active) setLoad({ kind: "failed", message: problemOf(reason).message });
      },
    );
    return () => {
      active = false;
    };
  }, [reads, reportReady]);

  const readAgain = useCallback(() => {
    engagedRef.current = true;
    setLoad({ kind: "loading" });
    setReads((value) => value + 1);
  }, []);

  const start = useCallback(() => {
    if (startingRef.current) return;
    startingRef.current = true;
    engagedRef.current = true;
    setStarting(true);
    setStartError(null);
    startBuild()
      .then(
        (job) => {
          if (!mountedRef.current) return;
          attemptsRef.current += 1;
          setRun({ attempt: attemptsRef.current, pollId: isActive(job) ? job.id : null, known: job });
          if (job.status === "done") reportReady();
        },
        (reason: unknown) => {
          if (!mountedRef.current) return;
          setRun(null);
          setStartError(problemOf(reason));
        },
      )
      .finally(() => {
        startingRef.current = false;
        if (mountedRef.current) setStarting(false);
      });
  }, [reportReady]);

  const view = viewOf(load, run, followed, starting, startError);

  const buildDone = view.kind === "building" && view.job.status === "done";
  useEffect(() => {
    if (buildDone) reportReady();
  }, [buildDone, reportReady]);

  useMoveFocus(view.kind, engagedRef, actionRef);

  const setup = load.kind === "loaded" && view.kind !== "ready" ? load.setup : null;
  const settingsToFix = setup?.settings.some((item) => item.code === "config_invalid") ?? false;
  const lacksSpace = startError?.code === "insufficient_space";

  return (
    <>
      <SetupView
        action={view}
        setup={setup}
        settingsToFix={settingsToFix}
        lacksSpace={lacksSpace}
        actionRef={actionRef}
        onStart={start}
        onReadAgain={readAgain}
      />
      {run !== null && <Follower key={run.attempt} run={run} onSeen={setFollowed} />}
    </>
  );
}

/**
 * After an action of the person, a new view must not leave focus on the page body: focus moves to its
 * enabled button, or to the action area when it has none. Focus the person moved elsewhere stays there.
 */
function useMoveFocus(viewKind: View["kind"], engagedRef: RefObject<boolean>, actionRef: RefObject<HTMLDivElement | null>) {
  useEffect(() => {
    const area = actionRef.current;
    if (!engagedRef.current || area === null) return;
    const active = document.activeElement;
    const lost = active === null || active === document.body || !active.isConnected;
    if (!lost && !area.contains(active)) return;
    const button = area.querySelector<HTMLButtonElement>("button:not(:disabled)");
    (button ?? area).focus();
  }, [viewKind, engagedRef, actionRef]);
}

/** Polls the job of one run and reports what it sees; renders nothing. */
function Follower({ run, onSeen }: { run: BuildRun; onSeen: (followed: Followed) => void }) {
  const polled = useJob(run.pollId);
  const lost = polled.error !== null;

  useEffect(() => {
    if (polled.job !== null || lost) onSeen({ attempt: run.attempt, job: polled.job, lost });
  }, [polled.job, lost, run.attempt, onSeen]);

  return null;
}
