// Concept C, "Gallery Wall" (tasks.md T251): the wait while a card is generated. Each step washes more of the
// chosen color up the wall, builds the frame and warms the spotlight. A static mockup that advances on a timer.
import { useEffect, useState } from "react";

import { requestCopy } from "../../../screens/request/copy";
import { Canvas, Frame } from "./FramedCard";
import styles from "./generating.module.css";
import { WALLS, wallStyle } from "./palette";
import wall from "./wall.module.css";

const STEPS = requestCopy.steps;
const STEP_MS = 1800;

/** How much of the frame stands at each step: nothing, the mat, the moulding, then the shadow. */
function builtAt(step: number): number {
  if (step <= 1) return 0;
  if (step === 2) return 1;
  if (step <= 4) return 2;
  return 3;
}

export function GalleryGenerating() {
  const [step, setStep] = useState(3);

  useEffect(() => {
    const timer = window.setInterval(() => setStep((current) => (current >= STEPS.length ? 1 : current + 1)), STEP_MS);
    return () => window.clearInterval(timer);
  }, []);

  const current = STEPS[step - 1] ?? STEPS[0]!;

  return (
    <div
      className={`${wall.root} ${styles.page}`}
      style={wallStyle(WALLS.plum, { "--wash-paint": WALLS.G.paint, "--progress": String(step / STEPS.length) })}
    >
      <div className={styles.hall}>
        <div className={`${wall.field} ${styles.hangZone}`}>
          <span className={styles.wash} aria-hidden="true" />
          <span className={styles.spot} aria-hidden="true" />
          <span className={`${wall.bigNumeral} ${styles.stepNumeral}`} aria-hidden="true">
            {String(step).padStart(2, "0")}
          </span>
          <div className={styles.hangSpot}>
            <Frame built={builtAt(step)}>
              <Canvas step={step} />
            </Frame>
          </div>
        </div>

        <div className={`${wall.field} ${styles.labelZone}`}>
          <span className={styles.wash} aria-hidden="true" />
          <p className={wall.caption}>Request · Green · Medium power</p>
          <h1 className={styles.title}>Generating</h1>
          <p className={styles.idea}>
            A lantern-bearing scout who leads lost travelers through an old forest and finds hidden paths.
          </p>
          <div
            className={styles.meter}
            role="progressbar"
            aria-label={requestCopy.stepsLabel}
            aria-valuemin={1}
            aria-valuemax={STEPS.length}
            aria-valuenow={step}
            aria-valuetext={requestCopy.stepOf(step, STEPS.length, current.name)}
          >
            <span className={styles.meterFill} />
          </div>
          <h2 className={wall.caption}>{requestCopy.stepsLabel}</h2>
          <ol className={styles.steps}>
            {STEPS.map((entry, index) => {
              const number = index + 1;
              const state = number < step ? "done" : number === step ? "current" : "next";
              return (
                <li
                  key={entry.value}
                  className={styles.step}
                  data-state={state}
                  aria-current={state === "current" ? "step" : undefined}
                >
                  <span className={styles.stepIndex} aria-hidden="true">
                    {String(number).padStart(2, "0")}
                  </span>
                  <span className={styles.stepName}>{entry.name}</span>
                  <span className={styles.stepState}>
                    {state === "done" ? "Done" : state === "current" ? "Now" : ""}
                  </span>
                </li>
              );
            })}
          </ol>
        </div>
      </div>
    </div>
  );
}
