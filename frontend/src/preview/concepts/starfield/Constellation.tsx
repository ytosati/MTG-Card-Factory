// Concept E "Starfield" (tasks.md T251): the color identity: the five colors in one aligned row, and Colorless apart.
import { requestCopy } from "../../../screens/request/copy";
import { ManaPick } from "./symbols/ManaPick";
import type { ManaColor } from "./symbols/manaSymbols";
import styles from "./constellation.module.css";

const COLORS = requestCopy.colors;

/** The five colors in W U B R G order, and Colorless apart; Colorless clears the colors and the reverse. */
export function Constellation(props: { colors: ManaColor[]; onChange: (colors: ManaColor[]) => void; describedBy: string; labelledBy: string }) {
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
        {COLORS.map((color) => (
          <span key={color.letter} className={styles.slot}>
            <ManaPick letter={color.letter} label={color.name} checked={props.colors.includes(color.letter)} onChange={(checked) => pick(color.letter, checked)} />
          </span>
        ))}
      </div>
      <span className={styles.or} aria-hidden="true">
        {requestCopy.or}
      </span>
      <span className={styles.slot}>
        <ManaPick letter="C" label={requestCopy.colorless} checked={props.colors.includes("C")} onChange={(checked) => pick("C", checked)} />
      </span>
    </fieldset>
  );
}
