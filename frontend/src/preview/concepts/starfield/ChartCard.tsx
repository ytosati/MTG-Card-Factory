// Concept E "Starfield" (tasks.md T251): the card as a celestial chart: its finished face, the face while it is
// generated, and its back. Original drawing; nothing comes from a printed Magic card.
import { Fragment, type CSSProperties, type ReactNode } from "react";

import type { CardVersion } from "../../../api/types";
import type { PreviewImage } from "../../fixtureTypes";
import { ManaCostSymbols, ManaSymbol } from "./symbols/ManaSymbol";
import type { ManaColor } from "./symbols/manaSymbols";
import { frameOf } from "./CardOutline";
import styles from "./chart.module.css";
import { CardSky, RuneLine, seeded } from "./Forging";
import { StarGlyph } from "./glyphs";

type Vars = CSSProperties & Record<`--${string}`, string>;

/** Rules text longer than this is set a step smaller, so a planeswalker's three abilities fit the box. */
const LONG_TEXT = 140;

/** The colors a mana cost shows, in W U B R G order; a cost with none is colorless. */
export function colorsOfCost(cost: string | null): ManaColor[] {
  const found = (["W", "U", "B", "R", "G"] as const).filter((color) => cost?.includes(color));
  return found.length > 0 ? [...found] : ["C"];
}

/** Rules text in paragraphs, with each {X} shown as its mana symbol and named for assistive technology. */
export function RulesText({ text, className, symbolSize = "1em" }: { text: string; className?: string; symbolSize?: string }) {
  return (
    <div className={className}>
      {text.split("\n").map((line, index) => (
        <p key={index}>
          {line.split(/(\{[^}]+\})/).map((part, at) =>
            /^\{[^}]+\}$/.test(part) ? <ManaSymbol key={at} symbol={part} size={symbolSize} className={styles.inline} /> : <Fragment key={at}>{part}</Fragment>,
          )}
        </p>
      ))}
    </div>
  );
}

function starsOf(seed: number, count: number, width: number, height: number) {
  const random = seeded(seed);
  return Array.from({ length: count }, () => ({ x: random() * width, y: random() * height, r: 0.12 + random() * random() * 0.5, o: 0.3 + random() * 0.6 }));
}

const BACK_STARS = starsOf(19, 90, 63, 88);

/** The rarity as a small star in the type line: faint for common, then ink, violet and cyan. */
function Rarity({ rarity }: { rarity: string }) {
  return (
    <span className={styles.rarity} data-rarity={rarity} role="img" aria-label={`Rarity: ${rarity}`}>
      <StarGlyph size={10} />
    </span>
  );
}

function Frame(props: { colors: readonly ManaColor[]; children: ReactNode; className?: string; state?: string; forging?: boolean }) {
  const { colors, children, className, state, forging } = props;
  return (
    <div className={[styles.card, className].filter(Boolean).join(" ")} data-state={state} data-forging={forging ? "true" : undefined}>
      <div className={styles.frame} style={{ "--frame": frameOf(colors) } as Vars}>
        <div className={styles.face}>
          <span className={styles.tick} data-corner="tl" aria-hidden="true" />
          <span className={styles.tick} data-corner="br" aria-hidden="true" />
          {children}
        </div>
      </div>
    </div>
  );
}

/**
 * The finished card. With textHidden set, its text repeats words shown beside it and is hidden from assistive
 * technology, while the art keeps its text alternative. The contract has no starting loyalty yet, so a
 * planeswalker's comes from the caller.
 */
export function ChartCard(props: { version: CardVersion; image: PreviewImage | null; loyalty?: string; textHidden?: boolean; className?: string }) {
  const { version, image, loyalty, textHidden = false, className } = props;
  const long = version.rules_text.length > LONG_TEXT;
  const hidden = textHidden ? ("true" as const) : undefined;
  return (
    <div className={className}>
      <Frame colors={colorsOfCost(version.mana_cost)}>
        <div className={styles.nameBar} aria-hidden={hidden}>
          <span className={styles.name}>{version.name}</span>
          {version.mana_cost ? <ManaCostSymbols cost={version.mana_cost} size="5.2cqi" className={styles.cost} /> : null}
        </div>
        <div className={styles.art} data-long={long ? "true" : "false"}>
          {image ? <img className={styles.image} src={image.src} alt={image.alt} /> : <CardSky colors={colorsOfCost(version.mana_cost)} />}
        </div>
        <div className={styles.typeBar} aria-hidden={hidden}>
          <span className={styles.type}>{version.type_line}</span>
          <Rarity rarity={version.rarity} />
        </div>
        <div aria-hidden={hidden} className={styles.textWrap}>
          <RulesText text={version.rules_text} className={styles.text} symbolSize="1.05em" />
        </div>
        <div className={styles.foot} data-long={long ? "true" : "false"} aria-hidden={hidden}>
          <span className={styles.meta}>CF · {String(version.mana_value).padStart(2, "0")} · EN</span>
          {version.power !== null && version.toughness !== null ? (
            <span className={styles.stat}>
              {version.power}/{version.toughness}
            </span>
          ) : loyalty ? (
            <span className={styles.loyalty}>
              <span>{loyalty}</span>
            </span>
          ) : null}
        </div>
      </Frame>
    </div>
  );
}

/** When each part of the card is written, in milliseconds from the draft step: the name, the type line, the text. */
const WRITE = { name: 0, type: 520, text: 860, namePace: 40, typePace: 26, textPace: 10 };
/** The runes of the forging card in words: the name, the type line and four lines of rules text. */
const NAME_WORDS = [7, 5];
const TYPE_WORDS = [6, 1, 5, 6];
const TEXT_LINES = [
  [4, 3, 6, 2, 5, 3, 4],
  [2, 5, 4, 7, 3, 4, 2],
  [5, 2, 3, 6, 4, 5, 3],
  [4, 2, 6, 3, 5, 4, 3],
  [3, 6, 2, 5],
];

/**
 * The card while it is generated, step by step (RN-55): the frame is drawn and the figure of the art window lights
 * star by star as related cards are found; from the draft on, runes write the card top to bottom: the name, the
 * type line, then the rules text. Validation sends a shimmer through the writing, revision writes a few runes again,
 * the art step gathers the sky's dust, and the finished figure glows once.
 */
export function ChartInProgress({ step, colors }: { step: number; colors: readonly ManaColor[] }) {
  const writing = step >= 2;
  const pips = colors.length > 0 ? colors.length : 1;
  return (
    <div aria-hidden="true">
      <Frame colors={colors} className={styles.working} state={step >= 6 ? "done" : `step-${step}`} forging>
        <div className={styles.nameBar}>
          {writing ? (
            <span className={styles.runeName}>
              <RuneLine hand="name" words={NAME_WORDS} seed={3} start={WRITE.name} pace={WRITE.namePace} />
            </span>
          ) : (
            <span className={styles.guide} />
          )}
          <span className={styles.pips} data-on={writing ? "true" : "false"}>
            {Array.from({ length: pips }, (_, at) => (
              <span key={at} style={{ transitionDelay: `${WRITE.type - 180 + at * 90}ms` }} />
            ))}
          </span>
        </div>
        <div className={styles.art}>
          <CardSky colors={colors} drawn={step >= 1} />
        </div>
        <div className={styles.typeBar}>
          {writing ? (
            <span className={styles.runeType}>
              <RuneLine hand="type" words={TYPE_WORDS} seed={5} start={WRITE.type} pace={WRITE.typePace} />
            </span>
          ) : (
            <span className={styles.guide} data-short="true" />
          )}
          <span className={styles.rarityMark} data-on={writing ? "true" : "false"}>
            <StarGlyph size={10} />
          </span>
        </div>
        <div className={styles.text}>
          {writing ? (
            <div className={styles.runeText}>
              {TEXT_LINES.map((words, line) => {
                const before = TEXT_LINES.slice(0, line).reduce((sum, value) => sum + value.reduce((total, length) => total + length, 0), 0);
                return (
                  <span key={line} className={styles.runeRow}>
                    <RuneLine hand="text" words={words} seed={11 + line} start={WRITE.text + before * WRITE.textPace} pace={WRITE.textPace} index={line} />
                  </span>
                );
              })}
            </div>
          ) : null}
        </div>
        <div className={styles.foot}>
          <span />
          <span className={styles.veilStat} data-on={step >= 4 ? "true" : "false"} />
        </div>
      </Frame>
    </div>
  );
}

/** The back of every card: deep indigo, a fine star chart and a small arcane sigil at its centre. */
export function CardBack({ className }: { className?: string }) {
  const rings = [9, 16, 23, 30];
  const figure = [
    [12, 20],
    [19, 14],
    [27, 17],
    [31, 9],
    [44, 12],
    [50, 21],
  ];
  return (
    <svg className={[styles.back, className].filter(Boolean).join(" ")} viewBox="0 0 63 88" aria-hidden="true" focusable="false">
      <rect width="63" height="88" rx="2.6" fill="#141533" />
      <rect x="2.2" y="2.2" width="58.6" height="83.6" rx="1.6" fill="#1b1c3a" stroke="#2c2e5c" strokeWidth="0.3" />
      <g fill="none" stroke="#e9f1fb" strokeOpacity="0.1" strokeWidth="0.18">
        {rings.map((r) => (
          <circle key={r} cx="31.5" cy="47" r={r} />
        ))}
        {Array.from({ length: 12 }, (_, index) => {
          const angle = (index * Math.PI) / 6;
          return <line key={index} x1={31.5 + Math.cos(angle) * 9} y1={47 + Math.sin(angle) * 9} x2={31.5 + Math.cos(angle) * 30} y2={47 + Math.sin(angle) * 30} />;
        })}
        <ellipse cx="31.5" cy="47" rx="30" ry="9" transform="rotate(-22 31.5 47)" strokeOpacity="0.18" />
      </g>
      {BACK_STARS.map((star, index) => (
        <circle key={index} cx={star.x} cy={star.y} r={star.r * 0.7} fill="#e9f1fb" opacity={star.o * 0.7} />
      ))}
      <polyline points={figure.map((point) => point.join(",")).join(" ")} fill="none" stroke="#5bd2fe" strokeOpacity="0.55" strokeWidth="0.22" />
      {figure.map(([x, y], index) => (
        <circle key={index} cx={x} cy={y} r="0.55" fill="#e9f1fb" />
      ))}
      {/* The sigil: a ring, a triangle within it and a four-pointed star at the heart. */}
      <g transform="translate(31.5 47)">
        <circle r="6.2" fill="#141533" stroke="#b98eff" strokeWidth="0.3" />
        <circle r="4.6" fill="none" stroke="#b98eff" strokeOpacity="0.5" strokeWidth="0.2" />
        <path d="M0 -4.6 L3.98 2.3 L-3.98 2.3 Z" fill="none" stroke="#b98eff" strokeWidth="0.25" />
        <path d="M0 -2.4 L0.42 -0.42 L2.4 0 L0.42 0.42 L0 2.4 L-0.42 0.42 L-2.4 0 L-0.42 -0.42 Z" fill="#e9f1fb" />
        <circle cx="5.6" cy="-2.8" r="0.5" fill="#5bd2fe" />
      </g>
      <line x1="22" y1="79" x2="41" y2="79" stroke="#e9f1fb" strokeOpacity="0.2" strokeWidth="0.2" />
      <circle cx="31.5" cy="79" r="0.6" fill="#b98eff" />
    </svg>
  );
}
