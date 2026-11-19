// @vitest-environment jsdom
// Smoke test of the pixel effect canvas (tasks.md T251): it mounts and unmounts cleanly, loop and one-shot alike.
import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { EMBERS, PICK_BURST } from "./effects";
import { PixelFx } from "./PixelFx";

afterEach(cleanup);

describe("PixelFx (T251)", () => {
  it("mounts a decorative canvas at the effect's pixel size and unmounts cleanly", () => {
    const { container, unmount, rerender } = render(<PixelFx effect={EMBERS.effect} options={EMBERS.options} width={96} height={128} scale={2} />);
    const canvas = container.querySelector("canvas");
    expect(canvas?.getAttribute("width")).toBe("96");
    expect(canvas?.getAttribute("aria-hidden")).toBe("true");
    const burst = PICK_BURST.R;
    rerender(<PixelFx effect={burst.effect} options={burst.options} width={burst.width} height={burst.height} mode="once" playKey={1} />);
    expect(() => unmount()).not.toThrow();
  });
});
