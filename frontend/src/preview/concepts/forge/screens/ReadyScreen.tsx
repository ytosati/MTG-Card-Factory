// Concept D "Forge" (tasks.md T251): the finished card waits face down in the forge; revealing it flips it
// with an intensity that follows the power level.
import { useEffect, useRef, useState, type CSSProperties } from "react";

import type { PowerLevel } from "../../../../api/types";
import type { PreviewCard } from "../../../fixtureTypes";
import { FLAME_COLORS } from "../machine/palette";
import { playReveal } from "../sound/forgeAudio";
import { ForgeCardFace, colorsOf } from "./ForgeCard";
import { ForgeStage } from "./ForgeStage";
import { CardBack, RuneRing } from "./ornaments";
import { Shell, shell } from "./Shell";
import styles from "./ready.module.css";

type Vars = CSSProperties & Record<`--${string}`, string>;

const RESULT_HASH = "#/preview/concept-forge/result";
const TIER_WORDS: Record<PowerLevel, string> = { casual: "Casual", medium: "Medium", strong: "Strong" };
const SPARK_COUNT: Record<PowerLevel, number> = { casual: 7, medium: 16, strong: 26 };
/** How long the forge roars in the card's colors after a reveal; a casual card leaves it quiet. */
const FLARE_MS: Record<PowerLevel, number> = { casual: 0, medium: 1300, strong: 2000 };

/** A spread of sparks around the card, the same on every reveal. */
const SPARKS = Array.from({ length: 26 }, (_, index) => {
  const angle = index * 2.399963;
  const reach = 9 + ((index * 37) % 13);
  return {
    dx: Math.cos(angle) * reach * 1.6,
    dy: Math.sin(angle) * reach - 4,
    delay: (index * 23) % 160,
    tone: index % 3,
  };
});

/** Embers that rain over the forge on a strong reveal. */
const EMBERS = Array.from({ length: 24 }, (_, index) => ({
  left: (index * 41 + 7) % 100,
  drift: ((index * 13) % 9) - 4,
  delay: 250 + ((index * 97) % 900),
  duration: 1500 + ((index * 61) % 1000),
  tone: index % 3,
}));

const PUFFS = [
  { dx: -6, delay: 120 },
  { dx: 4, delay: 200 },
  { dx: -1, delay: 320 },
  { dx: 9, delay: 420 },
];

function Effects({ tier, flare }: { tier: PowerLevel; flare: string }) {
  return (
    <div className={styles.effects} data-tier={tier} style={{ "--flare": flare } as Vars} aria-hidden="true">
      {tier !== "casual" && <span className={styles.flare} />}
      {tier === "strong" && <RuneRing className={styles.ring} />}
      {tier !== "casual" &&
        PUFFS.slice(0, tier === "strong" ? 4 : 3).map((puff, index) => (
          <span
            key={index}
            className={styles.puff}
            style={{ "--dx": `${puff.dx}%`, animationDelay: `${puff.delay}ms` } as Vars}
          />
        ))}
      {SPARKS.slice(0, SPARK_COUNT[tier]).map((spark, index) => (
        <span
          key={index}
          className={styles.spark}
          data-tone={spark.tone}
          style={
            {
              "--dx": `${spark.dx.toFixed(1)}cqw`,
              "--dy": `${spark.dy.toFixed(1)}cqw`,
              animationDelay: `${(tier === "strong" ? 700 : 280) + spark.delay}ms`,
            } as Vars
          }
        />
      ))}
      {tier === "strong" &&
        EMBERS.map((ember, index) => (
          <span
            key={index}
            className={styles.ember}
            data-tone={ember.tone}
            style={
              {
                left: `${ember.left}%`,
                "--drift": `${ember.drift}cqw`,
                animationDelay: `${ember.delay}ms`,
                animationDuration: `${ember.duration}ms`,
              } as Vars
            }
          />
        ))}
    </div>
  );
}

/** The Ready screen: the card face down in the cooling forge, revealed on demand. */
export function ReadyScreen({ tier, entry }: { tier: PowerLevel; entry: PreviewCard }) {
  const [revealed, setRevealed] = useState(false);
  const [flaring, setFlaring] = useState(false);
  const link = useRef<HTMLAnchorElement>(null);
  const colors = colorsOf(entry);
  const flare = FLAME_COLORS[colors[0] ?? "C"].bright;
  const name = entry.current_version.name;

  useEffect(() => {
    if (revealed) link.current?.focus();
  }, [revealed]);

  useEffect(() => {
    if (!flaring) return undefined;
    const timer = window.setTimeout(() => setFlaring(false), FLARE_MS[tier]);
    return () => window.clearTimeout(timer);
  }, [flaring, tier]);

  function reveal() {
    if (revealed) return;
    playReveal(tier);
    setRevealed(true);
    setFlaring(FLARE_MS[tier] > 0);
  }

  return (
    <Shell current="Request">
      <div className={styles.head}>
        <p className={shell.rubric}>{TIER_WORDS[tier]} power</p>
        <h1 className={shell.display}>Card ready</h1>
      </div>

      <ForgeStage
        className={styles.plate}
        phase={flaring ? "working" : "cooling"}
        step="art"
        colors={colors}
        data={{ "data-tier": tier, "data-revealed": revealed ? "true" : "false" }}
        effects={revealed ? <Effects tier={tier} flare={flare} /> : null}
        slot={
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
        }
      />

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
