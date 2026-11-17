// Request screen view: the generation fields, the generate action and its progress.
// Details: specs/spec.md, RN-11, RN-49, RN-53 to RN-56, CA-26, CA-80 and "Screens" (Request).
import { useId, useRef, useState } from "react";
import type { FormEvent, ReactNode, RefObject } from "react";

import type { ColorLetter, JobResponse, PowerLevel } from "../../api/types";
import { cx } from "../../components/classNames";
import { ProgressBar, progressOf, progressStyles } from "../../components/ProgressBar";
import { Screen, screenStyles } from "../../components/Screen";
import { StatusIcon, toneStyles } from "../../components/StatusIcon";
import { StepIndicator } from "../../components/StepIndicator";
import { requestCopy as copy } from "./copy";
import type { CardLanguage, GenerationEffort, GenerationStep, RequestField } from "./copy";
import styles from "./RequestView.module.css";

export type RequestFieldErrors = Partial<Record<RequestField, string>>;

/** A failure of the generation, with the setting to check when there is one. */
export interface RequestProblem {
  message: string;
  setting: string | null;
  /** The provider refused the request; the person is offered to edit it (RN-56). */
  refused?: boolean | undefined;
}

/** The advanced options as typed; an empty value is no choice (RN-54). */
export interface AdvancedOptions {
  types: string[];
  supertypes: string[];
  subtypes: string;
  manaValue: string;
  power: string;
  toughness: string;
  startingLoyalty: string;
}

export const NO_ADVANCED_OPTIONS: AdvancedOptions = {
  types: [],
  supertypes: [],
  subtypes: "",
  manaValue: "",
  power: "",
  toughness: "",
  startingLoyalty: "",
};

/** The fields the request does not send yet: shown only when given (wired by later tasks). */
export interface GenerationControls {
  effort: GenerationEffort | null;
  language: CardLanguage;
  advanced: AdvancedOptions;
  onEffortChange: (effort: GenerationEffort) => void;
  onLanguageChange: (language: CardLanguage) => void;
  onAdvancedChange: (advanced: AdvancedOptions) => void;
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
  /** Generation effort, card language and advanced options; left out of the screen when absent. */
  controls?: GenerationControls | undefined;
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
  const { idea, colors, colorless, power, errors, refusedByServer, busy, sending, progress, failure, controls, formRef } =
    props;
  const ids = useId();
  const ideaRef = useRef<HTMLTextAreaElement>(null);
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
              ref={ideaRef}
              id={fieldId("idea")}
              data-field="idea"
              className={styles.idea}
              rows={4}
              value={idea}
              disabled={busy}
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

          <fieldset
            className={sectionClass("color_identity")}
            aria-describedby={describedBy("color_identity", `${fieldId("color_identity")}-hint`)}
          >
            <legend className={styles.label}>{copy.fieldLabels.color_identity}</legend>
            <p id={`${fieldId("color_identity")}-hint`} className={styles.hint}>
              {copy.colorHint}
            </p>
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
            <div className={styles.optionGrid}>
              {copy.powerLevels.map((level, index) => (
                <div key={level.value} className={styles.option}>
                  <label className={styles.choice}>
                    <input
                      type="radio"
                      name={`${ids}-power`}
                      value={level.value}
                      data-field={index === 0 ? "power_level" : undefined}
                      checked={power === level.value}
                      aria-describedby={`${ids}-power-${level.value}`}
                      onChange={() => props.onPowerChange(level.value)}
                    />
                    {level.name}
                  </label>
                  <p id={`${ids}-power-${level.value}`} className={styles.meaning}>
                    {level.meaning}
                  </p>
                </div>
              ))}
            </div>
            <FieldError id={`${fieldId("power_level")}-error`} message={errors.power_level} />
          </fieldset>

          {controls !== undefined && <EffortAndLanguage controls={controls} />}
        </fieldset>

        {controls !== undefined && <AdvancedSection controls={controls} locked={busy} />}

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
          {failure !== null && <FailureNotice problem={failure} onEdit={() => ideaRef.current?.focus()} />}
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

function FailureNotice({ problem, onEdit }: { problem: RequestProblem; onEdit: () => void }) {
  return (
    <div className={cx(styles.problem, toneStyles.tone)} role="alert">
      <StatusIcon tone="danger" />
      <div className={toneStyles.toneBody}>
        <p>{problem.message}</p>
        {problem.refused === true && (
          <p>
            <button type="button" className={styles.inlineAction} onClick={onEdit}>
              {copy.editRequest}
            </button>
          </p>
        )}
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

/** Generation effort and card language, each choice with its meaning (RN-53, RN-30). */
function EffortAndLanguage({ controls }: { controls: GenerationControls }) {
  const ids = useId();
  return (
    <>
      <fieldset className={styles.section}>
        <legend className={styles.label}>{copy.effortLabel}</legend>
        <div className={styles.optionGrid}>
          {copy.efforts.map((effort) => (
            <div key={effort.value} className={styles.option}>
              <label className={styles.choice}>
                <input
                  type="radio"
                  name={`${ids}-effort`}
                  value={effort.value}
                  checked={controls.effort === effort.value}
                  aria-describedby={`${ids}-effort-${effort.value}`}
                  onChange={() => controls.onEffortChange(effort.value)}
                />
                {effort.name}
              </label>
              <p id={`${ids}-effort-${effort.value}`} className={styles.meaning}>
                {effort.meaning}
              </p>
            </div>
          ))}
        </div>
      </fieldset>

      <fieldset className={styles.section} aria-describedby={`${ids}-language-hint`}>
        <legend className={styles.label}>{copy.languageLabel}</legend>
        <p id={`${ids}-language-hint`} className={styles.hint}>
          {copy.languageHint}
        </p>
        <div className={styles.choiceRow}>
          {copy.languages.map((language) => (
            <label key={language.value} className={styles.choice}>
              <input
                type="radio"
                name={`${ids}-language`}
                value={language.value}
                checked={controls.language === language.value}
                onChange={() => controls.onLanguageChange(language.value)}
              />
              {language.name}
            </label>
          ))}
        </div>
      </fieldset>
    </>
  );
}

/** The advanced options, hidden until requested; the toggle stays usable while a generation runs (RN-54). */
function AdvancedSection({ controls, locked }: { controls: GenerationControls; locked: boolean }) {
  const ids = useId();
  const [open, setOpen] = useState(false);
  const { advanced } = controls;
  const change = (next: Partial<AdvancedOptions>) => controls.onAdvancedChange({ ...advanced, ...next });
  const toggled = (list: string[], item: string) =>
    list.includes(item) ? list.filter((entry) => entry !== item) : [...list, item];

  return (
    <div className={styles.advanced}>
      <button
        type="button"
        className={styles.disclosure}
        aria-expanded={open}
        aria-controls={`${ids}-panel`}
        onClick={() => setOpen((previous) => !previous)}
      >
        <span className={styles.chevron} aria-hidden="true" />
        {copy.advancedToggle}
      </button>
      {open && (
        <fieldset id={`${ids}-panel`} className={styles.advancedPanel} disabled={locked}>
          <p className={styles.hint}>{copy.advancedHint}</p>
          <ChoiceSet
            label={copy.cardTypesLabel}
            options={copy.cardTypes}
            chosen={advanced.types}
            onToggle={(item) => change({ types: toggled(advanced.types, item) })}
          />
          <ChoiceSet
            label={copy.supertypesLabel}
            options={copy.supertypes}
            chosen={advanced.supertypes}
            onToggle={(item) => change({ supertypes: toggled(advanced.supertypes, item) })}
          />
          <div className={styles.inputGrid}>
            <TextField
              className={styles.wide}
              label={copy.subtypesLabel}
              hint={copy.subtypesHint}
              value={advanced.subtypes}
              onChange={(subtypes) => change({ subtypes })}
            />
            <TextField
              label={copy.manaValueLabel}
              hint={copy.manaValueHint}
              number={{ min: 0, max: 16 }}
              value={advanced.manaValue}
              onChange={(manaValue) => change({ manaValue })}
            />
            <TextField
              label={copy.loyaltyLabel}
              hint={copy.loyaltyHint}
              number={{ min: 1, max: 99 }}
              value={advanced.startingLoyalty}
              onChange={(startingLoyalty) => change({ startingLoyalty })}
            />
            <TextField
              label={copy.powerLabel}
              hint={copy.powerToughnessHint}
              number={{ min: 0, max: 99 }}
              value={advanced.power}
              onChange={(value) => change({ power: value })}
            />
            <TextField
              label={copy.toughnessLabel}
              hint={copy.powerToughnessHint}
              number={{ min: 0, max: 99 }}
              value={advanced.toughness}
              onChange={(toughness) => change({ toughness })}
            />
          </div>
        </fieldset>
      )}
    </div>
  );
}

interface ChoiceSetProps {
  label: string;
  options: string[];
  chosen: string[];
  onToggle: (item: string) => void;
}

function ChoiceSet({ label, options, chosen, onToggle }: ChoiceSetProps) {
  return (
    <fieldset className={styles.subsection}>
      <legend className={styles.label}>{label}</legend>
      <div className={styles.choiceRow}>
        {options.map((option) => (
          <label key={option} className={styles.choice}>
            <input type="checkbox" checked={chosen.includes(option)} onChange={() => onToggle(option)} />
            {option}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

interface TextFieldProps {
  label: string;
  hint: string;
  value: string;
  onChange: (value: string) => void;
  /** A whole number within these bounds; absent for free text. */
  number?: { min: number; max: number } | undefined;
  className?: string | undefined;
}

function TextField({ label, hint, value, onChange, number, className }: TextFieldProps) {
  const id = useId();
  return (
    <div className={cx(styles.inputField, className)}>
      <label className={styles.label} htmlFor={id}>
        {label}
      </label>
      <input
        id={id}
        className={styles.input}
        type={number !== undefined ? "number" : "text"}
        inputMode={number !== undefined ? "numeric" : undefined}
        min={number?.min}
        max={number?.max}
        step={number !== undefined ? 1 : undefined}
        value={value}
        aria-describedby={`${id}-hint`}
        onChange={(event) => onChange(event.target.value)}
      />
      <p id={`${id}-hint`} className={styles.hint}>
        {hint}
      </p>
    </div>
  );
}

/** The steps of a running generation, the running one marked; art is listed only when it was requested (RN-55). */
export function GenerationSteps({ step, withArt }: { step: GenerationStep; withArt: boolean }) {
  const steps = copy.steps.filter((entry) => withArt || entry.value !== "art");
  return (
    <div className={styles.progress}>
      <p role="status" className={styles.stepsHead}>
        {copy.generating}
      </p>
      <StepIndicator
        label={copy.stepsLabel}
        steps={steps.map((entry) => entry.name)}
        current={steps.findIndex((entry) => entry.value === step)}
      />
    </div>
  );
}
