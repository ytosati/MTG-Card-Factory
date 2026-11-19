// @vitest-environment jsdom
// Smoke test of concept B "Drafting Table" (tasks.md T251): each state renders one level-1 heading, and the
// Result mockup shows the card art with its text alternative and a callout for each part of the card.
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { draftingStates } from "./drafting.states";
import { reviewCard } from "./ResultMockup";

afterEach(cleanup);

function renderState(id: string): void {
  const state = draftingStates.find((each) => each.id === id);
  if (state === undefined) throw new Error(`No state ${id}`);
  render(<>{state.render()}</>);
}

describe("drafting table concept (T251)", () => {
  it.each(["concept", "request", "generating", "result"])("state %s has a single level-1 heading", (id) => {
    renderState(id);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });

  it("shows the card art with its alternative text and numbered callouts", () => {
    renderState("result");
    expect(screen.getByRole("img", { name: reviewCard.image?.alt ?? "" })).toBeTruthy();
    const callouts = screen.getByRole("list", { name: "Parts of the card" });
    expect(within(callouts).getAllByRole("listitem")).toHaveLength(6);
  });
});
