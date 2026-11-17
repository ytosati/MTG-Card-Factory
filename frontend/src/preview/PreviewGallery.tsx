// Preview gallery of the development server: every screen and named state with fictional fixtures.
// Details: specs/plan.md, sections 2 and 14 ("Screen previews"); spec RN-49.
import { useEffect, useId, useState } from "react";

import { previewScreens } from "./registry";
import styles from "./PreviewGallery.module.css";
import type { PreviewScreen, PreviewState } from "./types";

const INDEX = "#/preview";

const WIDTHS = ["360", "768", "1280"] as const;

type Width = (typeof WIDTHS)[number];

type Address =
  | { kind: "index" }
  | { kind: "state"; screen: PreviewScreen; state: PreviewState }
  | { kind: "unknown" };

function addressOf(state: { screenId: string; stateId: string }): string {
  return `${INDEX}/${state.screenId}/${state.stateId}`;
}

function decoded(part: string): string | null {
  try {
    return decodeURIComponent(part);
  } catch {
    return null;
  }
}

/** The index, one state named by the hash, or an address that names none. */
function resolve(hash: string, screens: PreviewScreen[]): Address {
  if (hash === INDEX || hash === `${INDEX}/`) return { kind: "index" };
  if (!hash.startsWith(`${INDEX}/`)) return { kind: "unknown" };
  const parts = hash.slice(INDEX.length + 1).split("/").map(decoded);
  if (parts.length !== 2) return { kind: "unknown" };
  const [screenId, stateId] = parts;
  const screen = screens.find((entry) => entry.id === screenId);
  const state = screen?.states.find((entry) => entry.id === stateId);
  return screen !== undefined && state !== undefined ? { kind: "state", screen, state } : { kind: "unknown" };
}

function useHash(): string {
  const [hash, setHash] = useState(() => window.location.hash);
  useEffect(() => {
    const onHashChange = () => setHash(window.location.hash);
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);
  return hash;
}

/** The gallery; it follows the hash, and keeps the chosen width and motion while the state changes. */
export function PreviewGallery({ screens = previewScreens }: { screens?: PreviewScreen[] }) {
  const address = resolve(useHash(), screens);
  const [width, setWidth] = useState<Width>("1280");
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    document.title = "Preview gallery · Card Factory";
  }, []);

  return (
    <div className={styles.gallery}>
      {address.kind === "index" && <Index screens={screens} />}
      {address.kind === "unknown" && (
        <main className={styles.index}>
          <h1>Preview gallery</h1>
          <p role="alert">No such preview exists at this address.</p>
          <p>
            <a href={INDEX}>Back to the index</a>
          </p>
        </main>
      )}
      {address.kind === "state" && (
        <>
          <Toolbar
            title={`${address.screen.name}: ${address.state.name}`}
            width={width}
            reducedMotion={reducedMotion}
            onWidth={setWidth}
            onReducedMotion={setReducedMotion}
          />
          <section
            className={styles.frame}
            aria-label="Preview"
            data-width={width}
            data-reduced-motion={reducedMotion ? "true" : "false"}
          >
            {address.state.render()}
          </section>
        </>
      )}
    </div>
  );
}

function Index({ screens }: { screens: PreviewScreen[] }) {
  return (
    <main className={styles.index}>
      <h1>Preview gallery</h1>
      {screens.length === 0 && <p className={styles.empty}>No screen has a preview yet.</p>}
      {screens.map((screen) => (
        <section key={screen.id} aria-labelledby={`preview-screen-${screen.id}`}>
          <h2 id={`preview-screen-${screen.id}`}>{screen.name}</h2>
          {screen.states.length === 0 ? (
            <p className={styles.empty}>No states yet.</p>
          ) : (
            <ul className={styles.screenList}>
              {screen.states.map((state) => (
                <li key={state.id}>
                  <a href={addressOf({ screenId: screen.id, stateId: state.id })}>{state.name}</a>
                </li>
              ))}
            </ul>
          )}
        </section>
      ))}
    </main>
  );
}

interface ToolbarProps {
  title: string;
  width: Width;
  reducedMotion: boolean;
  onWidth: (width: Width) => void;
  onReducedMotion: (reduced: boolean) => void;
}

function Toolbar({ title, width, reducedMotion, onWidth, onReducedMotion }: ToolbarProps) {
  const group = useId();
  return (
    <nav className={styles.toolbar} aria-label="Preview controls">
      <a href={INDEX}>Back to the index</a>
      <p className={styles.stateName}>{title}</p>
      <fieldset className={styles.switch} role="radiogroup" aria-label="Width">
        <legend aria-hidden="true">Width</legend>
        {WIDTHS.map((value) => (
          <label key={value} className={styles.option}>
            <input
              type="radio"
              name={group}
              value={value}
              checked={width === value}
              onChange={() => onWidth(value)}
            />
            {`${value} px`}
          </label>
        ))}
      </fieldset>
      <label className={styles.option}>
        <input type="checkbox" checked={reducedMotion} onChange={(event) => onReducedMotion(event.target.checked)} />
        Reduced motion
      </label>
    </nav>
  );
}
