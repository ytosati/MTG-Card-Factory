// Concept D "Forge" (tasks.md T251): the Result screen; the card at the centre of a lit stage, its text beside it.
import { useRef, type PointerEvent } from "react";

import { resultCopy } from "../../../../screens/result/copy";
import { cardWithImage } from "../../../fixtures";
import type { PreviewCard } from "../../../fixtureTypes";
import { ManaCostSymbols } from "../symbols/ManaSymbol";
import { ForgeCardFace } from "./ForgeCard";
import { useMotionOff } from "./motion";
import { PowerGauge, SmallGauge } from "./ornaments";
import { Engraved, Shell, shell } from "./Shell";
import styles from "./result.module.css";

/** The largest tilt of the card, in degrees, at the edge of the stage. */
const MAX_TILT = 6;

export const RESULT_CARD: PreviewCard = {
  ...cardWithImage,
  current_version: {
    ...cardWithImage.current_version,
    power_justification: "A steady defender for four mana, in line with other white soldiers that lift a team.",
  },
};

const CHECK_WORDS: Record<string, string> = { mana_cost: "Mana cost", color_identity: "Color identity" };
const RARITY_WORDS: Record<string, string> = { common: "Common", uncommon: "Uncommon", rare: "Rare", mythic: "Mythic" };
const COUNT = new Intl.NumberFormat("en-US");

function Check() {
  return (
    <svg className={styles.check} viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      <path d="M3 8.5 L6.5 12 L13 4.5" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="square" />
    </svg>
  );
}

/** The stage: soft light from above, a pipe along the top; a mouse tilts the card toward the pointer. */
function Stage({ entry }: { entry: PreviewCard }) {
  const [stage, motionOff] = useMotionOff<HTMLDivElement>();
  const card = useRef<HTMLDivElement>(null);

  function onPointerMove(event: PointerEvent<HTMLDivElement>) {
    const element = stage.current;
    const target = card.current;
    if (element === null || target === null || event.pointerType !== "mouse" || motionOff) return;
    const box = element.getBoundingClientRect();
    const x = Math.min(Math.max((event.clientX - box.left) / box.width, 0), 1);
    const y = Math.min(Math.max((event.clientY - box.top) / box.height, 0), 1);
    target.style.transform = `rotateX(${((0.5 - y) * 2 * MAX_TILT).toFixed(2)}deg) rotateY(${((x - 0.5) * 2 * MAX_TILT).toFixed(2)}deg)`;
    target.style.setProperty("--sheen-x", `${(x * 100).toFixed(1)}%`);
  }

  function onPointerLeave() {
    const target = card.current;
    if (target === null) return;
    target.style.removeProperty("transform");
    target.style.removeProperty("--sheen-x");
  }

  return (
    <div ref={stage} className={styles.stage} onPointerMove={onPointerMove} onPointerLeave={onPointerLeave}>
      <span className={styles.pipe} aria-hidden="true">
        <span className={styles.collar} data-at="1" />
        <span className={styles.collar} data-at="2" />
        <SmallGauge className={styles.gauge} />
      </span>
      <div className={styles.cardWrap}>
        <span className={styles.shadow} aria-hidden="true" />
        <div ref={card} className={styles.tilt}>
          <ForgeCardFace entry={entry} />
        </div>
      </div>
    </div>
  );
}

/** The Result screen: the card, then its text as plain rows, its checks, power and usage. */
export function ResultScreen() {
  const entry = RESULT_CARD;
  const version = entry.current_version;
  const usage = entry.usage.text;
  const total = usage.reduce(
    (sum, record) => ({ input: sum.input + record.input_tokens, output: sum.output + record.output_tokens }),
    { input: 0, output: 0 },
  );
  const hasBody = version.power !== null && version.toughness !== null;

  return (
    <Shell current="Request">
      <div className={styles.grid}>
        <Stage entry={entry} />

        <div className={styles.side}>
          <p className={shell.rubric}>{resultCopy.title}</p>
          <div className={styles.oracle}>
            <div className={styles.row} data-kind="name">
              <h1 className={styles.name}>{version.name}</h1>
              {version.mana_cost !== null && <ManaCostSymbols cost={version.mana_cost} size={22} />}
            </div>
            <p className={styles.row} data-kind="type">
              {version.type_line}
            </p>
            <div className={styles.row} data-kind="text">
              {version.rules_text.split("\n").map((line, index) => (
                <p key={index}>{line}</p>
              ))}
            </div>
            {hasBody && (
              <p className={styles.row} data-kind="body">
                {version.power}/{version.toughness}
              </p>
            )}
            <p className={styles.row} data-kind="meta">
              <span>{RARITY_WORDS[version.rarity] ?? version.rarity}</span>
              <span>Mana value {version.mana_value}</span>
            </p>
          </div>

          <section className={styles.section} aria-labelledby="forge-validation">
            <Engraved id="forge-validation">Validation</Engraved>
            <p className={styles.verdict}>
              <span className={styles.approved}>{resultCopy.approved}</span>{" "}
              {resultCopy.checksPassed(version.validation.checks_run.length)}
            </p>
            <ul className={styles.checks}>
              {version.validation.checks_run.map((check) => (
                <li key={check}>
                  <Check />
                  {CHECK_WORDS[check] ?? check}
                </li>
              ))}
            </ul>
          </section>

          <section className={styles.section} aria-labelledby="forge-power">
            <Engraved id="forge-power">{resultCopy.powerHeading}</Engraved>
            <div className={styles.power}>
              <figure className={styles.dial}>
                <PowerGauge indicator={version.power_indicator} className={styles.gaugeArt} />
                <ol className={styles.scale} aria-label="Power assessment">
                  {(["too_weak", "in_range", "too_strong"] as const).map((value) => (
                    <li key={value} aria-current={value === version.power_indicator ? "true" : undefined}>
                      {resultCopy.powerWords[value]}
                    </li>
                  ))}
                </ol>
              </figure>
              <div>
                <p className={styles.powerText}>{version.power_justification || resultCopy.noJustification}</p>
                <p className={shell.hint}>{resultCopy.powerHint}</p>
              </div>
            </div>
          </section>

          <section className={styles.section} aria-labelledby="forge-usage">
            <Engraved id="forge-usage">{resultCopy.usageHeading}</Engraved>
            {usage.length === 0 ? (
              <p className={shell.hint}>{resultCopy.noUsage}</p>
            ) : (
              <dl className={styles.usage}>
                <div>
                  <dt>Model</dt>
                  <dd>{usage[0]?.model}</dd>
                </div>
                <div>
                  <dt>{resultCopy.usageInput}</dt>
                  <dd className={styles.num}>{COUNT.format(total.input)}</dd>
                </div>
                <div>
                  <dt>{resultCopy.usageOutput}</dt>
                  <dd className={styles.num}>{COUNT.format(total.output)}</dd>
                </div>
              </dl>
            )}
          </section>

          <div className={styles.actions}>
            <button type="button" className={shell.primary}>
              Generate again
            </button>
            <a className={shell.secondary} href="#/preview/concept-forge/request">
              New request
            </a>
          </div>
        </div>
      </div>
    </Shell>
  );
}
