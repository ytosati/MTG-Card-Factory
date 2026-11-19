// @vitest-environment jsdom
// Smoke test of concept D "Forge" (tasks.md T251): each state renders one level-1 heading, the Result shows
// the card art with its text alternative, and revealing a card offers the way to the result.
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { cardWithImage } from "../../fixtures";
import { forgeStates } from "./forge.states";

afterEach(cleanup);

function renderState(id: string) {
  const state = forgeStates.find((entry) => entry.id === id);
  return render(<>{state?.render()}</>);
}

describe("Forge concept (T251)", () => {
  it.each(forgeStates.map((state) => [state.id, state] as const))("%s has one level-1 heading", (_id, state) => {
    render(<>{state.render()}</>);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });

  it("shows the result card with its art", () => {
    renderState("result");
    expect(screen.getByAltText(cardWithImage.image?.alt ?? "")).toBeTruthy();
  });

  it("reveals the card face down in the forge", () => {
    renderState("ready-strong");
    fireEvent.click(screen.getAllByRole("button", { name: "Reveal card" })[0]!);
    expect(screen.getByRole("link", { name: "See result" })).toBeTruthy();
  });
});
