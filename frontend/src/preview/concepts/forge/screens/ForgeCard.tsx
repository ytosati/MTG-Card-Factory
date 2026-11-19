// Concept D "Forge" (tasks.md T251): the card face in its original gold frame, and the same frame being forged.
import type { CSSProperties } from "react";

import type { PreviewCard } from "../../../fixtureTypes";
import { FLAME_COLORS, type ManaLetter } from "../machine/palette";
import { ManaCostSymbols } from "../symbols/ManaSymbol";
import styles from "./card.module.css";
import { Filigree, RuneLine, gearPath } from "./ornaments";

type Vars = CSSProperties & Record<`--${string}`, string>;

const RARITY_WORDS: Record<string, string> = { common: "Common", uncommon: "Uncommon", rare: "Rare", mythic: "Mythic" };
const LETTERS: readonly ManaLetter[] = ["W", "U", "B", "R", "G"];
/** Rows of runes in the text box while a card is forged; the last one is shorter, like a last line. */
const RUNE_ROWS = [15, 14, 15, 9] as const;
/** Above this many characters the rules text is set smaller so it fits the box. */
const LONG_TEXT = 150;

/** The colors of a card, read from the letters of its mana cost. */
export function colorsOf(entry: PreviewCard): ManaLetter[] {
  const cost = entry.current_version.mana_cost ?? "";
  return LETTERS.filter((letter) => cost.includes(letter));
}

function tintOf(colors: ManaLetter[]): Vars {
  const first = FLAME_COLORS[colors[0] ?? "C"];
  const second = FLAME_COLORS[colors[1] ?? colors[0] ?? "C"];
  return { "--tint": first.mid, "--tint-2": second.mid };
}

function SetMark({ rarity }: { rarity: string }) {
  return (
    <svg className={styles.setMark} data-rarity={rarity} viewBox="0 0 20 20" aria-hidden="true" focusable="false">
      <path d={gearPath(10, 10, 9.5, 7.5, 8)} fill="currentColor" />
      <circle cx="10" cy="10" r="3.6" fill="#1d1529" />
    </svg>
  );
}

/** A generated card as an object: gold frame, filigree, name bar with its cost, art, type line and text. */
export function ForgeCardFace({ entry, className }: { entry: PreviewCard; className?: string }) {
  const version = entry.current_version;
  const hasBody = version.power !== null && version.toughness !== null;
  const lines = version.rules_text.split("\n");
  return (
    <div className={[styles.box, className].filter(Boolean).join(" ")}>
      <article className={styles.card} aria-label={`${version.name}, generated card`} style={tintOf(colorsOf(entry))}>
        <div className={styles.inner}>
          <Filigree className={styles.filigree} />
          <header className={styles.bar}>
            <span className={styles.name}>{version.name}</span>
            {version.mana_cost !== null && <ManaCostSymbols cost={version.mana_cost} size="5.2cqi" />}
          </header>
          <div className={styles.art}>
            {entry.image ? (
              <img src={entry.image.src} alt={entry.image.alt} width={745} height={1040} />
            ) : (
              <span className={styles.noArt}>No art</span>
            )}
          </div>
          <div className={styles.bar}>
            <span className={styles.typeLine}>{version.type_line}</span>
            <SetMark rarity={version.rarity} />
          </div>
          <div className={styles.text} data-long={version.rules_text.length > LONG_TEXT ? "true" : "false"}>
            {lines.map((line, index) => (
              <p key={index}>{line}</p>
            ))}
          </div>
          <footer className={styles.foot}>
            <span>{RARITY_WORDS[version.rarity] ?? version.rarity}</span>
            <span>Card Factory</span>
          </footer>
          {hasBody && (
            <span className={styles.pt} aria-label={`Power ${version.power}, toughness ${version.toughness}`}>
              {version.power}/{version.toughness}
            </span>
          )}
          <span className={styles.sheen} aria-hidden="true" />
        </div>
      </article>
    </div>
  );
}

/**
 * The empty frame while the job runs: the name bar shimmers, the text box fills with runes, one row for each
 * step from the search to the revision, and on the art step the art window swirls. Purely decorative.
 */
export function ForgingCard({ stepIndex, colors }: { stepIndex: number; colors: ManaLetter[] }) {
  return (
    <div className={styles.box} aria-hidden="true">
      <div className={`${styles.card} ${styles.forging}`} style={tintOf(colors)}>
        <div className={styles.inner}>
          <Filigree className={styles.filigree} />
          <div className={styles.bar}>
            <span className={styles.shimmer} />
          </div>
          <div className={styles.art} data-swirl={stepIndex >= 5 ? "full" : "faint"}>
            <span className={styles.swirl} />
          </div>
          <div className={styles.bar}>
            <span className={`${styles.shimmer} ${styles.shimmerShort}`} />
          </div>
          <div className={styles.text}>
            {RUNE_ROWS.map((count, row) => {
              const state = row < stepIndex - 1 ? "done" : row === stepIndex - 1 ? "active" : "waiting";
              return (
                <RuneLine
                  key={`${row}-${state}`}
                  seed={row + 1}
                  count={count}
                  className={styles.runeRow}
                  runeClass={styles.rune}
                  state={state}
                />
              );
            })}
          </div>
          <footer className={styles.foot} />
        </div>
      </div>
    </div>
  );
}
