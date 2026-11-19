// @vitest-environment jsdom
// Concept D "Forge" (tasks.md T251): the mute setting persists, and sounds never throw without Web Audio.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// The test environment has no working storage, so a small one stands in for it.
const stored = new Map<string, string>();
beforeEach(() => {
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => stored.get(key) ?? null,
    setItem: (key: string, value: string) => void stored.set(key, value),
  });
});

afterEach(() => {
  stored.clear();
  vi.unstubAllGlobals();
  vi.resetModules();
});

describe("forge audio", () => {
  it("is not muted by default and keeps the choice in storage", async () => {
    const audio = await import("./forgeAudio");
    expect(audio.isMuted()).toBe(false);
    audio.setMuted(true);
    expect(window.localStorage.getItem("cardfactory.sound.muted")).toBe("true");
    vi.resetModules();
    const reloaded = await import("./forgeAudio");
    expect(reloaded.isMuted()).toBe(true);
  });

  it("plays nothing and throws nothing when Web Audio is missing", async () => {
    const audio = await import("./forgeAudio");
    expect("AudioContext" in window).toBe(false);
    expect(() => {
      (["W", "U", "B", "R", "G", "C"] as const).forEach(audio.playPick);
      audio.playLever();
      audio.playReveal("strong");
      audio.playStepTick();
    }).not.toThrow();
  });
});
