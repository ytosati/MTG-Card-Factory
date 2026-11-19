// Concept C, "Gallery Wall" (tasks.md T251): the concept sheet, set in the concept itself. It names the typography,
// color, depth, texture, motion and card presentation, and the changes to the standards the concept needs.
import { WALLS, contrast, wallStyle } from "./palette";
import type { WallKey } from "./palette";
import styles from "./concept.module.css";
import wall from "./wall.module.css";

const WALL_ORDER: { key: WallKey; stands: string }[] = [
  { key: "W", stands: "White" },
  { key: "U", stands: "Blue" },
  { key: "B", stands: "Black" },
  { key: "R", stands: "Red" },
  { key: "G", stands: "Green" },
  { key: "gilt", stands: "Three or more colors" },
  { key: "stone", stands: "Colorless" },
  { key: "plum", stands: "No color chosen" },
];

const RATIO = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1, minimumFractionDigits: 1 });

const MOTION: { name: string; time: string; what: string }[] = [
  {
    name: "Wash",
    time: "700 to 1,200 ms",
    what: "The wall changes paint when colors are chosen and rises step by step while a card is generated.",
  },
  {
    name: "Build",
    time: "900 ms per step",
    what: "The mat, the moulding and the wall shadow appear around the empty canvas.",
  },
  { name: "Hang", time: "820 ms, once", what: "The finished card drops onto its cords, swings once and settles." },
  { name: "Lift", time: "260 ms", what: "A chosen paint chip lifts off the wall and tilts." },
  { name: "Press", time: "120 ms", what: "The main action sinks onto its own shadow." },
];

const CHANGES: string[] = [
  "Walls in the colors of the card replace the single light paper scheme of the current direction; every wall has its own checked ink, caption and violet (light on dark walls, deep on light ones). Card art keeps a neutral surround on the paper mat.",
  "One light pool behind the hung card: a warm, low radial gradient that draws the spotlight. It is never violet and never blurred.",
  "Display sizes far beyond the current type scale, for the screen title, the card name and the numerals.",
  "Paint chips, paper sheets and the frame cast shadows, not only card-shaped areas.",
];

export function GalleryConcept() {
  return (
    <div className={wall.root} style={wallStyle(WALLS.plum)}>
      <div className={`${wall.field} ${styles.sheet}`}>
        <header className={styles.head}>
          <p className={wall.caption}>Concept C · Card Factory</p>
          <h1 className={styles.title}>Gallery Wall</h1>
          <p className={styles.lede}>
            Each card is exhibited. The page is a painted wall in the card&apos;s colors, the card hangs framed beside a
            museum label, and the notes read like a catalogue spread.
          </p>
        </header>

        <section className={styles.section} aria-labelledby="concept-type">
          <span className={`${wall.bigNumeral} ${styles.sectionNumeral}`} aria-hidden="true">
            01
          </span>
          <div className={styles.sectionBody}>
            <h2 id="concept-type" className={styles.sectionTitle}>
              Typography
            </h2>
            <div className={styles.specimens}>
              <figure className={styles.specimen}>
                <p className={styles.specimenSerif}>Mossgate</p>
                <figcaption>
                  Display and card serif: Iowan Old Style, Palatino Linotype, Book Antiqua, Georgia. Bold, tight
                  leading, negative tracking at extreme sizes; italic for what the person writes.
                </figcaption>
              </figure>
              <figure className={styles.specimen}>
                <p className={styles.specimenNumerals}>2/3 · 04</p>
                <figcaption>
                  Numerals and figures: Bahnschrift Condensed, Arial Narrow. Mana value, power and toughness, step and
                  token counts are painted large as graphic elements.
                </figcaption>
              </figure>
              <figure className={styles.specimen}>
                <p className={styles.specimenCaption}>Exhibition caption · 0.75 rem · tracked 0.18 em</p>
                <figcaption>
                  Labels and controls: Bahnschrift, DIN Alternate, Franklin Gothic Medium. Small, tracked capitals.
                </figcaption>
              </figure>
            </div>
            <p className={styles.note}>
              Proposed, needs approval: Fraunces (display serif) and Archivo (grotesque with condensed widths), both
              under the SIL Open Font License, bundled with the built frontend so every system shows the same type.
            </p>
          </div>
        </section>

        <section className={styles.section} aria-labelledby="concept-color">
          <span className={`${wall.bigNumeral} ${styles.sectionNumeral}`} aria-hidden="true">
            02
          </span>
          <div className={styles.sectionBody}>
            <h2 id="concept-color" className={styles.sectionTitle}>
              Color
            </h2>
            <p className={styles.text}>
              One wall per color identity, fixed and checked: one color paints the wall, two split it into two fields,
              three or more give gilt. Violet stays the color of action and focus.
            </p>
            <ul className={styles.walls}>
              {WALL_ORDER.map(({ key, stands }) => {
                const paint = WALLS[key];
                return (
                  <li key={key} className={`${wall.field} ${styles.wallChip}`} style={wallStyle(paint)}>
                    <span className={styles.wallSample} aria-hidden="true">
                      Aa
                    </span>
                    <span className={styles.wallName}>{paint.name}</span>
                    <span className={styles.wallMeta}>{stands}</span>
                    <span className={styles.wallMeta}>{paint.paint}</span>
                    <span className={styles.wallMeta}>Ink {RATIO.format(contrast(paint.paint, paint.ink))} : 1</span>
                    <span className={styles.wallAccent}>Violet {paint.accent}</span>
                  </li>
                );
              })}
            </ul>
          </div>
        </section>

        <section className={styles.section} aria-labelledby="concept-depth">
          <span className={`${wall.bigNumeral} ${styles.sectionNumeral}`} aria-hidden="true">
            03
          </span>
          <div className={styles.sectionBody}>
            <h2 id="concept-depth" className={styles.sectionTitle}>
              Depth and texture
            </h2>
            <ol className={styles.layers}>
              <li>
                <span className={styles.layerSample} data-layer="wall" aria-hidden="true" />
                <span>
                  <strong>Wall.</strong> Flat paint with a broad tonal variation, as a roller leaves it, and fine
                  horizontal brushing.
                </span>
              </li>
              <li>
                <span className={styles.layerSample} data-layer="paper" aria-hidden="true" />
                <span>
                  <strong>Paper.</strong> The idea sheet, paint chips, the label and the catalogue band: crisp, one soft
                  shadow.
                </span>
              </li>
              <li>
                <span className={styles.layerSample} data-layer="frame" aria-hidden="true" />
                <span>
                  <strong>Frame.</strong> A dark moulding with a brass fillet, a deep mat with a bevelled window, a long
                  wall shadow and cords to a picture rail.
                </span>
              </li>
            </ol>
          </div>
        </section>

        <section className={styles.section} aria-labelledby="concept-motion">
          <span className={`${wall.bigNumeral} ${styles.sectionNumeral}`} aria-hidden="true">
            04
          </span>
          <div className={styles.sectionBody}>
            <h2 id="concept-motion" className={styles.sectionTitle}>
              Motion
            </h2>
            <dl className={styles.motion}>
              {MOTION.map((entry) => (
                <div key={entry.name}>
                  <dt>
                    {entry.name}
                    <span>{entry.time}</span>
                  </dt>
                  <dd>{entry.what}</dd>
                </div>
              ))}
            </dl>
            <p className={styles.note}>Reduced motion turns every animation and transition off.</p>
          </div>
        </section>

        <section className={styles.section} aria-labelledby="concept-card">
          <span className={`${wall.bigNumeral} ${styles.sectionNumeral}`} aria-hidden="true">
            05
          </span>
          <div className={styles.sectionBody}>
            <h2 id="concept-card" className={styles.sectionTitle}>
              Card presentation
            </h2>
            <p className={styles.text}>
              The card is the hero and hangs off-center: full-bleed art inside a border in the card&apos;s colors, the
              name and text on paper plates. Beside it a museum label gives the type, the rules text as its medium and
              the validation as an ink stamp; the power indicator reads as a scale. Figures and design notes follow as a
              catalogue spread.
            </p>
          </div>
        </section>

        <section className={`${styles.section} ${styles.changes}`} aria-labelledby="concept-changes">
          <span className={`${wall.bigNumeral} ${styles.sectionNumeral}`} aria-hidden="true">
            06
          </span>
          <div className={styles.sectionBody}>
            <h2 id="concept-changes" className={styles.sectionTitle}>
              Changes to the standards this concept needs
            </h2>
            <ul className={styles.changeList}>
              {CHANGES.map((change) => (
                <li key={change}>{change}</li>
              ))}
            </ul>
          </div>
        </section>
      </div>
    </div>
  );
}
