// Concept D "Forge" (tasks.md T251): the finished card waits face down on the anvil; revealing it turns it over
// with an intensity that follows the power level, and the crew celebrates.
import { useEffect, useRef, useState } from "react";

import type { PowerLevel } from "../../../../api/types";
import type { PreviewCard } from "../../../fixtureTypes";
import { REVEAL } from "../fx/effects";
import { FxLayers } from "../fx/FxLayers";
import { Goblin } from "../goblins/Goblin";
import { playReveal } from "../sound/forgeAudio";
import { AnvilStage, Valve, type Fire } from "./Forge";
import { ForgeCardFace, colorsOf } from "./ForgeCard";
import forge from "./forge.module.css";
import { CardBack } from "./ornaments";
import { Shell, shell } from "./Shell";
import crew from "./generating.module.css";
import styles from "./ready.module.css";

const RESULT_HASH = "#/preview/concept-forge/result";
const TIER_WORDS: Record<PowerLevel, string> = { casual: "Casual", medium: "Medium", strong: "Strong" };
/** How long the fire roars in the card's colors after a reveal; a casual card leaves it low. */
const FLARE_MS: Record<PowerLevel, number> = { casual: 0, medium: 1400, strong: 2200 };
/** When the reveal's burst plays: at the turn of a casual or medium card, at the landing of a strong one. */
const BURST_DELAY_MS: Record<PowerLevel, number> = { casual: 260, medium: 320, strong: 820 };

/** The Ready screen: the card face down over the anvil, revealed on demand. */
export function ReadyScreen({ tier, entry }: { tier: PowerLevel; entry: PreviewCard }) {
  const [revealed, setRevealed] = useState(false);
  const [flaring, setFlaring] = useState(false);
  const [burst, setBurst] = useState(false);
  const link = useRef<HTMLAnchorElement>(null);
  const colors = colorsOf(entry);
  const name = entry.current_version.name;

  useEffect(() => {
    if (revealed) link.current?.focus();
  }, [revealed]);

  useEffect(() => {
    if (!revealed) return undefined;
    const timers = [window.setTimeout(() => setBurst(true), BURST_DELAY_MS[tier])];
    if (FLARE_MS[tier] > 0) timers.push(window.setTimeout(() => setFlaring(false), FLARE_MS[tier]));
    return () => timers.forEach((timer) => window.clearTimeout(timer));
  }, [revealed, tier]);

  function reveal() {
    if (revealed) return;
    playReveal(tier);
    setRevealed(true);
    setFlaring(FLARE_MS[tier] > 0);
  }

  const fire: Fire = flaring ? "roar" : "low";
  const cheer = revealed ? "cheer" : "idle";
  const sageAction = !revealed ? "idle" : tier === "casual" ? "nod" : "cast";

  return (
    <Shell current="Request">
      <div className={styles.head}>
        <p className={shell.rubric}>{TIER_WORDS[tier]} power</p>
        <h1 className={shell.display}>Card ready</h1>
      </div>

      <AnvilStage
        className={styles.stage}
        colors={colors}
        fire={fire}
        embers={revealed && tier !== "casual" ? "full" : "faint"}
        data={{ "data-tier": tier, "data-revealed": revealed ? "true" : "false" }}
        card={
          <div className={styles.flipWrap}>
            <div className={styles.flipper} data-tier={tier} data-revealed={revealed ? "true" : "false"}>
              <button
                type="button"
                className={styles.back}
                // The visible "Reveal card" button below is the one assistive technology reaches.
                aria-hidden="true"
                tabIndex={-1}
                onClick={reveal}
              >
                <CardBack className={styles.backArt} />
              </button>
              <div className={styles.front} aria-hidden={revealed ? undefined : "true"}>
                <ForgeCardFace entry={entry} />
              </div>
            </div>
            {burst && <FxLayers layers={REVEAL[tier]} scale={tier === "casual" ? 2 : 3} mode="once" className={styles.burst} />}
          </div>
        }
      >
        <span className={`${forge.pipe} ${crew.feed}`} aria-hidden="true">
          <span className={forge.collar} style={{ left: "30%" }} />
          <span className={`${forge.valve} ${crew.valve}`}>
            <Valve />
          </span>
        </span>
        <Goblin who="engineer" action={cheer} scale={3} className={`${forge.goblin} ${crew.engineer}`} />
        <Goblin who="sage" action={sageAction} scale={3} className={`${forge.goblin} ${crew.sage}`} />
        <Goblin who="operator" action={cheer} scale={3} flip className={`${forge.goblin} ${crew.operator}`} />
      </AnvilStage>

      <div className={styles.actions}>
        {revealed ? (
          <a ref={link} className={shell.primary} href={RESULT_HASH}>
            See result
          </a>
        ) : (
          <button type="button" className={shell.primary} onClick={reveal}>
            Reveal card
          </button>
        )}
        <p className={shell.srOnly} role="status">
          {revealed ? `Revealed: ${name}.` : ""}
        </p>
      </div>
    </Shell>
  );
}
