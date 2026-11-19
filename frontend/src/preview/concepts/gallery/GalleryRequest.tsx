// Concept C, "Gallery Wall" (tasks.md T251): the Request screen as an exhibition commission; the wall takes the
// chosen colors as they are picked. A static mockup with local state; nothing calls the API.
import { useState } from "react";
import type { FormEvent } from "react";

import type { ColorLetter, PowerLevel } from "../../../api/types";
import { requestCopy } from "../../../screens/request/copy";
import type { GenerationEffort } from "../../../screens/request/copy";
import { IDEA_MAX_CHARACTERS } from "../../../screens/request/RequestView";
import { WALLS, wallStyle, wallsOf } from "./palette";
import type { Wall } from "./palette";
import styles from "./request.module.css";
import wall from "./wall.module.css";

const IDEA =
  "A lantern-bearing scout who leads lost travelers through an old forest and finds hidden paths. " +
  "It should reward decks that play many lands.";

const COLOR_NAMES: Record<ColorLetter, string> = { W: "white", U: "blue", B: "black", R: "red", G: "green" };

/** What the wall reads: its name and the identity it stands for. */
function wallReading(
  colors: ColorLetter[],
  colorless: boolean,
  walls: [Wall, Wall],
): { name: string; meaning: string } {
  if (colorless) return { name: walls[0].name, meaning: "Colorless" };
  if (colors.length === 0) return { name: walls[0].name, meaning: "Choose a color to paint the wall" };
  if (colors.length > 2) return { name: walls[0].name, meaning: "Three or more colors" };
  const names = walls[0] === walls[1] ? walls[0].name : `${walls[0].name} / ${walls[1].name}`;
  const words = colors.map((letter) => COLOR_NAMES[letter]).join(" and ");
  return { name: names, meaning: words.charAt(0).toUpperCase() + words.slice(1) };
}

export function GalleryRequest() {
  const [idea, setIdea] = useState(IDEA);
  const [colors, setColors] = useState<ColorLetter[]>(["G"]);
  const [colorless, setColorless] = useState(false);
  const [power, setPower] = useState<PowerLevel | null>("medium");
  const [effort, setEffort] = useState<GenerationEffort>("medium");

  const walls = wallsOf(colors, colorless);
  const [left, right] = walls;
  const reading = wallReading(colors, colorless, walls);

  function toggle(letter: ColorLetter) {
    setColorless(false);
    setColors((current) =>
      current.includes(letter) ? current.filter((value) => value !== letter) : [...current, letter],
    );
  }

  function chooseColorless() {
    setColorless((current) => !current);
    setColors([]);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
  }

  return (
    <div className={`${wall.root} ${styles.page}`} style={wallStyle(left)}>
      <form className={styles.spread} onSubmit={submit} noValidate>
        <header className={`${wall.field} ${styles.head}`} style={wallStyle(left)}>
          <p className={wall.caption}>Card Factory</p>
          <h1 className={styles.title}>Request</h1>
          <p className={styles.summary}>Describe the card, choose its colors and power, then generate it.</p>
        </header>

        <section className={`${wall.field} ${styles.ident}`} style={wallStyle(right)} aria-labelledby="gallery-wall">
          <h2 id="gallery-wall" className={wall.caption}>
            Wall
          </h2>
          <p className={styles.wallName} aria-live="polite">
            {reading.name}
            <span className={styles.wallMeaning}>{reading.meaning}</span>
          </p>
        </section>

        <div className={styles.ideaRow} style={wallStyle(right, { "--wall-a": left.paint, "--wall-b": right.paint })}>
          <div className={styles.sheet}>
            <label className={styles.sheetLabel} htmlFor="gallery-idea">
              <span className={styles.index} aria-hidden="true">
                01
              </span>
              {requestCopy.fieldLabels.idea}
            </label>
            <textarea
              id="gallery-idea"
              className={styles.idea}
              rows={4}
              value={idea}
              onChange={(event) => setIdea(event.target.value)}
              aria-describedby="gallery-idea-count"
            />
            <p id="gallery-idea-count" className={styles.count}>
              {requestCopy.characterCount(idea.length, IDEA_MAX_CHARACTERS)}
            </p>
          </div>
        </div>

        <div className={`${wall.field} ${styles.colors}`} style={wallStyle(left)}>
          <fieldset className={styles.choiceSet}>
            <legend className={styles.legend}>
              <span className={`${wall.bigNumeral} ${styles.legendNumeral}`} aria-hidden="true">
                02
              </span>
              {requestCopy.fieldLabels.color_identity}
            </legend>
            <p className={styles.hint}>{requestCopy.colorHint}</p>
            <div className={styles.chips}>
              {requestCopy.colors.map(({ letter, name }) => (
                <Chip
                  key={letter}
                  name={name}
                  wall={WALLS[letter]}
                  checked={colors.includes(letter)}
                  onChange={() => toggle(letter)}
                />
              ))}
              <span className={styles.or}>{requestCopy.or}</span>
              <Chip name={requestCopy.colorless} wall={WALLS.stone} checked={colorless} onChange={chooseColorless} />
            </div>
          </fieldset>

        </div>

        <div className={`${wall.field} ${styles.choices}`} style={wallStyle(right)}>
          <fieldset className={styles.choiceSet}>
            <legend className={styles.legend}>
              <span className={`${wall.bigNumeral} ${styles.legendNumeral}`} aria-hidden="true">
                03
              </span>
              {requestCopy.fieldLabels.power_level}
            </legend>
            <div className={styles.words}>
              {requestCopy.powerLevels.map((level) => (
                <label key={level.value} className={styles.word}>
                  <input
                    className={wall.hidden}
                    type="radio"
                    name="gallery-power"
                    checked={power === level.value}
                    onChange={() => setPower(level.value)}
                  />
                  <span className={styles.wordFace}>{level.name}</span>
                  <span className={styles.wordMeaning}>{level.meaning}</span>
                </label>
              ))}
            </div>
          </fieldset>

          <fieldset className={styles.choiceSet}>
            <legend className={styles.legend}>
              <span className={`${wall.bigNumeral} ${styles.legendNumeral}`} aria-hidden="true">
                04
              </span>
              {requestCopy.effortLabel}
            </legend>
            <div className={`${styles.words} ${styles.wordsInline}`}>
              {requestCopy.efforts.map((level) => (
                <label key={level.value} className={`${styles.word} ${styles.wordSmall}`}>
                  <input
                    className={wall.hidden}
                    type="radio"
                    name="gallery-effort"
                    checked={effort === level.value}
                    onChange={() => setEffort(level.value)}
                  />
                  <span className={styles.wordFace}>{level.name}</span>
                  <span className={styles.wordMeaning}>{level.meaning}</span>
                </label>
              ))}
            </div>
          </fieldset>

          <div className={styles.actionRow}>
            <button type="submit" className={wall.action}>
              {requestCopy.generate}
              <svg className={styles.arrow} viewBox="0 0 32 12" aria-hidden="true" focusable="false">
                <path d="M0 6h29M24 1l6 5-6 5" fill="none" stroke="currentColor" strokeWidth="2" />
              </svg>
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}

/** A paint chip: the wall color above, its name on a paper strip below; a chosen chip lifts off the wall. */
function Chip({
  name,
  wall: paint,
  checked,
  onChange,
}: {
  name: string;
  wall: Wall;
  checked: boolean;
  onChange: () => void;
}) {
  return (
    <label className={styles.chip}>
      <input className={wall.hidden} type="checkbox" checked={checked} onChange={onChange} />
      <span className={styles.chipFace}>
        <span className={styles.chipPaint} style={{ background: paint.paint }}>
          <svg className={styles.chipMark} viewBox="0 0 20 20" aria-hidden="true" focusable="false">
            <path d="M4 10.5l4 4 8-9" fill="none" stroke="currentColor" strokeWidth="2.6" />
          </svg>
        </span>
        <span className={styles.chipStrip}>
          <span className={styles.chipName}>{name}</span>
          <span className={styles.chipWall} aria-hidden="true">
            {paint.name}
          </span>
        </span>
      </span>
    </label>
  );
}
