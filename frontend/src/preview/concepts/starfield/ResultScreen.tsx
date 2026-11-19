// Concept E "Starfield" (tasks.md T251): the Result screen as a card page: the card beside its text in rules format,
// the verdicts in a side column, then the design and the usage in quiet ruled sections.
import { useEffect, useId } from "react";

import type { CardVersion, PowerIndicator } from "../../../api/types";
import { resultCopy } from "../../../screens/result/copy";
import { statusCopy } from "../../../screens/status/copy";
import type { PreviewCard } from "../../fixtureTypes";
import { ManaCostSymbols } from "../forge/symbols/ManaSymbol";
import { ChartCard, RulesText } from "./ChartCard";
import { StarGlyph } from "./glyphs";
import { Section } from "./parts";
import { sceneCopy } from "./scenes";
import ui from "./screen.module.css";
import { Shell } from "./Shell";
import styles from "./result.module.css";

/** What the card page shows that the card response does not carry yet (the art and editing milestones). */
export interface ResultExtras {
  notes: string[];
  base: string | null;
  art: { provider: string; model: string; images: number } | null;
  loyalty?: string;
}

const COUNT = new Intl.NumberFormat("en-US");

/** A check's code read as words: "color_identity" becomes "Color identity". */
export function checkName(code: string): string {
  const words = code.replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

const DIAL_ANGLE: Record<PowerIndicator, number> = { too_weak: 150, in_range: 90, too_strong: 30 };
const ZONES: { value: PowerIndicator; from: number; to: number }[] = [
  { value: "too_weak", from: 180, to: 122 },
  { value: "in_range", from: 118, to: 62 },
  { value: "too_strong", from: 58, to: 0 },
];

function point(angle: number, radius: number): { x: number; y: number } {
  const radians = (angle * Math.PI) / 180;
  return { x: 100 + Math.cos(radians) * radius, y: 100 - Math.sin(radians) * radius };
}

function arc(from: number, to: number, radius: number): string {
  const start = point(from, radius);
  const end = point(to, radius);
  return `M ${start.x.toFixed(2)} ${start.y.toFixed(2)} A ${radius} ${radius} 0 0 1 ${end.x.toFixed(2)} ${end.y.toFixed(2)}`;
}

/** The power indicator as a half dial in three zones, the assessed zone lit and a star on its needle. */
export function PowerDial({ value }: { value: PowerIndicator }) {
  const tip = point(DIAL_ANGLE[value], 74);
  return (
    <div className={styles.dial}>
      <svg viewBox="0 0 200 112" role="img" aria-label={`${resultCopy.powerHeading}: ${resultCopy.powerWords[value]}`}>
        {Array.from({ length: 19 }, (_, index) => {
          const angle = index * 10;
          const outer = point(angle, 92);
          const inner = point(angle, index % 3 === 0 ? 86 : 89);
          return <line key={angle} x1={inner.x} y1={inner.y} x2={outer.x} y2={outer.y} className={styles.dialTick} />;
        })}
        {ZONES.map((zone) => (
          <path key={zone.value} d={arc(zone.from, zone.to, 80)} className={styles.zone} data-on={zone.value === value ? "true" : "false"} />
        ))}
        <line x1="100" y1="100" x2={tip.x} y2={tip.y} className={styles.needle} />
        <circle cx="100" cy="100" r="3" className={styles.hub} />
        <path transform={`translate(${tip.x} ${tip.y})`} d="M0 -6 L1.2 -1.2 L6 0 L1.2 1.2 L0 6 L-1.2 1.2 L-6 0 L-1.2 -1.2 Z" className={styles.tip} />
      </svg>
      <div className={styles.dialScale} aria-hidden="true">
        {ZONES.map((zone) => (
          <span key={zone.value} data-on={zone.value === value ? "true" : "false"}>
            {sceneCopy.powerScale[zone.value]}
          </span>
        ))}
      </div>
    </div>
  );
}

export function Validation({ version }: { version: CardVersion }) {
  const { validation } = version;
  const approved = validation.status === "approved";
  return (
    <section className={styles.verdict} aria-labelledby="sf-validation" data-status={validation.status}>
      <h2 id="sf-validation" className={ui.label}>
        {sceneCopy.validationHeading}
      </h2>
      <p className={styles.verdictWord}>
        <span className={styles.verdictMark} aria-hidden="true" />
        {approved ? resultCopy.approved : resultCopy.rejected}
      </p>
      {approved ? (
        <>
          <p className={styles.quiet}>{resultCopy.checksPassed(validation.checks_run.length)}</p>
          <ul className={styles.checks} aria-label={sceneCopy.checksRun}>
            {validation.checks_run.map((check) => (
              <li key={check}>{checkName(check)}</li>
            ))}
          </ul>
        </>
      ) : (
        <>
          <p className={styles.quiet}>{resultCopy.causesCount(validation.causes.length)}</p>
          <ol className={styles.causes}>
            {validation.causes.map((cause) => (
              <li key={cause.code}>
                <span className={styles.causeCheck}>{checkName(cause.check)}</span>
                <span>{cause.message}</span>
              </li>
            ))}
          </ol>
        </>
      )}
    </section>
  );
}

/** The text usage of a card: one row per provider call, then the totals. */
export function UsageTable({ entry }: { entry: PreviewCard }) {
  const totalIn = entry.usage.text.reduce((sum, record) => sum + record.input_tokens, 0);
  const totalOut = entry.usage.text.reduce((sum, record) => sum + record.output_tokens, 0);
  return (
    <table className={styles.usage}>
      <thead>
        <tr>
          <th scope="col">{resultCopy.usageCall}</th>
          <th scope="col">{resultCopy.usageProviderModel}</th>
          <th scope="col" className={styles.num}>
            {resultCopy.usageInput}
          </th>
          <th scope="col" className={styles.num}>
            {resultCopy.usageOutput}
          </th>
        </tr>
      </thead>
      <tbody>
        {entry.usage.text.map((record, index) => (
          <tr key={index} data-failed={record.outcome === "failed" ? "true" : "false"}>
            <td className={styles.mono}>{String(index + 1).padStart(2, "0")}</td>
            <td>
              {statusCopy.providerNames[record.provider] ?? record.provider} <span className={styles.model}>{record.model}</span>
              {record.outcome === "failed" ? <span className={styles.failed}>{resultCopy.usageFailed}</span> : null}
            </td>
            <td className={styles.num}>{COUNT.format(record.input_tokens)}</td>
            <td className={styles.num}>{COUNT.format(record.output_tokens)}</td>
          </tr>
        ))}
      </tbody>
      <tfoot>
        <tr>
          <th scope="row" colSpan={2}>
            {resultCopy.usageTotal}
          </th>
          <td className={styles.num}>{COUNT.format(totalIn)}</td>
          <td className={styles.num}>{COUNT.format(totalOut)}</td>
        </tr>
      </tfoot>
    </table>
  );
}

export function ResultScreen({ entry, extras }: { entry: PreviewCard; extras: ResultExtras }) {
  const version = entry.current_version;
  const powerId = useId();

  useEffect(() => {
    document.title = `${version.name} · Card Factory`;
  }, [version.name]);

  return (
    <Shell current="Library">
      <div className={`${ui.page} ${styles.page}`}>
        <div className={styles.top}>
          <div className={styles.figure}>
            <ChartCard version={version} image={entry.image} loyalty={extras.loyalty} textHidden />
            {entry.image ? (
              <a className={ui.link} href={entry.image.src} target="_blank" rel="noreferrer">
                {sceneCopy.fullResolution}
              </a>
            ) : null}
          </div>

          <article className={styles.rules} aria-label={sceneCopy.rulesLabel}>
            <div className={styles.nameRow}>
              <h1 className={styles.name}>{version.name}</h1>
              {version.mana_cost ? <ManaCostSymbols cost={version.mana_cost} size={26} className={styles.cost} /> : null}
            </div>
            <p className={styles.typeLine}>{version.type_line}</p>
            <RulesText text={version.rules_text} className={styles.rulesText} />
            {version.power !== null && version.toughness !== null ? (
              <p className={styles.stat}>
                {version.power} / {version.toughness}
              </p>
            ) : extras.loyalty ? (
              <p className={styles.stat}>Loyalty {extras.loyalty}</p>
            ) : null}
            <dl className={`${ui.facts} ${styles.facts}`}>
              <div>
                <dt>{sceneCopy.rarity}</dt>
                <dd className={styles.capital}>{version.rarity}</dd>
              </div>
              <div>
                <dt>{sceneCopy.artist}</dt>
                <dd>{extras.art ? sceneCopy.artGenerated(extras.art.model) : sceneCopy.noArt}</dd>
              </div>
            </dl>
            <div className={`${ui.actions} ${styles.actions}`} role="group" aria-label={sceneCopy.actionsLabel}>
              <button type="button" className={ui.primary}>
                <StarGlyph size={10} className={ui.primaryStar} />
                {sceneCopy.newRequest}
              </button>
              <button type="button" className={ui.secondary}>
                {entry.image ? sceneCopy.retryArt : sceneCopy.generateArt}
              </button>
              <button type="button" className={ui.secondary}>
                {sceneCopy.uploadArt}
              </button>
            </div>
          </article>

          <aside className={styles.side}>
            <Validation version={version} />
            <section className={styles.power} aria-labelledby={powerId}>
              <h2 id={powerId} className={ui.label}>
                {resultCopy.powerHeading}
              </h2>
              <PowerDial value={version.power_indicator} />
              <p className={styles.justification}>{version.power_justification || resultCopy.noJustification}</p>
              <p className={styles.hint}>{resultCopy.powerHint}</p>
            </section>
          </aside>
        </div>

        <div className={styles.sections}>
          <Section id="sf-intent" title={resultCopy.intentHeading}>
            <p className={styles.prose} data-empty={version.design_intent ? "false" : "true"}>
              {version.design_intent || resultCopy.noIntent}
            </p>
          </Section>
          <Section id="sf-rationale" title={resultCopy.rationaleHeading}>
            <p className={styles.prose} data-empty={version.rationale ? "false" : "true"}>
              {version.rationale || resultCopy.noRationale}
            </p>
          </Section>
          {extras.notes.length > 0 ? (
            <Section id="sf-notes" title={sceneCopy.notesHeading}>
              <ul className={styles.notes}>
                {extras.notes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            </Section>
          ) : null}
          <Section id="sf-comparables" title={resultCopy.comparablesHeading}>
            {version.comparables.length > 0 ? (
              <ul className={styles.comparables}>
                {version.comparables.map((card) => (
                  <li key={card.oracle_id}>
                    <span className={styles.comparableName}>{card.name}</span>
                    <span className={styles.comparableRole}>{card.role}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className={styles.quiet}>{resultCopy.noComparables}</p>
            )}
          </Section>
          <Section id="sf-base" title={sceneCopy.baseHeading}>
            <p className={styles.quiet}>{extras.base ?? sceneCopy.noBase}</p>
          </Section>
          <Section id="sf-skipped" title={sceneCopy.skippedHeading}>
            {version.validation.skipped.length > 0 ? (
              <ul className={styles.checks}>
                {version.validation.skipped.map((check) => (
                  <li key={check}>{checkName(check)}</li>
                ))}
              </ul>
            ) : (
              <p className={styles.quiet}>{sceneCopy.noSkipped}</p>
            )}
          </Section>
          <Section id="sf-usage" title={resultCopy.usageHeading}>
            {entry.usage.text.length > 0 ? (
              <UsageTable entry={entry} />
            ) : (
              <p className={styles.quiet}>{resultCopy.noUsage}</p>
            )}
          </Section>
          <Section id="sf-art-usage" title={sceneCopy.artUsageHeading}>
            {extras.art ? (
              <dl className={ui.facts}>
                <div>
                  <dt>{resultCopy.usageProviderModel}</dt>
                  <dd>
                    {statusCopy.providerNames[extras.art.provider] ?? extras.art.provider} <span className={styles.model}>{extras.art.model}</span>
                  </dd>
                </div>
                <div>
                  <dt>{sceneCopy.artUsageImages}</dt>
                  <dd className={styles.mono}>{extras.art.images}</dd>
                </div>
              </dl>
            ) : (
              <p className={styles.quiet}>{sceneCopy.noArtUsage}</p>
            )}
          </Section>
        </div>
      </div>
    </Shell>
  );
}
