// Concept E "Starfield" (tasks.md T251): mana symbols from the reference sheet, alone or as a whole cost.
// Symbols the sheet does not have fall back to flat SVG circles in the same style.
import { useId, type CSSProperties } from "react";

import { PieceGlyph, SPECIAL_FILL, SpecialGlyph } from "./glyphs";
import { MANA_FILL, parseManaCost, parseManaSymbol, spokenSymbol, type ManaPiece, type ParsedSymbol } from "./manaSymbols";
import styles from "./ManaSymbol.module.css";

// One image per symbol, cut from the reference sheet chosen by the maintainer.
const SHEET = import.meta.glob<string>("../../../../assets/mana/*.png", { eager: true, import: "default" });

const SHEET_BY_KEY: Record<string, string> = Object.fromEntries(
  Object.entries(SHEET).map(([path, url]) => [path.slice(path.lastIndexOf("/") + 1, -".png".length), url]),
);

function keyOf(piece: ManaPiece): string {
  return piece.kind === "color" ? piece.color.toLowerCase() : piece.text.toLowerCase();
}

/** The sheet image for a symbol, or undefined when the sheet does not have it. */
function sheetImage(parsed: ParsedSymbol): string | undefined {
  if (parsed.kind === "special") return SHEET_BY_KEY[parsed.special.toLowerCase()];
  const [first, second] = parsed.pieces;
  if (!second) {
    if (parsed.phyrexian) return SHEET_BY_KEY[first.kind === "color" && first.color !== "C" ? `${keyOf(first)}p` : "p"];
    return SHEET_BY_KEY[keyOf(first)];
  }
  if (parsed.phyrexian) return undefined;
  return SHEET_BY_KEY[keyOf(first) + keyOf(second)] ?? SHEET_BY_KEY[keyOf(second) + keyOf(first)];
}

const TOP_LEFT_HALF = "M0,0 H100 L0,100 Z";
const BOTTOM_RIGHT_HALF = "M100,0 V100 H0 Z";

function fillOf(piece: ManaPiece): string {
  return piece.kind === "color" ? MANA_FILL[piece.color] : MANA_FILL.generic;
}

function Piece({ piece, phyrexian, hole }: { piece: ManaPiece; phyrexian: boolean; hole: string }) {
  return piece.kind === "color" ? (
    <PieceGlyph color={piece.color} phyrexian={phyrexian} hole={hole} />
  ) : (
    <PieceGlyph text={piece.text} phyrexian={false} hole={hole} />
  );
}

function SymbolArt({ parsed, clipId }: { parsed: ParsedSymbol; clipId: string }) {
  if (parsed.kind === "special") {
    return (
      <>
        <circle cx="50" cy="50" r="50" fill={SPECIAL_FILL[parsed.special]} />
        {/* The black untap circle would vanish on a dark ground without a faint rim. */}
        {parsed.special === "Q" ? <circle cx="50" cy="50" r="48.5" fill="none" stroke="rgba(255, 255, 255, 0.22)" strokeWidth="3" /> : null}
        <SpecialGlyph special={parsed.special} />
      </>
    );
  }
  const [first, second] = parsed.pieces;
  if (!second) {
    const fill = fillOf(first);
    return (
      <>
        <circle cx="50" cy="50" r="50" fill={fill} />
        <Piece piece={first} phyrexian={parsed.phyrexian} hole={fill} />
      </>
    );
  }
  const firstFill = fillOf(first);
  const secondFill = fillOf(second);
  // A generic number in the upper half is drawn larger than a color emblem, as on printed cards.
  const firstScale = first.kind === "generic" ? 0.62 : 0.46;
  return (
    <>
      <clipPath id={clipId}>
        <circle cx="50" cy="50" r="50" />
      </clipPath>
      <g clipPath={`url(#${clipId})`}>
        <path d={TOP_LEFT_HALF} fill={firstFill} />
        <path d={BOTTOM_RIGHT_HALF} fill={secondFill} />
      </g>
      <g transform={`translate(${34 - 50 * firstScale} ${34 - 50 * firstScale}) scale(${firstScale})`}>
        <Piece piece={first} phyrexian={parsed.phyrexian} hole={firstFill} />
      </g>
      <g transform="translate(44 44) scale(0.46)">
        <Piece piece={second} phyrexian={parsed.phyrexian} hole={secondFill} />
      </g>
    </>
  );
}

type ManaSymbolProps = {
  /** Brace notation such as "{G}", "{W/U}", "{2/G}", "{G/P}", "{T}"; braces and case are optional. */
  symbol: string;
  /** Pixels, or any CSS length such as "var(--size)". */
  size?: number | string;
  title?: string;
  /** Hidden from assistive technology when a parent already names the symbol. */
  decorative?: boolean;
  className?: string;
};

/** One mana symbol; an unknown symbol is shown as its text on the generic circle. */
export function ManaSymbol({ symbol, size = 24, title, decorative = false, className }: ManaSymbolProps) {
  const clipId = useId();
  const parsed = parseManaSymbol(symbol);
  const label = title ?? (parsed ? spokenSymbol(parsed) : symbol);
  const style: CSSProperties = { width: size, height: size };
  const a11y = decorative ? { "aria-hidden": true } : { role: "img", "aria-label": label };
  const image = parsed ? sheetImage(parsed) : undefined;
  if (image) {
    return (
      <img
        src={image}
        alt={decorative ? "" : label}
        title={title}
        className={[styles.symbol, className].filter(Boolean).join(" ")}
        style={style}
        draggable={false}
      />
    );
  }
  return (
    <svg viewBox="0 0 100 100" className={[styles.symbol, className].filter(Boolean).join(" ")} style={style} focusable="false" {...a11y}>
      {title && !decorative ? <title>{title}</title> : null}
      {parsed ? (
        <SymbolArt parsed={parsed} clipId={clipId} />
      ) : (
        <>
          <circle cx="50" cy="50" r="50" fill={MANA_FILL.generic} />
          <PieceGlyph text={symbol.replace(/[{}]/g, "").slice(0, 3)} phyrexian={false} hole={MANA_FILL.generic} />
        </>
      )}
    </svg>
  );
}

/** A whole cost such as "{2}{G}{G}", named once for assistive technology; other text is shown as sent. */
export function ManaCostSymbols({ cost, size = 20, className }: { cost: string; size?: number | string; className?: string }) {
  const symbols = parseManaCost(cost);
  if (!symbols) return <span className={className}>{cost}</span>;
  const spoken = symbols.map((symbol) => {
    const parsed = parseManaSymbol(symbol);
    return parsed ? spokenSymbol(parsed) : symbol;
  });
  return (
    <span className={[styles.cost, className].filter(Boolean).join(" ")} role="img" aria-label={`Mana cost: ${spoken.join(", ")}`} title={cost}>
      {symbols.map((symbol, index) => (
        <ManaSymbol key={index} symbol={symbol} size={size} decorative />
      ))}
    </span>
  );
}
