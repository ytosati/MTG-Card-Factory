// @vitest-environment jsdom
// Tests for the data part of the Status screen: database readiness, the origin, publication date and
// download date of each source (spec RN-01, CA-08), an unreadable configuration file shown with no
// missing values (CA-77, RN-40) and keyboard focus on the screen's controls (RN-49).
//
// Behaviour under test (frontend/src/screens/StatusScreen.tsx):
// - Each source shows its origin URL as text; the browser loads nothing from it (no img, script,
//   frame or stylesheet points at it). A plain link is acceptable.
// - Each date is shown formatted, with the ISO value kept in <time dateTime="...">.
// - A database that is not ready says so and links to the Setup screen (#/setup).
// - While the configuration file cannot be read, no configuration field reads "Not set", the key is
//   not reported as missing, and the configuration section shows the .env item instead.
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";

import { StatusScreen } from "./StatusScreen";
import type { SourceInfo, StatusResponse } from "../api/types";
import {
  statusFullConfiguration,
  statusNotReady,
  statusUnreadableConfiguration,
  statusWithSources,
} from "../api/contract/samples";
import { jsonResponse, stubFetch } from "../test/fetchMock";
import { pressTab, tabbableElements } from "../test/keyboard";

// Vitest does not process stylesheets and jsdom applies no :focus-visible styles, so the rule is read as text.
const globalCss = readFileSync("src/styles/global.css", "utf8");

const scryfallOracle: SourceInfo = statusWithSources.sources[0]!;

/** A second, fictional source with distinct dates, built on the shape of the contract sample. */
const fictionalRules: SourceInfo = {
  source: "comprehensive_rules",
  url: "https://media.example.test/rules/FictionalComprehensiveRules-20260227.txt",
  published_at: "2026-02-27T12:00:00Z",
  downloaded_at: "2026-11-08T12:30:00Z",
};

const twoSources: StatusResponse = {
  ...statusWithSources,
  sources: [scryfallOracle, fictionalRules],
};

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

/** Renders the screen with one status answer and waits until the request has been answered and shown. */
async function renderWithStatus(body: unknown) {
  const fetchMock = stubFetch(async () => jsonResponse(body));
  render(<StatusScreen />);
  await waitFor(() => expect(fetchMock).toHaveBeenCalled());
  await waitFor(() => expect(screen.queryByText(/loading/i)).toBeNull());
  return fetchMock;
}

function bodyText(): string {
  return document.body.textContent ?? "";
}

/** The deepest element whose text contains the given string. */
function deepestContaining(text: string): HTMLElement {
  const matches = Array.from(document.body.querySelectorAll<HTMLElement>("*")).filter((element) =>
    (element.textContent ?? "").includes(text),
  );
  const deepest = matches.filter((element) => !matches.some((other) => other !== element && element.contains(other)));
  expect(deepest.length, `no element shows "${text}"`).toBeGreaterThan(0);
  return deepest[0]!;
}

function timesWith(root: ParentNode, iso: string): HTMLTimeElement[] {
  return Array.from(root.querySelectorAll<HTMLTimeElement>("time")).filter(
    (element) => element.getAttribute("datetime") === iso,
  );
}

/**
 * The block of one source: the nearest ancestor of its URL text that holds a <time> for the publication
 * date and a different <time> for the download date, and no URL of another source.
 */
function sourceBlock(source: SourceInfo, others: SourceInfo[]): HTMLElement {
  let element: HTMLElement | null = deepestContaining(source.url);
  while (element !== null && element !== document.body) {
    const published = timesWith(element, source.published_at);
    const downloaded = timesWith(element, source.downloaded_at);
    const distinct = published.some((p) => downloaded.some((d) => d !== p));
    if (distinct) {
      const text = element.textContent ?? "";
      expect(
        others.some((other) => text.includes(other.url)),
        `the block of ${source.source} also holds another source`,
      ).toBe(false);
      return element;
    }
    element = element.parentElement;
  }
  throw new Error(`no block shows ${source.source} with its URL and both dates in <time dateTime>`);
}

/** Elements that would make the browser load something from a URL (spec: images only from the local application). */
function loadingReferences(): string[] {
  const references: string[] = [];
  for (const element of Array.from(document.querySelectorAll("img, script, iframe, frame, embed, object, source, video, audio, track, image, input[type='image']"))) {
    for (const attribute of ["src", "srcset", "data", "poster", "href", "xlink:href"]) {
      const value = element.getAttribute(attribute);
      if (value) references.push(value);
    }
  }
  for (const element of Array.from(document.querySelectorAll("link"))) {
    const value = element.getAttribute("href");
    if (value) references.push(value);
  }
  for (const element of Array.from(document.querySelectorAll<HTMLElement>("[style]"))) {
    const style = element.getAttribute("style") ?? "";
    if (/url\(/i.test(style)) references.push(style);
  }
  return references;
}

describe("StatusScreen: data sources (RN-01, CA-08)", () => {
  it("CA-08: shows the origin URL of the contract sample source as text", async () => {
    await renderWithStatus(statusWithSources);

    expect(bodyText()).toContain(scryfallOracle.url);
  });

  it("RN-01, CA-08: each source shows its origin, its publication date and its download date", async () => {
    await renderWithStatus(twoSources);

    for (const source of twoSources.sources) {
      const others = twoSources.sources.filter((other) => other !== source);
      const block = sourceBlock(source, others);
      const text = block.textContent ?? "";
      expect(text, `no publication label for ${source.source}`).toMatch(/publish/i);
      expect(text, `no download label for ${source.source}`).toMatch(/download/i);
    }
  });

  it("CA-08: the sources keep the order of the response", async () => {
    await renderWithStatus(twoSources);

    const text = bodyText();
    const first = text.indexOf(scryfallOracle.url);
    const second = text.indexOf(fictionalRules.url);
    expect(first).toBeGreaterThanOrEqual(0);
    expect(second).toBeGreaterThan(first);
  });

  it("RN-01: dates are formatted for reading, with the ISO value kept in dateTime", async () => {
    await renderWithStatus(twoSources);

    const published = timesWith(document, fictionalRules.published_at);
    const downloaded = timesWith(document, fictionalRules.downloaded_at);
    expect(published).toHaveLength(1);
    expect(downloaded).toHaveLength(1);
    for (const time of [...published, ...downloaded]) {
      const shown = (time.textContent ?? "").trim();
      expect(shown).not.toBe("");
      expect(shown, "the raw ISO value is shown instead of a formatted date").not.toMatch(/\d{4}-\d{2}-\d{2}T/);
      expect(shown).toContain("2026");
      expect(shown).not.toMatch(/Invalid Date|NaN|\bundefined\b|\bnull\b/);
    }
  });

  it("RN-01, CA-08: equal publication and download dates are both shown (contract sample)", async () => {
    await renderWithStatus(statusWithSources);

    expect(scryfallOracle.published_at).toBe(scryfallOracle.downloaded_at);
    expect(timesWith(document, scryfallOracle.published_at).length).toBeGreaterThanOrEqual(2);
  });

  it("CLAUDE.md (the browser loads images only from the local application): no element loads from a source URL", async () => {
    await renderWithStatus(twoSources);

    for (const reference of loadingReferences()) {
      for (const source of twoSources.sources) {
        expect(reference).not.toContain(new URL(source.url).host);
      }
      expect(reference, `the screen loads "${reference}"`).not.toMatch(/^(https?:)?\/\//i);
    }
  });

  it("RN-01: a source URL with markup, odd characters and huge length is shown as plain text, never as a script link", async () => {
    const odd = `javascript:alert(1)//<img src=x onerror=alert(1)>&"'ç{W}{U/B}${"a".repeat(3000)}`;
    await renderWithStatus({
      ...statusWithSources,
      sources: [{ ...scryfallOracle, url: odd }],
    });

    expect(bodyText()).toContain(odd);
    expect(document.querySelector('img[src="x"]')).toBeNull();
    for (const anchor of Array.from(document.querySelectorAll("a[href]"))) {
      expect(anchor.getAttribute("href") ?? "").not.toMatch(/^\s*javascript:/i);
    }
  });

  it("RN-01: a malformed date from the response is shown as readable text, never as Invalid Date", async () => {
    await renderWithStatus({
      ...statusWithSources,
      sources: [{ ...scryfallOracle, published_at: "not-a-date", downloaded_at: "" }],
    });

    expect(bodyText()).toContain(scryfallOracle.url);
    expect(bodyText()).not.toMatch(/Invalid Date|NaN|\bundefined\b|\bnull\b|\[object Object\]/);
  });

  it("RN-01: an unknown source name from a later milestone is still listed with its URL", async () => {
    await renderWithStatus({
      ...statusWithSources,
      sources: [{ ...fictionalRules, source: "fictional_future_source" }],
    });

    expect(bodyText()).toContain(fictionalRules.url);
    expect(timesWith(document, fictionalRules.published_at)).toHaveLength(1);
    expect(timesWith(document, fictionalRules.downloaded_at)).toHaveLength(1);
  });
});

describe("StatusScreen: database readiness (RN-01, CA-08)", () => {
  it("CA-08: a database that is not ready says so and links to the Setup screen", async () => {
    await renderWithStatus(statusNotReady);

    expect(bodyText()).toMatch(/not ready/i);
    const link = screen.getByRole("link", { name: /setup/i });
    expect(link.getAttribute("href")).toBe("#/setup");
  });

  it("CA-08: a database that is not ready lists no source and shows no empty date", async () => {
    await renderWithStatus(statusNotReady);

    expect(document.querySelectorAll("time")).toHaveLength(0);
    expect(bodyText()).not.toMatch(/Invalid Date|NaN|\bundefined\b|\bnull\b/);
  });

  it("CA-08: a ready database is reported as ready, with no Setup link", async () => {
    await renderWithStatus(statusWithSources);

    const text = bodyText();
    expect(text).toMatch(/\bready\b/i);
    expect(text).not.toMatch(/not ready/i);
    expect(screen.queryByRole("link", { name: /setup/i })).toBeNull();
  });

  it("CA-08: readiness is shown together with the configuration fields", async () => {
    await renderWithStatus(statusNotReady);

    expect(screen.getByText("Text provider")).toBeTruthy();
    expect(bodyText()).toMatch(/not ready/i);
  });
});

describe("StatusScreen: unreadable configuration file (CA-77, RN-40)", () => {
  it("CA-77: no configuration field is shown as Not set", async () => {
    await renderWithStatus(statusUnreadableConfiguration);

    expect(bodyText()).toContain(".env");
    expect(bodyText()).not.toMatch(/not set/i);
  });

  it("CA-77: no missing key is reported (no key field reading No, no LLM_API_KEY)", async () => {
    await renderWithStatus(statusUnreadableConfiguration);

    const keyLabel = screen.queryByText("Text key configured");
    if (keyLabel !== null) {
      const value = (keyLabel.nextElementSibling?.textContent ?? "").trim();
      expect(value, "the key is reported as missing").not.toMatch(/^no$/i);
    }
    expect(bodyText()).not.toContain("LLM_API_KEY");
    expect(bodyText()).not.toMatch(/no key|key (is )?missing|missing key/i);
  });

  it("CA-77: the configuration section shows the .env item in place of the fields", async () => {
    await renderWithStatus(statusUnreadableConfiguration);

    const configuration = screen.getByRole("region", { name: "Configuration" });
    expect(configuration.textContent ?? "").toContain(".env");
    expect(configuration.textContent ?? "").not.toMatch(/not set/i);
  });

  it("CA-77: database readiness is still shown while the configuration file cannot be read", async () => {
    await renderWithStatus(statusUnreadableConfiguration);

    expect(bodyText()).toMatch(/not ready/i);
    expect(screen.getByRole("link", { name: /setup/i }).getAttribute("href")).toBe("#/setup");
  });

  it("CA-77: after the file is fixed, reopening the screen shows the configuration fields", async () => {
    const fetchMock = stubFetch(
      async () => jsonResponse(statusUnreadableConfiguration),
      async () => jsonResponse(statusFullConfiguration),
    );

    const first = render(<StatusScreen />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(bodyText()).toContain(".env"));
    first.unmount();

    render(<StatusScreen />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    const label = await screen.findByText("Text model");
    expect((label.nextElementSibling?.textContent ?? "").trim()).toBe(statusFullConfiguration.text_model);
    expect(bodyText()).not.toContain(".env");
  });
});

describe("StatusScreen: keyboard focus (RN-49)", () => {
  function drawsFocusRing(): boolean {
    const match = /(^|})\s*:focus-visible\s*\{([^}]*)\}/.exec(globalCss);
    if (match === null) return false;
    const outline = /(^|;|\s)outline\s*:\s*([^;]+)/i.exec(match[2]!);
    return outline !== null && !/^(none|0|0px|hidden)$/i.test(outline[2]!.trim());
  }

  async function tabThroughScreen(body: StatusResponse): Promise<HTMLElement[]> {
    await renderWithStatus(body);
    (document.activeElement as HTMLElement | null)?.blur();
    const reached: HTMLElement[] = [];
    const total = tabbableElements().length;
    for (let index = 0; index < total; index += 1) {
      const next = pressTab();
      expect(next).not.toBeNull();
      expect(document.activeElement, "Tab did not move the focus").toBe(next);
      reached.push(next!);
    }
    return reached;
  }

  it("RN-49: with a database not ready, Tab reaches the Setup link and the Check again button, each taking focus", async () => {
    const reached = await tabThroughScreen(statusNotReady);

    const setup = screen.getByRole("link", { name: /setup/i });
    const checkAgain = screen.getByRole("button", { name: /check again/i });
    expect(reached).toContain(setup);
    expect(reached).toContain(checkAgain);
  });

  it("RN-49: with sources and with an unreadable configuration, every control is reached with Tab", async () => {
    for (const body of [twoSources, statusUnreadableConfiguration]) {
      const reached = await tabThroughScreen(body);
      const controls = [
        ...screen.queryAllByRole("link"),
        ...screen.queryAllByRole("button"),
      ];
      expect(controls.length).toBeGreaterThan(0);
      for (const control of controls) {
        expect(reached, `"${control.textContent}" is not reached with Tab`).toContain(control);
      }
      cleanup();
    }
  });

  it("RN-49: no control leaves the Tab order or removes its focus outline inline", async () => {
    await renderWithStatus(statusNotReady);

    for (const control of [...screen.getAllByRole("link"), ...screen.getAllByRole("button")]) {
      expect(control.tabIndex, `"${control.textContent}" is out of the Tab order`).toBeGreaterThanOrEqual(0);
      expect(control.getAttribute("tabindex") ?? "0", "positive tabindex changes the Tab order").not.toMatch(/^[1-9]/);
      expect(control.style.outline).not.toMatch(/^(none|0|0px)$/);
      expect(control.style.outlineStyle).not.toMatch(/^(none|hidden)$/);
    }
  });

  it("RN-49: a focused control draws the global :focus-visible ring", async () => {
    await renderWithStatus(statusNotReady);
    const setup = screen.getByRole("link", { name: /setup/i });
    setup.focus();

    expect(document.activeElement).toBe(setup);
    expect(setup.matches(":focus")).toBe(true);
    expect(drawsFocusRing(), "global.css has no :focus-visible rule drawing an outline").toBe(true);
    expect(within(document.body).getByRole("link", { name: /setup/i })).toBe(setup);
  });
});
