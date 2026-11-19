// @vitest-environment jsdom
// Smoke test of the goblin crew (tasks.md T251): every goblin renders every action as a decorative pixel SVG,
// frames are square and drawn in the palette, and reduced motion shows the still frame.
import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { toPaths } from "../machine/pixelArt";
import { Goblin } from "./Goblin";
import { GOBLIN_PALETTE } from "./palette";
import { ACTIONS_OF, goblinAnimation } from "./sprites";
import { CANVAS, type GoblinName } from "./types";

afterEach(cleanup);

const cases = (Object.keys(ACTIONS_OF) as GoblinName[]).flatMap((who) => ACTIONS_OF[who].map((action) => [who, action] as const));

describe("goblin crew (T251)", () => {
  it.each(cases)("%s %s renders a hidden pixel sprite", (who, action) => {
    const { container } = render(<Goblin who={who} action={action} scale={2} />);
    const svg = container.querySelector("svg");
    expect(svg?.getAttribute("aria-hidden")).toBe("true");
    expect(svg?.getAttribute("width")).toBe(String(CANVAS * 2));
    expect(container.querySelectorAll("path").length).toBeGreaterThan(5);
  });

  it.each(cases)("%s %s frames are square and use only palette colours", (who, action) => {
    const { frames, still } = goblinAnimation(who, action);
    expect(frames[still]).toBeDefined();
    for (const frame of frames) {
      expect(frame).toHaveLength(CANVAS);
      for (const row of frame) {
        expect(row).toHaveLength(CANVAS);
        for (const ch of row) if (ch !== ".") expect(GOBLIN_PALETTE[ch]).toBeDefined();
      }
    }
  });

  it("shows the still frame under a reduced-motion ancestor", () => {
    const { container } = render(
      <div data-reduced-motion="true">
        <Goblin who="operator" action="pull" />
      </div>,
    );
    const { frames, still } = goblinAnimation("operator", "pull");
    const drawn = [...container.querySelectorAll("path")].map((path) => path.getAttribute("d"));
    expect(drawn).toEqual(toPaths(frames[still] ?? []).map(([, d]) => d));
  });
});
