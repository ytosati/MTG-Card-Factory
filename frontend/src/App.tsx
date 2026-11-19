// Application shell: a small hash-based screen switch (no router library) behind the readiness gate.
// Details: specs/plan.md, section 13; spec RN-28, RN-40, RN-49.
import { Fragment, Suspense, lazy, useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";

import { getStatus } from "./api/client";
import styles from "./App.module.css";
import { BrandMark } from "./components/BrandMark";
import { cx } from "./components/classNames";
import { StatusIcon, toneStyles } from "./components/StatusIcon";
import type { GenerationResult, RevisionFailure, StatusResponse } from "./api/types";
import { Screen } from "./components/Screen";
import { useHeartbeat } from "./hooks/useHeartbeat";
import { RequestScreen } from "./screens/RequestScreen";
import { ResultScreen } from "./screens/ResultScreen";
import { SetupScreen } from "./screens/SetupScreen";
import { StatusScreen } from "./screens/StatusScreen";

/** What the shell offers to the screens it renders. */
interface ShellActions {
  /** Reads readiness again; once the database is ready the shell leaves Setup. */
  onReady: () => void;
  /** Opens the Result screen for a generated card. */
  onGenerated: (result: GenerationResult) => void;
  /** The revision failure of the card shown on Result, when it was just generated (spec RN-15). */
  revisionFailureOf: (cardId: string) => RevisionFailure | null;
}

interface ScreenEntry {
  route: string;
  label: string;
  render: (shell: ShellActions) => ReactNode;
}

const SETUP: ScreenEntry = {
  route: "#/setup",
  label: "Setup",
  render: ({ onReady }) => <SetupScreen onReady={onReady} />,
};
const STATUS: ScreenEntry = { route: "#/status", label: "Status", render: () => <StatusScreen /> };
const REQUEST: ScreenEntry = {
  route: "#/request",
  label: "Request",
  render: ({ onGenerated }) => <RequestScreen onGenerated={onGenerated} />,
};

const RESULT_PREFIX = "#/result/";
const CARD_ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** The Result screen of one card; its address carries the card id, so a reload shows the card again. */
function resultEntry(hash: string): ScreenEntry | null {
  if (!hash.startsWith(RESULT_PREFIX)) return null;
  const cardId = hash.slice(RESULT_PREFIX.length);
  if (!CARD_ID.test(cardId)) return null;
  return {
    route: hash,
    label: "Result",
    render: ({ revisionFailureOf }) => <ResultScreen cardId={cardId} revisionFailure={revisionFailureOf(cardId)} />,
  };
}

/** Screens offered before the database is ready, also during the build (see spec RN-28). */
const GATED_SCREENS: ScreenEntry[] = [SETUP, STATUS];

/** Screens offered once the database is ready. Result is reached from Request, never from the navigation. */
const READY_SCREENS: ScreenEntry[] = [REQUEST, STATUS];

/** The screen opened once the database is ready and nothing needs fixing. */
const HOME: ScreenEntry = STATUS;

type Readiness =
  | { kind: "loading" }
  | { kind: "unknown" }
  | { kind: "known"; ready: boolean; settingsToFix: boolean };

function readinessOf(status: StatusResponse): Readiness {
  return {
    kind: "known",
    ready: status.database_ready,
    settingsToFix: status.settings.some((item) => item.code === "config_invalid"),
  };
}

/** The screens offered and the one opened when the hash names none of them (null: wait). */
function gate(readiness: Readiness): { screens: ScreenEntry[]; fallback: ScreenEntry | null } {
  switch (readiness.kind) {
    case "loading":
      // Status never depends on readiness; every other screen waits for the gate.
      return { screens: [STATUS], fallback: null };
    case "unknown":
      return { screens: GATED_SCREENS, fallback: STATUS };
    case "known":
      if (!readiness.ready) return { screens: GATED_SCREENS, fallback: SETUP };
      // See spec RN-40: settings to fix open the Status screen first.
      return { screens: READY_SCREENS, fallback: readiness.settingsToFix ? STATUS : HOME };
  }
}

/** The banner shown while the application is not answering heartbeats (spec RN-41). */
function StoppedNotice() {
  return (
    <div className={styles.stoppedNotice} role="alert">
      <div className={cx(styles.barInner, toneStyles.tone)}>
        <StatusIcon tone="danger" className={styles.stoppedIcon} />
        <div>
          <p className={styles.stoppedTitle}>Card Factory has stopped.</p>
          <p>To start it again, double-click the start file in its folder and use the new tab it opens.</p>
        </div>
      </div>
    </div>
  );
}

function ReadinessNotice({ onRetry }: { onRetry: () => void }) {
  return (
    <div className={styles.shellNotice} role="alert">
      <div className={cx(styles.barInner, toneStyles.tone, styles.shellTone)}>
        <StatusIcon tone="notice" className={styles.shellIcon} />
        <p>Card Factory could not tell whether the card database is ready, so only Status is shown.</p>
        <button type="button" className={styles.buttonQuiet} onClick={onRetry}>
          Try again
        </button>
      </div>
    </div>
  );
}

// The gallery and its fixtures are imported only in the development server, so the production build
// leaves them out (plan section 14, "Screen previews"). The mode is checked too because a production
// build started under NODE_ENV=test (as the built-file check does) still reports DEV.
const PREVIEW_ENABLED = import.meta.env.DEV && import.meta.env.MODE !== "production";

const PreviewGallery = PREVIEW_ENABLED
  ? lazy(() => import("./preview/PreviewGallery").then((module) => ({ default: module.PreviewGallery })))
  : null;

function isPreviewAddress(hash: string): boolean {
  return PREVIEW_ENABLED && (hash === "#/preview" || hash.startsWith("#/preview/"));
}

/** The location hash, followed as it changes. */
function useHash(): string {
  const [hash, setHash] = useState(() => window.location.hash);
  useEffect(() => {
    const onHashChange = () => setHash(window.location.hash);
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);
  return hash;
}

/** The application; in the development server, the preview gallery at its own address. */
export function App() {
  const hash = useHash();
  if (PreviewGallery !== null && isPreviewAddress(hash)) {
    return (
      <Suspense fallback={<p role="status">Loading…</p>}>
        <PreviewGallery />
      </Suspense>
    );
  }
  return <Shell />;
}

/** The shell: a header with the screens on offer and the screen named by the location hash. */
function Shell() {
  const [hash, setHash] = useState(() => window.location.hash);
  const [readiness, setReadiness] = useState<Readiness>({ kind: "loading" });
  const [reads, setReads] = useState(0);
  const { stopped } = useHeartbeat();
  // Set by a screen change the person made, so the new screen's heading takes focus.
  const focusHeadingRef = useRef(false);
  const shownRouteRef = useRef<string | null>(null);

  const readAgain = useCallback(() => setReads((value) => value + 1), []);

  // Every screen change reads readiness again, so a build finished in another tab opens the gate.
  useEffect(() => {
    const onHashChange = () => {
      focusHeadingRef.current = true;
      setHash(window.location.hash);
      readAgain();
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, [readAgain]);

  useEffect(() => {
    let active = true;
    getStatus().then(
      (status) => {
        if (active) setReadiness(readinessOf(status));
      },
      () => {
        // A failed re-read keeps the last answer; only a gate never decided becomes unknown.
        if (active) setReadiness((previous) => (previous.kind === "known" ? previous : { kind: "unknown" }));
      },
    );
    return () => {
      active = false;
    };
  }, [reads]);

  const retry = useCallback(() => {
    setReadiness({ kind: "loading" });
    readAgain();
  }, [readAgain]);

  const [generated, setGenerated] = useState<GenerationResult | null>(null);

  const onGenerated = useCallback((result: GenerationResult) => {
    setGenerated(result);
    window.location.hash = `${RESULT_PREFIX}${result.card}`;
  }, []);

  const revisionFailureOf = useCallback(
    (cardId: string) => (generated !== null && generated.card === cardId ? generated.revision_failure : null),
    [generated],
  );

  const { screens, fallback } = gate(readiness);
  const ready = readiness.kind === "known" && readiness.ready;
  // Kept per address, so the effects below see one entry while the screen stays the same.
  const result = useMemo(() => resultEntry(hash), [hash]);
  const current = (ready ? result : null) ?? screens.find((entry) => entry.route === hash) ?? fallback;

  // The address names the screen shown, so reloading or going back opens it again.
  useEffect(() => {
    // The gallery's address belongs to the gallery, which App shows in place of the shell.
    if (current !== null && current.route !== hash && !isPreviewAddress(hash)) {
      window.history.replaceState(null, "", current.route);
      setHash(current.route);
    }
  }, [current, hash]);

  useEffect(() => {
    document.title = current === null ? "Card Factory" : `${current.label} · Card Factory`;
  }, [current]);

  // A new screen replaces the control that had focus; its heading takes it, except on the first screen.
  useEffect(() => {
    if (current === null) return;
    const previous = shownRouteRef.current;
    shownRouteRef.current = current.route;
    if (previous === null || previous === current.route) return;
    const focusLost = document.activeElement === null || document.activeElement === document.body;
    if (!focusHeadingRef.current && !focusLost) return;
    focusHeadingRef.current = false;
    document.querySelector<HTMLElement>("main h1")?.focus();
  }, [current]);

  return (
    <div className={styles.app}>
      {stopped && <StoppedNotice />}
      <header className={styles.header}>
        <div className={cx(styles.barInner, styles.headerInner)}>
          <span className={styles.name}>
            <BrandMark />
            Card Factory
          </span>
          <nav aria-label="Screens" className={styles.nav}>
            {screens.map((entry) => (
              <a key={entry.route} href={entry.route} aria-current={entry === current ? "page" : undefined}>
                {entry.label}
              </a>
            ))}
          </nav>
        </div>
      </header>
      {readiness.kind === "unknown" && <ReadinessNotice onRetry={retry} />}
      {current === null ? (
        <Screen>
          <p role="status">Checking the card database…</p>
        </Screen>
      ) : (
        <Fragment key={current.route}>{current.render({ onReady: readAgain, onGenerated, revisionFailureOf })}</Fragment>
      )}
    </div>
  );
}
