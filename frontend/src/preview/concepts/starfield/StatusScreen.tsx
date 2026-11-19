// Concept E "Starfield" (tasks.md T251): the Status screen as a local mockup, read from the contract samples:
// the configuration, the reference database and its sources, and the settings to fix.
import { useEffect, useState } from "react";

import type { StatusResponse } from "../../../api/types";
import { statusCopy } from "../../../screens/status/copy";
import { StarGlyph } from "./glyphs";
import { Section } from "./parts";
import { sceneCopy } from "./scenes";
import ui from "./screen.module.css";
import { Shell } from "./Shell";
import styles from "./status.module.css";

const DATE = new Intl.DateTimeFormat("en-US", { year: "numeric", month: "long", day: "numeric", timeZone: "UTC" });

function dateOf(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? statusCopy.unknownDate : DATE.format(date);
}

function providerName(value: string | null): string {
  return value === null ? statusCopy.notSet : statusCopy.providerNames[value] ?? value;
}

/** Yes as a lit star, No as an empty ring, so the answer reads at a glance and in words. */
function YesNo({ value }: { value: boolean }) {
  return (
    <span className={styles.answer} data-yes={value ? "true" : "false"}>
      {value ? <StarGlyph size={10} className={styles.answerStar} /> : <span className={styles.answerRing} aria-hidden="true" />}
      {value ? statusCopy.yes : statusCopy.no}
    </span>
  );
}

export function StatusScreen({ status }: { status: StatusResponse }) {
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    document.title = `${statusCopy.title} · Card Factory`;
  }, []);

  useEffect(() => {
    if (!checking) return undefined;
    const timer = window.setTimeout(() => setChecking(false), 900);
    return () => window.clearTimeout(timer);
  }, [checking]);

  const toFix = status.settings.filter((setting) => setting.code === "config_invalid");
  const ignored = status.settings.filter((setting) => setting.code === "ignored");

  return (
    <Shell current="Status">
      <div className={`${ui.page} ${styles.layout}`}>
        <div className={styles.intro}>
          <p className={ui.rubric}>
            <StarGlyph size={8} className={ui.rubricStar} />
            {statusCopy.settingsSummary(toFix.length)}
          </p>
          <h1 className={ui.title}>{statusCopy.title}</h1>
          <p className={ui.summary}>{sceneCopy.statusLede}</p>
          <div className={`${ui.actions} ${styles.actions}`}>
            <button type="button" className={ui.primary} onClick={() => setChecking(true)} aria-busy={checking}>
              <StarGlyph size={10} className={ui.primaryStar} />
              {statusCopy.checkAgain}
            </button>
            <button type="button" className={ui.secondary}>
              {sceneCopy.testConnection}
            </button>
          </div>
          <p className={styles.live} role="status">
            {checking ? statusCopy.loading : ""}
          </p>
        </div>

        <div className={styles.body}>
          {toFix.length > 0 ? (
            <Section id="sf-fix" title={statusCopy.settingsToFixHeading}>
              <ul className={styles.issues}>
                {toFix.map((setting) => (
                  <li key={setting.setting}>
                    <code className={styles.setting}>{setting.setting}</code>
                    <span>{setting.message}</span>
                  </li>
                ))}
              </ul>
              <p className={styles.hint}>{statusCopy.settingsToFixHint}</p>
            </Section>
          ) : null}

          <Section id="sf-configuration" title={statusCopy.configurationHeading}>
            <dl className={ui.facts}>
              <div>
                <dt>{statusCopy.textProvider}</dt>
                <dd>{providerName(status.text_provider)}</dd>
              </div>
              <div>
                <dt>{statusCopy.textModel}</dt>
                <dd className={styles.mono}>{status.text_model ?? statusCopy.notSet}</dd>
              </div>
              <div>
                <dt>{statusCopy.textKeyConfigured}</dt>
                <dd>
                  <YesNo value={status.text_key_configured} />
                </dd>
              </div>
              <div>
                <dt>{statusCopy.imageProvider}</dt>
                <dd>{providerName(status.image_provider)}</dd>
              </div>
              <div>
                <dt>{statusCopy.imageModel}</dt>
                <dd className={styles.mono}>{status.image_model ?? statusCopy.notSet}</dd>
              </div>
            </dl>
          </Section>

          <Section id="sf-database" title={statusCopy.databaseHeading}>
            <p className={styles.database} data-ready={status.database_ready ? "true" : "false"}>
              <span className={styles.databaseMark} aria-hidden="true" />
              {status.database_ready ? statusCopy.databaseReady : `${statusCopy.databaseMissingBefore} ${statusCopy.databaseMissingLink} ${statusCopy.databaseMissingAfter}`}
            </p>
            <h3 className={styles.subhead}>{statusCopy.dataSources}</h3>
            {status.sources.length > 0 ? (
              status.sources.map((source) => (
                <dl key={source.source} className={`${ui.facts} ${styles.source}`}>
                  <div>
                    <dt>{statusCopy.origin}</dt>
                    <dd>
                      <span className={styles.sourceName}>{statusCopy.sourceNames[source.source] ?? source.source}</span>
                      <span className={styles.url}>{source.url}</span>
                    </dd>
                  </div>
                  <div>
                    <dt>{statusCopy.published}</dt>
                    <dd>{dateOf(source.published_at)}</dd>
                  </div>
                  <div>
                    <dt>{statusCopy.downloaded}</dt>
                    <dd>{dateOf(source.downloaded_at)}</dd>
                  </div>
                </dl>
              ))
            ) : (
              <p className={styles.hint}>{statusCopy.noSources}</p>
            )}
          </Section>

          {ignored.length > 0 ? (
            <Section id="sf-ignored" title={statusCopy.ignoredHeading}>
              <ul className={styles.issues}>
                {ignored.map((setting) => (
                  <li key={setting.setting}>
                    <code className={styles.setting}>{setting.setting}</code>
                    <span>{setting.message}</span>
                  </li>
                ))}
              </ul>
            </Section>
          ) : null}
        </div>
      </div>
    </Shell>
  );
}
