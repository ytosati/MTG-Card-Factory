// @vitest-environment jsdom
// Tests for the Result screen, card text part (spec RN-09, RN-12, RN-13, RN-14, RN-15, RN-22, RN-48,
// RN-49; CA-16, CA-27, CA-29, CA-58). T67.
//
// Component API under test (frontend/src/screens/ResultScreen.tsx):
//   <ResultScreen cardId={string} revisionFailure={{ code, message } | null} />
// - A level-1 heading names Result. The screen reads GET /api/cards/{cardId}.
// - It shows the card text in rules format (name, mana cost, type line, rules text, power and
//   toughness), the artist credit "Card Factory", the status (Approved or Rejected) with the cause
//   messages of a rejected card, the design intent, the rationale, the names of the comparables, the
//   power indicator as words (Too strong, In range, Too weak, never the raw code) with its
//   justification, and the text usage records (provider, model, input and output tokens).
// - A revision failure handed over by the Request screen is shown in an alert with its message.
// - A failed or unreadable card answer shows a readable failure in an alert.
//
// Mocks are built from the contract samples (plan section 6).
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ResultScreen } from "./ResultScreen";
import type { CardResponse } from "../api/types";
import { cardGenerated, errorNotFound, jobGenerationDone, jobGenerationRevisionFailed } from "../api/contract/samples";
import { calledUrl, jsonResponse, stubFetchByPath, textResponse } from "../test/fetchMock";

type CardShape = CardResponse;
type CardVersionShape = CardResponse["current_version"];
type RevisionFailureShape = { code: string; message: string };

/** The card id the Request screen hands over: the one in the done job's result. */
const CARD_ID = jobGenerationDone.result.card;

let fetchMock: ReturnType<typeof stubFetchByPath>;

function withVersion(overrides: Partial<CardVersionShape>, usage: CardShape["usage"] = cardGenerated.usage): CardShape {
  return { ...cardGenerated, current_version: { ...cardGenerated.current_version, ...overrides }, usage };
}

const rejectedCard = withVersion({
  mana_value: 5,
  status: "rejected",
  validation: {
    status: "rejected",
    checks_run: ["mana_cost", "color_identity", "name"],
    causes: [
      { check: "mana_cost", code: "mana_value_mismatch", message: "The stated mana value 5 does not match the cost {2}{G}{W}." },
      { check: "name", code: "existing_name", message: "The name is the name of an existing card." },
    ],
    skipped: [],
  },
});

const tooStrongCard = withVersion({
  power_indicator: "too_strong",
  power_justification: "Stronger than Lanternroot Shaman and Glowmoss Herder at the same cost.",
});

/** Installs a backend whose GET /api/cards/{id} answers `answer`, then renders the screen. */
async function renderCard(
  answer: CardShape | (() => Promise<Response>),
  revisionFailure: RevisionFailureShape | null = null,
) {
  fetchMock = stubFetchByPath({
    [`/api/cards/${CARD_ID}`]: typeof answer === "function" ? answer : async () => jsonResponse(answer),
  });
  render(<ResultScreen cardId={CARD_ID} revisionFailure={revisionFailure} />);
}

async function renderShown(card: CardShape, revisionFailure: RevisionFailureShape | null = null) {
  await renderCard(card, revisionFailure);
  await screen.findAllByText(card.current_version.name, { exact: false });
}

function mainText(): string {
  return (screen.getByRole("main").textContent ?? "").replace(/\s+/g, " ");
}

/** Text plus the text alternatives of symbols (alt, aria-label), so a cost drawn as symbols still counts. */
function shownCost(): string {
  const main = screen.getByRole("main");
  const alternatives = Array.from(main.querySelectorAll<HTMLElement>("[alt], [aria-label]"))
    .map((element) => element.getAttribute("alt") ?? element.getAttribute("aria-label") ?? "")
    .join("");
  return `${main.textContent ?? ""}\n${alternatives}`;
}

function alertText(): string {
  return screen
    .queryAllByRole("alert")
    .map((element) => element.textContent ?? "")
    .join(" ");
}

/** A token count as shown: plain or with a thousands separator. */
function countPattern(value: number): RegExp {
  const plain = String(value);
  const grouped = plain.replace(/\B(?=(\d{3})+(?!\d))/g, "[,.\\s  ]?");
  return new RegExp(`(^|\\D)${grouped}(\\D|$)`);
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

// ---------------------------------------------------------------------------------------------

describe("ResultScreen: card text (RN-12, RN-13, RN-49)", () => {
  it("RN-49: has a level-1 heading naming Result and reads GET /api/cards/{id}", async () => {
    await renderShown(cardGenerated);

    expect(screen.getByRole("heading", { level: 1, name: /result/i })).toBeTruthy();
    const reads = fetchMock.mock.calls.map((call) => calledUrl(call[0]).split("?")[0]);
    expect(reads).toContain(`/api/cards/${CARD_ID}`);
  });

  it("RN-12: shows the name, mana cost, type line, rules text, power and toughness", async () => {
    await renderShown(cardGenerated);
    const version = cardGenerated.current_version;

    const text = mainText();
    expect(text).toContain(version.name);
    expect(shownCost()).toContain(version.mana_cost);
    expect(text).toContain(version.type_line);
    expect(text).toContain(version.rules_text);
    expect(text).toMatch(/(^|\D)2\s*\/\s*3(\D|$)/);
  });

  it("CA-27: shows the design intent, the rationale and every comparable used", async () => {
    await renderShown(cardGenerated);
    const version = cardGenerated.current_version;

    const text = mainText();
    expect(text).toContain(version.design_intent);
    expect(text).toContain(version.rationale);
    for (const comparable of version.comparables) expect(text).toContain(comparable.name);
  });

  it("RN-12: a card with no power and toughness and no mana cost shows neither, and never null or undefined", async () => {
    await renderShown(
      withVersion({
        name: "Hollow Lantern Grove",
        mana_cost: null,
        mana_value: 0,
        type_line: "Land",
        rules_text: "{T}: Add {G} or {W}.",
        power: null,
        toughness: null,
      }),
    );

    const text = mainText();
    expect(text).toContain("Hollow Lantern Grove");
    expect(text).toContain("{T}: Add {G} or {W}.");
    expect(text).not.toMatch(/\bnull\b|\bundefined\b|NaN/);
  });

  it("RN-12: odd characters, hybrid and Phyrexian symbols and every line of a long rules text are shown verbatim", async () => {
    const lines = [
      "Flying, vigilance",
      "{G/W}, {T}: Create a 1/1 green and white Spirit creature token. ({G/W} can be paid with either {G} or {W}.)",
      "{G/P}: This creature gets +1/+1 until end of turn — once each turn.",
      `“Quoted” <b>markup</b> & Æther’s lamp: ${"lantern ".repeat(400).trim()}`,
    ];
    const name = "Æther-Lit Wanderer’s “Lamp”";
    await renderShown(withVersion({ name, mana_cost: "{X}{2}{G/W}{G/P}", rules_text: lines.join("\n") }));

    const text = mainText();
    expect(text).toContain(name);
    expect(shownCost()).toContain("{X}{2}{G/W}{G/P}");
    for (const line of lines) expect(text).toContain(line);
    expect(document.querySelector("main b")).toBeNull();
  });
});

describe("ResultScreen: artist credit (RN-48, CA-58)", () => {
  it("CA-58: shows Card Factory as the artist with the card text", async () => {
    await renderShown(cardGenerated);
    expect(mainText()).toMatch(/(artist|illustrat\w*)(\s+by)?\W*Card Factory/i);
  });
});

describe("ResultScreen: validation result (RN-14, RN-15)", () => {
  it("RN-14: an approved card is shown as approved and not as rejected", async () => {
    await renderShown(cardGenerated);

    const text = mainText();
    expect(text).toMatch(/\bapproved\b/i);
    expect(text).not.toMatch(/\brejected\b/i);
  });

  it("RN-14, RN-15: a rejected card is shown as rejected with every cause, and not as approved", async () => {
    await renderShown(rejectedCard);

    const text = mainText();
    expect(text).toMatch(/\brejected\b/i);
    expect(text).not.toMatch(/\bapproved\b/i);
    for (const cause of rejectedCard.current_version.validation.causes) expect(text).toContain(cause.message);
  });

  it("RN-15: a revision failure handed over is shown in an alert, beside the rejected card and its causes", async () => {
    const failure = jobGenerationRevisionFailed.result.revision_failure;
    await renderShown(rejectedCard, failure);

    expect(alertText()).toContain(failure.message);
    const text = mainText();
    expect(text).toMatch(/\brejected\b/i);
    for (const cause of rejectedCard.current_version.validation.causes) expect(text).toContain(cause.message);
  });

  it("RN-15: with no revision failure no failure notice is shown", async () => {
    await renderShown(cardGenerated, null);

    expect(mainText()).not.toContain(jobGenerationRevisionFailed.result.revision_failure.message);
    expect(alertText().trim()).toBe("");
  });
});

describe("ResultScreen: power indicator (RN-22, CA-29)", () => {
  it("CA-29: an in-range card shows the indicator in words with its justification citing a comparable", async () => {
    await renderShown(cardGenerated);

    const text = mainText();
    expect(text).toMatch(/\bin range\b/i);
    expect(text).toContain(cardGenerated.current_version.power_justification);
  });

  it("CA-29: a too-strong indicator is shown and the card stays approved", async () => {
    await renderShown(tooStrongCard);

    const text = mainText();
    expect(text).toMatch(/\btoo strong\b/i);
    expect(text).toContain(tooStrongCard.current_version.power_justification);
    expect(text).toMatch(/\bapproved\b/i);
    expect(text).not.toMatch(/\brejected\b/i);
  });

  it("CA-29: a too-weak indicator is shown in words", async () => {
    await renderShown(withVersion({ power_indicator: "too_weak" }));
    expect(mainText()).toMatch(/\btoo weak\b/i);
  });

  it("RN-22: the raw indicator codes are never shown", async () => {
    for (const indicator of ["too_strong", "in_range", "too_weak"] as const) {
      await renderShown(withVersion({ power_indicator: indicator }));
      expect(mainText()).not.toContain(indicator);
      cleanup();
    }
  });
});

describe("ResultScreen: text usage (RN-09, CA-16)", () => {
  it("CA-16: shows the provider, model and input and output tokens of each text call", async () => {
    await renderShown(cardGenerated);

    const text = mainText();
    expect(text).toMatch(/usage|tokens/i);
    for (const record of cardGenerated.usage.text) {
      expect(text).toContain(record.provider);
      expect(text).toContain(record.model);
      expect(text).toMatch(countPattern(record.input_tokens));
      expect(text).toMatch(countPattern(record.output_tokens));
    }
  });

  it("CA-16: a draft and its revision show as separate records, including a failed call", async () => {
    const records = [
      ...cardGenerated.usage.text,
      {
        provider: "openai",
        model: "fake-text-model-1",
        input_tokens: 2990,
        output_tokens: 402,
        outcome: "failed" as const,
        created_at: "2000-01-01T00:00:00Z",
      },
    ];
    await renderShown(withVersion({}, { text: records }));

    const text = mainText();
    for (const record of records) {
      expect(text).toMatch(countPattern(record.input_tokens));
      expect(text).toMatch(countPattern(record.output_tokens));
    }
  });

  it("RN-09: a card with no usage records still shows the card, with no null or undefined", async () => {
    await renderShown(withVersion({}, { text: [] }));
    expect(mainText()).not.toMatch(/\bnull\b|\bundefined\b|NaN/);
  });
});

describe("ResultScreen: failures reading the card (RN-10)", () => {
  it("RN-10: an unknown card shows the cause in an alert", async () => {
    await renderCard(async () => jsonResponse(errorNotFound, 404));
    await waitFor(() => expect(alertText()).toContain(errorNotFound.error.message));
  });

  it("RN-10: an answer that is not JSON shows a readable failure", async () => {
    await renderCard(async () => textResponse("<html>gateway</html>", 502));
    await waitFor(() => expect(alertText().trim()).not.toBe(""));
    expect(alertText()).not.toContain("<html>");
  });

  it("RN-10: a malformed card answer (no current version) shows a failure, never a half card", async () => {
    await renderCard(async () => jsonResponse({ id: CARD_ID, usage: { text: [] } }));
    await waitFor(() => expect(alertText().trim()).not.toBe(""));
    const text = mainText();
    expect(text).not.toMatch(/\bundefined\b|\bnull\b|NaN/);
    expect(text).not.toMatch(/\bapproved\b/i);
  });
});
