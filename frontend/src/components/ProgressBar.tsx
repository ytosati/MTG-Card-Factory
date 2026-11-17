// A progress bar for a long job, named by a label elsewhere on the screen.
import styles from "./ProgressBar.module.css";

/** Classes of the label row above a bar: the row and the value shown in it. */
export const progressStyles = { head: styles.head, value: styles.value };

/** A clamped fraction (0 to 1) and its whole percent; anything that is not a number reads as 0. */
export function progressOf(value: number): { fraction: number; percent: number } {
  const fraction = Math.min(1, Math.max(0, Number.isFinite(value) ? value : 0));
  return { fraction, percent: Math.round(fraction * 100) };
}

/** The bar itself, with the quarter marks over its fill. */
export function ProgressBar({ labelId, fraction, percent }: { labelId: string; fraction: number; percent: number }) {
  return (
    <div
      className={styles.track}
      role="progressbar"
      aria-labelledby={labelId}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={percent}
      aria-valuetext={`${percent}%`}
    >
      <div className={styles.fill} style={{ transform: `scaleX(${fraction})` }} />
    </div>
  );
}
