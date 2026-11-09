// Application shell: a small hash-based screen switch (no router library) behind the readiness gate.
// Details: specs/plan.md, section 13; spec RN-28, RN-40, RN-49.
import { Fragment, useCallback, useEffect, useState } from "react";
import type { ReactNode } from "react";

import { getStatus } from "./api/client";
import type { StatusResponse } from "./api/types";
import { useHeartbeat } from "./hooks/useHeartbeat";
import { SetupScreen } from "./screens/SetupScreen";
import { StatusScreen } from "./screens/StatusScreen";

/** What the shell offers to the screens it renders. */
interface ShellActions {
  /** Reads readiness again; once the database is ready the shell leaves Setup. */
  onReady: () => void;
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

/** Screens offered before the database is ready, also during the build (see spec RN-28). */
const GATED_SCREENS: ScreenEntry[] = [SETUP, STATUS];

/** Screens offered once the database is ready. */
const READY_SCREENS: ScreenEntry[] = [STATUS];

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
    <div className="stopped-notice" role="alert">
      <p className="stopped-notice-title">Card Factory has stopped.</p>
      <p>To start it again, double-click the start file in its folder and use the new tab it opens.</p>
    </div>
  );
}

function ReadinessNotice({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="shell-notice" role="alert">
      <p>Card Factory could not tell whether the card database is ready, so only Status is shown.</p>
      <button type="button" className="button-quiet" onClick={onRetry}>
        Try again
      </button>
    </div>
  );
}

/** The application: a header with the screens on offer and the screen named by the location hash. */
export function App() {
  const [hash, setHash] = useState(() => window.location.hash);
  const [readiness, setReadiness] = useState<Readiness>({ kind: "loading" });
  const [reads, setReads] = useState(0);
  const { stopped } = useHeartbeat();

  const readAgain = useCallback(() => setReads((value) => value + 1), []);

  // Every screen change reads readiness again, so a build finished in another tab opens the gate.
  useEffect(() => {
    const onHashChange = () => {
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

  const { screens, fallback } = gate(readiness);
  const current = screens.find((entry) => entry.route === hash) ?? fallback;

  // The address names the screen shown, so reloading or going back opens it again.
  useEffect(() => {
    if (current !== null && current.route !== hash) {
      window.history.replaceState(null, "", current.route);
      setHash(current.route);
    }
  }, [current, hash]);

  return (
    <div className="app">
      {stopped && <StoppedNotice />}
      <header className="app-header">
        <span className="app-name">Card Factory</span>
        <nav aria-label="Screens" className="app-nav">
          {screens.map((entry) => (
            <a key={entry.route} href={entry.route} aria-current={entry === current ? "page" : undefined}>
              {entry.label}
            </a>
          ))}
        </nav>
      </header>
      {readiness.kind === "unknown" && <ReadinessNotice onRetry={retry} />}
      {current === null ? (
        <main className="screen">
          <p role="status">Checking the card database…</p>
        </main>
      ) : (
        <Fragment key={current.route}>{current.render({ onReady: readAgain })}</Fragment>
      )}
    </div>
  );
}
