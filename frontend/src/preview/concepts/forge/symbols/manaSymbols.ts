// Concept D "Forge" (tasks.md T251): parsing of mana symbols in brace notation, their colors and spoken names.

export type ManaColor = "W" | "U" | "B" | "R" | "G" | "C";

export type SpecialSymbol = "T" | "Q" | "S" | "E";

/** One half of a symbol: a color, or generic mana written as a number or a letter such as X. */
export type ManaPiece = { kind: "color"; color: ManaColor } | { kind: "generic"; text: string };

export type ParsedSymbol =
  | { kind: "mana"; pieces: [ManaPiece] | [ManaPiece, ManaPiece]; phyrexian: boolean }
  | { kind: "special"; special: SpecialSymbol };

/** Circle fills sampled from the reference sheet; C shares the generic gray. */
export const MANA_FILL: Record<ManaColor | "generic", string> = {
  W: "#f8f6d8",
  U: "#c1d7e9",
  B: "#bab1ab",
  R: "#e49977",
  G: "#a3c095",
  C: "#cac5c0",
  generic: "#cac5c0",
};

export const GLYPH_INK = "#0d0f0f";

export const COLOR_NAMES: Record<ManaColor, string> = {
  W: "white",
  U: "blue",
  B: "black",
  R: "red",
  G: "green",
  C: "colorless",
};

const NUMBER_WORDS = [
  "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
  "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty",
];

const SPECIAL_NAMES: Record<SpecialSymbol, string> = { T: "tap", Q: "untap", S: "snow mana", E: "energy" };

const COLORS = new Set<string>(["W", "U", "B", "R", "G", "C"]);
const SPECIALS = new Set<string>(["T", "Q", "S", "E"]);
const GENERIC = /^(\d{1,3}|[XYZ])$/;

function pieceOf(part: string): ManaPiece | null {
  if (COLORS.has(part)) return { kind: "color", color: part as ManaColor };
  if (GENERIC.test(part)) return { kind: "generic", text: String(/^\d+$/.test(part) ? Number(part) : part) };
  return null;
}

/** One symbol such as "{2/G}" or "w/u"; null when it is not a symbol this set draws. */
export function parseManaSymbol(symbol: string): ParsedSymbol | null {
  const body = symbol.trim().replace(/^\{(.*)\}$/, "$1").toUpperCase();
  if (SPECIALS.has(body)) return { kind: "special", special: body as SpecialSymbol };
  if (body === "P") return { kind: "mana", pieces: [{ kind: "color", color: "C" }], phyrexian: true };
  const parts = body.split("/");
  const phyrexian = parts.length > 1 && parts[parts.length - 1] === "P";
  const halves = phyrexian ? parts.slice(0, -1) : parts;
  if (halves.length < 1 || halves.length > 2) return null;
  const pieces = halves.map(pieceOf);
  const [first, second] = pieces;
  if (!first || pieces.includes(null)) return null;
  if (!second) return { kind: "mana", pieces: [first], phyrexian };
  // Only a color can follow the slash: {W/U} and {2/G} exist, {G/2} and {X/Y} do not.
  if (second.kind !== "color" || second.color === "C" || (first.kind === "color" && first.color === second.color)) {
    return null;
  }
  return { kind: "mana", pieces: [first, second], phyrexian };
}

function spokenPiece(piece: ManaPiece): string {
  if (piece.kind === "color") return COLOR_NAMES[piece.color];
  const number = /^\d+$/.test(piece.text) ? Number(piece.text) : null;
  if (number === null) return piece.text;
  return `${NUMBER_WORDS[number] ?? piece.text} generic`;
}

/** The accessible name of a parsed symbol: "green mana", "two generic mana", "white or blue hybrid mana". */
export function spokenSymbol(parsed: ParsedSymbol): string {
  if (parsed.kind === "special") return SPECIAL_NAMES[parsed.special];
  const words = parsed.pieces.map(spokenPiece).join(" or ");
  const hybrid = parsed.pieces.length === 2 ? " hybrid" : "";
  return `${parsed.phyrexian ? "Phyrexian " : ""}${words}${hybrid} mana`;
}

/** The symbols of a whole cost such as "{2}{G}{G}"; null when the text is not made only of known symbols. */
export function parseManaCost(cost: string): string[] | null {
  const symbols = [...cost.matchAll(/\{([^{}]+)\}/g)].map((match) => `{${match[1] ?? ""}}`);
  if (symbols.length === 0 || symbols.join("") !== cost.replace(/\s+/g, "")) return null;
  return symbols.every((symbol) => parseManaSymbol(symbol) !== null) ? symbols : null;
}
