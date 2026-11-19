// Concept E "Starfield" (tasks.md T251): the form's parts: a section row, a choice of one, chips and a counted text.
import { useId, type ReactNode } from "react";

import { Orbit, StarGlyph } from "./glyphs";
import styles from "./parts.module.css";

/** One row of the form: the heading and its note in the left margin, the controls on the right. */
export function Section(props: { id: string; title: string; note?: string; children: ReactNode }) {
  return (
    <section className={styles.section} aria-labelledby={props.id}>
      <div className={styles.margin}>
        <h2 id={props.id} className={styles.heading}>
          <StarGlyph size={8} className={styles.headingStar} />
          {props.title}
        </h2>
        {props.note ? <p className={styles.note}>{props.note}</p> : null}
      </div>
      <div className={styles.body}>{props.children}</div>
    </section>
  );
}

/** A choice of one, named by a heading elsewhere; the chosen option wears an orbit. */
export function Choices<T extends string>(props: {
  labelledBy: string;
  choices: { value: T; name: string; meaning?: string }[];
  value: T | null;
  onChange: (value: T) => void;
  layout?: "columns" | "inline";
  describedBy?: string;
}) {
  const name = useId();
  return (
    <fieldset className={styles.choices} data-layout={props.layout ?? "columns"} aria-labelledby={props.labelledBy} aria-describedby={props.describedBy}>
      {props.choices.map((choice) => {
        const checked = props.value === choice.value;
        return (
          <label key={choice.value} className={styles.choice} data-checked={checked ? "true" : "false"}>
            <input className={styles.srOnly} type="radio" name={name} value={choice.value} checked={checked} onChange={() => props.onChange(choice.value)} />
            <span className={styles.choiceHead}>
              <Orbit checked={checked} className={styles.orbit} />
              <span className={styles.choiceName}>{choice.name}</span>
            </span>
            {choice.meaning ? <span className={styles.meaning}>{choice.meaning}</span> : null}
          </label>
        );
      })}
    </fieldset>
  );
}

/** A choice of several, as small square chips. */
export function Chips(props: { legend: string; options: string[]; value: string[]; onChange: (value: string[]) => void }) {
  return (
    <fieldset className={styles.chipSet}>
      <legend className={styles.label}>{props.legend}</legend>
      <div className={styles.chips}>
        {props.options.map((option) => {
          const checked = props.value.includes(option);
          return (
            <label key={option} className={styles.chip}>
              <input
                className={styles.srOnly}
                type="checkbox"
                checked={checked}
                onChange={(event) =>
                  props.onChange(event.target.checked ? [...props.value, option] : props.value.filter((entry) => entry !== option))
                }
              />
              <span className={styles.chipFace}>{option}</span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

/** The count under a limited text, which turns to the violet text colour near the limit. */
export function Count({ id, count, max, text }: { id: string; count: number; max: number; text: string }) {
  return (
    <span id={id} className={styles.count} data-near={count > max * 0.9 ? "true" : "false"}>
      {text}
    </span>
  );
}

/** A labelled field with a hint, laid out as a small column. */
export function Field(props: { label: string; htmlFor: string; hint?: string; hintId?: string; children: ReactNode; wide?: boolean }) {
  return (
    <div className={styles.field} data-wide={props.wide ? "true" : "false"}>
      <label className={styles.label} htmlFor={props.htmlFor}>
        {props.label}
      </label>
      {props.children}
      {props.hint ? (
        <p id={props.hintId} className={styles.hint}>
          {props.hint}
        </p>
      ) : null}
    </div>
  );
}

export { styles as parts };
