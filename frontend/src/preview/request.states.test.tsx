// @vitest-environment jsdom
// Tests for the Request screen preview, generation fields (tasks.md T168; spec RN-11, RN-49, RN-50,
// RN-53, RN-54, RN-55, RN-56, RN-58 visual part).
//
// Contract under test (the implementer follows it):
//   frontend/src/preview/request.states.tsx exports `requestStates: PreviewState[]`, and
//   frontend/src/preview/registry.ts lists { id: "request", name: "Request", states: requestStates }.
//   State ids (addresses "#/preview/request/<id>"):
//     empty, filled, refused-field, generating-design-intent, generating-search, generating-draft,
//     generating-validation, generating-revision, generating-art, one-at-a-time, provider-refusal, prefilled
//   Every state renders one level-1 heading, and these controls by accessible name:
//     textbox "Idea or theme"; group "Color identity" (checkboxes White, Blue, Black, Red, Green,
//     Colorless; the group has a description); group "Power level" (radios Casual, Medium, Strong, each
//     with a description, the one-line meaning); group "Generation effort" (radios Low, Medium, High);
//     group "Card language" (radios English and Portuguese...); a button "Advanced options" with
//     aria-expanded, collapsed at first; once expanded, controls named "Card types", "Supertypes",
//     "Subtypes", "Mana value", "Power", "Toughness", "Starting loyalty"; button "Generate card".
//   Generating states: fields locked (idea disabled); a list named "Generation steps" whose item with
//     aria-current="step" names the running step (design intent, search for related cards, draft,
//     validation, revision, art).
//   Alerts: refused-field names the field ("Idea or theme") and marks the idea invalid; one-at-a-time says
//     a generation is already running; provider-refusal says the request was refused and offers a button
//     or link "Edit the request" (the idea stays as written).
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import type { ByRoleMatcher } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { PreviewGallery } from "./PreviewGallery";
import { previewScreens } from "./registry";

const STATE_IDS = [
  "empty",
  "filled",
  "refused-field",
  "generating-design-intent",
  "generating-search",
  "generating-draft",
  "generating-validation",
  "generating-revision",
  "generating-art",
  "one-at-a-time",
  "provider-refusal",
  "prefilled",
];

function openState(id: string): HTMLElement {
  window.location.hash = `#/preview/request/${id}`;
  render(<PreviewGallery />);
  return screen.getByRole("region", { name: "Preview" });
}

/** A control found by role first (groups of choices) and by label otherwise (single inputs). */
function control(frame: HTMLElement, name: string, roles: ByRoleMatcher[] = ["group"]): HTMLElement {
  for (const role of roles) {
    const found = within(frame).queryByRole(role as "group", { name });
    if (found) return found;
  }
  return within(frame).getByLabelText(name);
}

function description(element: HTMLElement): string {
  const ids = (element.getAttribute("aria-describedby") ?? "").split(/\s+/).filter(Boolean);
  return ids
    .map((id) => element.ownerDocument.getElementById(id)?.textContent ?? "")
    .join(" ")
    .trim();
}

function checkedNames(group: HTMLElement, role: "checkbox" | "radio"): string[] {
  return within(group)
    .getAllByRole(role)
    .filter((input) => (input as HTMLInputElement).checked)
    .map((input) => input.closest("label")?.textContent?.trim() ?? "");
}

beforeEach(() => {
  window.location.hash = "";
});
afterEach(cleanup);

describe("request preview: registry (T168)", () => {
  it("lists the Request screen with each named state, in the gallery index", () => {
    const entry = previewScreens.find((item) => item.id === "request");
    expect(entry?.name).toBe("Request");
    expect(entry?.states.map((state) => state.id)).toEqual(expect.arrayContaining(STATE_IDS));
    window.location.hash = "#/preview";
    render(<PreviewGallery />);
    for (const id of STATE_IDS) {
      expect(document.querySelector(`a[href="#/preview/request/${id}"]`)).not.toBeNull();
    }
  });
});

describe.each(STATE_IDS)("request preview state %s: every field is labeled (RN-49, RN-11)", (id) => {
  it("has a single level-1 heading and a label for every generation field", () => {
    const frame = openState(id);
    expect(within(frame).getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(within(frame).getByRole("textbox", { name: "Idea or theme" })).toBeTruthy();
    const colors = control(frame, "Color identity");
    for (const name of ["White", "Blue", "Black", "Red", "Green", "Colorless"]) {
      expect(within(colors).getByRole("checkbox", { name })).toBeTruthy();
    }
    const power = control(frame, "Power level");
    for (const name of ["Casual", "Medium", "Strong"]) {
      expect(within(power).getByRole("radio", { name })).toBeTruthy();
    }
    const effort = control(frame, "Generation effort");
    for (const name of ["Low", "Medium", "High"]) {
      expect(within(effort).getByRole("radio", { name })).toBeTruthy();
    }
    const language = control(frame, "Card language");
    expect(within(language).getByRole("radio", { name: /^English$/ })).toBeTruthy();
    expect(within(language).getByRole("radio", { name: /^Portuguese/ })).toBeTruthy();
    expect(within(frame).getByRole("button", { name: "Advanced options" })).toBeTruthy();
    expect(within(frame).getByRole("button", { name: "Generate card" })).toBeTruthy();
  });

  it("gives color identity and each power level a one-line meaning (RN-11, spec Screens)", () => {
    const frame = openState(id);
    expect(description(control(frame, "Color identity"))).not.toBe("");
    const power = control(frame, "Power level");
    for (const radio of within(power).getAllByRole("radio")) {
      expect(description(radio)).not.toBe("");
    }
  });

  it("hides the advanced options until requested, then shows every one with a label (RN-54)", () => {
    const frame = openState(id);
    const toggle = within(frame).getByRole("button", { name: "Advanced options" });
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    expect(within(frame).queryByLabelText("Starting loyalty")).toBeNull();
    expect(within(frame).queryByRole("group", { name: "Card types" })).toBeNull();
    fireEvent.click(toggle);
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    for (const name of ["Card types", "Supertypes"]) control(frame, name);
    for (const name of ["Subtypes", "Mana value", "Power", "Toughness", "Starting loyalty"]) {
      control(frame, name, []);
    }
    // Battle is not offered (RN-54).
    expect(within(frame).queryByRole("checkbox", { name: "Battle" })).toBeNull();
    fireEvent.click(toggle);
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    expect(within(frame).queryByLabelText("Starting loyalty")).toBeNull();
  });
});

describe("request preview: empty (RN-11)", () => {
  it("opens with no idea, no color and no power level chosen, and no message", () => {
    const frame = openState("empty");
    expect((within(frame).getByRole("textbox", { name: "Idea or theme" }) as HTMLTextAreaElement).value).toBe("");
    expect(checkedNames(control(frame, "Color identity"), "checkbox")).toEqual([]);
    expect(checkedNames(control(frame, "Power level"), "radio")).toEqual([]);
    expect(within(frame).queryByRole("alert")).toBeNull();
    expect((within(frame).getByRole("textbox", { name: "Idea or theme" }) as HTMLTextAreaElement).disabled).toBe(false);
  });
});

describe("request preview: filled (RN-11, RN-53)", () => {
  it("shows an idea, colors, a power level and one generation effort chosen", () => {
    const frame = openState("filled");
    expect((within(frame).getByRole("textbox", { name: "Idea or theme" }) as HTMLTextAreaElement).value).not.toBe("");
    expect(checkedNames(control(frame, "Color identity"), "checkbox").length).toBeGreaterThan(0);
    expect(checkedNames(control(frame, "Power level"), "radio")).toHaveLength(1);
    expect(checkedNames(control(frame, "Generation effort"), "radio")).toHaveLength(1);
    expect(checkedNames(control(frame, "Card language"), "radio")).toHaveLength(1);
    expect(within(frame).queryByRole("alert")).toBeNull();
  });
});

describe("request preview: a refused field is named (RN-54)", () => {
  it("says which field was refused and marks it invalid", () => {
    const frame = openState("refused-field");
    const alert = within(frame).getByRole("alert");
    expect(alert.textContent).toContain("Idea or theme");
    expect(within(frame).getByRole("textbox", { name: "Idea or theme" }).getAttribute("aria-invalid")).toBe("true");
  });
});

describe("request preview: generating at each step (RN-55)", () => {
  it.each([
    ["generating-design-intent", /design intent/i],
    ["generating-search", /search for related cards/i],
    ["generating-draft", /draft/i],
    ["generating-validation", /validation/i],
    ["generating-revision", /revision/i],
    ["generating-art", /art/i],
  ])("%s marks the running step and locks the fields", (id, step) => {
    const frame = openState(id);
    const steps = within(frame).getByRole("list", { name: "Generation steps" });
    const current = within(steps)
      .getAllByRole("listitem")
      .filter((item) => item.getAttribute("aria-current") === "step");
    expect(current).toHaveLength(1);
    expect(current[0]?.textContent ?? "").toMatch(step);
    expect((within(frame).getByRole("textbox", { name: "Idea or theme" }) as HTMLTextAreaElement).disabled).toBe(true);
  });

  it("lists the six steps in the order of the spec when art was requested", () => {
    const frame = openState("generating-art");
    const items = within(within(frame).getByRole("list", { name: "Generation steps" })).getAllByRole("listitem");
    const patterns = [/design intent/i, /related cards/i, /draft/i, /validation/i, /revision/i, /art/i];
    expect(items).toHaveLength(6);
    patterns.forEach((pattern, index) => expect(items[index]?.textContent ?? "").toMatch(pattern));
  });
});

describe("request preview: one at a time (RN-50)", () => {
  it("refuses with a message that says one generation is already running", () => {
    const frame = openState("one-at-a-time");
    expect(within(frame).getByRole("alert").textContent).toMatch(/already running/i);
  });
});

describe("request preview: provider refusal (RN-56)", () => {
  it("shows a refusal with the option to edit the request, and keeps the idea as written", () => {
    const frame = openState("provider-refusal");
    expect(within(frame).getByRole("alert").textContent).toMatch(/refus/i);
    const edit =
      within(frame).queryByRole("button", { name: /edit the request/i }) ??
      within(frame).getByRole("link", { name: /edit the request/i });
    expect(edit).toBeTruthy();
    expect((within(frame).getByRole("textbox", { name: "Idea or theme" }) as HTMLTextAreaElement).value).not.toBe("");
    expect((within(frame).getByRole("textbox", { name: "Idea or theme" }) as HTMLTextAreaElement).disabled).toBe(false);
  });
});

describe("request preview: prefilled from a card (RN-58)", () => {
  it("fills idea, color identity, power level and effort, and sends nothing", () => {
    const frame = openState("prefilled");
    expect((within(frame).getByRole("textbox", { name: "Idea or theme" }) as HTMLTextAreaElement).value).not.toBe("");
    expect(checkedNames(control(frame, "Color identity"), "checkbox").length).toBeGreaterThan(0);
    expect(checkedNames(control(frame, "Power level"), "radio")).toHaveLength(1);
    expect(checkedNames(control(frame, "Generation effort"), "radio")).toHaveLength(1);
    expect(within(frame).queryByRole("list", { name: "Generation steps" })).toBeNull();
    expect(within(frame).queryByRole("alert")).toBeNull();
  });

  it("leaves the other fields at their defaults: advanced options closed, English", () => {
    const frame = openState("prefilled");
    expect(within(frame).getByRole("button", { name: "Advanced options" }).getAttribute("aria-expanded")).toBe("false");
    expect(checkedNames(control(frame, "Card language"), "radio")).toEqual(["English"]);
  });
});
