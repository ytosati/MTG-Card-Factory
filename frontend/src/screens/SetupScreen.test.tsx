// @vitest-environment jsdom
// Tests for the Setup screen (spec RN-28, RN-49; CA-18, CA-59, CA-60; screens "First-run setup"). T63.
//
// Component API under test (frontend/src/screens/SetupScreen.tsx):
//   <SetupScreen onReady={() => void} />
// - On open it reads GET /api/setup and shows the expected download size, the free disk space needed
//   and, when known, the free space, as human-readable sizes (KB, MB, GB...), never as raw bytes.
// - It sends POST /api/setup/build only when the person presses the start button (a <button> whose
//   name contains "start" or "build"), once per press, never twice for a double press.
// - While a build job runs (started here or found running by GET /api/setup) it polls, at least every
//   5 seconds, and shows a progress bar (role="progressbar" with aria-valuenow) for the job progress.
// - A failed build shows the cause (the job error message) and a retry button (name "Try again" or
//   "Retry") that starts the build again.
// - A build refused for lack of space (POST answers 507 insufficient_space) shows the cause (CA-60)
//   and starts no job.
// - When the data source listing cannot be reached (listing_error), it shows the cause and a retry
//   button; it does not read GET /api/setup again until the person presses retry.
// - When settings need fixing it shows a notice with a link to Status (href "#/status").
// - When the build ends done (the database is ready) it calls onReady once; the shell then moves to
//   the normal screens. It also calls onReady when GET /api/setup already reports a ready database.
// - Status and error messages are in a live region (role status/alert or aria-live).
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SetupScreen } from "./SetupScreen";
import type { JobResponse, SetupResponse } from "../api/types";
import {
  jobBuildDone,
  jobBuildFailed,
  setupBuildAccepted,
  setupBuildFailed,
  setupBuildRefusedForSpace,
  setupBuilding,
  setupFreeSpaceUnknown,
  setupListingUnreachable,
  setupNotReady,
  setupSettingsToFix,
} from "../api/contract/samples";
import { calledUrl, jsonResponse, stubFetchByPath, textResponse } from "../test/fetchMock";
import { pressTab, tabbableElements } from "../test/keyboard";

/** One polling step: the screen must poll at least this often while a build runs. */
const POLL_MS = 5_000;
/** A long wait in which nothing may happen on its own. */
const LONG_WAIT_MS = 60_000;

const START_BUTTON = /start|build/i;
const RETRY_BUTTON = /try again|retry/i;

const MIB = 1024 * 1024;
const GIB = 1024 * MIB;

// ---------------------------------------------------------------------------------------------
// A fake backend whose state the test changes; every endpoint answers from the same state.
// ---------------------------------------------------------------------------------------------

interface FakeBackend {
  setup: SetupResponse;
  /** The job GET /api/jobs/{id} answers; also mirrored into GET /api/setup. */
  job: JobResponse | null;
  /** The answer of POST /api/setup/build. */
  buildAnswer: () => Promise<Response>;
  /** Overrides the answer of GET /api/setup (for malformed answers). */
  setupAnswer?: () => Promise<Response>;
}

let backend: FakeBackend;
let fetchMock: ReturnType<typeof stubFetchByPath>;

function setupBody(): SetupResponse {
  return { ...backend.setup, job: backend.job };
}

function installBackend(setup: SetupResponse) {
  backend = {
    setup,
    job: setup.job,
    buildAnswer: async () => {
      backend.job = setupBuildAccepted;
      return jsonResponse(setupBuildAccepted, 202);
    },
  };
  fetchMock = stubFetchByPath({
    "/api/setup": async () => (backend.setupAnswer ? backend.setupAnswer() : jsonResponse(setupBody())),
    "/api/setup/build": async (_url: string, init?: RequestInit) => {
      if ((init?.method ?? "GET").toUpperCase() !== "POST") {
        return jsonResponse({ error: { code: "method_not_allowed", message: "No.", setting: null, fields: null } }, 405);
      }
      return backend.buildAnswer();
    },
    "/api/jobs/": async () =>
      backend.job
        ? jsonResponse(backend.job)
        : jsonResponse({ error: { code: "not_found", message: "Not found.", setting: null, fields: null } }, 404),
  });
}

function callsTo(path: string, method?: string) {
  return fetchMock.mock.calls.filter((call) => {
    const url = calledUrl(call[0]).split("?")[0];
    const sameMethod = method === undefined || (call[1]?.method ?? "GET").toUpperCase() === method;
    return url === path && sameMethod;
  });
}

function jobCalls() {
  return fetchMock.mock.calls.filter((call) => calledUrl(call[0]).startsWith("/api/jobs/"));
}

function buildPosts() {
  return callsTo("/api/setup/build", "POST");
}

function setupReads() {
  return callsTo("/api/setup", "GET");
}

/** Advances the fake clock and lets pending promises and React updates settle. */
async function advance(ms: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

async function renderScreen(setup: SetupResponse, onReady = vi.fn()) {
  installBackend(setup);
  render(<SetupScreen onReady={onReady} />);
  await advance(0);
  await advance(0);
  return onReady;
}

async function press(element: HTMLElement) {
  await act(async () => {
    fireEvent.click(element);
  });
  await advance(0);
}

function startButton(): HTMLElement {
  return screen.getByRole("button", { name: START_BUTTON });
}

function retryButton(): HTMLElement {
  return screen.getByRole("button", { name: RETRY_BUTTON });
}

function progressBar(): HTMLElement {
  return screen.getByRole("progressbar");
}

/** The progress shown by a progress bar, as a fraction of its range (ARIA defaults: 0..100). */
function shownFraction(bar: HTMLElement): number {
  const now = bar.getAttribute("aria-valuenow");
  expect(now, "the progress bar has no aria-valuenow").not.toBeNull();
  const min = Number(bar.getAttribute("aria-valuemin") ?? "0");
  const max = Number(bar.getAttribute("aria-valuemax") ?? "100");
  return (Number(now) - min) / (max - min);
}

function bodyText(): string {
  return document.body.textContent ?? "";
}

/** True when the element is inside a live region, so screen readers announce it (RN-49). */
function inLiveRegion(element: HTMLElement): boolean {
  return element.closest("[role='status'], [role='alert'], [aria-live='polite'], [aria-live='assertive'], output") !== null;
}

function expectAnnounced(message: string) {
  const element = screen.getByText(message, { exact: false });
  expect(inLiveRegion(element), `"${message}" is not in a live region`).toBe(true);
}

// ---------------------------------------------------------------------------------------------
// Human-readable sizes: accepts decimal (1000) or binary (1024) units with 0 to 2 decimals.
// ---------------------------------------------------------------------------------------------

const DECIMAL_UNITS = ["B", "KB", "MB", "GB", "TB", "PB"];
const BINARY_UNITS = [
  ["B"],
  ["KB", "KiB"],
  ["MB", "MiB"],
  ["GB", "GiB"],
  ["TB", "TiB"],
  ["PB", "PiB"],
];

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function readableSizePattern(bytes: number): RegExp {
  const options = new Set<string>();
  const add = (value: number, units: string[]) => {
    for (const digits of [0, 1, 2]) {
      const text = value.toFixed(digits);
      for (const number of [text, text.replace(/\.?0+$/, "")]) {
        for (const unit of units) options.add(`${escapeRegExp(number)}\\s?${unit}`);
      }
    }
  };
  for (let power = 0; power < DECIMAL_UNITS.length; power += 1) {
    const value = bytes / 1000 ** power;
    if (value >= 1 && value < 1000 * 1.5) add(value, [DECIMAL_UNITS[power]!]);
  }
  for (let power = 0; power < BINARY_UNITS.length; power += 1) {
    const value = bytes / 1024 ** power;
    if (value >= 1 && value < 1024 * 1.5) add(value, BINARY_UNITS[power]!);
  }
  return new RegExp(`(^|[^\\d.])(${[...options].join("|")})(?![a-zA-Z])`, "i");
}

const sizedSetup: SetupResponse = {
  ...setupNotReady,
  download_size: 300 * MIB,
  space_needed: 2 * GIB,
  free_space: 50 * GIB,
};

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

// ---------------------------------------------------------------------------------------------

describe("SetupScreen: before the build (RN-28, CA-18)", () => {
  it("CA-18: has a level-1 heading naming Setup and reads GET /api/setup", async () => {
    await renderScreen(setupNotReady);

    expect(screen.getByRole("heading", { level: 1, name: /setup/i })).toBeTruthy();
    expect(setupReads().length).toBeGreaterThanOrEqual(1);
  });

  it("RN-28, CA-18: shows the expected download size and the free disk space needed, human-readable", async () => {
    await renderScreen(sizedSetup);

    const text = bodyText();
    expect(text).toMatch(readableSizePattern(300 * MIB));
    expect(text).toMatch(readableSizePattern(2 * GIB));
    expect(text).toMatch(/download/i);
    expect(text).toMatch(/space/i);
  });

  it("RN-28: shows the free space on the drive when it is known", async () => {
    await renderScreen(sizedSetup);

    expect(bodyText()).toMatch(readableSizePattern(50 * GIB));
  });

  it("RN-28: never shows sizes as raw byte counts", async () => {
    await renderScreen(sizedSetup);

    const text = bodyText();
    for (const raw of [300 * MIB, 2 * GIB, 50 * GIB]) {
      expect(text).not.toContain(String(raw));
      expect(text).not.toContain(raw.toLocaleString("en-US"));
    }
  });

  it("RN-28: shows the sizes from the contract sample (small values) with a unit", async () => {
    await renderScreen(setupNotReady);

    const text = bodyText();
    expect(text).toMatch(readableSizePattern(setupNotReady.download_size));
    expect(text).toMatch(readableSizePattern(setupNotReady.space_needed));
  });

  it("RN-28: with unknown free space it still shows the download size and the space needed, with no placeholder junk", async () => {
    await renderScreen(setupFreeSpaceUnknown);

    const text = bodyText();
    expect(text).toMatch(readableSizePattern(setupFreeSpaceUnknown.download_size));
    expect(text).toMatch(readableSizePattern(setupFreeSpaceUnknown.space_needed));
    expect(text).not.toMatch(/\b(null|undefined|NaN)\b/);
    expect(startButton()).toBeTruthy();
  });

  it("CA-18: nothing is downloaded until the person starts the build", async () => {
    await renderScreen(setupNotReady);
    await advance(LONG_WAIT_MS);

    expect(buildPosts()).toHaveLength(0);
    expect(jobCalls()).toHaveLength(0);
    expect(screen.queryByRole("progressbar")).toBeNull();
  });

  it("CA-18: offers a start button that is a real, enabled button", async () => {
    await renderScreen(setupNotReady);

    const button = startButton();
    expect(button.tagName).toBe("BUTTON");
    expect((button as HTMLButtonElement).disabled).toBe(false);
  });
});

describe("SetupScreen: starting the build and its progress (RN-28, CA-18)", () => {
  it("CA-18: pressing start sends one POST /api/setup/build", async () => {
    await renderScreen(setupNotReady);

    await press(startButton());

    expect(buildPosts()).toHaveLength(1);
  });

  it("RN-28: a double press starts the build only once", async () => {
    await renderScreen(setupNotReady);

    const button = startButton();
    await act(async () => {
      fireEvent.click(button);
      fireEvent.click(button);
    });
    await advance(0);

    expect(buildPosts()).toHaveLength(1);
  });

  it("CA-18: after the start it shows a progress bar and follows the job by polling", async () => {
    await renderScreen(setupNotReady);
    await press(startButton());

    expect(shownFraction(progressBar())).toBeCloseTo(0, 2);

    backend.job = { ...setupBuilding.job, progress: 0.05 };
    await advance(POLL_MS);
    expect(shownFraction(progressBar())).toBeCloseTo(0.05, 2);

    backend.job = { ...setupBuilding.job, progress: 0.5 };
    await advance(POLL_MS);
    expect(shownFraction(progressBar())).toBeCloseTo(0.5, 2);
  });

  it("RN-49: the progress bar has an accessible name", async () => {
    await renderScreen(setupBuilding);

    const bar = progressBar();
    const name = bar.getAttribute("aria-label") ?? bar.getAttribute("aria-labelledby");
    expect(name, "the progress bar has no aria-label or aria-labelledby").toBeTruthy();
  });

  it("RN-28: a build found running on open shows its progress without a new start", async () => {
    await renderScreen(setupBuilding);

    expect(shownFraction(progressBar())).toBeCloseTo(setupBuilding.job.progress, 2);
    expect(buildPosts()).toHaveLength(0);

    backend.job = { ...setupBuilding.job, progress: 0.75 };
    await advance(POLL_MS);
    expect(shownFraction(progressBar())).toBeCloseTo(0.75, 2);
    expect(buildPosts()).toHaveLength(0);
  });

  it("RN-28: while the build runs, the start button cannot start a second build", async () => {
    await renderScreen(setupBuilding);

    const button = screen.queryByRole("button", { name: START_BUTTON }) as HTMLButtonElement | null;
    if (button) {
      await press(button);
    }
    expect(buildPosts()).toHaveLength(0);
  });

  it.each([
    ["negative", -0.2, 0],
    ["above one", 1.7, 1],
  ])("RN-28: a %s progress from the backend is kept inside the progress bar range", async (_label, progress, expected) => {
    await renderScreen({ ...setupBuilding, job: { ...setupBuilding.job, progress } });

    const bar = progressBar();
    expect(shownFraction(bar)).toBeCloseTo(expected, 2);
  });

  it("CA-18: when the build ends done it calls onReady once", async () => {
    const onReady = await renderScreen(setupBuilding);
    expect(onReady).not.toHaveBeenCalled();

    backend.job = jobBuildDone;
    backend.setup = { ...backend.setup, database_ready: true };
    await advance(POLL_MS);
    await advance(POLL_MS);

    expect(onReady).toHaveBeenCalledTimes(1);
    await advance(LONG_WAIT_MS);
    expect(onReady).toHaveBeenCalledTimes(1);
  });

  it("CA-18: the whole path, start to done, ends in onReady and stops polling", async () => {
    const onReady = await renderScreen(setupNotReady);
    await press(startButton());

    backend.job = { ...setupBuilding.job, progress: 0.4 };
    await advance(POLL_MS);
    expect(onReady).not.toHaveBeenCalled();

    backend.job = jobBuildDone;
    backend.setup = { ...backend.setup, database_ready: true };
    await advance(POLL_MS);
    await advance(POLL_MS);
    expect(onReady).toHaveBeenCalledTimes(1);

    const callsAfterDone = fetchMock.mock.calls.length;
    await advance(LONG_WAIT_MS);
    expect(fetchMock.mock.calls.length).toBe(callsAfterDone);
  });

  it("CA-18: when GET /api/setup already reports a ready database it calls onReady", async () => {
    const onReady = await renderScreen({ ...setupNotReady, database_ready: true });

    expect(onReady).toHaveBeenCalledTimes(1);
    expect(buildPosts()).toHaveLength(0);
  });
});

describe("SetupScreen: failures (RN-28, CA-60)", () => {
  it("RN-28: a failed build found on open shows its cause and a retry", async () => {
    await renderScreen(setupBuildFailed);

    expect(screen.getByText(setupBuildFailed.job.error.error.message)).toBeTruthy();
    expect(retryButton().tagName).toBe("BUTTON");
    expect(buildPosts()).toHaveLength(0);
  });

  it("RN-28, RN-49: the cause of a failure is in a live region", async () => {
    await renderScreen(setupBuildFailed);

    expectAnnounced(setupBuildFailed.job.error.error.message);
  });

  it("RN-28: retry after a failed build starts the build again", async () => {
    await renderScreen(setupBuildFailed);

    await press(retryButton());

    expect(buildPosts()).toHaveLength(1);
    expect(screen.getByRole("progressbar")).toBeTruthy();
  });

  it("RN-28: a build that fails while it runs shows the cause and a retry", async () => {
    const onReady = await renderScreen(setupBuilding);

    backend.job = jobBuildFailed;
    await advance(POLL_MS);
    await advance(POLL_MS);

    expect(screen.getByText(jobBuildFailed.error.error.message)).toBeTruthy();
    expect(retryButton()).toBeTruthy();
    expect(onReady).not.toHaveBeenCalled();
  });

  it("RN-28: polling stops once the build has failed", async () => {
    await renderScreen(setupBuilding);
    backend.job = jobBuildFailed;
    await advance(POLL_MS);
    await advance(POLL_MS);

    const callsAfterFailure = fetchMock.mock.calls.length;
    await advance(LONG_WAIT_MS);
    expect(fetchMock.mock.calls.length).toBe(callsAfterFailure);
  });

  it("CA-60: a build refused for lack of disk space shows the cause and starts no job", async () => {
    await renderScreen(sizedSetup);
    backend.buildAnswer = async () => jsonResponse(setupBuildRefusedForSpace, 507);

    await press(startButton());
    await advance(LONG_WAIT_MS);

    expect(buildPosts()).toHaveLength(1);
    expect(screen.getByText(setupBuildRefusedForSpace.error.message)).toBeTruthy();
    expect(jobCalls()).toHaveLength(0);
    expect(screen.queryByRole("progressbar")).toBeNull();
  });

  it("CA-60: with the refusal shown, the screen still names the space needed", async () => {
    await renderScreen(sizedSetup);
    backend.buildAnswer = async () => jsonResponse(setupBuildRefusedForSpace, 507);

    await press(startButton());

    expect(bodyText()).toMatch(readableSizePattern(2 * GIB));
  });

  it("CA-60, RN-49: the refusal for lack of space is in a live region", async () => {
    await renderScreen(sizedSetup);
    backend.buildAnswer = async () => jsonResponse(setupBuildRefusedForSpace, 507);

    await press(startButton());

    expectAnnounced(setupBuildRefusedForSpace.error.message);
  });

  it("CA-60: after a refusal the person can try again once space is freed", async () => {
    await renderScreen(sizedSetup);
    backend.buildAnswer = async () => jsonResponse(setupBuildRefusedForSpace, 507);
    await press(startButton());

    backend.buildAnswer = async () => {
      backend.job = setupBuildAccepted;
      return jsonResponse(setupBuildAccepted, 202);
    };
    const again = screen.queryByRole("button", { name: RETRY_BUTTON }) ?? startButton();
    await press(again);

    expect(buildPosts()).toHaveLength(2);
    expect(screen.getByRole("progressbar")).toBeTruthy();
  });

  it("RN-28: an unreadable answer to the start (HTML 500) shows a cause and starts no job", async () => {
    await renderScreen(setupNotReady);
    backend.buildAnswer = async () => textResponse("<html><body>Server Error</body></html>", 500);

    await press(startButton());
    await advance(LONG_WAIT_MS);

    expect(jobCalls()).toHaveLength(0);
    expect(screen.queryByRole("progressbar")).toBeNull();
    expect(screen.queryByRole("alert") ?? document.querySelector("[aria-live]")).not.toBeNull();
    expect(bodyText()).not.toContain("<html>");
  });
});

describe("SetupScreen: data source listing unreachable (RN-28)", () => {
  it("RN-28: shows the cause and a retry, and offers no start", async () => {
    await renderScreen(setupListingUnreachable);

    expect(screen.getByText(setupListingUnreachable.listing_error.error.message)).toBeTruthy();
    expect(retryButton().tagName).toBe("BUTTON");
    expect(screen.queryByRole("button", { name: /start/i })).toBeNull();
  });

  it("RN-28, RN-49: the listing cause is in a live region", async () => {
    await renderScreen(setupListingUnreachable);

    expectAnnounced(setupListingUnreachable.listing_error.error.message);
  });

  it("RN-28: with no sizes known it shows no placeholder junk", async () => {
    await renderScreen(setupListingUnreachable);

    expect(bodyText()).not.toMatch(/\b(null|undefined|NaN)\b/);
  });

  it("RN-28: does not read GET /api/setup again on its own while the cause is shown", async () => {
    await renderScreen(setupListingUnreachable);
    const readsBefore = setupReads().length;

    await advance(LONG_WAIT_MS);

    expect(setupReads()).toHaveLength(readsBefore);
    expect(buildPosts()).toHaveLength(0);
  });

  it("RN-28: retry reads GET /api/setup again and, once reachable, shows the sizes and the start", async () => {
    await renderScreen(setupListingUnreachable);
    const readsBefore = setupReads().length;

    backend.setup = sizedSetup;
    await press(retryButton());
    await advance(0);

    expect(setupReads()).toHaveLength(readsBefore + 1);
    expect(buildPosts()).toHaveLength(0);
    expect(screen.queryByText(setupListingUnreachable.listing_error.error.message)).toBeNull();
    expect(bodyText()).toMatch(readableSizePattern(300 * MIB));
    expect(startButton()).toBeTruthy();
  });
});

describe("SetupScreen: settings to fix (RN-28)", () => {
  it("RN-28: shows a notice that settings need fixing with a link to Status", async () => {
    await renderScreen(setupSettingsToFix);

    const link = screen.getByRole("link", { name: /status/i });
    expect(link.getAttribute("href")).toBe("#/status");
    expect(bodyText()).toMatch(/setting/i);
  });

  it("RN-28: the settings notice does not hide the sizes or the start", async () => {
    await renderScreen(setupSettingsToFix);

    expect(bodyText()).toMatch(readableSizePattern(setupSettingsToFix.download_size));
    expect(startButton()).toBeTruthy();
  });
});

describe("SetupScreen: keyboard (RN-49, CA-59)", () => {
  it("RN-49: the start button is reached with Tab", async () => {
    await renderScreen(setupNotReady);

    const button = startButton();
    (document.activeElement as HTMLElement | null)?.blur();
    const reached: HTMLElement[] = [];
    for (let step = 0; step < 20; step += 1) {
      const next = pressTab();
      if (next === null) break;
      reached.push(next);
    }
    expect(reached).toContain(button);
  });

  it("RN-49: the settings link and the start button are both reached with Tab", async () => {
    await renderScreen(setupSettingsToFix);

    const tabbable = tabbableElements();
    expect(tabbable).toContain(screen.getByRole("link", { name: /status/i }));
    expect(tabbable).toContain(startButton());
  });

  it("RN-49: the retry of a listing failure is reached with Tab", async () => {
    await renderScreen(setupListingUnreachable);

    expect(tabbableElements()).toContain(retryButton());
  });

  it("RN-49: the retry of a failed build is reached with Tab", async () => {
    await renderScreen(setupBuildFailed);

    expect(tabbableElements()).toContain(retryButton());
  });

  it.each([
    ["not ready", setupNotReady],
    ["settings to fix", setupSettingsToFix],
    ["building", setupBuilding],
    ["failed", setupBuildFailed],
    ["listing unreachable", setupListingUnreachable],
  ] as const)("RN-49: no control uses a positive tabindex or hides focus (%s)", async (_label, setup) => {
    await renderScreen(setup);

    const main = screen.getByRole("main");
    for (const element of Array.from(main.querySelectorAll<HTMLElement>("[tabindex]"))) {
      expect(Number(element.getAttribute("tabindex"))).toBeLessThanOrEqual(0);
    }
    for (const control of within(main).queryAllByRole("button").concat(within(main).queryAllByRole("link"))) {
      expect(control.style.outline, "inline outline removed").not.toMatch(/none|^0/);
    }
  });
});

// ---------------------------------------------------------------------------------------------
// Review additions.
// ---------------------------------------------------------------------------------------------

/** A fictional 502 answer to the start: the data source answered with an error. */
const startBadGateway = {
  error: {
    code: "source_unreachable",
    message: "Fictional cause: the data source answered with an error (HTTP 502) when the build started.",
    setting: null,
    fields: null,
  },
};

/** Texts of the live regions that are not empty. */
function announcedTexts(): string[] {
  return Array.from(
    document.querySelectorAll<HTMLElement>(
      "[role='status'], [role='alert'], [aria-live='polite'], [aria-live='assertive'], output",
    ),
  )
    .map((element) => (element.textContent ?? "").trim())
    .filter((text) => text !== "");
}

/** Focuses a control as a keyboard user would, then activates it. */
async function pressWithKeyboardFocus(element: HTMLElement) {
  element.focus();
  await press(element);
}

function expectFocusInsideScreen() {
  const active = document.activeElement;
  expect(active, "focus fell to the page body").not.toBe(document.body);
  expect(active).not.toBeNull();
  expect(screen.getByRole("main").contains(active), "focus left the Setup screen").toBe(true);
}

async function renderWithFailingRead(setup: SetupResponse, failure: () => Promise<Response>) {
  installBackend(setup);
  backend.setupAnswer = failure;
  render(<SetupScreen onReady={vi.fn()} />);
  await advance(0);
  await advance(0);
}

const getFailures: Array<[string, () => Promise<Response>]> = [
  ["network error", () => Promise.reject(new TypeError("Failed to fetch"))],
  ["HTML 500", async () => textResponse("<html><body>Server Error</body></html>", 500)],
];

describe("SetupScreen: the tab may close during the build (RN-41)", () => {
  it("RN-41: the building text does not ask to keep the tab open and says the build keeps running if it closes", async () => {
    await renderScreen(setupBuilding);

    const text = bodyText();
    expect(text).not.toMatch(/keep (this|the) tab open/i);
    expect(text).toMatch(/\btab\b/i);
    expect(text).toMatch(/clos/i);
    expect(text).toMatch(
      /(keeps?|continues?|goes on)\b[^.]*\b(running|going|building|on)\b|(does not|doesn't|won't|will not) stop/i,
    );
  });
});

describe("SetupScreen: focus after an action (RN-49, CA-59)", () => {
  it("RN-49, CA-59: after pressing Start, focus stays inside the Setup screen", async () => {
    await renderScreen(setupNotReady);

    await pressWithKeyboardFocus(startButton());

    expectFocusInsideScreen();
  });

  it("RN-49, CA-59: after Try again on a failed build, focus stays inside the Setup screen", async () => {
    await renderScreen(setupBuildFailed);

    await pressWithKeyboardFocus(retryButton());

    expectFocusInsideScreen();
  });

  it("RN-49, CA-59, CA-60: after Try again on a refusal for lack of space, focus stays inside the Setup screen", async () => {
    await renderScreen(sizedSetup);
    backend.buildAnswer = async () => jsonResponse(setupBuildRefusedForSpace, 507);
    await pressWithKeyboardFocus(startButton());

    backend.buildAnswer = async () => {
      backend.job = setupBuildAccepted;
      return jsonResponse(setupBuildAccepted, 202);
    };
    await pressWithKeyboardFocus(retryButton());

    expectFocusInsideScreen();
  });

  it("RN-49, CA-59: after Try again on a listing failure, focus stays inside the Setup screen", async () => {
    await renderScreen(setupListingUnreachable);
    backend.setup = sizedSetup;

    await pressWithKeyboardFocus(retryButton());
    await advance(0);

    expectFocusInsideScreen();
  });

  it("RN-49, CA-59: after Try again on a failed GET /api/setup, focus stays inside the Setup screen", async () => {
    await renderWithFailingRead(setupNotReady, () => Promise.reject(new TypeError("Failed to fetch")));

    backend.setupAnswer = undefined;
    await pressWithKeyboardFocus(retryButton());
    await advance(0);

    expectFocusInsideScreen();
  });
});

describe("SetupScreen: edge cases of the build (RN-28, CA-18)", () => {
  it("RN-28: a job that disappears while polled (404 not_found) shows a cause and a retry that resumes tracking with the same id", async () => {
    await renderScreen(setupBuilding);
    expect(progressBar()).toBeTruthy();

    backend.job = null; // GET /api/jobs/{id} now answers 404 not_found.
    await advance(POLL_MS);
    await advance(POLL_MS);

    expect(screen.queryByRole("progressbar")).toBeNull();
    expect(announcedTexts().length).toBeGreaterThan(0);
    const postsBefore = buildPosts().length;

    // The restarted build carries the same id as the lost one; tracking must still resume.
    await press(retryButton());
    expect(buildPosts()).toHaveLength(postsBefore + 1);
    expect(progressBar()).toBeTruthy();

    backend.job = { ...setupBuilding.job, progress: 0.5 };
    await advance(POLL_MS);
    expect(shownFraction(progressBar())).toBeCloseTo(0.5, 2);
  });

  it("CA-18: a start answered by a job already done calls onReady exactly once", async () => {
    const onReady = await renderScreen(setupNotReady);
    backend.buildAnswer = async () => {
      backend.job = jobBuildDone;
      backend.setup = { ...backend.setup, database_ready: true };
      return jsonResponse(jobBuildDone, 202);
    };

    await press(startButton());
    await advance(POLL_MS);
    await advance(LONG_WAIT_MS);

    expect(onReady).toHaveBeenCalledTimes(1);
  });

  it("CA-18: with a ready database no start button is rendered", async () => {
    await renderScreen({ ...setupNotReady, database_ready: true });

    expect(screen.queryByRole("button", { name: START_BUTTON })).toBeNull();
    expect(buildPosts()).toHaveLength(0);
  });

  it("RN-28: with a failed job and a listing error both present, a retry answered by 502 shows the start error", async () => {
    await renderScreen({ ...setupBuildFailed, listing_error: setupListingUnreachable.listing_error });
    backend.buildAnswer = async () => jsonResponse(startBadGateway, 502);

    await press(retryButton());

    expect(buildPosts()).toHaveLength(1);
    expect(screen.getByText(startBadGateway.error.message)).toBeTruthy();
    expect(screen.queryByText(setupListingUnreachable.listing_error.error.message)).toBeNull();
  });
});

describe("SetupScreen: the first read fails (RN-28)", () => {
  it.each(getFailures)(
    "RN-28: a failed GET /api/setup (%s) shows a cause and Try again reads it again",
    async (_label, failure) => {
      await renderWithFailingRead(sizedSetup, failure);

      expect(announcedTexts().length).toBeGreaterThan(0);
      expect(bodyText()).not.toContain("<html>");
      const readsBefore = setupReads().length;

      backend.setupAnswer = undefined;
      await press(retryButton());
      await advance(0);

      expect(setupReads()).toHaveLength(readsBefore + 1);
      expect(bodyText()).toMatch(readableSizePattern(300 * MIB));
      expect(startButton()).toBeTruthy();
      expect(buildPosts()).toHaveLength(0);
    },
  );
});

describe("SetupScreen: notices and sizes (RN-28, RN-49)", () => {
  it("RN-28: a setting ignored with a notice (code ignored) does not show the settings-to-fix notice", async () => {
    await renderScreen({
      ...setupNotReady,
      settings: [
        { setting: "IMAGE_MODEL", code: "ignored", message: "IMAGE_MODEL is ignored because IMAGE_PROVIDER is not set." },
      ],
    });

    expect(document.querySelector("a[href='#/status']")).toBeNull();
  });

  it("CA-60, RN-49: less free space than needed is said in words, not only with color", async () => {
    await renderScreen({ ...sizedSetup, free_space: 1 * GIB });

    expect(bodyText()).toMatch(/not enough|insufficient|too little|more (free )?space/i);
  });

  it("RN-28, CA-60: with too little free space there is no start; Check again re-reads and then offers the start", async () => {
    // Needs 2 GiB, has 0.5 GiB: 1.5 GiB must be freed.
    await renderScreen({ ...sizedSetup, free_space: GIB / 2 });

    expect(screen.queryByRole("button", { name: /start/i })).toBeNull();
    expect(bodyText()).toMatch(readableSizePattern(1.5 * GIB));
    const readsBefore = setupReads().length;

    backend.setup = sizedSetup;
    await press(screen.getByRole("button", { name: /check again/i }));
    await advance(0);

    expect(setupReads()).toHaveLength(readsBefore + 1);
    expect(buildPosts()).toHaveLength(0);
    expect(startButton()).toBeTruthy();
    expect(buildPosts()).toHaveLength(0);
  });

  it("CA-60: enough free space shows no shortage text", async () => {
    await renderScreen(sizedSetup);

    expect(bodyText()).not.toMatch(/not enough|insufficient|too little/i);
  });

  it("RN-28: 1048575 bytes is shown as 1 MB, not 1024 KB", async () => {
    await renderScreen({ ...setupNotReady, download_size: 1048575, space_needed: 3 * 1048575 });

    const text = bodyText();
    expect(text).toMatch(/(^|[^\d.])1(\.0+)?\s?(MB|MiB)(?![a-zA-Z])/);
    expect(text).not.toMatch(/1024(\.0+)?\s?(KB|KiB)/i);
  });
});
