// @vitest-environment jsdom
// Tests for the application shell: the hash-based screen switch (plan section 13: no router library),
// the readiness gate (spec RN-28, CA-18), Status first when settings need fixing (RN-40, CA-46)
// and keyboard navigation with visible focus (RN-49, CA-59).
//
// Shell behaviour under test (frontend/src/App.tsx):
// - The shell decides readiness from GET /api/status (database_ready and settings); GET /api/setup is also
//   mocked consistently in most tests. The shell never starts the build itself.
// - While the database is not ready (also during the build), only Setup (#/setup) and Status (#/status)
//   are offered; with no hash or any other hash the Setup screen (level-1 heading containing "Setup")
//   opens, even when settings need fixing (RN-28: Setup says so and links to Status).
// - When the database is ready, the navigation offers every screen that exists and no longer Setup;
//   with no hash the shell does not open on Setup, and when settings need fixing it opens on Status.
// - The navigation (<nav aria-label="Screens">) is made of links reached with Tab, in the order shown.
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import type { JobResponse, SetupResponse, StatusResponse } from "./api/types";
import {
  setupBuilding,
  setupNotReady,
  setupSettingsToFix,
  statusFullConfiguration,
  statusMissingTextKey,
  statusNotReady,
  statusWithSources,
} from "./api/contract/samples";
import { calledUrl, jsonResponse, stubFetchByPath } from "./test/fetchMock";
import { pressTab, tabbableElements } from "./test/keyboard";
import { readFileSync } from "node:fs";

// Read as text from the frontend folder (where Vitest runs): Vitest does not process stylesheets,
// and jsdom applies no :focus-visible styles.
const globalCss = readFileSync("src/styles/global.css", "utf8");
const tokensCss = readFileSync("src/styles/tokens.css", "utf8");

const SETUP_HEADING = /setup/i;
const STATUS_HEADING = "Status";

interface Backend {
  status: StatusResponse;
  setup: SetupResponse;
  job?: JobResponse;
}

/** Ready database, nothing to fix (built from the samples: GET /api/setup has no ready sample). */
const readyBackend: Backend = {
  status: statusWithSources,
  setup: { ...setupNotReady, database_ready: true },
};

/** Ready database with a missing text key: the settings list of the missing-key sample. */
const readyWithSettingsToFix: Backend = {
  status: {
    ...statusWithSources,
    text_key_configured: false,
    settings: statusMissingTextKey.settings,
  },
  setup: { ...setupSettingsToFix, database_ready: true },
};

const notReadyBackend: Backend = { status: statusNotReady, setup: setupNotReady };

const notReadyWithSettingsToFix: Backend = { status: statusMissingTextKey, setup: setupSettingsToFix };

const buildingBackend: Backend = {
  status: statusNotReady,
  setup: setupBuilding,
  job: setupBuilding.job,
};

/** Stubs every endpoint the shell and its screens may read; the heartbeat answers 204. */
function stubBackend(backend: Backend) {
  return stubFetchByPath({
    "/api/status": backend.status,
    "/api/setup": backend.setup,
    "/api/jobs/": backend.job ?? backend.setup.job ?? setupBuilding.job,
    "/api/heartbeat": async () => new Response(null, { status: 204 }),
  });
}

function renderAt(hash: string, backend: Backend) {
  window.location.hash = hash;
  const fetchMock = stubBackend(backend);
  render(<App />);
  return fetchMock;
}

function navigation(): HTMLElement {
  return screen.getByRole("navigation", { name: "Screens" });
}

function navLinks(): HTMLAnchorElement[] {
  return within(navigation()).getAllByRole("link") as HTMLAnchorElement[];
}

function navLinkNames(): string[] {
  return navLinks().map((link) => (link.textContent ?? "").trim());
}

async function findScreenHeading(name: string | RegExp): Promise<HTMLElement> {
  return screen.findByRole("heading", { level: 1, name });
}

/** Waits until the shell has decided the gate: the navigation lists the given screens. */
async function waitForNav(names: string[]) {
  await waitFor(() => expect(navLinkNames()).toEqual(names));
}

afterEach(() => {
  cleanup();
  window.location.hash = "";
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("App", () => {
  it("RN-40: the #/status route opens the Status screen, which reads GET /api/status", async () => {
    const fetchMock = renderAt("#/status", { status: statusFullConfiguration, setup: setupNotReady });

    expect(await findScreenHeading(STATUS_HEADING)).toBeTruthy();
    expect(await screen.findByText("Text provider")).toBeTruthy();
    expect(fetchMock.mock.calls.some((call) => calledUrl(call[0]) === "/api/status")).toBe(true);
  });
});

describe("App readiness gate (database not ready)", () => {
  it("CA-18: with no hash the Setup screen opens first, and nothing starts the build", async () => {
    const fetchMock = renderAt("", notReadyBackend);

    expect(await findScreenHeading(SETUP_HEADING)).toBeTruthy();
    expect(screen.queryByRole("heading", { level: 1, name: STATUS_HEADING })).toBeNull();
    const buildCalls = fetchMock.mock.calls.filter((call) => calledUrl(call[0]) === "/api/setup/build");
    expect(buildCalls).toHaveLength(0);
  });

  it("RN-28, CA-18: the navigation offers only Setup and Status", async () => {
    renderAt("", notReadyBackend);

    await findScreenHeading(SETUP_HEADING);
    await waitForNav(["Setup", "Status"]);
    expect(navLinks().map((link) => link.getAttribute("href"))).toEqual(["#/setup", "#/status"]);
  });

  it("CA-18: the person can open the Status screen before the database is ready", async () => {
    const fetchMock = renderAt("#/status", notReadyBackend);

    expect(await findScreenHeading(STATUS_HEADING)).toBeTruthy();
    expect(screen.queryByRole("heading", { level: 1, name: SETUP_HEADING })).toBeNull();
    expect(fetchMock.mock.calls.some((call) => calledUrl(call[0]) === "/api/status")).toBe(true);
  });

  it("RN-28: #/setup opens the Setup screen", async () => {
    renderAt("#/setup", notReadyBackend);

    expect(await findScreenHeading(SETUP_HEADING)).toBeTruthy();
  });

  it.each(["#/library", "#/request", "#/result/00000000-0000-4000-8000-000000000001", "#/", "#/%E2%9C%A8%20<script>", "#/status/../library"])(
    "RN-28: any other screen is not available before the database is ready; %s opens Setup",
    async (hash) => {
      renderAt(hash, notReadyBackend);

      expect(await findScreenHeading(SETUP_HEADING)).toBeTruthy();
      expect(screen.queryByRole("heading", { level: 1, name: STATUS_HEADING })).toBeNull();
    },
  );

  it("RN-28: when settings need fixing before the database is ready, Setup still opens first", async () => {
    renderAt("", notReadyWithSettingsToFix);

    expect(await findScreenHeading(SETUP_HEADING)).toBeTruthy();
    expect(screen.queryByRole("heading", { level: 1, name: STATUS_HEADING })).toBeNull();
    await waitForNav(["Setup", "Status"]);
  });

  it("RN-28: during the build only Setup and Status are offered, and Status can be opened", async () => {
    renderAt("#/status", buildingBackend);

    expect(await findScreenHeading(STATUS_HEADING)).toBeTruthy();
    await waitForNav(["Setup", "Status"]);
  });

  it("RN-28: during the build any other screen opens Setup", async () => {
    renderAt("#/library", buildingBackend);

    expect(await findScreenHeading(SETUP_HEADING)).toBeTruthy();
    await waitForNav(["Setup", "Status"]);
  });
});

describe("App readiness gate (database ready)", () => {
  it("CA-18: with no hash the shell does not open on Setup", async () => {
    renderAt("", readyBackend);

    expect(await findScreenHeading(STATUS_HEADING)).toBeTruthy();
    expect(screen.queryByRole("heading", { level: 1, name: SETUP_HEADING })).toBeNull();
  });

  it("CA-18: the navigation offers every screen that exists and no longer Setup", async () => {
    renderAt("", readyBackend);

    await findScreenHeading(STATUS_HEADING);
    await waitFor(() => expect(navLinkNames()).toContain("Status"));
    expect(navLinkNames()).not.toContain("Setup");
  });

  it("CA-18: every screen offered in the navigation opens with a level-1 heading named as its link", async () => {
    renderAt("", readyBackend);
    await findScreenHeading(STATUS_HEADING);
    await waitFor(() => expect(navLinkNames()).toContain("Status"));

    const links = navLinks().map((link) => ({
      name: (link.textContent ?? "").trim(),
      href: link.getAttribute("href") ?? "",
    }));
    expect(links.length).toBeGreaterThan(0);
    for (const { name, href } of links) {
      expect(href.startsWith("#/"), `link "${name}" is not a hash route`).toBe(true);
      window.location.hash = href;
      window.dispatchEvent(new HashChangeEvent("hashchange"));
      expect(await findScreenHeading(name)).toBeTruthy();
    }
  });
});

describe("App opens on Status when settings need fixing (RN-40)", () => {
  it("CA-46: with a missing key and a ready database, the shell opens on Status and names the setting", async () => {
    renderAt("", readyWithSettingsToFix);

    expect(await findScreenHeading(STATUS_HEADING)).toBeTruthy();
    expect((await screen.findAllByText(/LLM_API_KEY/)).length).toBeGreaterThan(0);
    expect(screen.queryByRole("heading", { level: 1, name: SETUP_HEADING })).toBeNull();
  });
});

describe("App keyboard navigation (RN-49)", () => {
  it("CA-59: the navigation links are reached with Tab, in the order shown, and each takes focus", async () => {
    renderAt("", notReadyBackend);
    await findScreenHeading(SETUP_HEADING);
    await waitForNav(["Setup", "Status"]);

    const links = navLinks();
    const order = tabbableElements();
    for (const link of links) {
      expect(order, `"${link.textContent}" is not reached with Tab`).toContain(link);
      expect(link.getAttribute("tabindex")).toBeNull();
    }
    expect(order.indexOf(links[0]!)).toBeLessThan(order.indexOf(links[1]!));

    links[0]!.focus();
    expect(document.activeElement).toBe(links[0]);
    expect(pressTab()).toBe(links[1]);
    expect(document.activeElement).toBe(links[1]);
  });

  it("CA-59: no element uses a positive tabindex, so the Tab order follows the page", async () => {
    renderAt("", notReadyBackend);
    await findScreenHeading(SETUP_HEADING);
    await waitForNav(["Setup", "Status"]);

    const positive = Array.from(document.querySelectorAll<HTMLElement>("[tabindex]")).filter(
      (element) => element.tabIndex > 0,
    );
    expect(positive).toEqual([]);
  });

  it("CA-59: activating the focused Status link opens Status, marks it current and keeps focus on the page", async () => {
    renderAt("", notReadyBackend);
    await findScreenHeading(SETUP_HEADING);
    await waitForNav(["Setup", "Status"]);

    const setupLink = within(navigation()).getByRole("link", { name: "Setup" });
    expect(setupLink.getAttribute("aria-current")).toBe("page");

    const statusLink = within(navigation()).getByRole("link", { name: "Status" });
    statusLink.focus();
    // A link activated with Enter receives a click; jsdom then follows the hash link.
    fireEvent.click(statusLink);

    expect(await findScreenHeading(STATUS_HEADING)).toBeTruthy();
    await waitFor(() =>
      expect(within(navigation()).getByRole("link", { name: "Status" }).getAttribute("aria-current")).toBe("page"),
    );
    expect(within(navigation()).getByRole("link", { name: "Setup" }).getAttribute("aria-current")).toBeNull();
    expect(document.activeElement).not.toBe(document.body);
    expect(document.activeElement).not.toBeNull();
  });
});

/** The CSS rules of a stylesheet, innermost blocks only (rules inside @media included). */
function cssRules(css: string): Array<{ selectors: string[]; body: string }> {
  const withoutComments = css.replace(/\/\*[\s\S]*?\*\//g, "");
  const rules: Array<{ selectors: string[]; body: string }> = [];
  for (const match of withoutComments.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
    const selectors = match[1]!
      .split(",")
      .map((selector) => selector.trim())
      .filter((selector) => selector !== "");
    rules.push({ selectors, body: match[2]! });
  }
  return rules;
}

function removesOutline(body: string): boolean {
  return /(^|;|\s)outline(-style|-width)?\s*:\s*(none|0|0px|hidden)\s*(;|$)/i.test(body.trim());
}

function drawsOutline(body: string): boolean {
  const match = /(^|;|\s)outline\s*:\s*([^;]+)/i.exec(body);
  return match !== null && !/^(none|0|0px|hidden)$/i.test(match[2]!.trim());
}

describe("App visible focus (RN-49)", () => {
  it("CA-59: every focused element draws a focus ring with :focus-visible", () => {
    const rule = cssRules(globalCss).find((candidate) => candidate.selectors.includes(":focus-visible"));

    expect(rule, "no global :focus-visible rule").toBeDefined();
    expect(drawsOutline(rule!.body)).toBe(true);
  });

  it("CA-59: the focus ring tokens draw a visible ring (non-zero width, a color)", () => {
    const width = /--focus-ring-width\s*:\s*([^;]+);/.exec(tokensCss)?.[1]?.trim() ?? "";
    const color = /--focus-ring-color\s*:\s*([^;]+);/.exec(tokensCss)?.[1]?.trim() ?? "";

    expect(width).toMatch(/^[0-9.]+(px|rem|em)$/);
    expect(Number.parseFloat(width)).toBeGreaterThan(0);
    expect(color).not.toBe("");
    expect(color).not.toMatch(/^(transparent|none)$/i);
  });

  it("CA-59: no style removes the focus outline without drawing it again for keyboard focus", () => {
    const rules = cssRules(globalCss);
    const drawn = new Set(
      rules.filter((rule) => drawsOutline(rule.body)).flatMap((rule) => rule.selectors),
    );

    for (const rule of rules.filter((candidate) => removesOutline(candidate.body))) {
      for (const selector of rule.selectors) {
        expect(selector, `"${selector}" removes the outline outside of focus`).toMatch(/:focus/);
        if (selector.includes(":not(:focus-visible)")) continue;
        expect(selector, `"${selector}" removes the keyboard focus ring`).not.toMatch(/:focus-visible/);
        const restored = selector.replace(/:focus(?!-)/, ":focus-visible");
        // The global :focus-visible rule is less specific, so the same selector must draw it again.
        expect(drawn.has(restored), `"${selector}" is not restored by "${restored}"`).toBe(true);
      }
    }
  });
});

/** Ready answers from GET /api/status only: GET /api/setup is not mocked and answers 404. */
function stubStatusOnly(status: StatusResponse | (() => Promise<Response>)) {
  return stubFetchByPath({
    "/api/status": status,
    "/api/heartbeat": async () => new Response(null, { status: 204 }),
  });
}

/** An alert raised by the shell about the database readiness (not the Status screen's own errors). */
function readinessAlerts(): HTMLElement[] {
  return screen.queryAllByRole("alert").filter((element) => /database/i.test(element.textContent ?? ""));
}

async function settle(ms = 50) {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, ms));
  });
}

describe("App readiness comes from GET /api/status", () => {
  it("CA-18: a ready database in GET /api/status opens the normal screens even when GET /api/setup is not available", async () => {
    window.location.hash = "";
    stubStatusOnly(statusWithSources);
    render(<App />);

    expect(await findScreenHeading(STATUS_HEADING)).toBeTruthy();
    await waitFor(() => expect(navLinkNames()).toContain("Status"));
    expect(navLinkNames()).not.toContain("Setup");
    expect(screen.queryByRole("heading", { level: 1, name: SETUP_HEADING })).toBeNull();
    expect(readinessAlerts()).toEqual([]);
  });

  it("CA-46: settings to fix in GET /api/status open Status first, with no GET /api/setup", async () => {
    window.location.hash = "";
    stubStatusOnly(readyWithSettingsToFix.status);
    render(<App />);

    expect(await findScreenHeading(STATUS_HEADING)).toBeTruthy();
    expect((await screen.findAllByText(/LLM_API_KEY/)).length).toBeGreaterThan(0);
    expect(navLinkNames()).not.toContain("Setup");
  });

  it("RN-28: while readiness is still loading, the navigation offers no Setup link", async () => {
    window.location.hash = "";
    stubFetchByPath({
      "/api/status": () => new Promise<Response>(() => {}),
      "/api/setup": () => new Promise<Response>(() => {}),
      "/api/heartbeat": async () => new Response(null, { status: 204 }),
    });
    render(<App />);
    await settle();

    expect(within(navigation()).queryByRole("link", { name: "Setup" })).toBeNull();
  });

  it("RN-28: a failed re-read after the database was known ready keeps the gate open, with no readiness alert", async () => {
    let failing = false;
    window.location.hash = "#/status";
    const fetchMock = stubStatusOnly(async () => {
      if (failing) throw new TypeError("Failed to fetch");
      return jsonResponse(statusWithSources);
    });
    render(<App />);
    await findScreenHeading(STATUS_HEADING);
    await waitFor(() => expect(navLinkNames()).toContain("Status"));
    expect(navLinkNames()).not.toContain("Setup");

    failing = true;
    const before = fetchMock.mock.calls.length;
    window.location.hash = "#/library";
    window.dispatchEvent(new HashChangeEvent("hashchange"));
    await settle();

    expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(before);
    expect(navLinkNames()).not.toContain("Setup");
    expect(navLinkNames()).toContain("Status");
    expect(screen.queryByRole("heading", { level: 1, name: SETUP_HEADING })).toBeNull();
    expect(readinessAlerts()).toEqual([]);
  });

  it("RN-28: a screen outside the gate while not ready shows Setup and the address becomes #/setup", async () => {
    renderAt("#/library", notReadyBackend);

    expect(await findScreenHeading(SETUP_HEADING)).toBeTruthy();
    await waitFor(() => expect(window.location.hash).toBe("#/setup"));
  });
});
