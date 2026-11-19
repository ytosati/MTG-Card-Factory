// Concept D "Forge" (tasks.md T251): a self-running wait; the crew forges the card on the anvil through the six steps.
import { useEffect, useState } from "react";

import { requestCopy } from "../../../../screens/request/copy";
import { RUNE_WRITE, SPARKS_HIT, STEAM_BURST } from "../fx/effects";
import { PixelFx } from "../fx/PixelFx";
import { Goblin } from "../goblins/Goblin";
import { playLever, playStepTick } from "../sound/forgeAudio";
import { AnvilStage, Valve } from "./Forge";
import { ForgingCard } from "./ForgeCard";
import forge from "./forge.module.css";
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

/** The runes written into the card's text box, line by line, while the job runs. */
function Writing() {
  return (
    <PixelFx
      effect={RUNE_WRITE.effect}
      options={RUNE_WRITE.options}
      width={RUNE_WRITE.width}
      height={RUNE_WRITE.height}
      scale={2}
      className={styles.writing}
    />
  );
}

/** The Generating screen: the card frame over the anvil, the crew at work around it, the steps beneath. */
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
    <Shell current="Request" working={!finished}>
      <div className={styles.head}>
        <div>
          <p className={shell.rubric}>{finished ? "Done" : `Step ${index + 1} of ${STEPS.length}`}</p>
          <h1 className={shell.display}>{finished ? "Card ready" : "Generating"}</h1>
          <p className={styles.idea}>{IDEA}</p>
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

      <AnvilStage
        className={styles.stage}
        colors={["W"]}
        fire={finished ? "low" : "roar"}
        embers={finished ? "faint" : "full"}
        runes={!finished}
        card={<ForgingCard stepIndex={index} colors={["W"]} writing={finished ? undefined : <Writing />} />}
      >
        <span className={`${forge.pipe} ${styles.feed}`} aria-hidden="true">
          <span className={forge.collar} style={{ left: "30%" }} />
          <span className={`${forge.valve} ${styles.valve}`} data-turning={finished ? "false" : "true"}>
            <Valve />
          </span>
        </span>
        <span className={`${forge.burst} ${styles.steamAt}`} aria-hidden="true">
          <PixelFx
            effect={STEAM_BURST.effect}
            options={STEAM_BURST.options}
            width={STEAM_BURST.width}
            height={STEAM_BURST.height}
            scale={2}
            mode="once"
            playKey={`${run}-${index}`}
          />
        </span>
        {current?.value === "revision" && !finished && (
          <span className={`${forge.burst} ${styles.sparksAt}`} aria-hidden="true">
            <PixelFx
              effect={SPARKS_HIT.effect}
              options={SPARKS_HIT.options}
              width={SPARKS_HIT.width}
              height={SPARKS_HIT.height}
              origin={SPARKS_HIT.origin}
              scale={2}
              mode="once"
              playKey={run}
            />
          </span>
        )}
        <Goblin who="engineer" action={finished ? "idle" : "work"} scale={3} className={`${forge.goblin} ${styles.engineer}`} />
        <Goblin who="sage" action={finished ? "idle" : "cast"} scale={3} className={`${forge.goblin} ${styles.sage}`} />
        <Goblin who="operator" action={finished ? "idle" : "pull"} scale={3} flip className={`${forge.goblin} ${styles.operator}`} />
      </AnvilStage>

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
              <span className={styles.stepName}>
                <span className={styles.stepNumber} aria-hidden="true">
                  {String(row + 1).padStart(2, "0")}
                </span>
                {step.name}
                <span className={shell.srOnly}>, {SPOKEN[state]}</span>
              </span>
            </li>
          );
        })}
      </ol>
    </Shell>
  );
}
