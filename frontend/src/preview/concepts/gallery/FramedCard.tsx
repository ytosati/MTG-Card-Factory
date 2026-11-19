// Concept C, "Gallery Wall" (tasks.md T251): a card hung as a framed print, with the mat, the moulding and the cords.
import type { CSSProperties, ReactNode } from "react";

import { ManaCost } from "../../../components/ManaCost";
import type { PreviewCard } from "../../fixtureTypes";
import styles from "./framedCard.module.css";
import type { Wall } from "./palette";

type CardStyle = CSSProperties & Record<`--${string}`, string>;

/** The frame, the mat and the window; `arriving` plays the short weighted hang once. */
export function Frame({
  children,
  arriving = false,
  built = 3,
}: {
  children: ReactNode;
  arriving?: boolean;
  built?: number;
}) {
  return (
    <div className={styles.hang} data-arriving={arriving ? "true" : "false"} data-built={built}>
      <span className={styles.cords} aria-hidden="true" />
      <div className={styles.frame}>
        <div className={styles.mat}>
          <div className={styles.window}>{children}</div>
        </div>
      </div>
    </div>
  );
}

/** The face of a card in the concept's own frame: full-bleed art, a name plate and a text plate in paper. */
export function CardFace({ card, walls }: { card: PreviewCard; walls: [Wall, Wall] }) {
  const version = card.current_version;
  const tint: CardStyle = { "--card-a": walls[0].paint, "--card-b": walls[1].paint };
  const lines = version.rules_text.split("\n");
  return (
    <div className={styles.card} style={tint}>
      {card.image ? (
        <img className={styles.art} src={card.image.src} alt={card.image.alt} width={745} height={1040} />
      ) : (
        <span className={styles.art} aria-hidden="true" />
      )}
      <div className={styles.namePlate}>
        <span className={styles.cardName}>{version.name}</span>
        {version.mana_cost !== null && <ManaCost cost={version.mana_cost} />}
      </div>
      <div className={styles.textPlate}>
        <p className={styles.typeLine}>{version.type_line}</p>
        {lines.map((line, index) => (
          <p key={index} className={styles.rules}>
            {line}
          </p>
        ))}
      </div>
      {version.power !== null && version.toughness !== null && (
        <span className={styles.pt} aria-label={`Power ${version.power}, toughness ${version.toughness}`}>
          {`${version.power}/${version.toughness}`}
        </span>
      )}
    </div>
  );
}

/** The empty canvas in the window while a card is generated: sketched plates that fill in step by step. */
export function Canvas({ step }: { step: number }) {
  return (
    <div className={styles.canvas} data-step={step} aria-hidden="true">
      <span className={styles.sketchName} />
      <span className={styles.sketchArt} />
      <span className={styles.sketchLine} />
      <span className={styles.sketchLine} />
      <span className={styles.sketchLine} />
    </div>
  );
}
