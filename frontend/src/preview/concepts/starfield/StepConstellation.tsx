// Concept E "Starfield" (tasks.md T251): the generation steps as a vertical constellation: each finished step lights
// its star and draws a line to the next (RN-55).
import type { ReactNode } from "react";

import { requestCopy } from "../../../screens/request/copy";
import styles from "./steps.module.css";

/** The height of one step's row and how far each star sits from the left of its column, in pixels. */
const ROW = 60;
const DRIFT = [10, 30, 16, 38, 22, 34] as const;
const WIDTH = 48;

function centre(index: number): { x: number; y: number } {
  return { x: DRIFT[index % DRIFT.length] ?? 20, y: index * ROW + ROW / 2 };
}

export type StepPhase = "done" | "running" | "waiting";

/**
 * The steps with the running one marked; `current` past the last step means every step is finished. A caller may
 * draw each step's words itself through `label`, for example to add a description and a time.
 */
export function StepConstellation({ current, labelledBy, label }: { current: number; labelledBy: string; label?: (index: number, phase: StepPhase) => ReactNode }) {
  const steps = requestCopy.steps;
  const phaseOf = (index: number): StepPhase => (index < current ? "done" : index === current ? "running" : "waiting");

  return (
    <div className={styles.wrap} style={{ height: steps.length * ROW }}>
      <svg className={styles.lines} width={WIDTH} height={steps.length * ROW} aria-hidden="true" focusable="false">
        {steps.slice(1).map((step, index) => {
          const from = centre(index);
          const to = centre(index + 1);
          return (
            <line
              key={step.value}
              x1={from.x}
              y1={from.y}
              x2={to.x}
              y2={to.y}
              pathLength={1}
              className={styles.line}
              data-drawn={index < current ? "true" : "false"}
            />
          );
        })}
        {steps.map((step, index) => {
          const { x, y } = centre(index);
          const phase = phaseOf(index);
          return (
            <g key={step.value} className={styles.star} data-phase={phase} transform={`translate(${x} ${y})`}>
              <circle r="9" className={styles.halo} />
              <path d="M0 -6 L1.1 -1.1 L6 0 L1.1 1.1 L0 6 L-1.1 1.1 L-6 0 L-1.1 -1.1 Z" className={styles.point} />
              <circle r="1.6" className={styles.dot} />
            </g>
          );
        })}
      </svg>
      <ol className={styles.list} aria-labelledby={labelledBy}>
        {steps.map((step, index) => {
          const phase = phaseOf(index);
          return (
            <li key={step.value} className={styles.step} data-phase={phase} style={{ height: ROW }} aria-current={phase === "running" ? "step" : undefined}>
              <span className={styles.number} aria-hidden="true">
                {String(index + 1).padStart(2, "0")}
              </span>
              {label ? label(index, phase) : <span className={styles.name}>{step.name}</span>}
              <span className={styles.srOnly}>{phase === "done" ? ", done" : phase === "running" ? ", running" : ""}</span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
