// @vitest-environment jsdom
// Smoke test of concept E "Starfield" (tasks.md T251): each state renders one level-1 heading, the footer notice
// (RN-69) and a decorative starfield; Colorless excludes the colors; a custom art version asks only for card and art.
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { starfieldStates } from "./starfield.states";

afterEach(cleanup);

function renderState(id: string) {
  const state = starfieldStates.find((entry) => entry.id === id);
  return render(<>{state?.render()}</>);
}

describe("Starfield concept (T251)", () => {
  it.each(starfieldStates.map((state) => [state.id, state] as const))("%s has one level-1 heading and a decorative sky", (_id, state) => {
    const { container } = render(<>{state.render()}</>);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("contentinfo").textContent).toMatch(/Fan content notice/);
    container.querySelectorAll("canvas").forEach((canvas) => expect(canvas.closest('[aria-hidden="true"]')).not.toBeNull());
  });

  it("clears the colors when Colorless is chosen", () => {
    renderState("request");
    const white = screen.getByRole("checkbox", { name: "White" }) as HTMLInputElement;
    expect(white.checked).toBe(true);
    fireEvent.click(screen.getByRole("checkbox", { name: "Colorless" }));
    expect(white.checked).toBe(false);
  });

  it("names the missing required fields instead of generating an empty request", () => {
    renderState("request-empty");
    fireEvent.click(screen.getByRole("button", { name: "Generate card" }));
    expect(screen.getByText(/Fill in before generating: Idea or theme, Color identity, Power level/)).toBeTruthy();
  });

  it("keeps the advanced options collapsed until asked", () => {
    renderState("request");
    const toggle = screen.getByRole("button", { name: "Advanced options" });
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByLabelText("Mana value")).toBeNull();
    fireEvent.click(toggle);
    expect(screen.getByLabelText("Mana value")).toBeTruthy();
  });

  it("asks a custom art version only for the card and its art", () => {
    renderState("request-custom-art");
    expect(screen.queryByRole("group", { name: "Color identity" })).toBeNull();
    expect(screen.getByLabelText("Printing")).toBeTruthy();
    expect(screen.queryByRole("radio", { name: "No art" })).toBeNull();
  });
});
