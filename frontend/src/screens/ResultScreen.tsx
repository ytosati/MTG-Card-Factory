// Result screen: the card text in rules format, its validation, design, power indicator and text usage.
// Details: specs/spec.md, RN-09, RN-12–RN-15, RN-22, RN-48 and "Screens" (Result); specs/plan.md, section 6.
import { useCallback, useEffect, useRef, useState } from "react";

import { getCard } from "../api/client";
import type {
  CardResponse,
  CardVersion,
  Comparable,
  PowerIndicator,
  RevisionFailure,
  TextUsageRecord,
  ValidationCause,
} from "../api/types";
import { StatusIcon } from "../components/StatusIcon";

interface ResultScreenProps {
  cardId: string;
  /** A failed automatic revision handed over by the generation job (spec RN-15), or null. */
  revisionFailure: RevisionFailure | null;
}

type Load = { kind: "loading" } | { kind: "failed"; message: string } | { kind: "loaded"; card: CardResponse };

/** See spec RN-48. */
const ARTIST = "Card Factory";

const UNREADABLE_CARD = "Card Factory sent a card that could not be read. Try again.";
const UNKNOWN_FAILURE = "The card could not be loaded. Try again.";

const POWER_WORDS: Record<PowerIndicator, string> = {
  too_weak: "Too weak",
  in_range: "In range",
  too_strong: "Too strong",
};

const POWER_SCALE: PowerIndicator[] = ["too_weak", "in_range", "too_strong"];

const COUNT_FORMAT = new Intl.NumberFormat("en-US");

const MANA_SYMBOL = /\{([^{}]+)\}/g;

// ---------------------------------------------------------------------------------------------
// Reading the card answer: anything outside the contract's shape is a failure, never a half card.
// ---------------------------------------------------------------------------------------------

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isString(value: unknown): value is string {
  return typeof value === "string";
}

function isCount(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value) && value >= 0;
}

/** An optional text field: absent, null and empty all read as null. */
function optionalText(value: unknown): string | null | undefined {
  if (value === null || value === undefined || value === "") return null;
  return isString(value) ? value : undefined;
}

function isPowerIndicator(value: unknown): value is PowerIndicator {
  return value === "too_strong" || value === "in_range" || value === "too_weak";
}

function readComparable(value: unknown): Comparable | null {
  if (!isRecord(value) || !isString(value.name)) return null;
  return {
    oracle_id: isString(value.oracle_id) ? value.oracle_id : "",
    name: value.name,
    role: isString(value.role) ? value.role : "",
  };
}

function readCause(value: unknown): ValidationCause | null {
  if (!isRecord(value) || !isString(value.message)) return null;
  return {
    check: isString(value.check) ? value.check : "",
    code: isString(value.code) ? value.code : "",
    message: value.message,
  };
}

function readUsage(value: unknown): TextUsageRecord | null {
  if (!isRecord(value) || !isString(value.provider) || !isString(value.model)) return null;
  if (!isCount(value.input_tokens) || !isCount(value.output_tokens)) return null;
  if (value.outcome !== "ok" && value.outcome !== "failed") return null;
  return {
    provider: value.provider,
    model: value.model,
    input_tokens: value.input_tokens,
    output_tokens: value.output_tokens,
    outcome: value.outcome,
    created_at: isString(value.created_at) ? value.created_at : "",
  };
}

function readAll<T>(value: unknown, read: (item: unknown) => T | null): T[] | null {
  if (!Array.isArray(value)) return null;
  const items = value.map(read);
  return items.every((item): item is T => item !== null) ? items : null;
}

function readVersion(value: unknown): CardVersion | null {
  if (!isRecord(value)) return null;
  const { name, type_line, rules_text, design_intent, rationale, power_justification, validation } = value;
  if (!isString(name) || name === "" || !isString(type_line)) return null;
  if (!isString(rules_text) || !isString(design_intent) || !isString(rationale) || !isString(power_justification)) {
    return null;
  }
  const manaCost = optionalText(value.mana_cost);
  const power = optionalText(value.power);
  const toughness = optionalText(value.toughness);
  if (manaCost === undefined || power === undefined || toughness === undefined) return null;
  if (!isPowerIndicator(value.power_indicator)) return null;
  if (value.status !== "approved" && value.status !== "rejected") return null;
  if (!isRecord(validation)) return null;
  const comparables = readAll(value.comparables, readComparable);
  const causes = readAll(validation.causes, readCause);
  if (comparables === null || causes === null) return null;
  return {
    name,
    mana_cost: manaCost,
    mana_value: isCount(value.mana_value) ? value.mana_value : 0,
    type_line,
    rules_text,
    power,
    toughness,
    rarity: isString(value.rarity) ? value.rarity : "",
    design_intent,
    rationale,
    comparables,
    power_indicator: value.power_indicator,
    power_justification,
    origin: isString(value.origin) ? value.origin : "",
    status: value.status,
    validation: {
      status: value.status,
      checks_run: readAll(validation.checks_run, (item) => (isString(item) ? item : null)) ?? [],
      causes,
      skipped: readAll(validation.skipped, (item) => (isString(item) ? item : null)) ?? [],
    },
  };
}

function readCardResponse(value: unknown): CardResponse | null {
  if (!isRecord(value) || !isString(value.id)) return null;
  const version = readVersion(value.current_version);
  if (version === null || !isRecord(value.usage)) return null;
  const text = readAll(value.usage.text, readUsage);
  if (text === null) return null;
  return { id: value.id, current_version: version, usage: { text } };
}

// ---------------------------------------------------------------------------------------------

/** The Result screen for one saved card. */
export function ResultScreen({ cardId, revisionFailure }: ResultScreenProps) {
  const [load, setLoad] = useState<Load>({ kind: "loading" });
  const [attempt, setAttempt] = useState(0);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const focusHeadingAfterLoad = useRef(false);

  useEffect(() => {
    let active = true;
    setLoad({ kind: "loading" });
    getCard(cardId).then(
      (answer) => {
        if (!active) return;
        const card = readCardResponse(answer);
        setLoad(card === null ? { kind: "failed", message: UNREADABLE_CARD } : { kind: "loaded", card });
      },
      (reason: unknown) => {
        if (active) setLoad({ kind: "failed", message: reason instanceof Error ? reason.message : UNKNOWN_FAILURE });
      },
    );
    return () => {
      active = false;
    };
  }, [cardId, attempt]);

  // The button that asked for the reload disappears while loading, so focus returns to the heading.
  useEffect(() => {
    if (load.kind !== "loading" && focusHeadingAfterLoad.current) {
      focusHeadingAfterLoad.current = false;
      headingRef.current?.focus();
    }
  }, [load]);

  const reload = useCallback(() => {
    focusHeadingAfterLoad.current = true;
    setAttempt((value) => value + 1);
  }, []);

  return (
    <main className="screen">
      <h1 ref={headingRef} tabIndex={-1}>
        Result
      </h1>{" "}
      {revisionFailure !== null && (
        <div className="result-revision-failure tone" role="alert">
          <StatusIcon tone="notice" />
          <div className="tone-body">
            <p className="result-revision-failure-title">The automatic revision did not complete.</p>
            <p>{revisionFailure.message}</p>
          </div>
        </div>
      )}
      {load.kind === "loading" && <p role="status">Loading the card…</p>}
      {load.kind === "failed" && (
        <div className="error-panel">
          <div role="alert">
            <p>{load.message}</p>
          </div>
          <button type="button" onClick={reload}>
            Try again
          </button>
        </div>
      )}
      {load.kind === "loaded" && <CardResult card={load.card} />}
    </main>
  );
}

// The spaces between blocks keep words apart when the screen text is copied or read as one string.
function CardResult({ card }: { card: CardResponse }) {
  const version = card.current_version;
  return (
    <>
      <Verdict version={version} /> <CardText version={version} />{" "}
      <section aria-labelledby="result-power">
        <h2 id="result-power">Power indicator</h2> <PowerReading indicator={version.power_indicator} />{" "}
        <TextOrMissing text={version.power_justification} missing="No justification was recorded." />{" "}
        <p className="hint">Assessed by the text model against the comparables. It does not affect validation.</p>
      </section>{" "}
      <section aria-labelledby="result-design">
        <h2 id="result-design">Design</h2> <h3 className="result-subheading">Intent</h3>{" "}
        <TextOrMissing text={version.design_intent} missing="No design intent was recorded." />{" "}
        <h3 className="result-subheading">Rationale</h3>{" "}
        <TextOrMissing text={version.rationale} missing="No rationale was recorded." />
      </section>{" "}
      <section aria-labelledby="result-comparables">
        <h2 id="result-comparables">Comparables</h2>{" "}
        {version.comparables.length > 0 ? (
          <ul className="result-comparables">
            {version.comparables.map((comparable, index) => (
              <li key={`${comparable.oracle_id}-${index}`}>
                <span className="result-comparable-name">{comparable.name}</span>{" "}
                {comparable.role !== "" && <span className="result-comparable-role">{comparable.role}</span>}
              </li>
            ))}
          </ul>
        ) : (
          <p className="hint">No comparables are recorded for this card.</p>
        )}
      </section>{" "}
      <Usage records={card.usage.text} />
    </>
  );
}

/** The validation result: approved, or rejected with every cause (spec RN-14, RN-15). */
function Verdict({ version }: { version: CardVersion }) {
  const checks = version.validation.checks_run.length;
  if (version.status === "approved") {
    return (
      <div className="result-verdict result-verdict-approved tone">
        <StatusIcon tone="success" />
        <p>
          <strong>Approved.</strong>{" "}
          {checks > 0 ? `${checks} ${checks === 1 ? "check" : "checks"} passed.` : "No check found a problem."}
        </p>
      </div>
    );
  }
  const causes = version.validation.causes;
  return (
    <div className="result-verdict result-verdict-rejected tone">
      <StatusIcon tone="danger" />
      <div className="tone-body">
        <p>
          <strong>Rejected.</strong>{" "}
          {causes.length > 0
            ? `${causes.length} ${causes.length === 1 ? "cause" : "causes"}:`
            : "No cause was recorded."}
        </p>{" "}
        {causes.length > 0 && (
          <ul className="result-causes">
            {causes.map((cause, index) => (
              <li key={`${cause.check}-${cause.code}-${index}`}>{cause.message}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

/** The card text in rules format, in the manner of a card page on Scryfall (spec "Screens", Result). */
function CardText({ version }: { version: CardVersion }) {
  const lines = version.rules_text.split("\n").filter((line) => line.trim() !== "");
  const hasPowerToughness = version.power !== null && version.toughness !== null;
  return (
    <article className="card-text" aria-labelledby="result-card-name">
      <div className="card-text-row card-text-title">
        <h2 id="result-card-name" className="card-text-name">
          {version.name}
        </h2>{" "}
        {version.mana_cost !== null && <ManaCost cost={version.mana_cost} />}
      </div>{" "}
      <p className="card-text-row card-text-type">{version.type_line}</p>{" "}
      {lines.length > 0 && (
        <div className="card-text-row card-text-rules">
          {lines.map((line, index) => (
            <p key={index}>{line}</p>
          ))}
        </div>
      )}{" "}
      <div className="card-text-row card-text-foot">
        <p className="card-text-artist">
          Illustrated by <span className="card-text-artist-name">{ARTIST}</span>
        </p>{" "}
        {hasPowerToughness && (
          <p className="card-text-pt">
            {version.power}/{version.toughness}
          </p>
        )}
      </div>
    </article>
  );
}

/** Mana symbols drawn as text in colored circles, with a spoken cost as the text alternative. */
function ManaCost({ cost }: { cost: string }) {
  const symbols = [...cost.matchAll(MANA_SYMBOL)].map((match) => match[1] ?? "");
  // Anything outside braces is not a cost written in symbols; it is shown as it was sent.
  if (symbols.length === 0 || symbols.map((symbol) => `{${symbol}}`).join("") !== cost) {
    return <span className="mana-cost mana-cost-plain">{cost}</span>;
  }
  return (
    <span className="mana-cost" role="img" aria-label={`Mana cost: ${symbols.map(spokenSymbol).join(", ")}`} title={cost}>
      {symbols.map((symbol, index) => (
        <ManaSymbol key={index} symbol={symbol} />
      ))}
    </span>
  );
}

const SYMBOL_COLORS = new Set(["W", "U", "B", "R", "G", "C"]);

const SPOKEN_PARTS: Record<string, string> = {
  W: "white",
  U: "blue",
  B: "black",
  R: "red",
  G: "green",
  C: "colorless",
  S: "snow",
};

/** One symbol in words: {2} "2 generic", {W/U} "white or blue", {G/P} "Phyrexian green". */
function spokenSymbol(symbol: string): string {
  const parts = symbol.toUpperCase().split("/");
  const phyrexian = parts.length > 1 && parts.includes("P");
  const words = parts
    .filter((part) => !phyrexian || part !== "P")
    .map((part) => SPOKEN_PARTS[part] ?? (/^\d+$/.test(part) ? `${part} generic` : part));
  const spoken = words.join(" or ");
  return phyrexian ? `Phyrexian ${spoken}` : spoken;
}

/** The fill of one half of a symbol: a color, or the generic fill for numbers and letters such as X. */
function fillOf(part: string): string {
  return SYMBOL_COLORS.has(part) ? part.toLowerCase() : "generic";
}

function ManaSymbol({ symbol }: { symbol: string }) {
  const parts = symbol.toUpperCase().split("/");
  // The P of a Phyrexian symbol is a mark, not a half: {G/P} is filled green.
  const fills = parts.filter((part) => parts.length === 1 || part !== "P").map(fillOf);
  const first = fills[0] ?? "generic";
  const second = fills[1];
  const classes = ["mana-symbol", `mana-${first}`];
  if (second !== undefined && second !== first) classes.push(`mana-hybrid-${second}`);
  if (parts.length > 1) classes.push("mana-symbol-split");
  // The braces are hidden on screen but stay in the text, so a copied cost reads in rules format.
  return (
    <span className={classes.join(" ")}>
      <span className="mana-brace">{"{"}</span>
      {symbol}
      <span className="mana-brace">{"}"}</span>
    </span>
  );
}

/** The indicator in words beside a three-step scale; the scale only repeats the words. */
function PowerReading({ indicator }: { indicator: PowerIndicator }) {
  return (
    <p className={`power-reading power-${indicator}`}>
      <span className="power-scale" aria-hidden="true">
        {POWER_SCALE.map((step) => (
          <span key={step} className={step === indicator ? "power-step power-step-current" : "power-step"} />
        ))}
      </span>{" "}
      <strong>{POWER_WORDS[indicator]}</strong>
    </p>
  );
}

function TextOrMissing({ text, missing }: { text: string; missing: string }) {
  if (text.trim() === "") return <p className="hint">{missing}</p>;
  return <p className="result-prose">{text}</p>;
}

/** The text usage of the card, one row per provider call (spec RN-09, CA-16). */
function Usage({ records }: { records: TextUsageRecord[] }) {
  const input = records.reduce((sum, record) => sum + record.input_tokens, 0);
  const output = records.reduce((sum, record) => sum + record.output_tokens, 0);
  return (
    <section aria-labelledby="result-usage">
      <h2 id="result-usage">Text usage</h2>{" "}
      {records.length === 0 ? (
        <p className="hint">No text usage is recorded for this card.</p>
      ) : (
        <div className="usage-table-frame">
          <table className="usage-table">
            <thead>
              <tr>
                <th scope="col">Call</th>
                <th scope="col">Provider and model</th>
                <th scope="col" className="usage-number">
                  Input tokens
                </th>
                <th scope="col" className="usage-number">
                  Output tokens
                </th>
              </tr>
            </thead>
            <tbody>
              {records.map((record, index) => (
                <tr key={index}>
                  <th scope="row">
                    {index + 1}
                    {record.outcome === "failed" && <span className="usage-failed"> Failed</span>}{" "}
                  </th>
                  <td className="usage-model">
                    <code>{record.provider}</code> <code>{record.model}</code>{" "}
                  </td>
                  <td className="usage-number">{COUNT_FORMAT.format(record.input_tokens)} </td>
                  <td className="usage-number">{COUNT_FORMAT.format(record.output_tokens)} </td>
                </tr>
              ))}
            </tbody>
            {records.length > 1 && (
              <tfoot>
                <tr>
                  <th scope="row" colSpan={2}>
                    Total{" "}
                  </th>
                  <td className="usage-number">{COUNT_FORMAT.format(input)} </td>
                  <td className="usage-number">{COUNT_FORMAT.format(output)} </td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      )}
    </section>
  );
}
