// Concept E "Starfield" (tasks.md T251): the page of every screen: the starfield, the header, the places and the footer.
import type { ReactNode } from "react";

import { CompassMark, StarGlyph } from "./glyphs";
import styles from "./shell.module.css";
import { Starfield } from "./Starfield";
import tokens from "./tokens.module.css";
import type { StarfieldSpeed } from "./useStarfield";

export type Place = "Request" | "Library" | "Status";

const PLACES: Place[] = ["Request", "Library", "Status"];

/** The page: the field of stars behind, the header with the wordmark and places, the work and the footer (RN-69). */
export function Shell({ current, speed = "rest", children }: { current?: Place; speed?: StarfieldSpeed; children: ReactNode }) {
  return (
    <div className={`${tokens.tokens} ${styles.root}`}>
      <div className={styles.sky} aria-hidden="true">
        <Starfield speed={speed} className={styles.stars} />
      </div>
      <header className={styles.bar}>
        <span className={styles.brand}>
          <span className={styles.mark}>
            <CompassMark />
          </span>
          Card Factory
        </span>
        {/* Setup opens before the other places exist, so it shows none. */}
        {current ? (
          <nav aria-label="Main">
            <ul className={styles.nav}>
              {PLACES.map((place) => (
                <li key={place}>
                  <span className={styles.place} aria-current={place === current ? "page" : undefined}>
                    <StarGlyph size={7} className={styles.placeStar} />
                    {place}
                  </span>
                </li>
              ))}
            </ul>
          </nav>
        ) : null}
      </header>
      <main className={styles.main}>{children}</main>
      <footer className={styles.footer}>
        {/* The exact notice and the repository address are still to come (spec RN-69, open questions). */}
        <p className={styles.notice}>Fan content notice: its exact text is pending.</p>
        <a className={styles.source} href="#/preview">
          Source code
        </a>
      </footer>
    </div>
  );
}
