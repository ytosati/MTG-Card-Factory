// Concept E "Starfield" (tasks.md T251): the black glyphs of the mana symbols, drawn on a 100-unit square.
import type { ReactElement } from "react";

import { GLYPH_INK, type ManaColor, type SpecialSymbol } from "./manaSymbols";

/** `hole` is the circle fill behind the glyph, used where the glyph shows the circle through a gap. */
type GlyphProps = { hole: string };

const SERIF = "'Palatino Linotype', 'Book Antiqua', Palatino, 'Iowan Old Style', Georgia, serif";

const round = (value: number) => Math.round(value * 10) / 10;

/** A flame tongue along a spiral around (cx, cy): width shrinks from w0 to a point while the radius goes r0 to r1. */
function tongue(cx: number, cy: number, r0: number, r1: number, a0: number, a1: number, w0: number): string {
  const steps = 28;
  const outer: string[] = [];
  const inner: string[] = [];
  for (let i = 0; i <= steps; i += 1) {
    const t = i / steps;
    const angle = ((a0 + (a1 - a0) * t) * Math.PI) / 180;
    const radius = r0 + (r1 - r0) * t;
    const half = (w0 / 2) * Math.pow(1 - t, 0.8);
    const x = Math.cos(angle);
    const y = Math.sin(angle);
    outer.push(`${round(cx + x * (radius + half))},${round(cy + y * (radius + half))}`);
    inner.push(`${round(cx + x * (radius - half))},${round(cy + y * (radius - half))}`);
  }
  return `M${outer.join("L")}L${inner.reverse().join("L")}Z`;
}

const SUN_RAY = "M44.5,31 C44,24 46.5,17 53,9.5 C51.5,14.5 51.8,18 53.8,21 C56,18.8 59,17.6 62.5,17.6 C58.6,21.6 57,26 56.6,31.5 Z";

function Sun({ hole }: GlyphProps) {
  return (
    <g fill={GLYPH_INK}>
      {Array.from({ length: 8 }, (_, index) => (
        <path key={index} d={SUN_RAY} transform={`rotate(${index * 45} 50 50)`} />
      ))}
      <circle cx="50" cy="50" r="20" />
      <circle cx="50" cy="50" r="15.6" fill="none" stroke={hole} strokeWidth="2.2" />
    </g>
  );
}

function Drop({ hole }: GlyphProps) {
  return (
    <g>
      <path
        fill={GLYPH_INK}
        d="M47,14 C44.5,29 29,43 29,61 C29,74.5 39,85 52,85 C65,85 75,75.5 75,62 C75,49 65,40 57,32 C51.5,26.5 48,21.5 47,14 Z"
      />
      <path fill={hole} d="M64,55 C66,60.5 69,64.5 68.2,69.6 C67.5,73.8 61.6,74.2 60.8,70.6 C60,66.4 63,61.5 64,55 Z" />
    </g>
  );
}

const SKULL =
  "M50,14 C28.5,14 16,27.5 16,45 C16,55 21.5,62 29.5,65.5 L30.5,77 C31,82 34,86 38.5,86 L41.5,86 L42.5,79.5 L45.2,79.5 L45.8,87 L48.7,87 L48.8,79.5 L51.2,79.5 L51.3,87 L54.2,87 L54.8,79.5 L57.5,79.5 L58.5,86 L61.5,86 C66,86 69,82 69.5,77 L70.5,65.5 C78.5,62 84,55 84,45 C84,27.5 71.5,14 50,14 Z " +
  "M24.5,47.5 C24.2,40.5 31.5,37.5 39.5,39.8 C45.6,41.6 47.2,47.6 44.6,53 C42,57.6 33.6,58.2 29.2,56 C26,54.2 24.6,51 24.5,47.5 Z " +
  "M75.5,47.5 C75.8,40.5 68.5,37.5 60.5,39.8 C54.4,41.6 52.8,47.6 55.4,53 C58,57.6 66.4,58.2 70.8,56 C74,54.2 75.4,51 75.5,47.5 Z " +
  "M50,55 L46.6,68.5 L50,66.8 L53.4,68.5 Z " +
  "M30.5,22 L39.5,30.5 L37.4,31.6 Z M69.5,22 L60.5,30.5 L62.6,31.6 Z";

function Skull() {
  return <path fill={GLYPH_INK} fillRule="evenodd" d={SKULL} />;
}

const FIREBALL = [
  tongue(54, 50, 28, 38, 105, -146, 17),
  tongue(54, 50, 37, 45, 44, 14, 6),
  tongue(54, 50, 21, 25, 38, -96, 9),
  tongue(54, 50, 31, 36, -142, -182, 6.5),
  tongue(54, 50, 17, 21, -108, -152, 5.5),
];

const FIREBALL_CORE =
  "M18,66 C18,53 27,46 38,45 C48,44.4 57,40 64,31 C63.4,39 61.6,45 62.4,50 C66,47.4 70,43.2 73,38.5 C72.4,48 68.6,56 64,61.5 C63.6,77 53,88 40,88 C27.6,88 18,78.6 18,66 Z";

function Fireball() {
  return (
    <g fill={GLYPH_INK}>
      <path d={FIREBALL_CORE} />
      {FIREBALL.map((d) => (
        <path key={d} d={d} />
      ))}
    </g>
  );
}

const CROWN: [number, number, number][] = [
  [50, 27, 14], [35, 29, 11], [65, 29, 11], [25, 40, 10], [75, 40, 10],
  [21, 52, 8.5], [79, 52, 8.5], [32, 50, 10], [68, 50, 10], [50, 42, 13], [40, 38, 11], [60, 38, 11],
];

const BRANCHES = "M47.5,66 C41,60 33,58.5 25,60.5 M48,61 C46.5,55 43,50 37.5,45.5 M52,61 C53.5,55 57,50 62.5,45.5 M52.5,66 C59,60 67,58.5 75,60.5";

function Tree({ hole }: GlyphProps) {
  return (
    <g fill={GLYPH_INK}>
      {CROWN.map(([cx, cy, r]) => (
        <circle key={`${cx}-${cy}`} cx={cx} cy={cy} r={r} />
      ))}
      <path fill={hole} d="M27,62.5 C31,53 40,47.5 50,47.5 C60,47.5 69,53 73,62.5 Z" />
      <path d={BRANCHES} fill="none" stroke={GLYPH_INK} strokeWidth="5.4" strokeLinecap="round" />
      <path d="M44.5,85 C46.4,77 46.8,68 45.6,58 L54.4,58 C53.2,68 53.6,77 55.5,85 Z" />
      <path d="M26,88.5 C35,87 41.5,83.6 44.6,78 L55.4,78 C58.5,83.6 65,87 74,88.5 C65,89.4 57.5,88.4 53,86.8 L50,89.5 L47,86.8 C42.5,88.4 35,89.4 26,88.5 Z" />
    </g>
  );
}

function Diamond() {
  return (
    <path
      fill="none"
      stroke={GLYPH_INK}
      strokeWidth="6.5"
      strokeMiterlimit="12"
      d="M50,21 Q58,42 79,50 Q58,58 50,79 Q42,58 21,50 Q42,42 50,21 Z"
    />
  );
}

function Phyrexian() {
  return (
    <g fill={GLYPH_INK}>
      <path
        fillRule="evenodd"
        d="M50,28.5 C62.6,28.5 71,38 71,50 C71,62 62.6,71.5 50,71.5 C37.4,71.5 29,62 29,50 C29,38 37.4,28.5 50,28.5 Z M50,35.4 C41.8,35.4 36.2,41.8 36.2,50 C36.2,58.2 41.8,64.6 50,64.6 C58.2,64.6 63.8,58.2 63.8,50 C63.8,41.8 58.2,35.4 50,35.4 Z"
      />
      <path d="M50.8,10 C53,25 54.4,38 53.6,50 C54.2,62 52.8,75 49.2,90 C47.4,75 46.2,62 46.6,50 C46,38 47.4,25 50.8,10 Z" />
    </g>
  );
}

function GenericText({ text }: { text: string }) {
  const digits = text.length;
  const fontSize = digits === 1 ? 84 : digits === 2 ? 72 : 50;
  return (
    <text
      x="50"
      y={digits === 1 ? 79 : digits === 2 ? 75.5 : 67}
      textAnchor="middle"
      fontFamily={SERIF}
      fontSize={fontSize}
      fill={GLYPH_INK}
      stroke={GLYPH_INK}
      strokeWidth="1.3"
      {...(digits > 1 ? { textLength: digits === 2 ? 80 : 82, lengthAdjust: "spacingAndGlyphs" } : {})}
    >
      {text}
    </text>
  );
}

const COLOR_GLYPHS: Record<ManaColor, (props: GlyphProps) => ReactElement> = {
  W: Sun,
  U: Drop,
  B: Skull,
  R: Fireball,
  G: Tree,
  C: Diamond,
};

/** The glyph of one half: a color's emblem, the Phyrexian mark, or generic text. */
export function PieceGlyph({ color, text, phyrexian, hole }: { color?: ManaColor; text?: string; phyrexian: boolean; hole: string }) {
  if (phyrexian) return <Phyrexian />;
  if (text !== undefined) return <GenericText text={text} />;
  const Glyph = COLOR_GLYPHS[color ?? "C"];
  return <Glyph hole={hole} />;
}

function TapArrow() {
  return (
    <g fill={GLYPH_INK}>
      <path d="M37,80 C31.5,64 34,52 47,47.5 C51.5,46 56,45.6 62,46" fill="none" stroke={GLYPH_INK} strokeWidth="10.5" />
      <path d="M55,29 L81,46.5 L56,64 L60.5,46.5 Z" />
    </g>
  );
}

function UntapArrow() {
  return (
    <g fill="#ffffff">
      <path d="M27,58 C31,73 43,80 54,78.5 C66,77 72.5,67 70,56.5 C68.4,50 64,45.5 58.5,43" fill="none" stroke="#ffffff" strokeWidth="10.5" />
      <path d="M45,23 L72.5,21 L63,30.5 L61.5,50 L51.5,47.5 L54.5,33 Z" />
    </g>
  );
}

const SIXTHS = [0, 60, 120, 180, 240, 300];

function Snowflake() {
  return (
    <g>
      <g fill={GLYPH_INK}>
        {SIXTHS.map((angle) => (
          <g key={angle} transform={`rotate(${angle} 50 50)`}>
            <path d="M50,8 L60.5,23 L50,40 L39.5,23 Z" />
            <path d="M50,45 H83 L92,50 L83,55 H50 Z" />
          </g>
        ))}
        <circle cx="50" cy="50" r="12" />
      </g>
      <g fill="#ffffff">
        {SIXTHS.map((angle) => (
          <g key={angle} transform={`rotate(${angle} 50 50)`}>
            <path d="M50,15.5 L55.2,23 L50,32 L44.8,23 Z" />
            <path d="M50,48.4 H82 V51.6 H50 Z" />
            <circle cx="82" cy="50" r="3.4" />
          </g>
        ))}
      </g>
    </g>
  );
}

function Energy() {
  return <path fill={GLYPH_INK} d="M57,13 L29,55 L46,55 L39,87 L71,41 L54,41 L62,13 Z" />;
}

export const SPECIAL_FILL: Record<SpecialSymbol, string> = {
  T: "#cac5c0",
  Q: GLYPH_INK,
  S: "#cac5c0",
  E: "#cac5c0",
};

const SPECIAL_GLYPHS: Record<SpecialSymbol, () => ReactElement> = {
  T: TapArrow,
  Q: UntapArrow,
  S: Snowflake,
  E: Energy,
};

/** The glyph of tap, untap, snow and energy. */
export function SpecialGlyph({ special }: { special: SpecialSymbol }) {
  const Glyph = SPECIAL_GLYPHS[special];
  return <Glyph />;
}
