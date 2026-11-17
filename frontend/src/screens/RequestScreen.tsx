// Request screen container: checks the request, sends it, follows the generation job until it ends.
// Details: specs/spec.md, RN-11, RN-49, CA-26, CA-80 and "Screens" (Request); specs/plan.md, section 6.
import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";

import { ApiError, startGeneration } from "../api/client";
import type { ColorLetter, GenerationJobResponse, GenerationResult, JobResponse, PowerLevel } from "../api/types";
import { useJob } from "../hooks/useJob";
import { requestCopy } from "./request/copy";
import { FIELD_ORDER, GenerationProgress, IDEA_MAX_CHARACTERS, RequestView, characterCount } from "./request/RequestView";
import type { RequestFieldErrors, RequestProblem } from "./request/RequestView";

interface RequestScreenProps {
  /** Called once with the result of a generation job that ended done. */
  onGenerated: (result: GenerationResult) => void;
}

type FieldErrors = RequestFieldErrors;

type Problem = RequestProblem;

/** One generation followed on this screen; a new attempt remounts its follower, even when the job id repeats. */
interface Run {
  attempt: number;
  jobId: string;
}

type Phase =
  | { kind: "idle" }
  | { kind: "sending" }
  | { kind: "following"; run: Run }
  | { kind: "failed"; problem: Problem }
  | { kind: "finished" };

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

/** The result of a done generation job, or null when it does not have the contract's shape. */
function generationResultOf(job: JobResponse): GenerationResult | null {
  const result = job.result;
  if (!isRecord(result) || typeof result.card !== "string" || result.card === "") return null;
  const failure = result.revision_failure;
  if (failure === null || failure === undefined) return { card: result.card, revision_failure: null };
  if (!isRecord(failure) || typeof failure.code !== "string" || typeof failure.message !== "string") return null;
  return { card: result.card, revision_failure: { code: failure.code, message: failure.message } };
}

function problemOf(reason: unknown): Problem {
  if (reason instanceof ApiError) return { message: reason.message, setting: reason.setting };
  if (reason instanceof Error) return { message: reason.message, setting: null };
  return { message: requestCopy.unknownFailure, setting: null };
}

/** The Request screen. Nothing is chosen when it opens (see spec CA-26). */
export function RequestScreen({ onGenerated }: RequestScreenProps) {
  const [idea, setIdea] = useState("");
  const [colors, setColors] = useState<ColorLetter[]>([]);
  const [colorless, setColorless] = useState(false);
  const [power, setPower] = useState<PowerLevel | null>(null);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [refusedByServer, setRefusedByServer] = useState(false);
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });
  const attempts = useRef(0);
  const formRef = useRef<HTMLFormElement>(null);

  const busy = phase.kind === "sending" || phase.kind === "following";
  const ideaLength = characterCount(idea);

  const clearError = (name: keyof FieldErrors) =>
    setErrors((previous) => {
      if (previous[name] === undefined) return previous;
      const next = { ...previous };
      delete next[name];
      return next;
    });

  const toggleColor = (letter: ColorLetter) => {
    setColorless(false);
    setColors((previous) => (previous.includes(letter) ? previous.filter((item) => item !== letter) : [...previous, letter]));
    clearError("color_identity");
  };

  const toggleColorless = () => {
    setColorless((previous) => !previous);
    setColors([]);
    clearError("color_identity");
  };

  function validate(): FieldErrors {
    const found: FieldErrors = {};
    if (idea.trim() === "") found.idea = requestCopy.ideaMissing;
    else if (ideaLength > IDEA_MAX_CHARACTERS) found.idea = requestCopy.ideaTooLong(IDEA_MAX_CHARACTERS);
    if (colors.length === 0 && !colorless) found.color_identity = requestCopy.colorMissing;
    if (power === null) found.power_level = requestCopy.powerMissing;
    return found;
  }

  function showErrors(found: FieldErrors, fromServer: boolean) {
    setErrors(found);
    setRefusedByServer(fromServer);
    const first = FIELD_ORDER.find((name) => found[name] !== undefined);
    if (first === undefined) return;
    // The first named field takes focus, so the person lands where the fix is.
    const target =
      formRef.current?.querySelector<HTMLElement>(`[data-field="${first}"]:not(:disabled)`) ?? null;
    target?.focus();
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    const found = validate();
    if (Object.keys(found).length > 0 || power === null) {
      showErrors(found, false);
      return;
    }
    showErrors({}, false);
    setPhase({ kind: "sending" });
    try {
      const job: GenerationJobResponse = await startGeneration({
        idea,
        color_identity: colorless
          ? []
          : requestCopy.colors.map((color) => color.letter).filter((letter) => colors.includes(letter)),
        power_level: power,
      });
      attempts.current += 1;
      setPhase({ kind: "following", run: { attempt: attempts.current, jobId: job.id } });
    } catch (reason: unknown) {
      if (reason instanceof ApiError && reason.code === "validation" && reason.fields !== null) {
        const named: FieldErrors = {};
        for (const name of FIELD_ORDER) {
          const messages = reason.fields[name];
          if (messages !== undefined && messages.length > 0) named[name] = messages.join(" ");
        }
        if (Object.keys(named).length > 0) {
          setPhase({ kind: "idle" });
          showErrors(named, true);
          return;
        }
      }
      setPhase({ kind: "failed", problem: problemOf(reason) });
    }
  }

  const finish = (result: GenerationResult) => {
    setPhase({ kind: "finished" });
    onGenerated(result);
  };

  const fail = (problem: Problem) => setPhase({ kind: "failed", problem });

  return (
    <RequestView
      idea={idea}
      colors={colors}
      colorless={colorless}
      power={power}
      errors={errors}
      refusedByServer={refusedByServer}
      busy={busy}
      sending={phase.kind === "sending"}
      progress={
        phase.kind === "following" ? (
          <GenerationFollower key={phase.run.attempt} jobId={phase.run.jobId} onDone={finish} onFailed={fail} />
        ) : null
      }
      failure={phase.kind === "failed" ? phase.problem : null}
      formRef={formRef}
      onIdeaChange={(value) => {
        setIdea(value);
        clearError("idea");
      }}
      onToggleColor={toggleColor}
      onToggleColorless={toggleColorless}
      onPowerChange={(value) => {
        setPower(value);
        clearError("power_level");
      }}
      onSubmit={submit}
    />
  );
}

interface FollowerProps {
  jobId: string;
  onDone: (result: GenerationResult) => void;
  onFailed: (problem: Problem) => void;
}

/** Follows one generation job and reports its end once. */
function GenerationFollower({ jobId, onDone, onFailed }: FollowerProps) {
  const { job, error } = useJob(jobId);
  const reported = useRef(false);

  useEffect(() => {
    if (reported.current) return;
    if (error !== null) {
      reported.current = true;
      onFailed({ message: requestCopy.lost, setting: null });
      return;
    }
    if (job === null) return;
    if (job.status === "failed") {
      reported.current = true;
      const envelope = job.error?.error;
      onFailed({ message: envelope?.message ?? requestCopy.failed, setting: envelope?.setting ?? null });
      return;
    }
    if (job.status !== "done") return;
    reported.current = true;
    const result = generationResultOf(job);
    if (result === null) onFailed({ message: requestCopy.unreadableResult, setting: null });
    else onDone(result);
  }, [job, error, onDone, onFailed]);

  return <GenerationProgress job={job} />;
}
