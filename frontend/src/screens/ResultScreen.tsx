// Result screen container: reads the card, checks its shape and hands each state to the view.
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
import { resultCopy } from "./result/copy";
import { ResultView } from "./result/ResultView";
import type { ResultViewState } from "./result/ResultView";

interface ResultScreenProps {
  cardId: string;
  /** A failed automatic revision handed over by the generation job (spec RN-15), or null. */
  revisionFailure: RevisionFailure | null;
}

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
  const [load, setLoad] = useState<ResultViewState>({ kind: "loading" });
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
        setLoad(card === null ? { kind: "failed", message: resultCopy.unreadableCard } : { kind: "loaded", card });
      },
      (reason: unknown) => {
        if (active) setLoad({ kind: "failed", message: reason instanceof Error ? reason.message : resultCopy.unknownFailure });
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

  return <ResultView state={load} revisionFailure={revisionFailure} headingRef={headingRef} onReload={reload} />;
}
