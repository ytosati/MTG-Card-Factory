// Concept E "Starfield" (tasks.md T251): the generation in progress as a local mockup: the field speeds up, the card
// is drawn as a chart and the steps light as a constellation, walked automatically.
import { useEffect, useId, useState } from "react";

import { requestCopy } from "../../../screens/request/copy";
import { ManaCostSymbols } from "../forge/symbols/ManaSymbol";
import { ChartInProgress } from "./ChartCard";
import { StarGlyph } from "./glyphs";
import { sceneCopy } from "./scenes";
import ui from "./screen.module.css";
import { Shell } from "./Shell";
import { StepConstellation } from "./StepConstellation";
import styles from "./generating.module.css";

/** Time each step stays on screen in the mockup. */
const STEP_MS = 2000;

const IDEA = "A lighthouse keeper who trades memories with the tide, drawing a card whenever the sea takes something back.";

export function GeneratingScreen() {
  const [step, setStep] = useState(0);
  const stepsId = useId();
  const total = requestCopy.steps.length;
  const done = step >= total;
  const running = requestCopy.steps[step];

  useEffect(() => {
    if (done) return undefined;
    const timer = window.setTimeout(() => setStep((current) => current + 1), STEP_MS);
    return () => window.clearTimeout(timer);
  }, [step, done]);

  return (
    <Shell current="Request" speed={done ? "rest" : "generating"}>
      <div className={`${ui.page} ${styles.layout}`}>
        <div className={styles.intro}>
          <p className={ui.rubric}>
            <StarGlyph size={8} className={ui.rubricStar} />
            {done ? sceneCopy.generatedRubric : `${String(Math.min(step + 1, total)).padStart(2, "0")} / ${String(total).padStart(2, "0")}`}
          </p>
          <h1 className={ui.title}>{done ? sceneCopy.generatedTitle : sceneCopy.generatingTitle}</h1>
          <blockquote className={styles.idea}>
            <p>{IDEA}</p>
          </blockquote>
          <dl className={`${ui.facts} ${styles.facts}`}>
            <div>
              <dt>{requestCopy.fieldLabels.color_identity}</dt>
              <dd>
                <ManaCostSymbols cost="{W}{U}" size={18} />
              </dd>
            </div>
            <div>
              <dt>{requestCopy.fieldLabels.power_level}</dt>
              <dd>Medium</dd>
            </div>
            <div>
              <dt>{requestCopy.effortLabel}</dt>
              <dd>Medium</dd>
            </div>
          </dl>
          <p className={styles.live} role="status" aria-live="polite">
            {done ? sceneCopy.generatedStatus : running ? requestCopy.stepOf(step + 1, total, running.name) : ""}
          </p>
          <div className={ui.actions}>
            {done ? (
              <a className={ui.primary} href="#/preview/concept-starfield/ready-medium">
                <StarGlyph size={10} className={ui.primaryStar} />
                {sceneCopy.toReady}
              </a>
            ) : null}
            <button type="button" className={ui.secondary} onClick={() => setStep(0)}>
              {sceneCopy.replay}
            </button>
          </div>
        </div>

        <section className={`${ui.stage} ${styles.stage}`} aria-labelledby={stepsId}>
          <div className={styles.cardCol}>
            <ChartInProgress step={step} colors={["W", "U"]} />
          </div>
          <div className={styles.stepsCol}>
            <h2 id={stepsId} className={ui.label}>
              {requestCopy.stepsLabel}
            </h2>
            <StepConstellation current={step} labelledBy={stepsId} />
          </div>
        </section>
      </div>
    </Shell>
  );
}
