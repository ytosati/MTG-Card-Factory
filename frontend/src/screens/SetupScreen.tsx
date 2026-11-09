// Setup screen: opens first while the reference database is not ready.
// Details: specs/spec.md, RN-28 and "Screens" (First-run setup); specs/plan.md, section 6.
import { useCallback, useEffect, useId, useRef, useState } from "react";
import type { RefObject } from "react";

import { ApiError, getSetup, startBuild } from "../api/client";
import type { JobResponse, SetupResponse } from "../api/types";
import { StatusIcon } from "../components/StatusIcon";
import { useJob } from "../hooks/useJob";

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

/** What the action area shows; a change of view may move focus (see moveFocus). */
type View =
  | { kind: "loading" }
  | { kind: "load-failed"; message: string }
  | { kind: "ready" }
  | { kind: "listing-failed"; message: string }
  | { kind: "start"; problem: Problem | null }
  | { kind: "short"; missing: string | null }
  | { kind: "starting" }
  | { kind: "building"; job: JobResponse }
  | { kind: "build-failed"; message: string };

const UNITS = ["B", "KB", "MB", "GB", "TB", "PB"];
const STEP = 1024;

const LOST_MESSAGE = "Card Factory lost track of the build. Try again to follow or restart it.";
const FAILED_MESSAGE = "The build failed. Try again.";
const RUNNING_TEXT = "Downloading the card data and building the database. The build keeps running if you close this tab.";

/** A byte count in binary units with at most one decimal, for example "77.5 KB"; null when it is not a size. */
function formatSize(bytes: number): string | null {
  if (!Number.isFinite(bytes) || bytes < 0) return null;
  let value = bytes;
  let unit = 0;
  while (value >= STEP && unit < UNITS.length - 1) {
    value /= STEP;
    unit += 1;
  }
  const digits = unit === 0 || value >= 100 ? 0 : 1;
  // Rounding can reach the next unit (1048575 bytes is "1024 KB"), so promote it.
  if (Number(value.toFixed(digits)) >= STEP && unit < UNITS.length - 1) {
    value /= STEP;
    unit += 1;
  }
  const text = value.toFixed(unit === 0 || value >= 100 ? 0 : 1).replace(/\.0$/, "");
  return `${text} ${UNITS[unit]}`;
}

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
  return { code: null, message: "Something went wrong in Card Factory. Try again." };
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
    if (seen?.lost) return { kind: "build-failed", message: LOST_MESSAGE };
    const job = seen?.job ?? run.known;
    if (job.status === "failed") return { kind: "build-failed", message: job.error?.error.message ?? FAILED_MESSAGE };
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

function statusText(view: View): string {
  switch (view.kind) {
    case "loading":
      return "Reading what the build needs…";
    case "ready":
      return "Opening Card Factory…";
    case "start":
      return view.problem === null ? "Nothing is downloaded until you start." : "";
    case "starting":
      return "Starting the build…";
    case "building":
      if (view.job.status === "queued") return "Waiting to start…";
      if (view.job.status === "done") return "Done. Opening Card Factory…";
      return RUNNING_TEXT;
    case "build-failed":
      return "The build stopped.";
    case "load-failed":
    case "listing-failed":
    case "short":
      return "";
  }
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
    <main className="screen setup">
      <h1 tabIndex={-1}>Setup</h1>
      <p className="summary">
        Card Factory checks every card it designs against a local database of existing Magic cards. Build it once
        to open the other screens.
      </p>

      {settingsToFix && (
        <div className="notice tone setup-settings">
          <StatusIcon tone="notice" />
          <p>
            Some settings need fixing. You can still build the database now.{" "}
            <a href="#/status">See them on the Status screen</a>
          </p>
        </div>
      )}

      {run !== null && <Follower key={run.attempt} run={run} onSeen={setFollowed} />}

      <section className="setup-panel" aria-label="Card database">
        {setup !== null && <SizeLedger setup={setup} lacksSpace={lacksSpace} />}

        {/* The focus target when the control that was used disappears (see useMoveFocus). */}
        <div className="setup-action" ref={actionRef} tabIndex={-1}>
          <ActionContent view={view} onStart={start} onReadAgain={readAgain} />
          <p className="hint setup-status" role="status">
            {statusText(view)}
          </p>
        </div>
      </section>
    </main>
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

interface ActionContentProps {
  view: View;
  onStart: () => void;
  onReadAgain: () => void;
}

function ActionContent({ view, onStart, onReadAgain }: ActionContentProps) {
  switch (view.kind) {
    case "loading":
    case "ready":
      return null;
    case "load-failed":
    case "listing-failed":
      return <ProblemBlock message={view.message} actionLabel="Try again" onAction={onReadAgain} />;
    case "build-failed":
      return <ProblemBlock message={view.message} actionLabel="Try again" onAction={onStart} />;
    case "start":
      return view.problem === null ? (
        <div className="setup-start">
          <button type="button" onClick={onStart}>
            Start the build
          </button>
        </div>
      ) : (
        <ProblemBlock message={view.problem.message} actionLabel="Try again" onAction={onStart} />
      );
    case "short":
      return (
        <div className="setup-start">
          <div className="setup-problem tone">
            <StatusIcon tone="danger" />
            <p>
              This drive does not have enough free space for the build.{" "}
              {view.missing === null ? "Free some space" : `Free ${view.missing} on this drive`}, then check again.
            </p>
          </div>
          <button type="button" onClick={onReadAgain}>
            Check again
          </button>
        </div>
      );
    case "starting":
      return (
        <div className="setup-start">
          <button type="button" disabled>
            Start the build
          </button>
        </div>
      );
    case "building":
      return <BuildProgress job={view.job} />;
  }
}

function ProblemBlock({ message, actionLabel, onAction }: { message: string; actionLabel: string; onAction: () => void }) {
  return (
    <div className="setup-start">
      <div className="setup-problem tone" role="alert">
        <StatusIcon tone="danger" />
        <p>{message}</p>
      </div>
      <button type="button" onClick={onAction}>
        {actionLabel}
      </button>
    </div>
  );
}

function SizeLedger({ setup, lacksSpace }: { setup: SetupResponse; lacksSpace: boolean }) {
  const download = setup.download_size === null ? null : formatSize(setup.download_size);
  const needed = setup.space_needed === null ? null : formatSize(setup.space_needed);
  const free = setup.free_space === null ? null : formatSize(setup.free_space);
  if (download === null && needed === null && free === null) return null;
  const short =
    lacksSpace || (setup.free_space !== null && setup.space_needed !== null && setup.free_space < setup.space_needed);

  return (
    <dl className="setup-ledger">
      {download !== null && <LedgerItem label="Download" size={download} />}
      {needed !== null && <LedgerItem label="Space needed" size={needed} />}
      {free !== null && <LedgerItem label="Free on this drive" size={free} short={short} />}
    </dl>
  );
}

function LedgerItem({ label, size, short = false }: { label: string; size: string; short?: boolean }) {
  return (
    <div className={short ? "setup-ledger-item setup-ledger-short" : "setup-ledger-item"}>
      <dt>{label}</dt>
      {/* The trailing space keeps the size apart from the next label when the text is copied or read as one. */}
      <dd>
        {size}
        {short && <span className="setup-ledger-note"> Not enough space</span>}{" "}
      </dd>
    </div>
  );
}

function BuildProgress({ job }: { job: JobResponse }) {
  const labelId = useId();
  const fraction = Math.min(1, Math.max(0, Number.isFinite(job.progress) ? job.progress : 0));
  const percent = Math.round(fraction * 100);

  return (
    <div className="setup-progress">
      <div className="setup-progress-head">
        <span id={labelId}>Building the card database</span>
        <span className="setup-progress-value" aria-hidden="true">
          {percent}%
        </span>
      </div>
      <div
        className="setup-progress-track"
        role="progressbar"
        aria-labelledby={labelId}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
        aria-valuetext={`${percent}%`}
      >
        <div className="setup-progress-fill" style={{ transform: `scaleX(${fraction})` }} />
      </div>
    </div>
  );
}
