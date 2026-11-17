// Request screen view: idea or theme, color identity and power level, the generate action and its progress.
// Details: specs/spec.md, RN-11, RN-49, CA-26, CA-80 and "Screens" (Request).
import { useId } from "react";
import type { FormEvent, ReactNode, RefObject } from "react";

import type { ColorLetter, JobResponse, PowerLevel } from "../../api/types";
import { cx } from "../../components/classNames";
import { ProgressBar, progressOf, progressStyles } from "../../components/ProgressBar";
import { Screen, screenStyles } from "../../components/Screen";
import { StatusIcon, toneStyles } from "../../components/StatusIcon";
import { requestCopy as copy } from "./copy";
import type { RequestField } from "./copy";
import styles from "./RequestView.module.css";

export type RequestFieldErrors = Partial<Record<RequestField, string>>;

/** A failure of the generation, with the setting to check when there is one. */
export interface RequestProblem {
  message: string;
  setting: string | null;
}

/** See spec RN-11: counted in Unicode characters, as the backend counts them. */
export const IDEA_MAX_CHARACTERS = 1_000;

export const FIELD_ORDER: RequestField[] = ["idea", "color_identity", "power_level"];

interface RequestViewProps {
  idea: string;
  colors: ColorLetter[];
  colorless: boolean;
  power: PowerLevel | null;
  errors: RequestFieldErrors;
  /** The named fields were refused by the server, not found missing here. */
  refusedByServer: boolean;
  /** The request is being sent or followed; the fields are locked. */
  busy: boolean;
  sending: boolean;
  /** The progress of the generation being followed, or null. */
  progress: ReactNode;
  failure: RequestProblem | null;
  formRef?: RefObject<HTMLFormElement | null> | undefined;
  onIdeaChange: (idea: string) => void;
  onToggleColor: (letter: ColorLetter) => void;
  onToggleColorless: () => void;
  onPowerChange: (power: PowerLevel) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}

export function characterCount(text: string): number {
  return [...text].length;
}

/** The Request screen form. Nothing is chosen when it opens (see spec CA-26). */
export function RequestView(props: RequestViewProps) {
  const { idea, colors, colorless, power, errors, refusedByServer, busy, sending, progress, failure, formRef } = props;
  const ids = useId();
  const fieldId = (name: RequestField) => `${ids}-${name}`;
  const ideaLength = characterCount(idea);
  const named = FIELD_ORDER.filter((name) => errors[name] !== undefined);
  const describedBy = (name: RequestField, ...extra: string[]) =>
    [...extra, ...(errors[name] !== undefined ? [`${fieldId(name)}-error`] : [])].join(" ") || undefined;
  const sectionClass = (name: RequestField) => cx(styles.section, errors[name] !== undefined && styles.sectionInvalid);

  return (
    <Screen>
      <h1 tabIndex={-1}>{copy.title}</h1>
      <p className={screenStyles.summary}>{copy.summary}</p>
      <form ref={formRef} className={styles.panel} noValidate onSubmit={props.onSubmit}>
        <fieldset className={styles.fields} disabled={busy}>
          <div className={sectionClass("idea")}>
            <label className={styles.label} htmlFor={fieldId("idea")}>
              {copy.fieldLabels.idea}
            </label>
            <textarea
              id={fieldId("idea")}
              data-field="idea"
              className={styles.idea}
              rows={4}
              value={idea}
              aria-invalid={errors.idea !== undefined || undefined}
              aria-describedby={describedBy("idea", `${fieldId("idea")}-count`)}
              // No maxLength: the browser counts UTF-16 units, so it would cut ideas the backend accepts.
              onChange={(event) => props.onIdeaChange(event.target.value)}
            />
            <div className={styles.fieldFoot}>
              <FieldError id={`${fieldId("idea")}-error`} message={errors.idea} />
              <p
                id={`${fieldId("idea")}-count`}
                className={cx(styles.count, ideaLength > IDEA_MAX_CHARACTERS && styles.countOver)}
              >
                {copy.characterCount(ideaLength, IDEA_MAX_CHARACTERS)}
              </p>
            </div>
          </div>

          <fieldset className={sectionClass("color_identity")} aria-describedby={describedBy("color_identity")}>
            <legend className={styles.label}>{copy.fieldLabels.color_identity}</legend>
            <div className={styles.choiceRow}>
              {copy.colors.map((color, index) => (
                <label key={color.letter} className={styles.choice}>
                  <input
                    type="checkbox"
                    data-field={index === 0 ? "color_identity" : undefined}
                    checked={colors.includes(color.letter)}
                    onChange={() => props.onToggleColor(color.letter)}
                  />
                  <span className={cx(styles.swatch, styles[`swatch-${color.letter.toLowerCase()}`])} aria-hidden="true" />
                  {color.name}
                </label>
              ))}
              <span className={styles.or} aria-hidden="true">
                {copy.or}
              </span>
              <label className={styles.choice}>
                <input type="checkbox" checked={colorless} onChange={props.onToggleColorless} />
                <span className={cx(styles.swatch, styles["swatch-c"])} aria-hidden="true" />
                {copy.colorless}
              </label>
            </div>
            <FieldError id={`${fieldId("color_identity")}-error`} message={errors.color_identity} />
          </fieldset>

          <fieldset className={sectionClass("power_level")} aria-describedby={describedBy("power_level")}>
            <legend className={styles.label}>{copy.fieldLabels.power_level}</legend>
            <div className={styles.choiceRow}>
              {copy.powerLevels.map((level, index) => (
                <label key={level.value} className={styles.choice}>
                  <input
                    type="radio"
                    name={`${ids}-power`}
                    value={level.value}
                    data-field={index === 0 ? "power_level" : undefined}
                    checked={power === level.value}
                    onChange={() => props.onPowerChange(level.value)}
                  />
                  {level.name}
                </label>
              ))}
            </div>
            <FieldError id={`${fieldId("power_level")}-error`} message={errors.power_level} />
          </fieldset>
        </fieldset>

        <div className={styles.action}>
          <div className={styles.start}>
            <button type="submit" aria-disabled={busy || undefined}>
              {copy.generate}
            </button>
            {sending && <p role="status">{copy.sending}</p>}
            {progress}
          </div>
          {named.length > 0 && (
            <div className={cx(styles.problem, toneStyles.tone)} role="alert">
              <StatusIcon tone="danger" />
              <p>
                {refusedByServer ? copy.refusedPrefix : copy.missingPrefix}
                {named.map((name) => copy.fieldLabels[name]).join(", ")}.
              </p>
            </div>
          )}
          {failure !== null && <FailureNotice problem={failure} />}
        </div>
      </form>
    </Screen>
  );
}

function FieldError({ id, message }: { id: string; message: string | undefined }) {
  if (message === undefined) return null;
  return (
    <p id={id} className={styles.fieldError}>
      {message}
    </p>
  );
}

function FailureNotice({ problem }: { problem: RequestProblem }) {
  return (
    <div className={cx(styles.problem, toneStyles.tone)} role="alert">
      <StatusIcon tone="danger" />
      <div className={toneStyles.toneBody}>
        <p>{problem.message}</p>
        {problem.setting !== null && (
          <p>
            {copy.settingLabel} <code>{problem.setting}</code>
            {copy.checkOnStatusBefore} <a href="#/status">{copy.statusLink}</a> {copy.checkOnStatusAfter}
          </p>
        )}
      </div>
    </div>
  );
}

/** The state of the generation job being followed: waiting, or running with its progress. */
export function GenerationProgress({ job }: { job: JobResponse | null }) {
  const labelId = useId();
  const running = job !== null && job.status === "running";
  const { fraction, percent } = running ? progressOf(job.progress) : { fraction: 0, percent: 0 };
  return (
    <div className={styles.progress}>
      <p role="status" id={labelId} className={progressStyles.head}>
        <span>{job?.status === "queued" ? copy.waiting : copy.generating}</span>
        {running && percent > 0 && <span className={progressStyles.value}> {percent}%</span>}
      </p>
      {running && <ProgressBar labelId={labelId} fraction={fraction} percent={percent} />}
    </div>
  );
}
