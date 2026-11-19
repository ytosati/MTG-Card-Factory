// Concept B "Drafting Table" (tasks.md T251): the wait while a card generates, drawn as the card being drafted.
import type { CSSProperties } from "react";

import { requestCopy } from "../../../screens/request/copy";
import type { GenerationStep } from "../../../screens/request/copy";
import { CropMarks, Mat, MatFooter, Sheet, TitleBlock } from "./parts";
import styles from "./generating.module.css";

const RUNNING: GenerationStep = "validation";

/** The fictional request being generated, shown as a short specification. */
const BRIEF_EXCERPT = "A night watchman spirit that keeps a lantern lit at the edge of a ruined town…";

export function GeneratingMockup() {
  const steps = requestCopy.steps;
  const runningIndex = steps.findIndex((step) => step.value === RUNNING);
  const running = steps[runningIndex];
  return (
    <Mat current="request" sheetLabel="Sheet 01 · Generating" title="Request">
      <div className={styles.layout}>
        <div className={styles.board}>
          <div className={styles.drawingSlot}>
            <CropMarks />
            <CardDraft />
          </div>
        </div>
        <div className={styles.side}>
          <section aria-labelledby="drafting-steps">
            <h2 id="drafting-steps" className={styles.heading}>
              {requestCopy.stepsLabel}
            </h2>
            <p className={styles.status} role="status">
              {running !== undefined && requestCopy.stepOf(runningIndex + 1, steps.length, running.name)}
            </p>
            <ol className={styles.steps}>
              {steps.map((step, index) => {
                const state = index < runningIndex ? "done" : index === runningIndex ? "running" : "waiting";
                return (
                  <li key={step.value} className={styles.step} data-state={state} style={{ "--i": index } as CSSProperties}>
                    <span className={styles.stepNum}>{String(index + 1).padStart(2, "0")}</span>
                    <span className={styles.stepName}>{step.name}</span>
                    <span className={styles.stepLine} aria-hidden="true" />
                    <span className={styles.stepState}>
                      {state === "done" ? "Done" : state === "running" ? "Running" : "Waiting"}
                    </span>
                  </li>
                );
              })}
            </ol>
          </section>
          <Sheet hold="pin" className={styles.brief} aria-labelledby="drafting-brief">
            <h2 id="drafting-brief" className={styles.heading}>
              Brief
            </h2>
            <p className={styles.excerpt}>{BRIEF_EXCERPT}</p>
            <TitleBlock
              label="Specification of the request"
              cells={[
                { term: "Colors", value: "White" },
                { term: "Power", value: "Medium" },
                { term: "Effort", value: "Medium", wide: true },
              ]}
            />
          </Sheet>
        </div>
      </div>
      <MatFooter>Concept B · Drafting Table · Generation in progress, nothing is sent</MatFooter>
    </Mat>
  );
}

/**
 * The card being drafted: the outline and zones of the finished steps are drawn, the text box of the running
 * step is traced again and again, and a scan line sweeps the card while the checks run.
 */
function CardDraft() {
  return (
    <svg className={styles.draft} viewBox="-60 -60 750 1000" aria-hidden="true">
      <g className={styles.construction}>
        <path d="M-60 40H690M-60 840H690M40 -60V940M590 -60V940M315 -60V940" />
        <path d="M40 120 590 500M590 120 40 500" />
        <circle cx="315" cy="310" r="120" />
      </g>
      <rect className={styles.stroke} style={{ "--d": 0 } as CSSProperties} x="0" y="0" width="630" height="880" rx="30" pathLength={1} />
      <rect className={styles.stroke} style={{ "--d": 1 } as CSSProperties} x="40" y="40" width="550" height="64" pathLength={1} />
      <rect className={styles.stroke} style={{ "--d": 2 } as CSSProperties} x="40" y="120" width="550" height="380" pathLength={1} />
      <rect className={styles.stroke} style={{ "--d": 3 } as CSSProperties} x="40" y="516" width="550" height="52" pathLength={1} />
      <g className={styles.pencilText}>
        <path d="M66 72h250M470 72h24M506 72h24M542 72h24" />
        <path d="M66 542h300" />
        <path d="M70 620h470M70 656h420M70 692h480M70 728h260" />
      </g>
      <rect className={styles.tracing} x="40" y="584" width="550" height="210" pathLength={1} />
      <rect className={styles.pending} x="460" y="800" width="130" height="56" />
      <g className={styles.scan}>
        <path d="M-40 640H670" />
        <text x="-40" y="630">
          checking
        </text>
      </g>
    </svg>
  );
}
