// A mana cost drawn as symbols, with the cost in rules format kept as text and spoken as words.
import { cx } from "./classNames";
import styles from "./ManaCost.module.css";
import { VisuallyHidden } from "./VisuallyHidden";

const MANA_SYMBOL = /\{([^{}]+)\}/g;

const SYMBOL_COLORS = new Set(["W", "U", "B", "R", "G", "C"]);

const SPOKEN_PARTS: Record<string, string> = {
  W: "white",
  U: "blue",
  B: "black",
  R: "red",
  G: "green",
  C: "colorless",
  S: "snow",
};

/** One symbol in words: {2} "2 generic", {W/U} "white or blue", {G/P} "Phyrexian green". */
function spokenSymbol(symbol: string): string {
  const parts = symbol.toUpperCase().split("/");
  const phyrexian = parts.length > 1 && parts.includes("P");
  const words = parts
    .filter((part) => !phyrexian || part !== "P")
    .map((part) => SPOKEN_PARTS[part] ?? (/^\d+$/.test(part) ? `${part} generic` : part));
  const spoken = words.join(" or ");
  return phyrexian ? `Phyrexian ${spoken}` : spoken;
}

/** The fill of one half of a symbol: a color, or the generic fill for numbers and letters such as X. */
function fillOf(part: string): string {
  return SYMBOL_COLORS.has(part) ? part.toLowerCase() : "generic";
}

/** A mana cost; anything outside braces is not a cost written in symbols and is shown as it was sent. */
export function ManaCost({ cost }: { cost: string }) {
  const symbols = [...cost.matchAll(MANA_SYMBOL)].map((match) => match[1] ?? "");
  if (symbols.length === 0 || symbols.map((symbol) => `{${symbol}}`).join("") !== cost) {
    return <span className={cx(styles.cost, styles.plain)}>{cost}</span>;
  }
  return (
    <span className={styles.cost} role="img" aria-label={`Mana cost: ${symbols.map(spokenSymbol).join(", ")}`} title={cost}>
      <VisuallyHidden>{cost}</VisuallyHidden>
      <span className={styles.symbols}>
        {symbols.map((symbol, index) => (
          <ManaSymbol key={index} symbol={symbol} />
        ))}
      </span>
    </span>
  );
}

function ManaSymbol({ symbol }: { symbol: string }) {
  const parts = symbol.toUpperCase().split("/");
  // The P of a Phyrexian symbol is a mark, not a half: {G/P} is filled green.
  const fills = parts.filter((part) => parts.length === 1 || part !== "P").map(fillOf);
  const first = fills[0] ?? "generic";
  const second = fills[1];
  return (
    <span
      className={cx(
        styles.symbol,
        styles[`mana-${first}`],
        second !== undefined && second !== first && styles[`hybrid-${second}`],
        parts.length > 1 && styles.split,
      )}
    >
      {symbol}
    </span>
  );
}
