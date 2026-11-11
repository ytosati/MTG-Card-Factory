// @vitest-environment jsdom
// Tests for the Request screen (spec RN-11, RN-49; CA-26, CA-80). T65.
//
// Component API under test (frontend/src/screens/RequestScreen.tsx):
//   <RequestScreen onGenerated={(result: { card: string; revision_failure: { code, message } | null }) => void} />
// - A level-1 heading names Request.
// - Fields, each with a label: "Idea or theme" (a text box whose name contains "idea"); one control per
//   color, labelled White, Blue, Black, Red and Green; a "Colorless" control; and a power level chosen
//   among Casual, Medium and Strong (radio buttons or a select labelled "Power level"). Nothing is
//   chosen when the screen opens: no color, not colorless, no power level.
// - The button whose name contains "generate" sends POST /api/generations
//   {idea, color_identity: ["W" | "U" | "B" | "R" | "G"], power_level: "casual" | "medium" | "strong"};
//   colorless sends color_identity [].
// - A missing field is named in an alert and the request is not sent (CA-26). An idea that is empty or
//   only spaces is missing. No color and no colorless is a missing color identity. An idea longer than
//   1,000 Unicode characters is refused, naming the idea, and is not sent (CA-80).
// - After the 202 answer it follows GET /api/jobs/{id}. A done job calls onGenerated once with the job
//   result; a failed job shows the cause (the job error message) in an alert and does not call it.
//
// Mocks are built from the contract samples (plan section 6).
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { RequestScreen } from "./RequestScreen";
import type { GenerationJobResponse } from "../api/types";
import {
  generationAccepted,
  generationMissingFields,
  generationRunning,
  jobGenerationDone,
  jobGenerationKeyRejected,
  jobGenerationRevisionFailed,
} from "../api/contract/samples";
import { calledUrl, jsonResponse, stubFetchByPath, textResponse } from "../test/fetchMock";

/** The polling hook reads at once, then every second; a few steps are always enough. */
const POLL_STEP_MS = 1_000;

/** The accepted job while it runs: the 202 sample with a running status. */
const generationRunningJob: GenerationJobResponse = { ...generationAccepted, status: "running", progress: 0.4 };

const IDEA_NAMES = /idea/i;
const COLOR_IDENTITY_NAMES = /colou?r identity|colou?rs?\b/i;
const POWER_LEVEL_NAMES = /power level/i;

// ---------------------------------------------------------------------------------------------
// A fake backend: POST /api/generations answers with `postAnswer`, the job reads walk `jobs`.
// ---------------------------------------------------------------------------------------------

let fetchMock: ReturnType<typeof stubFetchByPath>;
let jobAnswers: Array<() => Promise<Response>>;

function installBackend(
  postAnswer: () => Promise<Response> = async () => jsonResponse(generationAccepted, 202),
  jobs: Array<() => Promise<Response>> = [async () => jsonResponse(jobGenerationDone)],
) {
  jobAnswers = [...jobs];
  fetchMock = stubFetchByPath({
    "/api/generations": async (_url: string, init?: RequestInit) => {
      if ((init?.method ?? "GET").toUpperCase() !== "POST") {
        return jsonResponse({ error: { code: "method_not_allowed", message: "No.", setting: null, fields: null } }, 405);
      }
      return postAnswer();
    },
    "/api/jobs/": async () => {
      const answer = jobAnswers.length > 1 ? jobAnswers.shift()! : jobAnswers[0]!;
      return answer();
    },
  });
}

function generationPosts() {
  return fetchMock.mock.calls.filter(
    (call) => calledUrl(call[0]).split("?")[0] === "/api/generations" && (call[1]?.method ?? "GET").toUpperCase() === "POST",
  );
}

function jobReads() {
  return fetchMock.mock.calls.filter((call) => calledUrl(call[0]).startsWith("/api/jobs/"));
}

interface SentRequest {
  idea: string;
  color_identity: string[];
  power_level: string;
}

function sentBody(index = 0): SentRequest {
  const call = generationPosts()[index];
  expect(call, "no POST /api/generations was sent").toBeDefined();
  return JSON.parse(String(call![1]?.body)) as SentRequest;
}

async function advance(ms: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

async function renderScreen(onGenerated = vi.fn()) {
  render(<RequestScreen onGenerated={onGenerated} />);
  await advance(0);
  return onGenerated;
}

// ---------------------------------------------------------------------------------------------
// Form helpers: they find controls by role and label, never by markup.
// ---------------------------------------------------------------------------------------------

function ideaField(): HTMLInputElement | HTMLTextAreaElement {
  return screen.getByRole("textbox", { name: IDEA_NAMES }) as HTMLInputElement | HTMLTextAreaElement;
}

function typeIdea(text: string) {
  fireEvent.change(ideaField(), { target: { value: text } });
}

function colorControl(name: string): HTMLInputElement {
  return screen.getByLabelText(new RegExp(`^\\s*${name}\\b`, "i")) as HTMLInputElement;
}

function chooseColors(...names: string[]) {
  for (const name of names) fireEvent.click(colorControl(name));
}

function powerSelect(): HTMLSelectElement | null {
  return screen.queryByRole("combobox", { name: POWER_LEVEL_NAMES }) as HTMLSelectElement | null;
}

function choosePower(level: "casual" | "medium" | "strong") {
  const select = powerSelect();
  if (select !== null) {
    const option = Array.from(select.options).find((item) => item.textContent?.trim().toLowerCase() === level);
    expect(option, `no ${level} option in the power level select`).toBeDefined();
    fireEvent.change(select, { target: { value: option!.value } });
    return;
  }
  fireEvent.click(screen.getByRole("radio", { name: new RegExp(`^\\s*${level}\\b`, "i") }));
}

async function pressGenerate() {
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: /generate/i }));
  });
  await advance(0);
  await advance(0);
}

async function fillAndSend(idea: string, colors: string[], power: "casual" | "medium" | "strong") {
  typeIdea(idea);
  chooseColors(...colors);
  choosePower(power);
  await pressGenerate();
}

function alertText(): string {
  return screen
    .queryAllByRole("alert")
    .map((element) => element.textContent ?? "")
    .join(" ");
}

const IDEA = "An elf that makes the lanterns of the forest glow and grows the army.";

beforeEach(() => {
  vi.useFakeTimers();
  installBackend();
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

// ---------------------------------------------------------------------------------------------

describe("RequestScreen: fields (RN-11, RN-49)", () => {
  it("RN-49: has a level-1 heading naming Request", async () => {
    await renderScreen();
    expect(screen.getByRole("heading", { level: 1, name: /request/i })).toBeTruthy();
  });

  it("RN-11, RN-49: offers the idea, the five colors, colorless and the three power levels, each labelled", async () => {
    await renderScreen();
    expect(ideaField()).toBeTruthy();
    for (const color of ["White", "Blue", "Black", "Red", "Green", "Colorless"]) {
      expect(colorControl(color)).toBeTruthy();
    }
    const select = powerSelect();
    const levels = select
      ? Array.from(select.options).map((option) => option.textContent?.trim().toLowerCase())
      : screen.getAllByRole("radio").map((radio) => (radio.getAttribute("value") ?? "").toLowerCase());
    for (const level of ["casual", "medium", "strong"]) expect(levels).toContain(level);
  });

  it("RN-49: every field on the screen has a label", async () => {
    await renderScreen();
    const fields = Array.from(document.querySelectorAll<HTMLElement>("input, textarea, select")).filter(
      (element) => element.getAttribute("type") !== "hidden",
    );
    expect(fields.length).toBeGreaterThan(0);
    for (const field of fields) {
      const labelled =
        ((field as HTMLInputElement).labels?.length ?? 0) > 0 ||
        (field.getAttribute("aria-label") ?? "").trim() !== "" ||
        (field.getAttribute("aria-labelledby") ?? "").trim() !== "";
      expect(labelled, `a ${field.tagName.toLowerCase()} has no label`).toBe(true);
    }
  });

  it("CA-26: nothing is chosen when the screen opens: no color, not colorless and no power level", async () => {
    await renderScreen();
    expect(ideaField().value).toBe("");
    for (const color of ["White", "Blue", "Black", "Red", "Green", "Colorless"]) {
      expect(colorControl(color).checked, `${color} starts chosen`).toBe(false);
    }
    const select = powerSelect();
    if (select !== null) {
      expect(["casual", "medium", "strong"]).not.toContain(select.value.toLowerCase());
    } else {
      for (const radio of screen.getAllByRole("radio") as HTMLInputElement[]) {
        if (/casual|medium|strong/i.test(radio.value)) expect(radio.checked).toBe(false);
      }
    }
  });
});

describe("RequestScreen: missing fields are named and the request is not sent (RN-11, CA-26)", () => {
  it("CA-26: an empty request names the idea, the color identity and the power level, and sends nothing", async () => {
    await renderScreen();
    await pressGenerate();

    const text = alertText();
    expect(text).toMatch(IDEA_NAMES);
    expect(text).toMatch(COLOR_IDENTITY_NAMES);
    expect(text).toMatch(POWER_LEVEL_NAMES);
    expect(generationPosts()).toHaveLength(0);
  });

  it("CA-26: a missing idea alone is named, and the fields that were filled are not", async () => {
    await renderScreen();
    chooseColors("Green");
    choosePower("medium");
    await pressGenerate();

    const text = alertText();
    expect(text).toMatch(IDEA_NAMES);
    expect(text).not.toMatch(POWER_LEVEL_NAMES);
    expect(text).not.toMatch(/colou?r identity/i);
    expect(generationPosts()).toHaveLength(0);
  });

  it("CA-26: an idea made only of spaces and line breaks counts as missing", async () => {
    await renderScreen();
    await fillAndSend("   \n\t  ", ["Green"], "medium");

    expect(alertText()).toMatch(IDEA_NAMES);
    expect(generationPosts()).toHaveLength(0);
  });

  it("CA-26: no color and no colorless chosen is a missing color identity, never a colorless request", async () => {
    await renderScreen();
    await fillAndSend(IDEA, [], "casual");

    const text = alertText();
    expect(text).toMatch(COLOR_IDENTITY_NAMES);
    expect(text).not.toMatch(IDEA_NAMES);
    expect(generationPosts()).toHaveLength(0);
  });

  it("CA-26: a missing power level is named and the request is not sent", async () => {
    await renderScreen();
    typeIdea(IDEA);
    chooseColors("White");
    await pressGenerate();

    const text = alertText();
    expect(text).toMatch(POWER_LEVEL_NAMES);
    expect(text).not.toMatch(IDEA_NAMES);
    expect(generationPosts()).toHaveLength(0);
  });

  it("CA-26: fixing the named fields lets the request go, and the earlier names are no longer shown", async () => {
    await renderScreen();
    await pressGenerate();
    expect(generationPosts()).toHaveLength(0);

    await fillAndSend(IDEA, ["Green"], "medium");

    expect(generationPosts()).toHaveLength(1);
    expect(alertText()).not.toMatch(POWER_LEVEL_NAMES);
  });

  it("CA-26: fields the backend names in the validation envelope are named on the screen", async () => {
    installBackend(async () => jsonResponse(generationMissingFields, 400));
    const onGenerated = await renderScreen();
    await fillAndSend(IDEA, ["Green"], "medium");

    const text = alertText();
    expect(text).toMatch(IDEA_NAMES);
    expect(text).toMatch(COLOR_IDENTITY_NAMES);
    expect(text).toMatch(POWER_LEVEL_NAMES);
    expect(jobReads()).toHaveLength(0);
    expect(onGenerated).not.toHaveBeenCalled();
  });
});

describe("RequestScreen: the request sent (RN-11, CA-26)", () => {
  it("RN-11: sends the idea, the chosen colors as letters and the power level", async () => {
    await renderScreen();
    await fillAndSend(IDEA, ["Green", "White"], "strong");

    expect(generationPosts()).toHaveLength(1);
    const body = sentBody();
    expect(body.idea).toBe(IDEA);
    expect([...body.color_identity].sort()).toEqual(["G", "W"]);
    expect(body.power_level).toBe("strong");
  });

  it("RN-11: every color maps to its letter (W, U, B, R, G)", async () => {
    await renderScreen();
    await fillAndSend(IDEA, ["White", "Blue", "Black", "Red", "Green"], "casual");

    expect([...sentBody().color_identity].sort()).toEqual(["B", "G", "R", "U", "W"]);
    expect(sentBody().power_level).toBe("casual");
  });

  it("CA-26: colorless chosen explicitly sends an empty color identity", async () => {
    await renderScreen();
    await fillAndSend(IDEA, ["Colorless"], "medium");

    expect(generationPosts()).toHaveLength(1);
    expect(sentBody().color_identity).toEqual([]);
    expect(sentBody().power_level).toBe("medium");
  });

  it("RN-11: an idea with quotes, markup, accents, emoji and line breaks is sent unchanged", async () => {
    const odd = `Lâmpada "élfica" <b>&amp;</b> {G/W} — 🌿🔥\nsecond line 'with' \\ backslash`;
    await renderScreen();
    await fillAndSend(odd, ["Green"], "medium");

    expect(sentBody().idea).toBe(odd);
  });
});

describe("RequestScreen: idea length (RN-11, CA-80)", () => {
  it("CA-80: an idea of exactly 1,000 characters is sent", async () => {
    const idea = "a".repeat(1_000);
    await renderScreen();
    await fillAndSend(idea, ["Red"], "medium");

    expect(generationPosts()).toHaveLength(1);
    expect(sentBody().idea).toBe(idea);
  });

  it("CA-80: an idea of 1,001 characters is refused naming the idea, and nothing is sent", async () => {
    await renderScreen();
    await fillAndSend("a".repeat(1_001), ["Red"], "medium");

    expect(alertText()).toMatch(IDEA_NAMES);
    expect(generationPosts()).toHaveLength(0);
  });

  it("CA-80: the limit counts Unicode characters, so 1,000 characters outside the BMP are sent", async () => {
    // Each character below takes two UTF-16 code units.
    const idea = "🌿".repeat(1_000);
    await renderScreen();
    await fillAndSend(idea, ["Green"], "medium");

    expect(generationPosts()).toHaveLength(1);
    expect(sentBody().idea).toBe(idea);
  });

  it("CA-80: 1,001 characters outside the BMP are refused", async () => {
    await renderScreen();
    await fillAndSend("🌿".repeat(1_001), ["Green"], "medium");

    expect(alertText()).toMatch(IDEA_NAMES);
    expect(generationPosts()).toHaveLength(0);
  });

  it("CA-80: a huge idea (100,000 characters) is refused without sending", async () => {
    await renderScreen();
    await fillAndSend("lantern ".repeat(12_500), ["Green"], "medium");

    expect(alertText()).toMatch(IDEA_NAMES);
    expect(generationPosts()).toHaveLength(0);
  });
});

describe("RequestScreen: following the generation job (RN-11, RN-10)", () => {
  it("RN-11: a job that ends done calls onGenerated once with the card and no revision failure", async () => {
    installBackend(undefined, [
      async () => jsonResponse(generationRunningJob),
      async () => jsonResponse(generationRunningJob),
      async () => jsonResponse(jobGenerationDone),
    ]);
    const onGenerated = await renderScreen();
    await fillAndSend(IDEA, ["Green", "White"], "medium");
    for (let step = 0; step < 5; step += 1) await advance(POLL_STEP_MS);

    expect(onGenerated).toHaveBeenCalledTimes(1);
    expect(onGenerated).toHaveBeenCalledWith(jobGenerationDone.result);
    expect(jobReads()[0] && calledUrl(jobReads()[0]![0])).toBe(`/api/jobs/${generationAccepted.id}`);
  });

  it("RN-15: a done job whose revision failed hands the revision failure on with the card", async () => {
    installBackend(undefined, [async () => jsonResponse(jobGenerationRevisionFailed)]);
    const onGenerated = await renderScreen();
    await fillAndSend(IDEA, ["Green"], "medium");
    await advance(POLL_STEP_MS);

    expect(onGenerated).toHaveBeenCalledTimes(1);
    expect(onGenerated).toHaveBeenCalledWith(jobGenerationRevisionFailed.result);
  });

  it("RN-10, CA-25: a failed job shows the provider failure with its cause and opens no result", async () => {
    installBackend(undefined, [async () => jsonResponse(jobGenerationKeyRejected)]);
    const onGenerated = await renderScreen();
    await fillAndSend(IDEA, ["Green"], "medium");
    await advance(POLL_STEP_MS);

    expect(alertText()).toContain(jobGenerationKeyRejected.error.error.message);
    expect(onGenerated).not.toHaveBeenCalled();
  });

  it("RN-10: after a failed job the person can send the request again", async () => {
    installBackend(undefined, [async () => jsonResponse(jobGenerationKeyRejected)]);
    const onGenerated = await renderScreen();
    await fillAndSend(IDEA, ["Green"], "medium");
    await advance(POLL_STEP_MS);

    jobAnswers = [async () => jsonResponse(jobGenerationDone)];
    await pressGenerate();
    await advance(POLL_STEP_MS);

    expect(generationPosts()).toHaveLength(2);
    expect(onGenerated).toHaveBeenCalledWith(jobGenerationDone.result);
  });

  it("RN-50: a generation already running is shown with its message and nothing is followed", async () => {
    installBackend(async () => jsonResponse(generationRunning, 409));
    const onGenerated = await renderScreen();
    await fillAndSend(IDEA, ["Green"], "medium");

    expect(alertText()).toContain(generationRunning.error.message);
    expect(jobReads()).toHaveLength(0);
    expect(onGenerated).not.toHaveBeenCalled();
  });

  it("RN-10: an answer that is not JSON shows a readable failure and opens no result", async () => {
    installBackend(async () => textResponse("<html>proxy error</html>", 502));
    const onGenerated = await renderScreen();
    await fillAndSend(IDEA, ["Green"], "medium");

    expect(alertText().trim()).not.toBe("");
    expect(alertText()).not.toContain("<html>");
    expect(onGenerated).not.toHaveBeenCalled();
  });

  it("RN-10: a done job with a malformed result shows a failure and opens no result", async () => {
    installBackend(undefined, [async () => jsonResponse({ ...jobGenerationDone, result: { revision_failure: null } })]);
    const onGenerated = await renderScreen();
    await fillAndSend(IDEA, ["Green"], "medium");
    await advance(POLL_STEP_MS);

    expect(onGenerated).not.toHaveBeenCalled();
    expect(alertText().trim()).not.toBe("");
  });

  it("RN-10: a done job with no result at all shows a failure and opens no result", async () => {
    installBackend(undefined, [async () => jsonResponse({ ...jobGenerationDone, result: null })]);
    const onGenerated = await renderScreen();
    await fillAndSend(IDEA, ["Green"], "medium");
    await advance(POLL_STEP_MS);

    expect(onGenerated).not.toHaveBeenCalled();
    expect(alertText().trim()).not.toBe("");
  });
});
