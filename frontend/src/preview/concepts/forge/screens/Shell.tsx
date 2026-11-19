// Concept D "Forge" (tasks.md T251): the page of every screen, its header, and the shared engraved controls.
import { useId, type ReactNode } from "react";

import { SoundToggle } from "../sound/SoundToggle";
import { GearMark } from "./ornaments";
import styles from "./shell.module.css";

export type Place = "Request" | "Library" | "Status";

/** The dark ground, the header with the wordmark, the places and the sound switch. */
export function Shell({ current, children }: { current: Place; children: ReactNode }) {
  return (
    <div className={styles.root}>
      <header className={styles.bar}>
        <span className={styles.brand}>
          <GearMark className={styles.brandMark} />
          Card Factory
        </span>
        <nav aria-label="Main" className={styles.navWrap}>
          <ul className={styles.nav}>
            {(["Request", "Library", "Status"] as const).map((item) => (
              <li key={item}>
                <span className={styles.navItem} aria-current={item === current ? "page" : undefined}>
                  {item}
                </span>
              </li>
            ))}
          </ul>
          <SoundToggle className={styles.sound} />
        </nav>
      </header>
      <main className={styles.main}>{children}</main>
    </div>
  );
}

/** Four brass rivets in the corners of a plate. */
export function Rivets() {
  return (
    <>
      {(["tl", "tr", "bl", "br"] as const).map((at) => (
        <span key={at} className={styles.rivet} data-at={at} aria-hidden="true" />
      ))}
    </>
  );
}

/** A section heading engraved between two gold rules. */
export function Engraved({ id, children }: { id: string; children: ReactNode }) {
  return (
    <h2 id={id} className={styles.engraved}>
      <span>{children}</span>
    </h2>
  );
}

/** A choice of one, cut into a brass groove; the chosen option is a raised violet key. */
export function Segmented<T extends string>(props: {
  legend: string;
  choices: { value: T; name: string }[];
  value: T;
  onChange: (value: T) => void;
  hint?: string;
}) {
  const name = useId();
  const hintId = useId();
  return (
    <fieldset className={styles.fieldset} aria-describedby={props.hint ? hintId : undefined}>
      <legend className={styles.rubric}>{props.legend}</legend>
      <div className={styles.groove}>
        {props.choices.map((choice) => (
          <label key={choice.value} className={styles.key}>
            <input
              className={styles.srOnly}
              type="radio"
              name={name}
              value={choice.value}
              checked={props.value === choice.value}
              onChange={() => props.onChange(choice.value)}
            />
            <span>{choice.name}</span>
          </label>
        ))}
      </div>
      {props.hint && (
        <p id={hintId} className={styles.hint}>
          {props.hint}
        </p>
      )}
    </fieldset>
  );
}

export { styles as shell };
