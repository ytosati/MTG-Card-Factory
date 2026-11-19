// Concept B "Drafting Table" (tasks.md T251): the concept sheet naming type, color, depth, texture, motion and the card.
import type { CSSProperties } from "react";

import { cx } from "../../../components/classNames";
import styles from "./concept.module.css";
import { CropMarks, Mat, MatFooter, RegistrationMark, Sheet } from "./parts";

const SPECIMENS = [
  {
    role: "Headings",
    family: "Bahnschrift Condensed, then DIN Alternate, Roboto Condensed, Arial Narrow",
    proposed: "Barlow Condensed (OFL), bundled: proposed, needs approval",
    className: "display",
    sample: "Lanternhollow Sentry",
  },
  {
    role: "Body and controls",
    family: "Bahnschrift, then DIN Alternate, Segoe UI, Helvetica Neue",
    proposed: null,
    className: "text",
    sample: "Describe the card, choose its color identity and power level, then generate it.",
  },
  {
    role: "Data, measures and labels",
    family: "Cascadia Mono, then SF Mono, Consolas, Liberation Mono",
    proposed: "JetBrains Mono (OFL), bundled: proposed, needs approval",
    className: "mono",
    sample: "MV 4 · 1,204 in / 236 out · 63 × 88 mm · Step 4 of 6",
  },
  {
    role: "Inside the card only",
    family: "Iowan Old Style, then Palatino Linotype, Book Antiqua, Georgia",
    proposed: null,
    className: "serif",
    sample: "Vigilance. Other creatures you control get +0/+1.",
  },
] as const;

const SWATCHES = [
  { name: "Film", hex: "#e8eef0", role: "The mat; every screen's ground", ink: false },
  { name: "Film edge", hex: "#d6dfe3", role: "Rulers and mat edges", ink: false },
  { name: "Sheet", hex: "#fbfcfc", role: "Pinned sheets, notes, fields", ink: false },
  { name: "Ink", hex: "#1b2228", role: "Text, rules, outlines · 13.7:1 on film", ink: true },
  { name: "Ink soft", hex: "#46525c", role: "Secondary text · 6.8:1 on film", ink: true },
  { name: "Pencil", hex: "#8796a0", role: "Construction lines, ticks; never text", ink: true },
  { name: "Pen violet", hex: "#5b2a86", role: "Actions, focus, selection, callouts · 8.5:1", ink: true },
  { name: "Pen tint", hex: "#ece4f4", role: "Hover and chosen fills", ink: false },
  { name: "Pass", hex: "#1d6a46", role: "A check passed · 5.6:1", ink: true },
  { name: "Caution", hex: "#8a5300", role: "A notice · 5.4:1", ink: true },
  { name: "Fail", hex: "#a1262b", role: "A check failed · 6.3:1", ink: true },
];

const MANA = [
  { letter: "W", hex: "#f1e9cc" },
  { letter: "U", hex: "#c9dcec" },
  { letter: "B", hex: "#cbc6c6" },
  { letter: "R", hex: "#f0cdbf" },
  { letter: "G", hex: "#cde3cf" },
  { letter: "C", hex: "#dfe3e6" },
];

const MOTION = [
  ["Card arrives", "Drops 10px onto the mat and stops exactly; no bounce", "260 ms"],
  ["Callouts", "Leader lines extend from the card, then each note appears", "240 ms, 70 ms apart"],
  ["Color chosen", "The check mark is drawn with the pen", "220 ms"],
  ["Scale moved", "The pointer slides to the station", "220 ms"],
  ["Button pressed", "Sinks 3px onto its shadow", "90 ms"],
  ["Generating", "Zones drawn stroke by stroke, running zone traced, scan line sweeps", "Until the job ends"],
  ["Step finished", "Its annotation line extends to Done", "320 ms"],
] as const;

export function ConceptSheet() {
  return (
    <Mat
      current="concept"
      sheetLabel="Concept B"
      title="Drafting Table"
      titleNote="The card designer's workbench: drawing film, a measured grid and one violet technical pen."
    >
      <div className={styles.grid}>
        <Sheet className={cx(styles.panel, styles.wide)} aria-labelledby="concept-type">
          <CropMarks />
          <h2 id="concept-type" className={styles.heading}>
            <span className={styles.num}>01</span> Typography
          </h2>
          <p className={styles.lead}>
            A condensed grotesque set big and tight for headings, a monospace for every number, measure and label, and a
            serif that never leaves the card.
          </p>
          <ul className={styles.specimens}>
            {SPECIMENS.map((specimen) => (
              <li key={specimen.role}>
                <p className={styles.specimenRole}>{specimen.role}</p>
                <p className={cx(styles.sample, styles[specimen.className])}>{specimen.sample}</p>
                <p className={styles.family}>{specimen.family}</p>
                {specimen.proposed !== null && <p className={styles.proposed}>{specimen.proposed}</p>}
              </li>
            ))}
          </ul>
        </Sheet>

        <Sheet hold="pin" className={cx(styles.panel, styles.wide)} aria-labelledby="concept-color">
          <h2 id="concept-color" className={styles.heading}>
            <span className={styles.num}>02</span> Color
          </h2>
          <p className={styles.lead}>
            Cool drawing film, graphite ink and one violet: the ink of the technical pen, used for what the person does
            and for every annotation.
          </p>
          <ul className={styles.swatches}>
            {SWATCHES.map((swatch) => (
              <li key={swatch.name}>
                <span className={styles.chip} style={{ "--chip": swatch.hex } as CSSProperties} aria-hidden="true" />
                <span className={styles.swatchName}>{swatch.name}</span>
                <span className={styles.hex}>{swatch.hex}</span>
                <span className={styles.swatchRole}>{swatch.role}</span>
              </li>
            ))}
          </ul>
          <h3 className={styles.subheading}>Mana tints</h3>
          <ul className={styles.mana}>
            {MANA.map((mana) => (
              <li key={mana.letter}>
                <span className={styles.pip} style={{ "--chip": mana.hex } as CSSProperties} aria-hidden="true">
                  {mana.letter}
                </span>
                <span className={styles.hex}>{mana.hex}</span>
              </li>
            ))}
          </ul>
        </Sheet>

        <Sheet hold="tape" className={styles.panel} aria-labelledby="concept-depth">
          <h2 id="concept-depth" className={styles.heading}>
            <span className={styles.num}>03</span> Depth
          </h2>
          <p className={styles.lead}>
            Three planes. The mat is flat. Sheets and the card lie on it with short, crisp shadows, like paper on a
            table. Nothing floats, nothing blurs.
          </p>
          <div className={styles.planes} aria-hidden="true">
            <span className={styles.planeMat}>mat</span>
            <span className={styles.planeSheet}>sheet</span>
            <span className={styles.planeCard}>card</span>
          </div>
        </Sheet>

        <Sheet hold="tape" className={styles.panel} aria-labelledby="concept-texture">
          <h2 id="concept-texture" className={styles.heading}>
            <span className={styles.num}>04</span> Texture
          </h2>
          <p className={styles.lead}>
            A 16px grid with a major line every 80px, rulers on the mat's edges, crop and registration marks around what
            is under review, faint pencil construction lines, tape and pins.
          </p>
          <div className={styles.textures} aria-hidden="true">
            <span className={styles.tileGrid} />
            <span className={styles.tileCrop}>
              <CropMarks />
            </span>
            <span className={styles.tileReg}>
              <RegistrationMark />
            </span>
            <span className={styles.tileTape} />
          </div>
        </Sheet>

        <Sheet hold="pin" className={cx(styles.panel, styles.wide)} aria-labelledby="concept-motion">
          <h2 id="concept-motion" className={styles.heading}>
            <span className={styles.num}>05</span> Motion
          </h2>
          <p className={styles.lead}>
            Motion is drawing: strokes are laid down, lines extend, things land and stop. All of it is off under reduced
            motion, where every drawing shows its finished state.
          </p>
          <table className={styles.motion}>
            <thead>
              <tr>
                <th scope="col">Event</th>
                <th scope="col">Motion</th>
                <th scope="col">Duration</th>
              </tr>
            </thead>
            <tbody>
              {MOTION.map(([event, motion, duration]) => (
                <tr key={event}>
                  <th scope="row">{event}</th>
                  <td>{motion}</td>
                  <td>{duration}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Sheet>

        <Sheet hold="tape" className={styles.panel} aria-labelledby="concept-card">
          <h2 id="concept-card" className={styles.heading}>
            <span className={styles.num}>06</span> Card presentation
          </h2>
          <ul className={styles.points}>
            <li>The card sits at the centre of the mat, 63 × 88, as a design under review, framed by crop marks.</li>
            <li>Dimension lines give its width and height.</li>
            <li>
              Numbered callouts join name, mana cost, art, type line, rules text and power/toughness to margin notes:
              the check of that part, its measure, the power indicator.
            </li>
            <li>Design notes, power and usage are pinned sheets below. On a phone the callouts become a numbered list.</li>
            <li>The card frame is original: a graphite border, a tint by color, a mono pip for each symbol.</li>
          </ul>
        </Sheet>

        <Sheet hold="pin" className={styles.panel} aria-labelledby="concept-changes">
          <h2 id="concept-changes" className={styles.heading}>
            <span className={styles.num}>07</span> Changes to the standards this concept needs
          </h2>
          <ol className={styles.points}>
            <li>
              Allow hard-stop CSS gradients that draw lines (grid, rulers, ruled lines, dashes), not only information;
              they are lines, never color fades.
            </li>
            <li>Pinned sheets cast a short shadow too; today only cards do.</li>
            <li>Two bundled OFL fonts, if approved; the system stacks above work until then.</li>
          </ol>
        </Sheet>
      </div>
      <MatFooter>Concept B · Drafting Table · Concept sheet</MatFooter>
    </Mat>
  );
}
