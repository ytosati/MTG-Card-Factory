// @vitest-environment jsdom
// Smoke test of the forge scene (tasks.md T251): every phase and step renders, and the card slot keeps 63:88.
import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { CARD_SLOT, FLAME_COLORS, ForgeScene, type ForgeStep } from "./ForgeScene";
import { SCENE_H, SCENE_W } from "./layout";

afterEach(cleanup);

const STEPS: ForgeStep[] = ["design", "search", "draft", "validation", "revision", "art"];

describe("ForgeScene (T251)", () => {
  it.each(["idle", "cooling"] as const)("renders while %s", (phase) => {
    const { container } = render(<ForgeScene phase={phase} colors={[]} />);
    expect(container.querySelector("svg")).toBeTruthy();
  });

  it.each(STEPS)("renders the %s step while working", (step) => {
    const { container } = render(<ForgeScene phase="working" step={step} colors={["U", "R"]} />);
    expect(container.querySelector("svg path")).toBeTruthy();
  });

  it("renders a still frame under reduced motion", () => {
    const { container } = render(<ForgeScene phase="working" step="draft" colors={["G"]} reducedMotion />);
    expect(container.querySelector("svg")).toBeTruthy();
  });

  it("exports a card slot near the 63:88 card ratio and a flame for each colour", () => {
    const ratio = (CARD_SLOT.width * SCENE_W) / (CARD_SLOT.height * SCENE_H);
    expect(Math.abs(ratio - 63 / 88)).toBeLessThan(0.01);
    expect(Object.keys(FLAME_COLORS).sort()).toEqual(["B", "C", "G", "R", "U", "W"]);
  });
});
