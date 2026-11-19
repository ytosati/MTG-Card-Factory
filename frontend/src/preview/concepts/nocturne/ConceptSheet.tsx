// Concept A "Nocturne" (tasks.md T251): the concept sheet, naming typography, color, depth, texture,
// motion and the way a card is presented, in the concept's own styling.
import { CardStage, Grain, NocturneCard, Shell } from "./parts";
import { RESULT_CARD } from "./screens";
import styles from "./nocturne.module.css";

const SWATCHES: [name: string, hex: string, role: string][] = [
  ["Ground", "#110d18", "Page; near-black toward violet"],
  ["Lacquer", "#1a1424", "Panels, fields, the card frame"],
  ["Velvet", "#241a31", "Raised inner surfaces"],
  ["Ink", "#ece6f3", "Text; 15.7:1 on ground"],
  ["Muted ink", "#a99dbb", "Secondary text; 7.5:1"],
  ["Violet", "#7a43b3", "Primary action; white text 6.1:1"],
  ["Bright violet", "#b48be6", "Focus, selection; 7.1:1"],
  ["Brass", "#c9a45c", "Rules, rubrics, marks; 8.2:1"],
];

/** The concept sheet as a page of its own. */
export function ConceptSheet() {
  return (
    <Shell current={null}>
      <header className={styles.sheetHead}>
        <p className={styles.rubric}>Concept A</p>
        <h1 className={styles.sheetTitle}>Nocturne</h1>
        <p className={styles.lede}>
          A dark atelier. The tool around the card is quiet lacquer and brass; the card is the one lit object, resting
          on a table under a warm light from above.
        </p>
      </header>

      <div className={styles.sheetGrid}>
        <section className={styles.sheetSection}>
          <h2>Typography</h2>
          <p>
            A high-contrast serif for titles, the idea and the card; a clean sans for the tool; tracked small caps for
            rubrics. Installed stacks only. Proposed, needs approval: bundling Fraunces or Bodoni Moda (SIL Open Font
            License) so every system shows the same display face.
          </p>
          <dl className={styles.specimens}>
            <div className={styles.specimen}>
              <dt>Display · Bodoni 72, Didot, Bodoni MT, Constantia, Georgia</dt>
              <dd className={styles.specimenDisplay}>Lanternhollow Sentry</dd>
            </div>
            <div className={styles.specimen}>
              <dt>Tool · Segoe UI, SF Pro, Helvetica Neue, Arial</dt>
              <dd className={styles.specimenSans}>Higher effort takes longer and uses more tokens.</dd>
            </div>
            <div className={styles.specimen}>
              <dt>Rubric · the tool face in small caps, tracked 0.18em, brass</dt>
              <dd className={styles.specimenRubric}>Validation · Power · Text usage</dd>
            </div>
            <div className={styles.specimen}>
              <dt>Figures · Cascadia Mono, SF Mono, Consolas</dt>
              <dd className={styles.specimenMono}>1,204 in · 236 out</dd>
            </div>
          </dl>
        </section>

        <section className={styles.sheetSection}>
          <h2>Color</h2>
          <p>
            Dark grounds tinted toward violet, never pure black. Violet, brightened for the dark, marks what can be
            acted on and what is chosen; brass is the second metal for rules and small marks. Contrast is measured on
            the ground.
          </p>
          <ul className={styles.swatches}>
            {SWATCHES.map(([name, hex, role]) => (
              <li key={name} className={styles.swatch}>
                <span className={styles.chip} style={{ background: hex }} aria-hidden="true" />
                <span>
                  <span className={styles.swatchName}>{name}</span>
                  <span className={styles.swatchMeta}>{hex}</span>
                  <span className={styles.swatchMeta}>{role}</span>
                </span>
              </li>
            ))}
          </ul>
        </section>

        <section className={styles.sheetSection}>
          <h2>Depth</h2>
          <p>
            Three materials stacked by light, not by borders: the ground, lacquer panels with a brass top edge, and
            velvet inner surfaces. Shadows are long and soft, cast downward by the light above.
          </p>
          <ul className={styles.layers}>
            <li className={styles.layer} data-depth="0">
              Ground
            </li>
            <li className={styles.layer} data-depth="1">
              Lacquer
            </li>
            <li className={styles.layer} data-depth="2">
              Velvet
            </li>
          </ul>
        </section>

        <section className={styles.sheetSection}>
          <h2>Texture</h2>
          <p>
            A fine grain over the page and the card, drawn by the browser from fractal noise (an inline SVG filter).
            No image files. Below at five times its usual strength.
          </p>
          <div className={styles.textureTile}>
            <Grain className={styles.tileGrain} />
          </div>
        </section>

        <section className={`${styles.sheetSection} ${styles.sheetWide}`}>
          <h2>Card presentation</h2>
          <div className={styles.presentation}>
            <CardStage>
              <NocturneCard entry={RESULT_CARD} />
            </CardStage>
            <div>
              <p>
                The card is a physical object, 63 by 88, on a dark table. An original frame: lacquer inside a double
                brass hairline, a recessed art window, the type line between two rules, the text on velvet.
              </p>
              <p>
                With a mouse, the card tilts toward the pointer by up to seven degrees and a faint sheen slides across
                it; the shadow moves against the tilt. Touch and reduced motion leave it flat and still.
              </p>
              <p>On Result the card is the visual center, with its label and panels beside it like a museum label.</p>
            </div>
          </div>
        </section>

        <section className={styles.sheetSection}>
          <h2>Motion</h2>
          <ul className={styles.motionList}>
            <li>
              <strong>Wait: the slot assembles</strong>
              The frame lines draw in one after another (1.1 s each, staggered 180 ms), then a slow band of light
              passes over the slot every 2.6 s until the card is ready.
            </li>
            <li>
              <strong>Arrival: the card lands</strong>
              560 ms, ease-out (0.2, 0.8, 0.2, 1): it comes down 26 px and settles as its shadow tightens. No bounce.
            </li>
            <li>
              <strong>Controls</strong>
              160 ms for color and selection, 90 ms for a press. Everything stops under reduced motion.
            </li>
          </ul>
        </section>

        <section className={styles.sheetSection}>
          <h2>Changes to the standards this concept needs</h2>
          <ul className={styles.changes}>
            <li>
              <strong>A dark scheme</strong>
              The paper tokens are replaced by the dark ones above; the violet accent stays as a solid color.
            </li>
            <li>
              <strong>Light on the card stage</strong>
              Soft gradients for the light on the table, the cast shadow and the foil sheen, only around the card.
              No gradients, glows or blurs on the tool itself.
            </li>
            <li>
              <strong>Tilt that follows the pointer</strong>
              Motion that answers the pointer, not a change of state; mouse only, off under reduced motion.
            </li>
          </ul>
        </section>
      </div>
    </Shell>
  );
}
