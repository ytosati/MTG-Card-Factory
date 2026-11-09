// Status screen: providers, models, key presence, settings to fix, database readiness and data sources.
// Details: specs/spec.md, RN-01, RN-08, CA-08, CA-77 and "Screens" (Status).
import { useCallback, useEffect, useRef, useState } from "react";

import { getStatus } from "../api/client";
import type { SettingIssue, SourceInfo, StatusResponse } from "../api/types";

type LoadState =
  | { kind: "loading" }
  | { kind: "error"; message: string; setting: string | null }
  | { kind: "ready"; status: StatusResponse };

const NOT_SET = "Not set";
const INVALID = "Invalid — see Settings to fix";

/** The settings item that names the configuration file itself when it cannot be read (spec CA-77). */
const CONFIGURATION_FILE = ".env";

const UNKNOWN_DATE = "Unknown";

const SOURCE_NAMES: Record<string, string> = {
  scryfall_oracle: "Scryfall Oracle cards",
};

// dateStyle and timeStyle cannot be combined with timeZoneName, so the parts are listed one by one.
const DATE_FORMAT = new Intl.DateTimeFormat("en-US", {
  year: "numeric",
  month: "short",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
  timeZoneName: "short",
});

const ISO_DATE_TIME = /^\d{4}-\d{2}-\d{2}T/;

const PROVIDER_NAMES: Record<string, string> = {
  openai: "OpenAI",
  anthropic: "Anthropic",
  google: "Google",
};

function providerName(provider: string | null): string | null {
  if (provider === null) return null;
  return PROVIDER_NAMES[provider] ?? provider;
}

function errorState(reason: unknown): LoadState {
  if (reason instanceof Error) {
    const setting = "setting" in reason && typeof reason.setting === "string" ? reason.setting : null;
    return { kind: "error", message: reason.message, setting };
  }
  return { kind: "error", message: "The status could not be loaded.", setting: null };
}

/** The Status screen; it reads GET /api/status each time it opens (spec CA-73). */
export function StatusScreen() {
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const [attempt, setAttempt] = useState(0);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const focusHeadingAfterLoad = useRef(false);

  useEffect(() => {
    let active = true;
    setState({ kind: "loading" });
    getStatus().then(
      (status) => {
        if (active) setState({ kind: "ready", status });
      },
      (reason: unknown) => {
        if (active) setState(errorState(reason));
      },
    );
    return () => {
      active = false;
    };
  }, [attempt]);

  // The button that asked for the reload disappears while loading, so focus returns to the heading.
  useEffect(() => {
    if (state.kind !== "loading" && focusHeadingAfterLoad.current) {
      focusHeadingAfterLoad.current = false;
      headingRef.current?.focus();
    }
  }, [state]);

  const reload = useCallback(() => {
    focusHeadingAfterLoad.current = true;
    setAttempt((value) => value + 1);
  }, []);

  return (
    <main className="screen">
      <h1 ref={headingRef} tabIndex={-1}>
        Status
      </h1>
      {state.kind === "loading" && <p role="status">Loading the status…</p>}
      {state.kind === "error" && (
        <div className="error-panel">
          <div role="alert">
            <p>{state.message}</p>
            {state.setting !== null && (
              <p>
                Setting: <code>{state.setting}</code>
              </p>
            )}
          </div>
          <button type="button" onClick={reload}>
            Try again
          </button>
        </div>
      )}
      {state.kind === "ready" && <Configuration status={state.status} onCheckAgain={reload} />}
    </main>
  );
}

function summaryText(count: number): string {
  if (count === 0) return "No settings to fix.";
  return `${count} ${count === 1 ? "setting" : "settings"} to fix in the configuration file.`;
}

function Configuration({ status, onCheckAgain }: { status: StatusResponse; onCheckAgain: () => void }) {
  const toFix = status.settings.filter((item) => item.code === "config_invalid");
  const ignored = status.settings.filter((item) => item.code === "ignored");
  const invalid = new Set(toFix.map((item) => item.setting));
  // An unreadable file leaves every value empty; showing them as unset would point at the wrong fix.
  const fileUnreadable = invalid.has(CONFIGURATION_FILE);

  return (
    <>
      <p className="summary">{summaryText(toFix.length)}</p>

      {toFix.length > 0 && (
        <section aria-labelledby="status-settings-to-fix">
          <h2 id="status-settings-to-fix">Settings to fix</h2>
          <SettingList items={toFix} variant="to-fix" />
          <p className="hint">
            Edit the configuration file (.env) in the Card Factory folder, then check again. Changes take
            effect without a restart, except the port.
          </p>
        </section>
      )}

      <p className="actions">
        <button type="button" onClick={onCheckAgain}>
          Check again
        </button>
      </p>

      <section aria-labelledby="status-configuration">
        <h2 id="status-configuration">Configuration</h2>
        {fileUnreadable ? (
          <p className="file-unreadable">
            <code>{CONFIGURATION_FILE}</code>
            <span>The configuration file cannot be read, so its settings are not shown.</span>
          </p>
        ) : (
          <ConfigurationFields status={status} invalid={invalid} />
        )}
        {status.next_start_port !== null && (
          <p className="notice">
            The port changes to {status.next_start_port} at the next start. After restarting, open
            http://127.0.0.1:{status.next_start_port}.
          </p>
        )}
      </section>

      <Database ready={status.database_ready} sources={status.sources} />

      {ignored.length > 0 && (
        <section aria-labelledby="status-ignored-settings">
          <h2 id="status-ignored-settings">Ignored settings</h2>
          <SettingList items={ignored} variant="ignored" />
        </section>
      )}
    </>
  );
}

function ConfigurationFields({ status, invalid }: { status: StatusResponse; invalid: Set<string> }) {
  return (
    <dl className="fields">
      <Field
        label="Text provider"
        value={providerName(status.text_provider)}
        invalid={invalid.has("LLM_PROVIDER")}
      />
      <Field label="Text model" value={status.text_model} invalid={invalid.has("LLM_MODEL")} />
      <div className="field">
        <dt>Text key configured</dt>
        <dd className={status.text_key_configured ? undefined : "value-danger"}>
          {status.text_key_configured ? "Yes" : "No"}
        </dd>
      </div>
      <Field
        label="Image provider"
        value={providerName(status.image_provider)}
        invalid={invalid.has("IMAGE_PROVIDER")}
      />
      <Field label="Image model" value={status.image_model} invalid={invalid.has("IMAGE_MODEL")} />
    </dl>
  );
}

/** Database readiness and, for each source, its origin, publication date and download date (spec RN-01, CA-08). */
function Database({ ready, sources }: { ready: boolean; sources: SourceInfo[] }) {
  return (
    <section aria-labelledby="status-database">
      <h2 id="status-database">Reference database</h2>
      {ready ? (
        <p className="readiness readiness-ready">The reference database is ready.</p>
      ) : (
        <p className="readiness readiness-missing">
          The reference database is not ready. Build it or follow its progress on the <a href="#/setup">Setup</a> screen.
        </p>
      )}
      {sources.length > 0 ? (
        <ul className="sources" aria-label="Data sources">
          {sources.map((source, index) => (
            <li key={`${source.source}-${index}`} className="source">
              <h3 className="source-name">{SOURCE_NAMES[source.source] ?? source.source}</h3>
              <dl className="source-details">
                <div className="source-detail">
                  <dt>Origin</dt>
                  <dd className="source-url">{source.url}</dd>
                </div>
                <div className="source-detail">
                  <dt>Published</dt>
                  <dd>
                    <DateValue iso={source.published_at} />
                  </dd>
                </div>
                <div className="source-detail">
                  <dt>Downloaded</dt>
                  <dd>
                    <DateValue iso={source.downloaded_at} />
                  </dd>
                </div>
              </dl>
            </li>
          ))}
        </ul>
      ) : (
        ready && <p className="hint">No data sources are recorded.</p>
      )}
    </section>
  );
}

/** A date from the response, formatted for people; a value that is not a date reads "Unknown". */
function DateValue({ iso }: { iso: string }) {
  const time = ISO_DATE_TIME.test(iso) ? Date.parse(iso) : Number.NaN;
  if (Number.isNaN(time)) return <span>{UNKNOWN_DATE}</span>;
  return <time dateTime={iso}>{DATE_FORMAT.format(time)}</time>;
}

/** A configuration value; a value whose setting must be fixed says so instead of looking merely unset. */
function Field({ label, value, invalid }: { label: string; value: string | null; invalid: boolean }) {
  if (invalid && value === null) {
    return (
      <div className="field">
        <dt>{label}</dt>
        <dd className="value-danger">{INVALID}</dd>
      </div>
    );
  }
  return (
    <div className="field">
      <dt>{label}</dt>
      <dd>
        {value ?? NOT_SET}
        {invalid && <span className="value-danger"> ({INVALID})</span>}
      </dd>
    </div>
  );
}

function SettingList({ items, variant }: { items: SettingIssue[]; variant: "to-fix" | "ignored" }) {
  return (
    <ul className={`settings settings-${variant}`}>
      {items.map((item, index) => (
        <li key={`${item.setting}-${index}`}>
          <code>{item.setting}</code>{" "}
          <span>{item.message}</span>
        </li>
      ))}
    </ul>
  );
}
