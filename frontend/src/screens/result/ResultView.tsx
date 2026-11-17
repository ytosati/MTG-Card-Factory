// Result screen view: the card text in rules format, its validation, design, power indicator and text usage.
// Details: specs/spec.md, RN-09, RN-12–RN-15, RN-22, RN-48 and "Screens" (Result).
import type { RefObject } from "react";

import type { CardResponse, CardVersion, PowerIndicator, RevisionFailure, TextUsageRecord } from "../../api/types";
import { CardText } from "../../components/CardText";
import { cx } from "../../components/classNames";
import { Screen, screenStyles } from "../../components/Screen";
import { StatusIcon, toneStyles } from "../../components/StatusIcon";
import { resultCopy as copy } from "./copy";
import styles from "./ResultView.module.css";

/** What the Result screen shows: the card being read, the read that failed, or the card. */
export type ResultViewState =
  | { kind: "loading" }
  | { kind: "failed"; message: string }
  | { kind: "loaded"; card: CardResponse };

interface ResultViewProps {
  state: ResultViewState;
  /** A failed automatic revision handed over by the generation job (spec RN-15), or null. */
  revisionFailure: RevisionFailure | null;
  headingRef?: RefObject<HTMLHeadingElement | null> | undefined;
  onReload: () => void;
}

const POWER_SCALE: PowerIndicator[] = ["too_weak", "in_range", "too_strong"];

const COUNT_FORMAT = new Intl.NumberFormat("en-US");

/** The Result screen for one state of its read. */
export function ResultView({ state, revisionFailure, headingRef, onReload }: ResultViewProps) {
  return (
    <Screen>
      <h1 ref={headingRef} tabIndex={-1}>
        {copy.title}
      </h1>{" "}
      {revisionFailure !== null && (
        <div className={cx(styles.revisionFailure, toneStyles.tone)} role="alert">
          <StatusIcon tone="notice" />
          <div className={toneStyles.toneBody}>
            <p className={styles.revisionFailureTitle}>{copy.revisionFailureTitle}</p>
            <p>{revisionFailure.message}</p>
          </div>
        </div>
      )}
      {state.kind === "loading" && <p role="status">{copy.loading}</p>}
      {state.kind === "failed" && (
        <div className={screenStyles.errorPanel}>
          <div role="alert">
            <p>{state.message}</p>
          </div>
          <button type="button" onClick={onReload}>
            {copy.tryAgain}
          </button>
        </div>
      )}
      {state.kind === "loaded" && <CardResult card={state.card} />}
    </Screen>
  );
}

// The spaces between blocks keep words apart when the screen text is copied or read as one string.
function CardResult({ card }: { card: CardResponse }) {
  const version = card.current_version;
  return (
    <>
      <Verdict version={version} /> <CardText version={version} />{" "}
      <section aria-labelledby="result-power">
        <h2 id="result-power">{copy.powerHeading}</h2> <PowerReading indicator={version.power_indicator} />{" "}
        <TextOrMissing text={version.power_justification} missing={copy.noJustification} />{" "}
        <p className={screenStyles.hint}>{copy.powerHint}</p>
      </section>{" "}
      <section aria-labelledby="result-design">
        <h2 id="result-design">{copy.designHeading}</h2> <h3 className={styles.subheading}>{copy.intentHeading}</h3>{" "}
        <TextOrMissing text={version.design_intent} missing={copy.noIntent} />{" "}
        <h3 className={styles.subheading}>{copy.rationaleHeading}</h3>{" "}
        <TextOrMissing text={version.rationale} missing={copy.noRationale} />
      </section>{" "}
      <section aria-labelledby="result-comparables">
        <h2 id="result-comparables">{copy.comparablesHeading}</h2>{" "}
        {version.comparables.length > 0 ? (
          <ul className={styles.comparables}>
            {version.comparables.map((comparable, index) => (
              <li key={`${comparable.oracle_id}-${index}`}>
                <span className={styles.comparableName}>{comparable.name}</span>{" "}
                {comparable.role !== "" && <span className={styles.comparableRole}>{comparable.role}</span>}
              </li>
            ))}
          </ul>
        ) : (
          <p className={screenStyles.hint}>{copy.noComparables}</p>
        )}
      </section>{" "}
      <Usage records={card.usage.text} />
    </>
  );
}

/** The validation result: approved, or rejected with every cause (spec RN-14, RN-15). */
function Verdict({ version }: { version: CardVersion }) {
  if (version.status === "approved") {
    return (
      <div className={cx(styles.verdict, styles.approved, toneStyles.tone)}>
        <StatusIcon tone="success" />
        <p>
          <strong>{copy.approved}</strong> {copy.checksPassed(version.validation.checks_run.length)}
        </p>
      </div>
    );
  }
  const causes = version.validation.causes;
  return (
    <div className={cx(styles.verdict, styles.rejected, toneStyles.tone)}>
      <StatusIcon tone="danger" />
      <div className={toneStyles.toneBody}>
        <p>
          <strong>{copy.rejected}</strong> {copy.causesCount(causes.length)}
        </p>{" "}
        {causes.length > 0 && (
          <ul className={styles.causes}>
            {causes.map((cause, index) => (
              <li key={`${cause.check}-${cause.code}-${index}`}>{cause.message}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

/** The indicator in words beside a three-step scale; the scale only repeats the words. */
function PowerReading({ indicator }: { indicator: PowerIndicator }) {
  return (
    <p className={styles.powerReading}>
      <span className={styles.powerScale} aria-hidden="true">
        {POWER_SCALE.map((step) => (
          <span key={step} className={cx(styles.powerStep, step === indicator && styles.powerStepCurrent)} />
        ))}
      </span>{" "}
      <strong>{copy.powerWords[indicator]}</strong>
    </p>
  );
}

function TextOrMissing({ text, missing }: { text: string; missing: string }) {
  if (text.trim() === "") return <p className={screenStyles.hint}>{missing}</p>;
  return <p className={styles.prose}>{text}</p>;
}

/** The text usage of the card, one row per provider call (spec RN-09, CA-16). */
function Usage({ records }: { records: TextUsageRecord[] }) {
  const input = records.reduce((sum, record) => sum + record.input_tokens, 0);
  const output = records.reduce((sum, record) => sum + record.output_tokens, 0);
  return (
    <section aria-labelledby="result-usage">
      <h2 id="result-usage">{copy.usageHeading}</h2>{" "}
      {records.length === 0 ? (
        <p className={screenStyles.hint}>{copy.noUsage}</p>
      ) : (
        <div className={styles.usageFrame}>
          <table className={styles.usageTable}>
            <thead>
              <tr>
                <th scope="col">{copy.usageCall}</th>
                <th scope="col">{copy.usageProviderModel}</th>
                <th scope="col" className={styles.number}>
                  {copy.usageInput}
                </th>
                <th scope="col" className={styles.number}>
                  {copy.usageOutput}
                </th>
              </tr>
            </thead>
            <tbody>
              {records.map((record, index) => (
                <tr key={index}>
                  <th scope="row">
                    {index + 1}
                    {record.outcome === "failed" && <span className={styles.usageFailed}> {copy.usageFailed}</span>}{" "}
                  </th>
                  <td className={styles.usageModel}>
                    <code>{record.provider}</code> <code>{record.model}</code>{" "}
                  </td>
                  <td className={styles.number}>{COUNT_FORMAT.format(record.input_tokens)} </td>
                  <td className={styles.number}>{COUNT_FORMAT.format(record.output_tokens)} </td>
                </tr>
              ))}
            </tbody>
            {records.length > 1 && (
              <tfoot>
                <tr>
                  <th scope="row" colSpan={2}>
                    {copy.usageTotal}{" "}
                  </th>
                  <td className={styles.number}>{COUNT_FORMAT.format(input)} </td>
                  <td className={styles.number}>{COUNT_FORMAT.format(output)} </td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      )}
    </section>
  );
}
