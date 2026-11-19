// Concept E "Starfield" (tasks.md T251): the card as a celestial chart: its finished face, the face while it is
// generated, and its back. Original drawing; nothing comes from a printed Magic card.
import { Fragment, type CSSProperties, type ReactNode } from "react";

import type { CardVersion } from "../../../api/types";
import type { PreviewImage } from "../../fixtureTypes";
import { RUNE_WRITE } from "../forge/fx/effects";
import { PixelFx } from "../forge/fx/PixelFx";
import { ManaCostSymbols, ManaSymbol } from "../forge/symbols/ManaSymbol";
import type { ManaColor } from "../forge/symbols/manaSymbols";
import { frameOf } from "./CardOutline";
import styles from "./chart.module.css";
import { StarGlyph } from "./glyphs";

type Vars = CSSProperties & Record<`--${string}`, string>;

/** The violet and cyan ramp the rune writing is drawn in, dark to bright. */
const STARLIGHT_RUNES = ["#140a26", "#2b1252", "#481c88", "#8b3dff", "#b07cff", "#5bd2fe", "#c8f0ff", "#ffffff"];

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

/** A seeded random sequence, so a chart is drawn the same on every render. */
function seeded(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

function starsOf(seed: number, count: number, width: number, height: number) {
  const random = seeded(seed);
  return Array.from({ length: count }, () => ({ x: random() * width, y: random() * height, r: 0.12 + random() * random() * 0.5, o: 0.3 + random() * 0.6 }));
}

const ART_STARS = starsOf(7, 46, 100, 72);
const BACK_STARS = starsOf(19, 90, 63, 88);

/** The empty art window: a patch of sky with a reticle and a small figure. */
function SkyArt({ drawn = true }: { drawn?: boolean }) {
  const figure = [
    [22, 48],
    [34, 30],
    [52, 36],
    [66, 20],
    [80, 28],
  ];
  return (
    <svg className={styles.sky} viewBox="0 0 100 72" preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false" data-drawn={drawn ? "true" : "false"}>
      <circle cx="50" cy="36" r="26" fill="none" stroke="currentColor" strokeOpacity="0.16" strokeWidth="0.3" />
      <circle cx="50" cy="36" r="14" fill="none" stroke="currentColor" strokeOpacity="0.12" strokeWidth="0.3" />
      <path d="M0 36 H100 M50 0 V72" stroke="currentColor" strokeOpacity="0.1" strokeWidth="0.25" />
      {ART_STARS.map((star, index) => (
        <circle key={index} cx={star.x} cy={star.y} r={star.r} fill="currentColor" opacity={star.o} />
      ))}
      <polyline className={styles.figure} points={figure.map((point) => point.join(",")).join(" ")} fill="none" stroke="var(--sf-cyan)" strokeWidth="0.35" pathLength={1} />
      {figure.map(([x, y], index) => (
        <circle key={index} cx={x} cy={y} r="0.9" fill="var(--sf-ink)" />
      ))}
    </svg>
  );
}

/** The rarity as a small star in the type line: faint for common, then ink, violet and cyan. */
function Rarity({ rarity }: { rarity: string }) {
  return (
    <span className={styles.rarity} data-rarity={rarity} role="img" aria-label={`Rarity: ${rarity}`}>
      <StarGlyph size={10} />
    </span>
  );
}

function Frame({ colors, children, className, state }: { colors: readonly ManaColor[]; children: ReactNode; className?: string; state?: string }) {
  return (
    <div className={[styles.card, className].filter(Boolean).join(" ")} data-state={state}>
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
          {image ? <img className={styles.image} src={image.src} alt={image.alt} /> : <SkyArt />}
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

/**
 * The card while it is generated, step by step (RN-55): the frame is drawn, related cards light as stars in the art
 * window, runes write the text box line by line from the draft on, a scan line passes at validation, and the art
 * window fills at the art step. The name stays veiled until the reveal.
 */
export function ChartInProgress({ step, colors }: { step: number; colors: readonly ManaColor[] }) {
  const writing = step >= 2;
  return (
    <div aria-hidden="true">
      <Frame colors={step >= 0 ? colors : []} className={styles.working} state={step >= 6 ? "done" : `step-${step}`}>
        <div className={styles.nameBar}>
          <span className={styles.veil} data-on={step >= 2 ? "true" : "false"} />
          <span className={styles.veilCost} data-on={step >= 2 ? "true" : "false"} />
        </div>
        <div className={styles.art} data-filling={step >= 5 ? "true" : "false"}>
          <SkyArt drawn={step >= 1} />
          {step === 3 || step === 4 ? <span className={styles.scan} /> : null}
        </div>
        <div className={styles.typeBar}>
          <span className={styles.veil} data-on={step >= 2 ? "true" : "false"} data-short="true" />
        </div>
        <div className={styles.text}>
          {writing ? (
            <span className={styles.runes}>
              <PixelFx
                effect={RUNE_WRITE.effect}
                options={{ ...RUNE_WRITE.options, palette: STARLIGHT_RUNES, lines: 4, perLine: 11 }}
                width={112}
                height={70}
                origin={{ x: 56, y: 62 }}
                scale={2}
                mode="loop"
              />
            </span>
          ) : null}
        </div>
        <div className={styles.foot}>
          <span className={styles.meta}>CF · ·· · EN</span>
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
