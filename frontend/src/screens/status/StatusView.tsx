// Status screen view: providers, models, key presence, settings to fix, database readiness and data sources.
// Details: specs/spec.md, RN-01, RN-08, CA-08, CA-77 and "Screens" (Status).
import type { RefObject } from "react";

import type { SettingIssue, SourceInfo, StatusResponse } from "../../api/types";
import { cx } from "../../components/classNames";
import { Screen, screenStyles } from "../../components/Screen";
import { StatusIcon, toneStyles } from "../../components/StatusIcon";
import { statusCopy as copy } from "./copy";
import styles from "./StatusView.module.css";

/** What the Status screen shows: the status being read, the read that failed, or the status. */
export type StatusViewState =
  | { kind: "loading" }
  | { kind: "error"; message: string; setting: string | null }
  | { kind: "ready"; status: StatusResponse };

interface StatusViewProps {
  state: StatusViewState;
  headingRef?: RefObject<HTMLHeadingElement | null> | undefined;
  onReload: () => void;
}

/** The settings item that names the configuration file itself when it cannot be read (spec CA-77). */
const CONFIGURATION_FILE = ".env";

/** The setting that holds the text key; only its name is ever shown, never a value. */
const TEXT_KEY_SETTING = "LLM_API_KEY";

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

function providerName(provider: string | null): string | null {
  if (provider === null) return null;
  return copy.providerNames[provider] ?? provider;
}

/** The Status screen for one state of its read. */
export function StatusView({ state, headingRef, onReload }: StatusViewProps) {
  return (
    <Screen>
      <h1 ref={headingRef} tabIndex={-1}>
        {copy.title}
      </h1>
      {state.kind === "loading" && <p role="status">{copy.loading}</p>}
      {state.kind === "error" && (
        <div className={screenStyles.errorPanel}>
          <div role="alert">
            <p>{state.message}</p>
            {state.setting !== null && (
              <p>
                {copy.settingLabel} <code>{state.setting}</code>
              </p>
            )}
          </div>
          <button type="button" onClick={onReload}>
            {copy.tryAgain}
          </button>
        </div>
      )}
      {state.kind === "ready" && <Configuration status={state.status} onCheckAgain={onReload} />}
    </Screen>
  );
}

function Configuration({ status, onCheckAgain }: { status: StatusResponse; onCheckAgain: () => void }) {
  const toFix = status.settings.filter((item) => item.code === "config_invalid");
  const ignored = status.settings.filter((item) => item.code === "ignored");
  const invalid = new Set(toFix.map((item) => item.setting));
  // An unreadable file leaves every value empty; showing them as unset would point at the wrong fix.
  const fileUnreadable = invalid.has(CONFIGURATION_FILE);

  return (
    <>
      {toFix.length > 0 ? (
        <>
          <p className={screenStyles.summary}>{copy.settingsSummary(toFix.length)}</p>
          <section aria-labelledby="status-settings-to-fix">
            <h2 id="status-settings-to-fix">{copy.settingsToFixHeading}</h2>
            <SettingList items={toFix} variant="to-fix" />
            <p className={screenStyles.hint}>{copy.settingsToFixHint}</p>
            <p className={screenStyles.actions}>
              <button type="button" onClick={onCheckAgain}>
                {copy.checkAgain}
              </button>
            </p>
          </section>
        </>
      ) : (
        <div className={screenStyles.summaryRow}>
          <p className={screenStyles.summary}>{copy.settingsSummary(toFix.length)}</p>
          <button type="button" onClick={onCheckAgain}>
            {copy.checkAgain}
          </button>
        </div>
      )}

      <section aria-labelledby="status-configuration">
        <h2 id="status-configuration">{copy.configurationHeading}</h2>
        {fileUnreadable ? (
          <p className={cx(styles.fileUnreadable, toneStyles.tone)}>
            <StatusIcon tone="danger" className={styles.dangerIcon} />
            <span className={toneStyles.toneBody}>
              <code>{CONFIGURATION_FILE}</code>
              <span>{copy.fileUnreadable}</span>
            </span>
          </p>
        ) : (
          <>
            <ConfigurationFields status={status} invalid={invalid} />
            {!status.text_key_configured && !invalid.has(TEXT_KEY_SETTING) && (
              <p className={screenStyles.hint}>
                {copy.noTextKeyBefore} <code>{TEXT_KEY_SETTING}</code> {copy.noTextKeyAfter}
              </p>
            )}
          </>
        )}
        {status.next_start_port !== null && <p className={styles.notice}>{copy.nextStartPort(status.next_start_port)}</p>}
      </section>

      <Database ready={status.database_ready} sources={status.sources} />

      {ignored.length > 0 && (
        <section aria-labelledby="status-ignored-settings">
          <h2 id="status-ignored-settings">{copy.ignoredHeading}</h2>
          <SettingList items={ignored} variant="ignored" />
        </section>
      )}
    </>
  );
}

function ConfigurationFields({ status, invalid }: { status: StatusResponse; invalid: Set<string> }) {
  return (
    <dl className={styles.fields}>
      <Field label={copy.textProvider} value={providerName(status.text_provider)} invalid={invalid.has("LLM_PROVIDER")} />
      <Field label={copy.textModel} value={status.text_model} invalid={invalid.has("LLM_MODEL")} />
      <div className={styles.field}>
        <dt>{copy.textKeyConfigured}</dt>
        <dd>{status.text_key_configured ? copy.yes : copy.no}</dd>
      </div>
      <Field label={copy.imageProvider} value={providerName(status.image_provider)} invalid={invalid.has("IMAGE_PROVIDER")} />
      <Field label={copy.imageModel} value={status.image_model} invalid={invalid.has("IMAGE_MODEL")} />
    </dl>
  );
}

/** Database readiness and, for each source, its origin, publication date and download date (spec RN-01, CA-08). */
function Database({ ready, sources }: { ready: boolean; sources: SourceInfo[] }) {
  return (
    <section aria-labelledby="status-database">
      <h2 id="status-database">{copy.databaseHeading}</h2>
      {ready ? (
        <p className={cx(styles.readiness, styles.readinessReady, toneStyles.tone)}>
          <StatusIcon tone="success" />
          <span>{copy.databaseReady}</span>
        </p>
      ) : (
        <p className={cx(styles.readiness, styles.readinessMissing, toneStyles.tone)}>
          <StatusIcon tone="notice" />
          <span>
            {copy.databaseMissingBefore} <a href="#/setup">{copy.databaseMissingLink}</a> {copy.databaseMissingAfter}
          </span>
        </p>
      )}
      {sources.length > 0 ? (
        <ul className={styles.sources} aria-label={copy.dataSources}>
          {sources.map((source, index) => (
            <li key={`${source.source}-${index}`} className={styles.source}>
              <h3 className={styles.sourceName}>{copy.sourceNames[source.source] ?? source.source}</h3>
              <dl className={styles.sourceDetails}>
                <div className={styles.sourceDetail}>
                  <dt>{copy.origin}</dt>
                  <dd className={styles.sourceUrl}>{source.url}</dd>
                </div>
                <div className={styles.sourceDetail}>
                  <dt>{copy.published}</dt>
                  <dd>
                    <DateValue iso={source.published_at} />
                  </dd>
                </div>
                <div className={styles.sourceDetail}>
                  <dt>{copy.downloaded}</dt>
                  <dd>
                    <DateValue iso={source.downloaded_at} />
                  </dd>
                </div>
              </dl>
            </li>
          ))}
        </ul>
      ) : (
        ready && <p className={screenStyles.hint}>{copy.noSources}</p>
      )}
    </section>
  );
}

/** A date from the response, formatted for people; a value that is not a date reads "Unknown". */
function DateValue({ iso }: { iso: string }) {
  const time = ISO_DATE_TIME.test(iso) ? Date.parse(iso) : Number.NaN;
  if (Number.isNaN(time)) return <span>{copy.unknownDate}</span>;
  return <time dateTime={iso}>{DATE_FORMAT.format(time)}</time>;
}

/** A configuration value; a value whose setting must be fixed says so instead of looking merely unset. */
function Field({ label, value, invalid }: { label: string; value: string | null; invalid: boolean }) {
  if (invalid && value === null) {
    return (
      <div className={styles.field}>
        <dt>{label}</dt>
        <dd className={styles.valueDanger}>{copy.invalid}</dd>
      </div>
    );
  }
  return (
    <div className={styles.field}>
      <dt>{label}</dt>
      <dd>
        {value ?? copy.notSet}
        {invalid && <span className={styles.valueDanger}> ({copy.invalid})</span>}
      </dd>
    </div>
  );
}

function SettingList({ items, variant }: { items: SettingIssue[]; variant: "to-fix" | "ignored" }) {
  const toFix = variant === "to-fix";
  return (
    <ul className={cx(styles.settings, toFix ? styles.settingsToFix : styles.settingsIgnored)}>
      {items.map((item, index) => (
        <li key={`${item.setting}-${index}`} className={toFix ? cx(toneStyles.tone, styles.toFixItem) : undefined}>
          {toFix && <StatusIcon tone="danger" className={styles.dangerIcon} />}
          <span className={toneStyles.toneBody}>
            <code>{item.setting}</code> <span>{item.message}</span>
          </span>
        </li>
      ))}
    </ul>
  );
}
