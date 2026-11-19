// @vitest-environment jsdom
// Smoke test of concept C, "Gallery Wall" (tasks.md T251): every state renders with one level-1 heading, and the
// fixed wall palette keeps its text contrast.
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { galleryStates } from "./gallery.states";
import { WALLS, contrast } from "./palette";

afterEach(cleanup);

describe("Gallery Wall concept (T251)", () => {
  it("has the request, result and concept states", () => {
    expect(galleryStates.map((state) => state.id)).toEqual(expect.arrayContaining(["request", "result", "concept"]));
  });

  it.each(galleryStates.map((state) => [state.id, state] as const))(
    "renders %s with one level-1 heading",
    (_, state) => {
      render(<>{state.render()}</>);
      expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    },
  );

  it("keeps body text contrast on every wall", () => {
    for (const wall of Object.values(WALLS)) {
      expect(contrast(wall.paint, wall.ink)).toBeGreaterThanOrEqual(4.5);
      expect(contrast(wall.paint, wall.soft)).toBeGreaterThanOrEqual(4.5);
      expect(contrast(wall.actionFill, wall.actionInk)).toBeGreaterThanOrEqual(4.5);
    }
  });
});
