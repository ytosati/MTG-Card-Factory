// Concept A "Nocturne" (tasks.md T251): static mockups of the Request, generating and Result screens.
// Local state only; nothing here calls the API.
import { useId, useState } from "react";

import type { PowerIndicator, PowerLevel } from "../../../api/types";
import type { GenerationEffort } from "../../../screens/request/copy";
import { cardWithImage } from "../../fixtures";
import type { PreviewCard } from "../../fixtureTypes";
import card from "./card.module.css";
import { CardStage, GEM_NAMES, GemStone, NocturneCard, Shell, type GemColor } from "./parts";
import styles from "./nocturne.module.css";

const IDEA =
  "A lantern-bearing spirit that keeps watch at the city gate and steadies the soldiers who stand beside it.";

/** The sample card of the Result mockup: the fixture with art, given a power justification. */
export const RESULT_CARD: PreviewCard = {
  ...cardWithImage,
  current_version: {
    ...cardWithImage.current_version,
    power_justification: "A steady defender for four mana, in line with other white soldiers that lift a team.",
  },
};

const POWER_CHOICES: [PowerLevel, string][] = [
  ["casual", "Casual"],
  ["medium", "Medium"],
  ["strong", "Strong"],
];

const EFFORT_CHOICES: [GenerationEffort, string][] = [
  ["low", "Low"],
  ["medium", "Medium"],
  ["high", "High"],
];

const INDICATOR_WORDS: [PowerIndicator, string][] = [
  ["too_weak", "Too weak"],
  ["in_range", "In range"],
  ["too_strong", "Too strong"],
];

const CHECK_WORDS: Record<string, string> = {
  mana_cost: "Mana cost",
  color_identity: "Color identity",
};

function Segmented<T extends string>(props: {
  legend: string;
  choices: [T, string][];
  value: T;
  onChange: (value: T) => void;
  hint?: string;
}) {
  const name = useId();
  return (
    <fieldset className={styles.fieldset}>
      <legend className={styles.rubric}>{props.legend}</legend>
      <div className={styles.segments}>
        {props.choices.map(([value, word]) => (
          <label key={value} className={styles.segment}>
            <input
              className={styles.srOnly}
              type="radio"
              name={name}
              value={value}
              checked={props.value === value}
              onChange={() => props.onChange(value)}
            />
            {word}
          </label>
        ))}
      </div>
      {props.hint && <p className={styles.hint}>{props.hint}</p>}
    </fieldset>
  );
}

function Corners() {
  return (
    <>
      {["tl", "tr", "bl", "br"].map((at) => (
        <span key={at} className={styles.corner} data-at={at} aria-hidden="true" />
      ))}
    </>
  );
}

/** The Request screen: the idea as the hero, colors as gems, power and effort as segmented choices. */
export function RequestMockup() {
  const [idea, setIdea] = useState(IDEA);
  const [colors, setColors] = useState<GemColor[]>(["W"]);
  const [colorless, setColorless] = useState(false);
  const [power, setPower] = useState<PowerLevel>("medium");
  const [effort, setEffort] = useState<GenerationEffort>("medium");
  const ideaId = useId();
  const hintId = useId();

  function toggle(color: GemColor) {
    setColorless(false);
    setColors((current) => (current.includes(color) ? current.filter((c) => c !== color) : [...current, color]));
  }

  return (
    <Shell current="Request">
      <div className={styles.requestGrid}>
        <div>
          <p className={styles.rubric}>New card</p>
          <h1 className={styles.display}>Request a card</h1>
          <form className={styles.form} onSubmit={(event) => event.preventDefault()}>
            <div>
              <label className={`${styles.rubric} ${styles.ideaLabel}`} htmlFor={ideaId}>
                Idea
              </label>
              <textarea
                id={ideaId}
                className={styles.idea}
                value={idea}
                onChange={(event) => setIdea(event.target.value)}
                aria-describedby={hintId}
                rows={4}
              />
              <p id={hintId} className={styles.hint}>
                Describe the card in a sentence or two: a mechanic, a creature or a moment.
              </p>
            </div>

            <fieldset className={styles.fieldset}>
              <legend className={styles.rubric}>Colors</legend>
              <div className={styles.gems}>
                {(Object.keys(GEM_NAMES) as GemColor[]).map((color) => (
                  <button
                    key={color}
                    type="button"
                    className={styles.gemButton}
                    aria-pressed={colors.includes(color)}
                    onClick={() => toggle(color)}
                  >
                    <GemStone color={color} />
                    {GEM_NAMES[color]}
                  </button>
                ))}
                <span className={styles.gemDivider} aria-hidden="true" />
                <button
                  type="button"
                  className={styles.gemButton}
                  aria-pressed={colorless}
                  onClick={() => {
                    setColorless(!colorless);
                    setColors([]);
                  }}
                >
                  <GemStone color="C" />
                  Colorless
                </button>
              </div>
            </fieldset>

            <div className={styles.choiceRow}>
              <Segmented legend="Power" choices={POWER_CHOICES} value={power} onChange={setPower} />
              <Segmented
                legend="Effort"
                choices={EFFORT_CHOICES}
                value={effort}
                onChange={setEffort}
                hint="Higher effort takes longer and uses more tokens."
              />
            </div>

            <div className={styles.actions}>
              <button type="submit" className={styles.primary}>
                Generate card
              </button>
            </div>
          </form>
        </div>

        <div className={styles.waitingSlot}>
          <div className={styles.emptySlot}>
            <Corners />
            <p>The card appears here.</p>
          </div>
        </div>
      </div>
    </Shell>
  );
}

const STEPS: [label: string, state: "done" | "running" | "waiting"][] = [
  ["Write the card", "done"],
  ["Check the rules", "running"],
  ["Paint the art", "waiting"],
];

/** The wait: the card slot draws its frame and light passes over it, beside the steps of the job. */
export function GeneratingMockup() {
  return (
    <Shell current="Request">
      <div className={styles.resultGrid}>
        <CardStage>
          <div className={card.slot}>
            <svg viewBox="0 0 63 88" preserveAspectRatio="none" aria-hidden="true" focusable="false">
              <rect className={card.slotLine} data-order="0" x="1.5" y="1.5" width="60" height="85" rx="2.2" pathLength="1" />
              <rect className={card.slotLine} data-order="1" x="4" y="10" width="55" height="38" rx="0.8" pathLength="1" />
              <line className={card.slotLine} data-order="2" x1="4" y1="52" x2="59" y2="52" pathLength="1" />
              <rect className={card.slotLine} data-order="3" x="4" y="56" width="55" height="23" rx="0.8" pathLength="1" />
              <line className={card.slotLine} data-order="4" x1="5" y1="6" x2="38" y2="6" pathLength="1" />
            </svg>
            <span className={card.slotSweep} aria-hidden="true" />
          </div>
        </CardStage>

        <div className={styles.label}>
          <div className={styles.labelHead}>
            <p className={styles.rubric}>Step 2 of 3</p>
            <h1 className={styles.display}>Generating</h1>
          </div>
          <ol className={styles.steps} role="status" aria-label="Steps">
            {STEPS.map(([label, state]) => (
              <li key={label} className={styles.step} data-state={state}>
                <span className={styles.stepDot} aria-hidden="true" />
                <span>
                  {label}
                  <span className={styles.srOnly}>
                    {state === "done" ? ", done" : state === "running" ? ", in progress" : ", waiting"}
                  </span>
                </span>
              </li>
            ))}
          </ol>
          <blockquote className={styles.quote}>{IDEA}</blockquote>
        </div>
      </div>
    </Shell>
  );
}

function CheckIcon() {
  return (
    <svg className={styles.markIcon} viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      <path d="M3 8.5 L6.5 12 L13 4.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

/** The Result screen: the card lands on its table; its label and the panels sit beside it. */
export function ResultMockup() {
  const version = RESULT_CARD.current_version;
  const usage = RESULT_CARD.usage.text[0];
  const indicator = INDICATOR_WORDS.find(([value]) => value === version.power_indicator)?.[1] ?? "";
  return (
    <Shell current="Request">
      <div className={styles.resultGrid}>
        <CardStage landing>
          <NocturneCard entry={RESULT_CARD} />
        </CardStage>

        <div className={styles.label}>
          <div className={styles.labelHead}>
            <p className={styles.rubric}>Result</p>
            <h1 className={styles.display}>{version.name}</h1>
            <p className={styles.typeMeta}>
              {version.type_line} · Mana value {version.mana_value}
            </p>
            <ul className={styles.marks} aria-label="Summary">
              <li className={`${styles.mark} ${styles.approved}`}>
                <CheckIcon />
                Approved
              </li>
              <li className={styles.mark}>Power {indicator.toLowerCase()}</li>
            </ul>
          </div>

          <section className={styles.panel} aria-labelledby="nocturne-validation">
            <h2 id="nocturne-validation" className={styles.panelTitle}>
              Validation
            </h2>
            <p className={styles.panelText}>Every check passed.</p>
            <ul className={styles.checks}>
              {version.validation.checks_run.map((check) => (
                <li key={check}>
                  <span className={styles.approved}>
                    <CheckIcon />
                  </span>
                  {CHECK_WORDS[check] ?? check}
                </li>
              ))}
            </ul>
          </section>

          <section className={styles.panel} aria-labelledby="nocturne-power">
            <h2 id="nocturne-power" className={styles.panelTitle}>
              Power
            </h2>
            <ol className={styles.scale} aria-label="Power assessment">
              {INDICATOR_WORDS.map(([value, word]) => (
                <li key={value} aria-current={value === version.power_indicator ? "true" : undefined}>
                  {word}
                </li>
              ))}
            </ol>
            <p className={styles.panelText}>{version.power_justification}</p>
          </section>

          {usage && (
            <section className={styles.panel} aria-labelledby="nocturne-usage">
              <h2 id="nocturne-usage" className={styles.panelTitle}>
                Text usage
              </h2>
              <dl className={styles.usage}>
                <dt>Model</dt>
                <dd>{usage.model}</dd>
                <dt>Input tokens</dt>
                <dd>{usage.input_tokens.toLocaleString("en-US")}</dd>
                <dt>Output tokens</dt>
                <dd>{usage.output_tokens.toLocaleString("en-US")}</dd>
              </dl>
            </section>
          )}

          <div className={styles.actions}>
            <button type="button" className={styles.primary}>
              Generate again
            </button>
            <button type="button" className={styles.secondary}>
              New request
            </button>
          </div>
        </div>
      </div>
    </Shell>
  );
}
