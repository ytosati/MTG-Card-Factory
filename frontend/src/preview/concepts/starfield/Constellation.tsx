// Concept E "Starfield" (tasks.md T251): the color identity as a constellation: chosen symbols are joined by thin lines.
import { requestCopy } from "../../../screens/request/copy";
import { ManaPick } from "../forge/symbols/ManaPick";
import type { ManaColor } from "../forge/symbols/manaSymbols";
import styles from "./constellation.module.css";

const COLORS = requestCopy.colors;

/** How far each of W U B R G sits below the row's top, in pixels, so the five read as a figure, not a toolbar. */
const DRIFT = [14, 0, 26, 4, 18] as const;

/** The symbol's size and the pick's top padding, in pixels; they place the lines on the symbols' centres. */
const SYMBOL = 48;
const PAD = 6;

function centreY(index: number): number {
  return (DRIFT[index] ?? 0) + PAD + SYMBOL / 2;
}

/** The five colors joined in W U B R G order, and Colorless apart; Colorless clears the colors and the reverse. */
export function Constellation(props: { colors: ManaColor[]; onChange: (colors: ManaColor[]) => void; describedBy: string; labelledBy: string }) {
  const chosen = COLORS.map((color, index) => ({ ...color, index })).filter((color) => props.colors.includes(color.letter));
  const share = 100 / COLORS.length;
  const x = (index: number) => `${(index + 0.5) * share}%`;

  function pick(letter: ManaColor, checked: boolean) {
    if (letter === "C") {
      props.onChange(checked ? ["C"] : []);
      return;
    }
    const colored = props.colors.filter((entry) => entry !== "C");
    props.onChange(checked ? [...colored, letter] : colored.filter((entry) => entry !== letter));
  }

  return (
    <fieldset className={styles.sky} aria-labelledby={props.labelledBy} aria-describedby={props.describedBy}>
      <div className={styles.five}>
        <svg className={styles.lines} aria-hidden="true" focusable="false">
          {chosen.slice(1).map((color, step) => {
            const from = chosen[step]!;
            return (
              <line
                key={`${from.letter}${color.letter}`}
                x1={x(from.index)}
                y1={centreY(from.index)}
                x2={x(color.index)}
                y2={centreY(color.index)}
                pathLength={1}
                className={styles.line}
              />
            );
          })}
        </svg>
        {COLORS.map((color, index) => (
          <span key={color.letter} className={styles.slot} style={{ paddingTop: DRIFT[index] }}>
            <ManaPick letter={color.letter} label={color.name} checked={props.colors.includes(color.letter)} onChange={(checked) => pick(color.letter, checked)} sound={false} />
          </span>
        ))}
      </div>
      <span className={styles.or} aria-hidden="true">
        {requestCopy.or}
      </span>
      <span className={styles.slot}>
        <ManaPick letter="C" label={requestCopy.colorless} checked={props.colors.includes("C")} onChange={(checked) => pick("C", checked)} sound={false} />
      </span>
    </fieldset>
  );
}
