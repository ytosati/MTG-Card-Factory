// @vitest-environment jsdom
// Tests for the preview gallery (spec RN-49 in part; tasks.md T167 "Done when": index, a state opened by
// its address, the width switch).
//
// Contract under test:
//   frontend/src/preview/types.ts
//     PreviewState  = { id: string; name: string; render: () => ReactNode }
//     PreviewScreen = { id: string; name: string; states: PreviewState[] }
//   frontend/src/preview/PreviewGallery.tsx
//     <PreviewGallery screens?={PreviewScreen[]} />   (default: the registry of src/preview/registry.ts)
//   Addresses: "#/preview" is the index; "#/preview/<screen id>/<state id>" is one state.
//   Index: level-1 heading "Preview gallery"; one level-2 heading per screen name; per state a link
//     named by the state name with href "#/preview/<screen id>/<state id>".
//   State page: a link "Back to the index" (href "#/preview"); a radiogroup "Width" with radios
//     "360 px", "768 px", "1280 px" (1280 checked by default); a checkbox "Reduced motion"; a region
//     named "Preview" that holds the state and carries data-width ("360" | "768" | "1280") and
//     data-reduced-motion ("true" | "false").
//   Unknown screen or state: an alert that says no such preview exists, and a link to the index.
//   The gallery follows the hash (hashchange) and also appears inside <App /> at "#/preview" in the
//   development server.
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "../App";
import { PreviewGallery } from "./PreviewGallery";
import type { PreviewScreen } from "./types";

const screens: PreviewScreen[] = [
  {
    id: "alpha",
    name: "Alpha screen",
    states: [
      { id: "empty", name: "Empty list", render: () => <p>Alpha empty content</p> },
      { id: "full", name: "Full list", render: () => <button type="button">Alpha full button</button> },
    ],
  },
  {
    id: "beta",
    name: "Beta screen",
    states: [{ id: "only", name: "Only state", render: () => <p>Beta only content</p> }],
  },
  { id: "gamma", name: "Gamma screen", states: [] },
];

function open(hash: string) {
  window.location.hash = hash;
  return render(<PreviewGallery screens={screens} />);
}

function navigate(hash: string) {
  act(() => {
    window.location.hash = hash;
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  });
}

beforeEach(() => {
  window.location.hash = "";
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("preview gallery: index (T167)", () => {
  it("lists every screen under a heading and every state as a link to its address", () => {
    open("#/preview");
    expect(screen.getByRole("heading", { level: 1, name: "Preview gallery" })).toBeTruthy();
    for (const entry of screens) {
      expect(screen.getByRole("heading", { level: 2, name: entry.name })).toBeTruthy();
      for (const state of entry.states) {
        const link = screen.getByRole("link", { name: state.name });
        expect(link.getAttribute("href")).toBe(`#/preview/${entry.id}/${state.id}`);
      }
    }
  });

  it("keeps each state under its own screen", () => {
    open("#/preview");
    const beta = screen.getByRole("heading", { level: 2, name: "Beta screen" }).closest("section, li, div");
    expect(beta).not.toBeNull();
    expect(within(beta as HTMLElement).getByRole("link", { name: "Only state" })).toBeTruthy();
    expect(within(beta as HTMLElement).queryByRole("link", { name: "Empty list" })).toBeNull();
  });

  it("a screen with no states still appears, and an empty registry shows the index without failing", () => {
    open("#/preview");
    expect(screen.getByRole("heading", { level: 2, name: "Gamma screen" })).toBeTruthy();
    cleanup();
    render(<PreviewGallery screens={[]} />);
    expect(screen.getByRole("heading", { level: 1, name: "Preview gallery" })).toBeTruthy();
  });

  it("does not render any state content on the index", () => {
    open("#/preview");
    expect(screen.queryByText("Alpha empty content")).toBeNull();
  });
});

describe("preview gallery: a state opened by its address (T167)", () => {
  it("renders the state named by the address and only that state", () => {
    open("#/preview/alpha/empty");
    const frame = screen.getByRole("region", { name: "Preview" });
    expect(within(frame).getByText("Alpha empty content")).toBeTruthy();
    expect(screen.queryByText("Beta only content")).toBeNull();
  });

  it("renders another state of the same screen and one of another screen", () => {
    open("#/preview/alpha/full");
    expect(
      within(screen.getByRole("region", { name: "Preview" })).getByRole("button", { name: "Alpha full button" }),
    ).toBeTruthy();
    cleanup();
    open("#/preview/beta/only");
    expect(within(screen.getByRole("region", { name: "Preview" })).getByText("Beta only content")).toBeTruthy();
  });

  it("follows the hash when it changes", () => {
    open("#/preview/alpha/empty");
    navigate("#/preview/beta/only");
    expect(screen.getByText("Beta only content")).toBeTruthy();
    expect(screen.queryByText("Alpha empty content")).toBeNull();
  });

  it("offers a link back to the index", () => {
    open("#/preview/alpha/empty");
    expect(screen.getByRole("link", { name: "Back to the index" }).getAttribute("href")).toBe("#/preview");
  });

  it.each([
    "#/preview/nope/empty",
    "#/preview/alpha/nope",
    "#/preview/alpha",
    "#/preview/alpha/empty/extra",
    "#/preview/%00/%E0",
  ])("an unknown address %s shows an alert and a link to the index, not a state", (hash) => {
    open(hash);
    expect(screen.getByRole("alert").textContent).toMatch(/no such preview/i);
    expect(screen.getByRole("link", { name: /index/i }).getAttribute("href")).toBe("#/preview");
    expect(screen.queryByText("Alpha empty content")).toBeNull();
  });
});

describe("preview gallery: width and reduced motion switches (T167)", () => {
  it("offers the three widths of plan section 14 as radios, 1280 px chosen first", () => {
    open("#/preview/alpha/empty");
    const group = screen.getByRole("radiogroup", { name: "Width" });
    for (const name of ["360 px", "768 px", "1280 px"]) {
      expect(within(group).getByRole("radio", { name })).toBeTruthy();
    }
    expect(within(group).getAllByRole("radio")).toHaveLength(3);
    expect((within(group).getByRole("radio", { name: "1280 px" }) as HTMLInputElement).checked).toBe(true);
    expect(screen.getByRole("region", { name: "Preview" }).getAttribute("data-width")).toBe("1280");
  });

  it.each([
    ["360 px", "360"],
    ["768 px", "768"],
    ["1280 px", "1280"],
  ])("choosing %s sets the preview width to %s", (name, width) => {
    open("#/preview/alpha/empty");
    fireEvent.click(screen.getByRole("radio", { name }));
    expect(screen.getByRole("region", { name: "Preview" }).getAttribute("data-width")).toBe(width);
    expect((screen.getByRole("radio", { name }) as HTMLInputElement).checked).toBe(true);
  });

  it("the width stays while the person moves to another state", () => {
    open("#/preview/alpha/empty");
    fireEvent.click(screen.getByRole("radio", { name: "360 px" }));
    navigate("#/preview/alpha/full");
    expect(screen.getByRole("region", { name: "Preview" }).getAttribute("data-width")).toBe("360");
  });

  it("the reduced-motion switch is a checkbox, off by default, and sets data-reduced-motion", () => {
    open("#/preview/alpha/empty");
    const box = screen.getByRole("checkbox", { name: "Reduced motion" }) as HTMLInputElement;
    const frame = screen.getByRole("region", { name: "Preview" });
    expect(box.checked).toBe(false);
    expect(frame.getAttribute("data-reduced-motion")).toBe("false");
    fireEvent.click(box);
    expect(frame.getAttribute("data-reduced-motion")).toBe("true");
    fireEvent.click(box);
    expect(frame.getAttribute("data-reduced-motion")).toBe("false");
  });

  it("the switches are native labeled controls, so the keyboard reaches them (RN-49)", () => {
    open("#/preview/alpha/empty");
    const controls = [...screen.getAllByRole("radio"), screen.getByRole("checkbox", { name: "Reduced motion" })];
    for (const control of controls) {
      expect((control as HTMLInputElement).disabled).toBe(false);
      expect(control.getAttribute("tabindex")).toBeNull();
    }
  });
});

describe("preview gallery inside the application in development (T167)", () => {
  it("<App /> at #/preview shows the gallery index, whatever the readiness answer", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new TypeError("offline"))));
    window.location.hash = "#/preview";
    render(<App />);
    expect(await screen.findByRole("heading", { level: 1, name: "Preview gallery" })).toBeTruthy();
  });
});
