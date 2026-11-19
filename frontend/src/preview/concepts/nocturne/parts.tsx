// Concept A "Nocturne" (tasks.md T251): the shell, grain, mana gems and the lit card object of the mockups.
import { useId, useRef, type PointerEvent, type ReactNode } from "react";

import type { PreviewCard } from "../../fixtureTypes";
import card from "./card.module.css";
import styles from "./nocturne.module.css";

/** The largest tilt of the card, in degrees, at the edge of the stage. */
const MAX_TILT = 7;
/** How far the cast shadow slides against the tilt, in pixels, at the edge of the stage. */
const MAX_SHADOW_SHIFT = 14;

export type GemColor = "W" | "U" | "B" | "R" | "G";

export const GEM_NAMES: Record<GemColor, string> = {
  W: "White",
  U: "Blue",
  B: "Black",
  R: "Red",
  G: "Green",
};

const RARITY_WORDS: Record<string, string> = {
  common: "Common",
  uncommon: "Uncommon",
  rare: "Rare",
  mythic: "Mythic",
};

/** A grain of fractal noise drawn by the browser; no image file. */
export function Grain({ className }: { className?: string }) {
  const filterId = `grain-${useId().replace(/[^a-zA-Z0-9]/g, "")}`;
  return (
    <svg className={className ?? styles.grain} aria-hidden="true" focusable="false">
      <filter id={filterId}>
        <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" stitchTiles="stitch" />
        <feColorMatrix type="saturate" values="0" />
      </filter>
      <rect width="100%" height="100%" filter={`url(#${filterId})`} />
    </svg>
  );
}

/** The page of every mockup: the dark ground, its grain and the header. */
export function Shell({ current, children }: { current: "Request" | "Library" | "Status" | null; children: ReactNode }) {
  return (
    <div className={styles.root}>
      <Grain />
      <header className={styles.bar}>
        <span className={styles.brand}>
          <BrandMark />
          Card Factory
        </span>
        <nav aria-label="Main">
          <ul className={styles.nav}>
            {(["Request", "Library", "Status"] as const).map((item) => (
              <li key={item}>
                <span className={styles.navItem} aria-current={item === current ? "page" : undefined}>
                  {item}
                </span>
              </li>
            ))}
          </ul>
        </nav>
      </header>
      <main className={styles.main}>{children}</main>
    </div>
  );
}

/** A lozenge in brass with a violet point: an original mark, not a set symbol. */
function BrandMark() {
  return (
    <svg className={styles.brandMark} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d="M12 2 L21 12 L12 22 L3 12 Z" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <path d="M12 7 L16.5 12 L12 17 L7.5 12 Z" fill="#b48be6" />
    </svg>
  );
}

/** Splits a cost in rules format into its symbols: "{3}{W}" gives ["3", "W"]. */
function symbolsOf(cost: string): string[] {
  return [...cost.matchAll(/\{([^{}]+)\}/g)].map((match) => match[1] ?? "");
}

function spokenCost(symbols: string[]): string {
  return symbols
    .map((symbol) => (symbol in GEM_NAMES ? GEM_NAMES[symbol as GemColor].toLowerCase() : `${symbol} generic`))
    .join(", ");
}

/** The mana cost of the card as small gems; read aloud as words. */
function CardCost({ cost }: { cost: string }) {
  const symbols = symbolsOf(cost);
  return (
    <span className={card.cost} role="img" aria-label={`Mana cost: ${spokenCost(symbols)}`}>
      {symbols.map((symbol, index) => (
        <span
          key={index}
          className={card.costGem}
          data-color={symbol in GEM_NAMES ? symbol : "generic"}
          aria-hidden="true"
        >
          {symbol in GEM_NAMES ? "" : symbol}
        </span>
      ))}
    </span>
  );
}

/** The card as an object: an original lacquer frame with brass hairlines, its art and its text. */
export function NocturneCard({ entry }: { entry: PreviewCard }) {
  const version = entry.current_version;
  const hasBody = version.power !== null && version.toughness !== null;
  return (
    <article className={card.card} aria-label={`${version.name}, generated card`}>
      <Grain className={card.cardGrain} />
      <header className={card.head}>
        <span className={card.name}>{version.name}</span>
        {version.mana_cost !== null && <CardCost cost={version.mana_cost} />}
      </header>
      <div className={card.art}>
        {entry.image ? (
          <img src={entry.image.src} alt={entry.image.alt} width={745} height={1040} />
        ) : (
          <span className={card.noArt}>No art</span>
        )}
      </div>
      <p className={card.typeLine}>{version.type_line}</p>
      <div className={card.rules}>
        {version.rules_text.split("\n").map((line, index) => (
          <p key={index}>{line}</p>
        ))}
      </div>
      <footer className={card.foot}>
        <span className={card.rarity}>{RARITY_WORDS[version.rarity] ?? version.rarity}</span>
        {hasBody && (
          <span className={card.body} aria-label={`Power ${version.power}, toughness ${version.toughness}`}>
            {version.power} / {version.toughness}
          </span>
        )}
      </footer>
      <span className={card.sheen} aria-hidden="true" />
    </article>
  );
}

/** True when motion is off, by the system setting or by the gallery switch on an ancestor. */
function motionReduced(element: Element): boolean {
  if (element.closest('[data-reduced-motion="true"]') !== null) return true;
  return typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/**
 * The table the card rests on. A mouse over it tilts the card toward the pointer and moves the sheen;
 * touch and pens leave it still, and so does reduced motion.
 */
export function CardStage({ children, landing = false }: { children: ReactNode; landing?: boolean }) {
  const stage = useRef<HTMLDivElement>(null);

  function onPointerMove(event: PointerEvent<HTMLDivElement>) {
    const element = stage.current;
    if (element === null || event.pointerType !== "mouse" || motionReduced(element)) return;
    const box = element.getBoundingClientRect();
    const x = Math.min(Math.max((event.clientX - box.left) / box.width, 0), 1);
    const y = Math.min(Math.max((event.clientY - box.top) / box.height, 0), 1);
    element.style.setProperty("--tilt-x", `${((0.5 - y) * 2 * MAX_TILT).toFixed(2)}deg`);
    element.style.setProperty("--tilt-y", `${((x - 0.5) * 2 * MAX_TILT).toFixed(2)}deg`);
    element.style.setProperty("--shadow-x", `${((0.5 - x) * 2 * MAX_SHADOW_SHIFT).toFixed(1)}px`);
    element.style.setProperty("--sheen-x", `${(x * 100).toFixed(1)}%`);
  }

  function onPointerLeave() {
    const element = stage.current;
    if (element === null) return;
    for (const property of ["--tilt-x", "--tilt-y", "--shadow-x", "--sheen-x"]) {
      element.style.removeProperty(property);
    }
  }

  return (
    <div ref={stage} className={card.stage} onPointerMove={onPointerMove} onPointerLeave={onPointerLeave}>
      <div className={card.lift} data-landing={landing ? "true" : "false"}>
        <span className={card.shadow} aria-hidden="true" />
        {children}
      </div>
    </div>
  );
}

/** One mana gem; the stone carries the color and a word under it carries the name. */
export function GemStone({ color }: { color: GemColor | "C" }) {
  return <span className={styles.gemStone} data-color={color} aria-hidden="true" />;
}
