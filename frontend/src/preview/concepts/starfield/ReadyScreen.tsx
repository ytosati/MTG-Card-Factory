// Concept E "Starfield" (tasks.md T251): the finished card waits face down; revealing it turns it over with a burst
// whose strength follows the power level. Reduced motion turns the flip into a crossfade without a burst.
import { useEffect, useRef, useState } from "react";

import type { PowerLevel } from "../../../api/types";
import type { PreviewCard } from "../../fixtureTypes";
import { FxLayers } from "../forge/fx/FxLayers";
import { CardBack, ChartCard } from "./ChartCard";
import { StarGlyph } from "./glyphs";
import { STAR_REVEAL, sceneCopy } from "./scenes";
import ui from "./screen.module.css";
import { Shell } from "./Shell";
import styles from "./ready.module.css";

const TIER_WORDS: Record<PowerLevel, string> = { casual: "Casual", medium: "Medium", strong: "Strong" };

/** When the burst plays: at the turn of a casual or medium card, at the landing of a strong one. */
const BURST_DELAY_MS: Record<PowerLevel, number> = { casual: 240, medium: 300, strong: 760 };

export function ReadyScreen({ tier, entry, loyalty }: { tier: PowerLevel; entry: PreviewCard; loyalty?: string }) {
  const [revealed, setRevealed] = useState(false);
  const [burst, setBurst] = useState(false);
  const link = useRef<HTMLAnchorElement>(null);

  useEffect(() => {
    if (!revealed) return undefined;
    link.current?.focus();
    const timer = window.setTimeout(() => setBurst(true), BURST_DELAY_MS[tier]);
    return () => window.clearTimeout(timer);
  }, [revealed, tier]);

  const state = revealed ? "true" : "false";

  return (
    <Shell current="Request">
      <div className={`${ui.page} ${styles.layout}`}>
        <div className={styles.intro}>
          <p className={ui.rubric}>
            <StarGlyph size={8} className={ui.rubricStar} />
            {sceneCopy.readyRubric(TIER_WORDS[tier])}
          </p>
          <h1 className={ui.title}>{sceneCopy.readyTitle}</h1>
          <p className={ui.summary}>{revealed ? sceneCopy.readyRevealedLede : sceneCopy.readyLede}</p>
          <div className={`${ui.actions} ${styles.actions}`}>
            {revealed ? (
              <a ref={link} className={ui.primary} href="#/preview/concept-starfield/result">
                <StarGlyph size={10} className={ui.primaryStar} />
                {sceneCopy.seeResult}
              </a>
            ) : (
              <button type="button" className={ui.primary} onClick={() => setRevealed(true)}>
                <StarGlyph size={10} className={ui.primaryStar} />
                {sceneCopy.reveal}
              </button>
            )}
          </div>
          <p className={styles.srOnly} role="status">
            {revealed ? sceneCopy.revealed(entry.current_version.name) : ""}
          </p>
        </div>

        <div className={`${ui.stage} ${styles.stage}`} data-tier={tier} data-revealed={state}>
          <div className={styles.orbit} aria-hidden="true" />
          <div className={styles.flipWrap}>
            {tier === "strong" && revealed ? <span className={styles.nova} aria-hidden="true" /> : null}
            <div className={styles.flipper} data-tier={tier} data-revealed={state}>
              <div className={styles.back} aria-hidden="true">
                <CardBack />
              </div>
              <div className={styles.front} aria-hidden={revealed ? undefined : "true"}>
                <ChartCard version={entry.current_version} image={entry.image} loyalty={loyalty} />
              </div>
            </div>
            {burst ? <FxLayers layers={STAR_REVEAL[tier]} scale={tier === "casual" ? 2 : 3} mode="once" className={styles.burst} /> : null}
          </div>
        </div>
      </div>
    </Shell>
  );
}
