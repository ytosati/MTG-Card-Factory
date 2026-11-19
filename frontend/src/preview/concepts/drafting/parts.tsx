// Concept B "Drafting Table" (tasks.md T251): the mat, the shell and the drawing marks shared by its mockups.
import type { HTMLAttributes, ReactNode } from "react";

import { cx } from "../../../components/classNames";
import styles from "./mat.module.css";

/** The drafting mat with its rulers, header strip and screen title. */
export function Mat({
  current,
  sheetLabel,
  title,
  titleNote,
  children,
}: {
  current: "request" | "result" | "concept";
  sheetLabel: string;
  title: ReactNode;
  titleNote?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className={styles.root}>
      <div className={styles.rulerTop} aria-hidden="true" />
      <div className={styles.rulerLeft} aria-hidden="true" />
      <div className={styles.shell}>
        <header className={styles.header}>
          <span className={styles.brand}>
            <BrandMark />
            Card Factory
            <span className={styles.drawingNo}>local</span>
          </span>
          <nav className={styles.nav} aria-label="Main">
            <ul>
              <li>
                <a href="#/request" aria-current={current === "request" ? "page" : undefined}>
                  Request
                </a>
              </li>
              <li>
                <a href="#/status">Status</a>
              </li>
            </ul>
          </nav>
        </header>
        <main>
          <div className={styles.titleRow}>
            <div>
              <span className={styles.sheetLabel}>{sheetLabel}</span>
              <h1 className={styles.title}>{title}</h1>
            </div>
            {titleNote !== undefined && <p className={styles.titleNote}>{titleNote}</p>}
          </div>
          {children}
        </main>
      </div>
    </div>
  );
}

/** The mark of the concept: a card outline crossed by a centre line, drawn with the technical pen. */
function BrandMark() {
  return (
    <svg className={styles.brandMark} viewBox="0 0 18 18" aria-hidden="true">
      <rect x="4" y="1.5" width="10" height="15" rx="1.2" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <path d="M1 9h16M9 0v3M9 15v3" stroke="currentColor" strokeWidth="1" />
    </svg>
  );
}

/** A sheet of paper laid on the mat, held by tape at both top corners or by a pin. */
export function Sheet({
  hold = "tape",
  className,
  children,
  ...rest
}: {
  hold?: "tape" | "pin" | "none";
  className?: string | undefined;
  children: ReactNode;
} & Omit<HTMLAttributes<HTMLElement>, "className" | "children">) {
  return (
    <section className={cx(styles.sheet, className)} {...rest}>
      {hold === "tape" && (
        <>
          <span className={cx(styles.tape, styles.tapeLeft)} aria-hidden="true" />
          <span className={cx(styles.tape, styles.tapeRight)} aria-hidden="true" />
        </>
      )}
      {hold === "pin" && <span className={styles.pin} aria-hidden="true" />}
      {children}
    </section>
  );
}

/** Crop marks at the four corners of the positioned parent. */
export function CropMarks() {
  return (
    <>
      <span className={cx(styles.crop, styles.cropTl)} aria-hidden="true" />
      <span className={cx(styles.crop, styles.cropTr)} aria-hidden="true" />
      <span className={cx(styles.crop, styles.cropBl)} aria-hidden="true" />
      <span className={cx(styles.crop, styles.cropBr)} aria-hidden="true" />
    </>
  );
}

/** A registration mark: a circle and its cross hairs. Position it with a class. */
export function RegistrationMark({ className }: { className?: string | undefined }) {
  return (
    <svg className={cx(styles.registration, className)} viewBox="0 0 22 22" aria-hidden="true">
      <circle cx="11" cy="11" r="6" fill="none" stroke="currentColor" strokeWidth="1" />
      <path d="M11 0v22M0 11h22" stroke="currentColor" strokeWidth="1" />
    </svg>
  );
}

/** The title block of a drawing: label and value cells; a `wide` cell spans the block. */
export function TitleBlock({
  label,
  cells,
  className,
}: {
  label: string;
  cells: { term: string; value: ReactNode; wide?: boolean }[];
  className?: string | undefined;
}) {
  return (
    <dl className={cx(styles.titleBlock, className)} aria-label={label}>
      {cells.map((cell) => (
        <div key={cell.term} className={cell.wide === true ? styles.wide : undefined}>
          <dt>{cell.term}</dt>
          <dd>{cell.value}</dd>
        </div>
      ))}
    </dl>
  );
}

/** The mat's bottom line: what the drawing is, in mono. */
export function MatFooter({ children }: { children: ReactNode }) {
  return <p className={styles.footer}>{children}</p>;
}

/** The fill class name of a mana letter, for the drafted circles and the pips on the card. */
export type ManaLetter = "W" | "U" | "B" | "R" | "G" | "C";

export const MANA_WORDS: Record<ManaLetter, string> = {
  W: "white",
  U: "blue",
  B: "black",
  R: "red",
  G: "green",
  C: "colorless",
};
