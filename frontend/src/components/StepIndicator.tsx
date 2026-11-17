// The running step of a long job: every step in order, the current one marked (spec RN-49).
import { cx } from "./classNames";
import styles from "./StepIndicator.module.css";
import { VisuallyHidden } from "./VisuallyHidden";

interface StepIndicatorProps {
  /** Names the list for assistive technology. */
  label: string;
  steps: string[];
  /** Index of the running step; a value outside the list marks no step. */
  current: number;
}

type StepState = "done" | "current" | "waiting";

const STATE_WORDS: Record<StepState, string> = {
  done: "done",
  current: "in progress",
  waiting: "waiting",
};

/** The steps as an ordered list; the state of each is also said in words, not only drawn. */
export function StepIndicator({ label, steps, current }: StepIndicatorProps) {
  const known = Number.isInteger(current) && current >= 0 && current < steps.length;
  const stateOf = (index: number): StepState => {
    if (!known || index > current) return "waiting";
    return index === current ? "current" : "done";
  };
  return (
    <ol className={styles.steps} aria-label={label}>
      {steps.map((step, index) => {
        const state = stateOf(index);
        return (
          <li
            key={`${index}-${step}`}
            className={cx(styles.step, state === "done" && styles.done, state === "current" && styles.current)}
            aria-current={state === "current" ? "step" : undefined}
          >
            <span className={styles.marker} aria-hidden="true" />
            <span>
              {step}
              <VisuallyHidden>{` (${STATE_WORDS[state]})`}</VisuallyHidden>
            </span>
          </li>
        );
      })}
    </ol>
  );
}
