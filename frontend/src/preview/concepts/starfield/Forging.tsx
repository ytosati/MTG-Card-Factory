// Concept E "Starfield" (tasks.md T251): the drawn parts of a card being forged: runes written in starlight and the
// constellation figure of its art window. Original drawing; the runes are the arcane library's rune alphabets
// (vendor/pixelfx/fx/arcane/_lib.js) traced as strokes.
import type { CSSProperties } from "react";

import { GLYPHS, SIGILS } from "../../../vendor/pixelfx/fx/arcane/_lib.js";
import type { ManaColor } from "../forge/symbols/manaSymbols";
import styles from "./forging.module.css";

type Vars = CSSProperties & Record<`--${string}`, string>;

/** A seeded random sequence, so a chart is drawn the same on every render. */
export function seeded(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * A bitmap rune as pen strokes: each lit cell joins its lit neighbours to the right and below, diagonals only where
 * no straight joint already links the two, and a lone cell becomes a dot. Cell centres sit on whole units.
 */
function strokesOf(rows: readonly string[]): string {
  const on = (x: number, y: number): boolean => rows[y]?.[x] === "#";
  const parts: string[] = [];
  rows.forEach((row, y) => {
    [...row].forEach((cell, x) => {
      if (cell !== "#") return;
      const near = [-1, 0, 1].some((dy) => [-1, 0, 1].some((dx) => (dx !== 0 || dy !== 0) && on(x + dx, y + dy)));
      if (!near) parts.push(`M${x} ${y}h0.01`);
      if (on(x + 1, y)) parts.push(`M${x} ${y}L${x + 1} ${y}`);
      if (on(x, y + 1)) parts.push(`M${x} ${y}L${x} ${y + 1}`);
      if (on(x + 1, y + 1) && !on(x + 1, y) && !on(x, y + 1)) parts.push(`M${x} ${y}L${x + 1} ${y + 1}`);
      if (on(x - 1, y + 1) && !on(x - 1, y) && !on(x, y + 1)) parts.push(`M${x} ${y}L${x - 1} ${y + 1}`);
    });
  });
  return parts.join("");
}

/** The small runes, less the one that reads as a Latin S. */
const SMALL_RUNES = (GLYPHS as string[][]).filter((_, at) => at !== 4).map(strokesOf);
const LARGE_RUNES = (SIGILS as string[][]).map(strokesOf);

/** The three hands of the forging card: the name in large sigils, the type line and the rules text in small runes. */
export type RuneHand = "name" | "type" | "text";

const HANDS: Record<RuneHand, { set: string[]; width: number; height: number; gap: number }> = {
  name: { set: LARGE_RUNES, width: 4, height: 6, gap: 1.9 },
  type: { set: SMALL_RUNES, width: 2, height: 4, gap: 1.5 },
  text: { set: SMALL_RUNES, width: 2, height: 4, gap: 1.6 },
};

/**
 * One line of runes written left to right, in words of the given lengths: rune i starts at start + i * pace
 * milliseconds. A few runes of the text are marked for the revision step, which writes them again.
 */
export function RuneLine(props: { hand: RuneHand; words: readonly number[]; seed: number; start: number; pace: number; index?: number }) {
  const { hand, words, seed, start, pace, index = 0 } = props;
  const { set, width, height, gap } = HANDS[hand];
  const random = seeded(seed);
  const pitch = width + gap;
  const runes: { x: number; d: string; revise: boolean }[] = [];
  let x = 0;
  words.forEach((length, word) => {
    if (word > 0) x += pitch * 0.75;
    for (let at = 0; at < length; at += 1) {
      runes.push({ x, d: set[Math.floor(random() * set.length)] ?? "", revise: hand === "text" && random() < 0.1 });
      x += pitch;
    }
  });
  const span = x - gap;
  return (
    <svg className={styles.runeLine} data-hand={hand} viewBox={`-0.6 -0.6 ${span + 1.2} ${height + 1.2}`} aria-hidden="true" focusable="false">
      {runes.map((rune, at) => (
        <path
          key={at}
          className={styles.rune}
          d={rune.d}
          transform={`translate(${rune.x.toFixed(2)} 0)`}
          pathLength={1}
          data-revise={rune.revise ? "true" : undefined}
          style={{ "--d": `${Math.round(start + at * pace)}ms`, "--i": String(index * 40 + at) } as Vars}
        />
      ))}
    </svg>
  );
}

/** A constellation figure: its stars as [x, y, magnitude] in a 100 x 72 sky, and the lines between them in order. */
interface Figure {
  name: string;
  stars: [number, number, number][];
  lines: [number, number][];
}

/** A bird rising with its wings raised, for white and red. */
const WINGED: Figure = {
  name: "winged",
  stars: [
    [50, 14, 1.2], [46, 9, 0.6], [50, 22, 0.7], [50, 31, 1.5], [50, 42, 0.8], [50, 52, 0.7], [44, 62, 0.9], [56, 62, 0.9],
    [42, 27, 0.6], [32, 18, 0.8], [13, 10, 1.3], [17, 21, 0.5], [25, 30, 0.6], [37, 35, 0.7],
    [58, 27, 0.6], [68, 18, 0.8], [87, 10, 1.3], [83, 21, 0.5], [75, 30, 0.6], [63, 35, 0.7],
  ],
  lines: [
    [1, 0], [0, 2], [2, 3], [3, 4], [4, 5], [5, 6], [5, 7],
    [3, 8], [8, 9], [9, 10], [10, 11], [11, 12], [12, 13], [13, 4],
    [3, 14], [14, 15], [15, 16], [16, 17], [17, 18], [18, 19], [19, 4],
  ],
};

/** A serpent in two coils with a forked tongue, for blue and black. */
const SERPENT: Figure = {
  name: "serpent",
  stars: [
    [8, 58, 0.5], [17, 53, 0.6], [27, 57, 0.7], [37, 51, 0.8], [42, 41, 0.9], [37, 31, 0.7], [42, 21, 0.8], [53, 15, 1.1],
    [64, 20, 0.8], [67, 31, 0.9], [62, 41, 0.8], [68, 50, 0.9], [78, 51, 0.8], [86, 46, 1.4], [91, 39, 0.9], [83, 39, 0.7],
    [96, 35, 0.5], [96, 43, 0.5],
  ],
  lines: [
    [0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7], [7, 8], [8, 9], [9, 10], [10, 11], [11, 12], [12, 13],
    [13, 14], [14, 15], [15, 13], [14, 16], [14, 17],
  ],
};

/** A stag turned to the left, antlers raised, for green and colorless. */
const STAG: Figure = {
  name: "stag",
  stars: [
    [20, 33, 0.7], [29, 28, 1.1], [32, 22, 0.7], [27, 14, 0.7], [21, 7, 0.9], [34, 6, 0.8], [41, 12, 0.9],
    [39, 32, 0.8], [61, 32, 0.9], [76, 35, 1.0], [82, 30, 0.6], [37, 44, 1.4], [40, 54, 0.7], [39, 64, 0.8],
    [62, 45, 0.7], [75, 52, 0.7], [78, 63, 0.8],
  ],
  lines: [
    [0, 1], [1, 2], [2, 3], [3, 4], [3, 5], [2, 6], [1, 7], [7, 8], [8, 9], [9, 10], [1, 11], [11, 12], [12, 13],
    [11, 14], [14, 15], [15, 16], [9, 15],
  ],
};

/** The figure a card's sky shows, from the first of its colors. */
export function figureOf(colors: readonly ManaColor[]): Figure {
  const first = colors[0] ?? "C";
  if (first === "U" || first === "B") return SERPENT;
  if (first === "W" || first === "R") return WINGED;
  return STAG;
}

/** The light of each color as the sky's dust; violet stands in for colorless. */
const DUST_TINTS: Record<ManaColor, string> = {
  W: "#f3e7ae",
  U: "#8cc2f0",
  B: "#b9a0d6",
  R: "#f39062",
  G: "#95d27e",
  C: "#b98eff",
};

function starsOf(seed: number, count: number) {
  const random = seeded(seed);
  return Array.from({ length: count }, () => ({ x: random() * 100, y: random() * 72, r: 0.12 + random() * random() * 0.45, o: 0.25 + random() * 0.5 }));
}

const FIELD = starsOf(7, 46);

/** Fine dust along a band across the sky, scattered most near its middle line. */
function dustOf(colors: readonly ManaColor[]) {
  const random = seeded(31);
  const tints = colors.length > 0 ? colors.map((color) => DUST_TINTS[color]) : [DUST_TINTS.C];
  return Array.from({ length: 150 }, (_, at) => {
    const along = random();
    const across = (random() + random() + random() - 1.5) * 11;
    return {
      x: -4 + along * 108 + across * 0.35,
      y: 64 - along * 54 + across,
      r: 0.12 + random() * random() * 0.5,
      o: 0.14 + random() * 0.42,
      fill: at % 5 === 0 ? "#b98eff" : (tints[at % tints.length] ?? DUST_TINTS.C),
    };
  });
}

const MOTES = [
  [18, 44], [34, 18], [58, 58], [72, 26], [88, 54], [46, 66],
];

/** A four-pointed glint of size s round the origin. */
function glint(s: number): string {
  const k = s * 0.16;
  return `M0 ${-s}L${k} ${-k}L${s} 0L${k} ${k}L0 ${s}L${-k} ${k}L${-s} 0L${-k} ${-k}Z`;
}

/**
 * The art window's sky: a field of stars, dust in the card's colors and a figure of the colors. While the card is
 * forged, drawn turns the figure's stars on one after another and then traces its lines; finished, it is shown whole.
 */
export function CardSky({ colors, drawn = true, label }: { colors: readonly ManaColor[]; drawn?: boolean; label?: string }) {
  const figure = figureOf(colors);
  const dust = dustOf(colors);
  const starStep = 70;
  const lineStart = figure.stars.length * starStep + 120;
  const linePace = 1500 / figure.lines.length;
  return (
    <svg
      className={styles.sky}
      viewBox="0 0 100 72"
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
      focusable="false"
      data-drawn={drawn ? "true" : "false"}
      data-figure={label ?? figure.name}
    >
      <g className={styles.dust}>
        {dust.map((mote, at) => (
          <circle key={at} cx={mote.x.toFixed(2)} cy={mote.y.toFixed(2)} r={mote.r.toFixed(2)} fill={mote.fill} opacity={mote.o.toFixed(2)} />
        ))}
      </g>
      <g className={styles.field}>
        {FIELD.map((star, at) => (
          <circle key={at} className={at % 4 === 0 ? styles.twinkle : undefined} cx={star.x} cy={star.y} r={star.r} fill="#e9f1fb" opacity={star.o} style={{ "--t": `${(at * 0.37) % 4}s` } as Vars} />
        ))}
      </g>
      <g className={styles.motes}>
        {MOTES.map(([x, y], at) => (
          <circle key={at} className={styles.mote} cx={x} cy={y} r="0.35" fill="#c8f0ff" style={{ "--t": `${at * 1.3}s` } as Vars} />
        ))}
      </g>
      <g className={styles.figure}>
        {figure.lines.map(([from, to], at) => {
          const a = figure.stars[from];
          const b = figure.stars[to];
          if (!a || !b) return null;
          return (
            <line
              key={at}
              className={styles.figureLine}
              x1={a[0]}
              y1={a[1]}
              x2={b[0]}
              y2={b[1]}
              pathLength={1}
              style={{ "--d": `${Math.round(lineStart + at * linePace)}ms` } as Vars}
            />
          );
        })}
        {figure.stars.map(([x, y, magnitude], at) => (
          <g key={at} className={styles.figureStar} transform={`translate(${x} ${y})`} style={{ "--d": `${at * starStep}ms` } as Vars}>
            <g className={styles.twinkle} style={{ "--t": `${(at * 0.61) % 3.4}s` } as Vars}>
              {magnitude >= 1.1 ? <path d={glint(magnitude * 2.1)} fill="#c8f0ff" opacity="0.85" /> : null}
              <circle r={(0.35 + magnitude * 0.42).toFixed(2)} fill="#f6faff" />
            </g>
          </g>
        ))}
      </g>
    </svg>
  );
}
