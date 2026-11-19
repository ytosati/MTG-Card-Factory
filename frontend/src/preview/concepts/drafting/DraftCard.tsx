// Concept B "Drafting Table" (tasks.md T251): a generated card drawn as a design under review, with its own frame.
import { cx } from "../../../components/classNames";
import type { PreviewCard } from "../../fixtureTypes";
import styles from "./card.module.css";
import { MANA_WORDS } from "./parts";
import type { ManaLetter } from "./parts";

const COLOR_LETTERS = new Set<string>(["W", "U", "B", "R", "G"]);

/** The parts of the card that callouts point at, with the height of their centre in percent of the card. */
export const CARD_PARTS = {
  name: 7.4,
  cost: 7.4,
  art: 32.7,
  type: 57,
  rules: 74.3,
  stats: 92.6,
} as const;

export type CardPart = keyof typeof CARD_PARTS;

/** The symbols of a cost in rules format: "{3}{W}" gives ["3", "W"]. */
export function symbolsOf(cost: string): string[] {
  return [...cost.matchAll(/\{([^{}]+)\}/g)].map((match) => match[1] ?? "");
}

function spoken(symbol: string): string {
  return symbol in MANA_WORDS ? MANA_WORDS[symbol as ManaLetter] : `${symbol} generic`;
}

/** The frame tint: one color gives its tint, several give the gold tint, none the colorless one. */
function frameOf(cost: string): string {
  const colors = new Set(symbolsOf(cost).filter((symbol) => COLOR_LETTERS.has(symbol)));
  if (colors.size > 1) return "multi";
  const [only] = [...colors];
  return only === undefined ? "c" : only.toLowerCase();
}

/** A mana cost as drafted pips, spoken as words. */
export function Pips({ cost, className }: { cost: string; className?: string | undefined }) {
  const symbols = symbolsOf(cost);
  return (
    <span
      className={cx(styles.pips, className)}
      role="img"
      aria-label={`Mana cost: ${symbols.map(spoken).join(", ")}`}
      title={cost}
    >
      {symbols.map((symbol, index) => (
        <span
          key={index}
          className={styles.pip}
          data-mana={symbol in MANA_WORDS ? symbol.toLowerCase() : "generic"}
          aria-hidden="true"
        >
          {symbol}
        </span>
      ))}
    </span>
  );
}

/** Rules text with each keyword-only line set in italic, the way a reminder of a keyword reads. */
function RulesText({ text }: { text: string }) {
  return (
    <div className={styles.rules}>
      {text.split("\n").map((line, index) =>
        /^[A-Z][a-z]+$/.test(line) ? (
          <p key={index} className={styles.keyword}>
            {line}
          </p>
        ) : (
          <p key={index}>{line}</p>
        ),
      )}
    </div>
  );
}

/**
 * The card at 63 by 88. `markers` draws the numbered callout markers on its edge; `arrive` plays the snap-in
 * when the card first appears.
 */
export function DraftCard({
  card,
  markers = [],
  arrive = false,
  className,
}: {
  card: PreviewCard;
  markers?: { part: CardPart; number: number; side: "left" | "right" }[];
  arrive?: boolean;
  className?: string | undefined;
}) {
  const version = card.current_version;
  const stats = version.power !== null && version.toughness !== null ? `${version.power}/${version.toughness}` : null;
  return (
    <article
      className={cx(styles.card, arrive && styles.arrive, className)}
      data-frame={frameOf(version.mana_cost ?? "")}
      aria-label={`Card: ${version.name}`}
    >
      <div className={styles.inner}>
        <div className={styles.titleLine}>
          <p className={styles.name}>{version.name}</p>
          {version.mana_cost !== null && <Pips cost={version.mana_cost} />}
        </div>
        <div className={styles.art}>
          {card.image !== null ? (
            <img src={card.image.src} alt={card.image.alt} width={745} height={1040} />
          ) : (
            <span className={styles.noArt}>No art</span>
          )}
        </div>
        <p className={styles.typeLine}>{version.type_line}</p>
        <RulesText text={version.rules_text} />
        <div className={styles.foot}>
          <span className={styles.footMark}>Card Factory · {version.rarity}</span>
          {stats !== null && (
            <span className={styles.stats} aria-label={`Power ${version.power}, toughness ${version.toughness}`}>
              {stats}
            </span>
          )}
        </div>
      </div>
      {markers.map((marker) => (
        <span
          key={marker.part}
          className={styles.marker}
          data-side={marker.side}
          style={{ top: `${CARD_PARTS[marker.part]}%` }}
          aria-hidden="true"
        >
          {marker.number}
        </span>
      ))}
    </article>
  );
}
