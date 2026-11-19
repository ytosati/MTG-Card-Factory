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
  /**
   * The cost and type line of each comparable, by oracle id. The card response names a comparable and its role
   * only; these stand in for what the reference database holds.
   */
  comparableFaces?: Record<string, { cost: string; typeLine: string }>;
}

const COUNT = new Intl.NumberFormat("en-US");

/** A check's code read as words: "color_identity" becomes "Color identity". */
export function checkName(code: string): string {
  const words = code.replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

const POWER_SCALE: PowerIndicator[] = ["too_weak", "in_range", "too_strong"];

/** The power indicator as one quiet line: the label, the three states with the assessed one lit, the reason below. */
export function PowerLine({ version, hint = false }: { version: CardVersion; hint?: boolean }) {
  const id = useId();
  return (
    <section className={styles.power} aria-labelledby={id}>
      <div className={styles.powerRow}>
        <h2 id={id} className={ui.label}>
          {sceneCopy.powerLabel}
        </h2>
        <ol className={styles.scale} aria-label={resultCopy.powerHeading}>
          {POWER_SCALE.map((level) => {
            const on = level === version.power_indicator;
            return (
              <li key={level} data-on={on ? "true" : "false"} aria-current={on ? "true" : undefined}>
                {on ? <StarGlyph size={8} className={styles.scaleStar} /> : null}
                {sceneCopy.powerScale[level]}
              </li>
            );
          })}
        </ol>
      </div>
      <p className={styles.justification}>{version.power_justification || resultCopy.noJustification}</p>
      {hint ? <p className={styles.hint}>{resultCopy.powerHint}</p> : null}
    </section>
  );
}

/** The existing cards the text model compared the card against: name, cost, type line and the role each played. */
export function Comparables({ version, faces = {} }: { version: CardVersion; faces?: ResultExtras["comparableFaces"] }) {
  const id = useId();
  return (
    <section className={styles.compared} aria-labelledby={id}>
      <h2 id={id} className={ui.label}>
        {resultCopy.comparablesHeading}
      </h2>
      {version.comparables.length > 0 ? (
        <ul className={styles.comparedList}>
          {version.comparables.map((card) => {
            const face = faces[card.oracle_id];
            return (
              <li key={card.oracle_id}>
                <span className={styles.comparedHead}>
                  <span className={styles.comparedName}>{card.name}</span>
                  {face?.cost ? <ManaCostSymbols cost={face.cost} size={15} className={styles.comparedCost} /> : null}
                </span>
                {face ? <span className={styles.comparedType}>{face.typeLine}</span> : null}
                <span className={styles.comparedRole}>
                  <StarGlyph size={7} className={styles.comparedStar} />
                  {card.role}
                </span>
              </li>
            );
          })}
        </ul>
      ) : (
        <p className={styles.quiet}>{resultCopy.noComparables}</p>
      )}
    </section>
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
            <PowerLine version={version} hint />
            <Comparables version={version} faces={extras.comparableFaces} />
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
