// Concept B "Drafting Table" (tasks.md T251): the Request screen as a brief pinned to the mat. Local state only.
import { useId, useState } from "react";
import type { CSSProperties } from "react";

import type { ColorLetter, PowerLevel } from "../../../api/types";
import { cx } from "../../../components/classNames";
import { requestCopy } from "../../../screens/request/copy";
import type { GenerationEffort } from "../../../screens/request/copy";
import { CropMarks, Mat, MatFooter, Sheet, TitleBlock } from "./parts";
import styles from "./request.module.css";

const IDEA_MAX = 1_000;
const COUNT = new Intl.NumberFormat("en-US");

const SAMPLE_IDEA =
  "A night watchman spirit that keeps a lantern lit at the edge of a ruined town. It protects the other " +
  "creatures more than it attacks, and it should feel calm rather than grim.";

/** The measure printed under each effort station: how many related cards the generation compares with. */
const EFFORT_MEASURE: Record<GenerationEffort, string> = { low: "≤ 8 cards", medium: "≤ 20 cards", high: "≤ 40 cards" };
const POWER_MEASURE: Record<PowerLevel, string> = { casual: "level 1", medium: "level 2", strong: "level 3" };

export function RequestMockup() {
  const [idea, setIdea] = useState(SAMPLE_IDEA);
  const [colors, setColors] = useState<ColorLetter[]>(["W"]);
  const [colorless, setColorless] = useState(false);
  const [power, setPower] = useState<PowerLevel>("medium");
  const [effort, setEffort] = useState<GenerationEffort>("medium");
  const ideaId = useId();
  const countId = useId();

  function toggleColor(letter: ColorLetter) {
    setColorless(false);
    setColors((current) => (current.includes(letter) ? current.filter((each) => each !== letter) : [...current, letter]));
  }

  const ideaLength = [...idea].length;
  const colorReading = colorless
    ? "Colorless"
    : colors.length === 0
      ? "Not chosen"
      : requestCopy.colors
          .filter((color) => colors.includes(color.letter))
          .map((color) => color.name)
          .join(" · ");

  return (
    <Mat
      current="request"
      sheetLabel="Sheet 01 · New card"
      title="Request"
      titleNote="Idea, colors and power are required. Everything else is optional."
    >
      <form className={styles.layout} onSubmit={(event) => event.preventDefault()} noValidate>
        <Sheet className={styles.brief} aria-labelledby={`${ideaId}-brief`}>
          <CropMarks />
          <h2 id={`${ideaId}-brief`} className={styles.sheetHeading}>
            Brief
          </h2>

          <div className={styles.block}>
            <label className={styles.label} htmlFor={ideaId}>
              <span className={styles.num}>01</span>
              {requestCopy.fieldLabels.idea}
            </label>
            <textarea
              id={ideaId}
              className={styles.idea}
              rows={6}
              value={idea}
              onChange={(event) => setIdea(event.target.value)}
              aria-describedby={countId}
            />
            <p id={countId} className={cx(styles.count, ideaLength > IDEA_MAX && styles.countOver)}>
              {COUNT.format(ideaLength)} / {COUNT.format(IDEA_MAX)} characters
            </p>
          </div>

          <fieldset className={styles.block}>
            <legend className={styles.label}>
              <span className={styles.num}>02</span>
              {requestCopy.fieldLabels.color_identity}
            </legend>
            <div className={styles.colors}>
              {requestCopy.colors.map((color) => (
                <label key={color.letter} className={styles.color} data-mana={color.letter.toLowerCase()}>
                  <input
                    type="checkbox"
                    checked={!colorless && colors.includes(color.letter)}
                    onChange={() => toggleColor(color.letter)}
                  />
                  <DraftedCircle letter={color.letter} />
                  <span className={styles.colorName}>{color.name}</span>
                </label>
              ))}
              <span className={styles.or} aria-hidden="true">
                or
              </span>
              <label className={cx(styles.color, styles.colorless)} data-mana="c">
                <input
                  type="checkbox"
                  checked={colorless}
                  onChange={(event) => {
                    setColorless(event.target.checked);
                    if (event.target.checked) setColors([]);
                  }}
                />
                <DraftedCircle letter="C" diamond />
                <span className={styles.colorName}>{requestCopy.colorless}</span>
              </label>
            </div>
          </fieldset>

          <Scale
            number="03"
            legend={requestCopy.fieldLabels.power_level}
            options={requestCopy.powerLevels}
            measure={POWER_MEASURE}
            value={power}
            onChange={setPower}
          />
          <Scale
            number="04"
            legend={requestCopy.effortLabel}
            options={requestCopy.efforts}
            measure={EFFORT_MEASURE}
            value={effort}
            onChange={setEffort}
          />
        </Sheet>

        <div className={styles.side}>
          <Sheet hold="pin" className={styles.spec} aria-labelledby={`${ideaId}-spec`}>
            <h2 id={`${ideaId}-spec`} className={styles.sheetHeading}>
              Specification
            </h2>
            <TitleBlock
              label="Specification of the request"
              cells={[
                { term: "Idea", value: `${COUNT.format(ideaLength)} chars` },
                { term: "Colors", value: colorReading },
                { term: "Power", value: requestCopy.powerLevels.find((each) => each.value === power)?.name },
                { term: "Effort", value: requestCopy.efforts.find((each) => each.value === effort)?.name },
                { term: "Output", value: "1 card, 63 × 88 mm", wide: true },
              ]}
            />
          </Sheet>
          <button type="submit" className={styles.generate}>
            <span>{requestCopy.generate}</span>
            <svg viewBox="0 0 32 16" aria-hidden="true" className={styles.arrow}>
              <path d="M0 8h29M22 1l8 7-8 7" fill="none" stroke="currentColor" strokeWidth="2" />
            </svg>
          </button>
          <p className={styles.generateNote}>Uses the text provider set on Status.</p>
        </div>
      </form>
      <MatFooter>Concept B · Drafting Table · Request mockup, nothing is sent</MatFooter>
    </Mat>
  );
}

/** A mana circle drafted with the pen: construction lines, the outline, the letter and, when chosen, a check. */
function DraftedCircle({ letter, diamond = false }: { letter: string; diamond?: boolean }) {
  return (
    <svg className={styles.glyph} viewBox="0 0 64 64" aria-hidden="true">
      <path className={styles.construction} d="M32 0v64M0 32h64" />
      {diamond ? (
        <path className={styles.outline} d="M32 6 58 32 32 58 6 32Z" />
      ) : (
        <circle className={styles.outline} cx="32" cy="32" r="25" />
      )}
      <text className={styles.letter} x="32" y="33" textAnchor="middle" dominantBaseline="middle">
        {letter}
      </text>
      <path className={styles.check} d="M44 48l5 5 11-13" pathLength={1} />
    </svg>
  );
}

/** A measured scale: three stations on a ruler, the chosen one marked by the pen's pointer. */
function Scale<Value extends string>({
  number,
  legend,
  options,
  measure,
  value,
  onChange,
}: {
  number: string;
  legend: string;
  options: { value: Value; name: string; meaning: string }[];
  measure: Record<Value, string>;
  value: Value;
  onChange: (value: Value) => void;
}) {
  const name = useId();
  const index = Math.max(
    0,
    options.findIndex((option) => option.value === value),
  );
  const chosen = options[index];
  return (
    <fieldset className={styles.block}>
      <legend className={styles.label}>
        <span className={styles.num}>{number}</span>
        {legend}
      </legend>
      <div className={styles.scale} style={{ "--at": index } as CSSProperties}>
        <span className={styles.ruler} aria-hidden="true" />
        <span className={styles.pointer} aria-hidden="true" />
        {options.map((option) => (
          <label key={option.value} className={styles.station}>
            <input
              type="radio"
              name={name}
              value={option.value}
              checked={option.value === value}
              onChange={() => onChange(option.value)}
            />
            <span className={styles.stationName}>{option.name}</span>
            <span className={styles.stationMeasure}>{measure[option.value]}</span>
          </label>
        ))}
      </div>
      {chosen !== undefined && <p className={styles.readout}>{chosen.meaning}</p>}
    </fieldset>
  );
}
