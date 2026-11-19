// Preview gallery of the development server: every screen and named state with fictional fixtures.
// Details: specs/plan.md, sections 2 and 14 ("Screen previews"); spec RN-49.
import { Fragment, useEffect, useId, useState } from "react";

import { previewScreens } from "./registry";
import styles from "./PreviewGallery.module.css";
import type { PreviewScreen, PreviewState } from "./types";

const INDEX = "#/preview";

const WIDTHS = ["360", "768", "1280"] as const;

type Width = (typeof WIDTHS)[number];

type Address =
  | { kind: "index" }
  | { kind: "state"; screen: PreviewScreen; state: PreviewState; full: boolean }
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
  // A trailing "full" shows the state alone at the window's own size, as the application would.
  const full = parts.length === 3 && parts[2] === "full";
  if (parts.length !== 2 && !full) return { kind: "unknown" };
  const [screenId, stateId] = parts;
  const screen = screens.find((entry) => entry.id === screenId);
  const state = screen?.states.find((entry) => entry.id === stateId);
  return screen !== undefined && state !== undefined ? { kind: "state", screen, state, full } : { kind: "unknown" };
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

  if (address.kind === "state" && address.full) {
    return (
      <div className={styles.full}>
        <Fragment key={`${address.screen.id}/${address.state.id}`}>{address.state.render()}</Fragment>
        <FullNavigator screens={screens} screen={address.screen} state={address.state} />
      </div>
    );
  }

  return (
    <div className={styles.gallery}>
      {address.kind === "index" && <Index screens={screens} />}
      {address.kind === "unknown" && (
        <main className={styles.index}>
          <h1>Preview gallery</h1>
          <p role="alert">No such preview exists at this address.</p>
          <p>
            <a href={INDEX}>Back to the index</a>
      <a href={`${window.location.hash}/full`}>Full window</a>
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
            {/* Keyed by address, so a state never inherits the fields typed into the one before it. */}
            <Fragment key={`${address.screen.id}/${address.state.id}`}>{address.state.render()}</Fragment>
          </section>
        </>
      )}
    </div>
  );
}

/** Moves between states without leaving the full window: previous, next, a list of every state, and out. */
function FullNavigator({ screens, screen, state }: { screens: PreviewScreen[]; screen: PreviewScreen; state: PreviewState }) {
  const [open, setOpen] = useState(true);
  const all = screens.flatMap((entry) => entry.states.map((item) => ({ screen: entry, state: item })));
  const index = all.findIndex((entry) => entry.screen.id === screen.id && entry.state.id === state.id);
  const go = (to: number) => {
    const target = all[(to + all.length) % all.length];
    if (target) window.location.hash = `${addressOf({ screenId: target.screen.id, stateId: target.state.id })}/full`;
  };
  const exit = addressOf({ screenId: screen.id, stateId: state.id });

  if (!open) {
    return (
      <nav className={styles.navigator} aria-label="Preview pages">
        <button type="button" onClick={() => setOpen(true)} aria-label="Show the page navigator">
          Pages
        </button>
      </nav>
    );
  }
  return (
    <nav className={styles.navigator} aria-label="Preview pages">
      <button type="button" onClick={() => go(index - 1)} aria-label="Previous page">
        ←
      </button>
      <select
        aria-label="Page"
        value={`${screen.id}/${state.id}`}
        onChange={(event) => {
          const [screenId, stateId] = event.target.value.split("/");
          window.location.hash = `${addressOf({ screenId: screenId ?? "", stateId: stateId ?? "" })}/full`;
        }}
      >
        {screens.map((entry) => (
          <optgroup key={entry.id} label={entry.name}>
            {entry.states.map((item) => (
              <option key={item.id} value={`${entry.id}/${item.id}`}>
                {item.name}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
      <button type="button" onClick={() => go(index + 1)} aria-label="Next page">
        →
      </button>
      <a href={exit}>Exit</a>
      <button type="button" onClick={() => setOpen(false)} aria-label="Hide the page navigator">
        ×
      </button>
    </nav>
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
