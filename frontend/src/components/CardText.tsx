// The card text in rules format, in the manner of a card page on Scryfall (spec "Screens", Result).
import { useId } from "react";

import type { CardVersion } from "../api/types";
import { cx } from "./classNames";
import styles from "./CardText.module.css";
import { ManaCost } from "./ManaCost";

/** See spec RN-48. */
const ARTIST = "Card Factory";

/** Name, mana cost, type line, rules text one paragraph per line, artist, and power and toughness. */
export function CardText({ version }: { version: CardVersion }) {
  const nameId = useId();
  const lines = version.rules_text.split("\n").filter((line) => line.trim() !== "");
  const hasPowerToughness = version.power !== null && version.toughness !== null;
  // The spaces between blocks keep words apart when the text is copied or read as one string.
  return (
    <article className={styles.card} aria-labelledby={nameId}>
      <div className={cx(styles.row, styles.title)}>
        <h2 id={nameId} className={styles.name}>
          {version.name}
        </h2>{" "}
        {version.mana_cost !== null && <ManaCost cost={version.mana_cost} />}
      </div>{" "}
      <p className={cx(styles.row, styles.type)}>{version.type_line}</p>{" "}
      {lines.length > 0 && (
        <div className={cx(styles.row, styles.rules)}>
          {lines.map((line, index) => (
            <p key={index}>{line}</p>
          ))}
        </div>
      )}{" "}
      <div className={cx(styles.row, styles.foot)}>
        <p className={styles.artist}>
          Illustrated by <span className={styles.artistName}>{ARTIST}</span>
        </p>{" "}
        {hasPowerToughness && <p className={styles.powerToughness}>{`${version.power}/${version.toughness}`}</p>}
      </div>
    </article>
  );
}
