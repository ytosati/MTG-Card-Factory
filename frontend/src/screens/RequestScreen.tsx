// Request screen: idea or theme, color identity and power level, then the generation job until it ends.
// Details: specs/spec.md, RN-11, RN-49, CA-26, CA-80 and "Screens" (Request); specs/plan.md, section 6.
import { useEffect, useId, useRef, useState } from "react";
import type { FormEvent } from "react";

import { ApiError, startGeneration } from "../api/client";
import type { ColorLetter, GenerationJobResponse, GenerationResult, JobResponse, PowerLevel } from "../api/types";
import { StatusIcon } from "../components/StatusIcon";
import { useJob } from "../hooks/useJob";

interface RequestScreenProps {
  /** Called once with the result of a generation job that ended done. */
  onGenerated: (result: GenerationResult) => void;
}

type FieldName = "idea" | "color_identity" | "power_level";

type FieldErrors = Partial<Record<FieldName, string>>;

interface Problem {
  message: string;
  setting: string | null;
}

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

/** See spec RN-11: counted in Unicode characters, as the backend counts them. */
const IDEA_MAX_CHARACTERS = 1_000;

const FIELD_ORDER: FieldName[] = ["idea", "color_identity", "power_level"];

const FIELD_LABELS: Record<FieldName, string> = {
  idea: "Idea or theme",
  color_identity: "Color identity",
  power_level: "Power level",
};

const COLORS: { letter: ColorLetter; name: string }[] = [
  { letter: "W", name: "White" },
  { letter: "U", name: "Blue" },
  { letter: "B", name: "Black" },
  { letter: "R", name: "Red" },
  { letter: "G", name: "Green" },
];

const POWER_LEVELS: { value: PowerLevel; name: string }[] = [
  { value: "casual", name: "Casual" },
  { value: "medium", name: "Medium" },
  { value: "strong", name: "Strong" },
];

const COUNT_FORMAT = new Intl.NumberFormat("en-US");

const FAILED_MESSAGE = "The generation failed. Try again.";
const LOST_MESSAGE = "Card Factory lost track of the generation. Try again.";
const UNREADABLE_RESULT = "The generation finished, but Card Factory could not read which card it saved. Try again.";
const UNKNOWN_FAILURE = "Something went wrong in Card Factory. Try again.";

function characterCount(text: string): number {
  return [...text].length;
}

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
  return { message: UNKNOWN_FAILURE, setting: null };
}

/** The Request screen. Nothing is chosen when it opens (see spec CA-26). */
export function RequestScreen({ onGenerated }: RequestScreenProps) {
  const ids = useId();
  const fieldId = (name: FieldName) => `${ids}-${name}`;
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

  const clearError = (name: FieldName) =>
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
    if (idea.trim() === "") found.idea = "Write the idea or theme of the card.";
    else if (ideaLength > IDEA_MAX_CHARACTERS)
      found.idea = `Shorten the idea to ${COUNT_FORMAT.format(IDEA_MAX_CHARACTERS)} characters or fewer.`;
    if (colors.length === 0 && !colorless) found.color_identity = "Choose one or more colors, or Colorless.";
    if (power === null) found.power_level = "Choose a power level.";
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
        color_identity: colorless ? [] : COLORS.map((color) => color.letter).filter((letter) => colors.includes(letter)),
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

  const named = FIELD_ORDER.filter((name) => errors[name] !== undefined);
  const describedBy = (name: FieldName, ...extra: string[]) =>
    [...extra, ...(errors[name] !== undefined ? [`${fieldId(name)}-error`] : [])].join(" ") || undefined;

  return (
    <main className="screen">
      <h1 tabIndex={-1}>Request</h1>
      <p className="summary">Describe the card, choose its color identity and power level, then generate it.</p>
      <form ref={formRef} className="request-panel" noValidate onSubmit={submit}>
        <fieldset className="request-fields" disabled={busy}>
          <div className={`request-section${errors.idea !== undefined ? " request-section-invalid" : ""}`}>
            <label className="request-label" htmlFor={fieldId("idea")}>
              {FIELD_LABELS.idea}
            </label>
            <textarea
              id={fieldId("idea")}
              data-field="idea"
              className="request-idea"
              rows={4}
              value={idea}
              aria-invalid={errors.idea !== undefined || undefined}
              aria-describedby={describedBy("idea", `${fieldId("idea")}-count`)}
              // No maxLength: the browser counts UTF-16 units, so it would cut ideas the backend accepts.
              onChange={(event) => {
                setIdea(event.target.value);
                clearError("idea");
              }}
            />
            <div className="request-field-foot">
              <FieldError id={`${fieldId("idea")}-error`} message={errors.idea} />
              <p
                id={`${fieldId("idea")}-count`}
                className={`request-count${ideaLength > IDEA_MAX_CHARACTERS ? " request-count-over" : ""}`}
              >
                {COUNT_FORMAT.format(ideaLength)} / {COUNT_FORMAT.format(IDEA_MAX_CHARACTERS)} characters
              </p>
            </div>
          </div>

          <fieldset
            className={`request-section${errors.color_identity !== undefined ? " request-section-invalid" : ""}`}
            aria-describedby={describedBy("color_identity")}
          >
            <legend className="request-label">{FIELD_LABELS.color_identity}</legend>
            <div className="choice-row">
              {COLORS.map((color, index) => (
                <label key={color.letter} className="choice">
                  <input
                    type="checkbox"
                    data-field={index === 0 ? "color_identity" : undefined}
                    checked={colors.includes(color.letter)}
                    onChange={() => toggleColor(color.letter)}
                  />
                  <span className={`choice-swatch swatch-${color.letter.toLowerCase()}`} aria-hidden="true" />
                  {color.name}
                </label>
              ))}
              <span className="choice-or" aria-hidden="true">
                or
              </span>
              <label className="choice">
                <input type="checkbox" checked={colorless} onChange={toggleColorless} />
                <span className="choice-swatch swatch-c" aria-hidden="true" />
                Colorless
              </label>
            </div>
            <FieldError id={`${fieldId("color_identity")}-error`} message={errors.color_identity} />
          </fieldset>

          <fieldset
            className={`request-section${errors.power_level !== undefined ? " request-section-invalid" : ""}`}
            aria-describedby={describedBy("power_level")}
          >
            <legend className="request-label">{FIELD_LABELS.power_level}</legend>
            <div className="choice-row">
              {POWER_LEVELS.map((level, index) => (
                <label key={level.value} className="choice">
                  <input
                    type="radio"
                    name={`${ids}-power`}
                    value={level.value}
                    data-field={index === 0 ? "power_level" : undefined}
                    checked={power === level.value}
                    onChange={() => {
                      setPower(level.value);
                      clearError("power_level");
                    }}
                  />
                  {level.name}
                </label>
              ))}
            </div>
            <FieldError id={`${fieldId("power_level")}-error`} message={errors.power_level} />
          </fieldset>
        </fieldset>

        <div className="request-action">
          <div className="request-start">
            <button type="submit" aria-disabled={busy || undefined}>
              Generate card
            </button>
            {phase.kind === "sending" && <p role="status">Sending the request…</p>}
            {phase.kind === "following" && (
              <GenerationFollower key={phase.run.attempt} jobId={phase.run.jobId} onDone={finish} onFailed={fail} />
            )}
          </div>
          {named.length > 0 && (
            <div className="request-problem tone" role="alert">
              <StatusIcon tone="danger" />
              <p>
                {refusedByServer ? "Card Factory refused the request. Check: " : "Fill in before generating: "}
                {named.map((name) => FIELD_LABELS[name]).join(", ")}.
              </p>
            </div>
          )}
          {phase.kind === "failed" && <FailureNotice problem={phase.problem} />}
        </div>
      </form>
    </main>
  );
}

function FieldError({ id, message }: { id: string; message: string | undefined }) {
  if (message === undefined) return null;
  return (
    <p id={id} className="request-field-error">
      {message}
    </p>
  );
}

function FailureNotice({ problem }: { problem: Problem }) {
  return (
    <div className="request-problem tone" role="alert">
      <StatusIcon tone="danger" />
      <div className="tone-body">
        <p>{problem.message}</p>
        {problem.setting !== null && (
          <p>
            Setting: <code>{problem.setting}</code>. Check it on the <a href="#/status">Status</a> screen.
          </p>
        )}
      </div>
    </div>
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
  const labelId = useId();

  useEffect(() => {
    if (reported.current) return;
    if (error !== null) {
      reported.current = true;
      onFailed({ message: LOST_MESSAGE, setting: null });
      return;
    }
    if (job === null) return;
    if (job.status === "failed") {
      reported.current = true;
      const envelope = job.error?.error;
      onFailed({ message: envelope?.message ?? FAILED_MESSAGE, setting: envelope?.setting ?? null });
      return;
    }
    if (job.status !== "done") return;
    reported.current = true;
    const result = generationResultOf(job);
    if (result === null) onFailed({ message: UNREADABLE_RESULT, setting: null });
    else onDone(result);
  }, [job, error, onDone, onFailed]);

  const running = job !== null && job.status === "running";
  const fraction = running ? Math.min(1, Math.max(0, Number.isFinite(job.progress) ? job.progress : 0)) : 0;
  const percent = Math.round(fraction * 100);
  return (
    <div className="request-progress">
      <p role="status" id={labelId} className="setup-progress-head">
        <span>{job?.status === "queued" ? "Waiting to start…" : "Generating the card…"}</span>
        {running && percent > 0 && <span className="setup-progress-value"> {percent}%</span>}
      </p>
      {running && (
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
      )}
    </div>
  );
}
