// Concept C, "Gallery Wall" (tasks.md T251): the Result screen as an exhibition. The wall takes the card's colors,
// the card hangs framed beside its museum label, and the notes follow as an editorial spread. A static mockup.
import { ManaCost } from "../../../components/ManaCost";
import type { PowerIndicator } from "../../../api/types";
import type { PreviewCard } from "../../fixtureTypes";
import { CardFace, Frame } from "./FramedCard";
import { identityOf, wallStyle, wallsOf } from "./palette";
import styles from "./result.module.css";
import wall from "./wall.module.css";

const COUNT = new Intl.NumberFormat("en-US");

const RARITY: Record<string, string> = { common: "Common", uncommon: "Uncommon", rare: "Rare", mythic: "Mythic" };

const SCALE: { value: PowerIndicator; name: string }[] = [
  { value: "too_weak", name: "Too weak" },
  { value: "in_range", name: "In range" },
  { value: "too_strong", name: "Too strong" },
];

const CHECK_NAMES: Record<string, string> = { mana_cost: "Mana cost", color_identity: "Color identity" };

export function GalleryResult({ card }: { card: PreviewCard }) {
  const version = card.current_version;
  const walls = wallsOf(identityOf(version.mana_cost, version.rules_text));
  const [left, right] = walls;
  const approved = version.validation.status === "approved";
  const indicator = SCALE.find((entry) => entry.value === version.power_indicator) ?? SCALE[1]!;
  const tokensIn = card.usage.text.reduce((sum, record) => sum + record.input_tokens, 0);
  const tokensOut = card.usage.text.reduce((sum, record) => sum + record.output_tokens, 0);
  const hasPt = version.power !== null && version.toughness !== null;

  return (
    <div className={`${wall.root} ${styles.page}`} style={wallStyle(left)}>
      <div className={styles.hall}>
        <span className={styles.rail} aria-hidden="true" />
        <div className={`${wall.field} ${styles.hangZone}`} style={wallStyle(left)}>
          <span className={`${wall.bigNumeral} ${styles.manaNumeral}`} aria-hidden="true">
            {version.mana_value}
          </span>
          <div className={styles.hangSpot}>
            <Frame arriving>
              <CardFace card={card} walls={walls} />
            </Frame>
          </div>
        </div>

        <div className={`${wall.field} ${styles.labelZone}`} style={wallStyle(right)}>
          <p className={wall.caption}>Result · {RARITY[version.rarity] ?? version.rarity}</p>
          <h1 className={styles.name}>{version.name}</h1>
          {version.mana_cost !== null && (
            <div className={styles.cost}>
              <ManaCost cost={version.mana_cost} />
            </div>
          )}

          <section className={styles.plaque} aria-labelledby="gallery-plaque">
            <h2 id="gallery-plaque" className={styles.plaqueTitle}>
              Label
            </h2>
            <dl className={styles.facts}>
              <div>
                <dt>Type</dt>
                <dd>{version.type_line}</dd>
              </div>
              <div>
                <dt>Medium</dt>
                <dd className={styles.medium}>
                  {version.rules_text.split("\n").map((line, index) => (
                    <span key={index}>{line}</span>
                  ))}
                </dd>
              </div>
              {hasPt && (
                <div>
                  <dt>Power and toughness</dt>
                  <dd>{`${version.power}/${version.toughness}`}</dd>
                </div>
              )}
            </dl>
            <p className={styles.stamp} data-status={version.validation.status}>
              <span className={wall.hidden}>Validation: </span>
              <span className={styles.stampWord}>{approved ? "Approved" : "Rejected"}</span>
              <span className={styles.stampChecks}>
                {version.validation.checks_run.map((check) => CHECK_NAMES[check] ?? check).join(" · ")}
              </span>
            </p>
          </section>

          <section className={styles.power} aria-labelledby="gallery-power">
            <h2 id="gallery-power" className={wall.caption}>
              Power
            </h2>
            <p className={styles.powerReading}>{indicator.name}</p>
            <div className={styles.scale} aria-hidden="true">
              {SCALE.map((entry) => (
                <span key={entry.value} className={styles.scaleStep} data-on={entry.value === indicator.value}>
                  {entry.name}
                </span>
              ))}
            </div>
            {version.power_justification && <p className={styles.justification}>{version.power_justification}</p>}
          </section>
        </div>
      </div>

      <div className={styles.band}>
        <section className={styles.figures} aria-labelledby="gallery-figures">
          <h2 id="gallery-figures" className={wall.hidden}>
            Figures
          </h2>
          <dl className={styles.figureList}>
            <div>
              <dt>Mana value</dt>
              <dd>{version.mana_value}</dd>
            </div>
            {hasPt && (
              <div>
                <dt>Power / toughness</dt>
                <dd>{`${version.power}/${version.toughness}`}</dd>
              </div>
            )}
            <div>
              <dt>Tokens in</dt>
              <dd>{COUNT.format(tokensIn)}</dd>
            </div>
            <div>
              <dt>Tokens out</dt>
              <dd>{COUNT.format(tokensOut)}</dd>
            </div>
          </dl>
        </section>

        {version.design_intent && (
          <section className={`${styles.note} ${styles.noteLead}`} aria-labelledby="gallery-intent">
            <h2 id="gallery-intent" className={styles.noteTitle}>
              Design intent
            </h2>
            <p>{version.design_intent}</p>
          </section>
        )}
        {version.rationale && (
          <section className={styles.note} aria-labelledby="gallery-rationale">
            <h2 id="gallery-rationale" className={styles.noteTitle}>
              Rationale
            </h2>
            <p>{version.rationale}</p>
          </section>
        )}
        {version.comparables.length > 0 && (
          <section className={styles.note} aria-labelledby="gallery-compared">
            <h2 id="gallery-compared" className={styles.noteTitle}>
              Compared with
            </h2>
            <ol className={styles.comparables}>
              {version.comparables.map((comparable) => (
                <li key={comparable.oracle_id}>
                  <span className={styles.comparableName}>{comparable.name}</span>
                  <span className={styles.comparableRole}>{comparable.role}</span>
                </li>
              ))}
            </ol>
          </section>
        )}

        <div className={styles.bandActions}>
          <button type="button" className={wall.quietAction}>
            Edit the request
          </button>
        </div>
      </div>
    </div>
  );
}
