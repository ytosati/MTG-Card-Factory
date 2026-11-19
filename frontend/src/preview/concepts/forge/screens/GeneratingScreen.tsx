// Concept D "Forge" (tasks.md T251): a self-running wait; the forge works through the six job steps.
import { useEffect, useState } from "react";

import { requestCopy } from "../../../../screens/request/copy";
import { playLever, playStepTick } from "../sound/forgeAudio";
import { ForgeStage } from "./ForgeStage";
import { ForgingCard } from "./ForgeCard";
import { IDEA } from "./RequestScreen";
import { Shell, shell } from "./Shell";
import styles from "./generating.module.css";

/** How long each step of the demo lasts. */
const STEP_MS = 2200;
const STEPS = requestCopy.steps;
const READY_HASH = "#/preview/concept-forge/ready-medium";

type StepState = "done" | "running" | "waiting";

function stateOf(row: number, index: number): StepState {
  return row < index ? "done" : row === index ? "running" : "waiting";
}

const SPOKEN: Record<StepState, string> = { done: "done", running: "in progress", waiting: "waiting" };

/** The Generating screen: the forge at work, the card frame filling with runes, the steps beneath. */
export function GeneratingScreen() {
  const [run, setRun] = useState(0);
  const [index, setIndex] = useState(0);
  const finished = index >= STEPS.length;

  useEffect(() => {
    playLever();
    setIndex(0);
    const timer = window.setInterval(() => {
      setIndex((current) => {
        if (current >= STEPS.length) {
          window.clearInterval(timer);
          return current;
        }
        return current + 1;
      });
    }, STEP_MS);
    return () => window.clearInterval(timer);
  }, [run]);

  useEffect(() => {
    if (index > 0) playStepTick();
  }, [index]);

  const current = STEPS[Math.min(index, STEPS.length - 1)];
  const announcement = finished
    ? "The card is ready."
    : requestCopy.stepOf(index + 1, STEPS.length, current?.name ?? "");

  return (
    <Shell current="Request">
      <div className={styles.head}>
        <div>
          <p className={shell.rubric}>{finished ? "Done" : `Step ${index + 1} of ${STEPS.length}`}</p>
          <h1 className={shell.display}>{finished ? "Card ready" : "Generating"}</h1>
        </div>
        <div className={styles.headActions}>
          <button type="button" className={shell.secondary} onClick={() => setRun((count) => count + 1)}>
            <svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true" focusable="false">
              <path d="M15.5 6.5A6.5 6.5 0 1 0 16.5 11" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
              <path d="M16.5 2.5v4.5H12" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Replay
          </button>
          {finished && (
            <a className={shell.primary} href={READY_HASH}>
              Reveal the card
            </a>
          )}
        </div>
      </div>

      <ForgeStage
        className={styles.stage}
        phase={finished ? "cooling" : "working"}
        step={current?.value}
        colors={["W"]}
        slot={<ForgingCard stepIndex={index} colors={["W"]} />}
      />

      <p className={shell.srOnly} role="status">
        {announcement}
      </p>

      <ol className={styles.steps} aria-label={requestCopy.stepsLabel}>
        {STEPS.map((step, row) => {
          const state = stateOf(row, index);
          return (
            <li key={step.value} className={styles.step} data-state={state}>
              <span className={styles.lamp} aria-hidden="true">
                {state === "done" && (
                  <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">
                    <path d="M3.5 8.5 L6.5 11.5 L12.5 4.5" fill="none" stroke="currentColor" strokeWidth="2" />
                  </svg>
                )}
              </span>
              <span className={styles.stepNumber} aria-hidden="true">
                {String(row + 1).padStart(2, "0")}
              </span>
              <span className={styles.stepName}>
                {step.name}
                <span className={shell.srOnly}>, {SPOKEN[state]}</span>
              </span>
            </li>
          );
        })}
      </ol>

      <figure className={styles.order}>
        <figcaption className={shell.rubric}>Idea</figcaption>
        <blockquote className={styles.quote}>{IDEA}</blockquote>
      </figure>
    </Shell>
  );
}
