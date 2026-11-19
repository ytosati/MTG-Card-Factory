// @vitest-environment jsdom
// Smoke test of concept A "Nocturne" (tasks.md T251): each state renders one level-1 heading, and the
// Result mockup shows the card art with its text alternative.
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { cardWithImage } from "../../fixtures";
import { nocturneStates } from "./nocturne.states";

afterEach(cleanup);

describe("Nocturne concept (T251)", () => {
  it.each(nocturneStates.map((state) => [state.id, state] as const))("%s has one level-1 heading", (_id, state) => {
    render(<>{state.render()}</>);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });

  it("shows the result card with its art", () => {
    const result = nocturneStates.find((state) => state.id === "result");
    render(<>{result?.render()}</>);
    expect(screen.getByAltText(cardWithImage.image?.alt ?? "")).toBeTruthy();
  });
});
