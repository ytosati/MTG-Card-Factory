// Concept C, "Gallery Wall" (tasks.md T251): the wall colors, one fixed and contrast-checked set per color identity.
import type { CSSProperties } from "react";

import type { ColorLetter } from "../../../api/types";

/** A wall: W, U, B, R and G for one color, gilt for three or more, stone for colorless, plum before a choice. */
export type WallKey = ColorLetter | "gilt" | "stone" | "plum";

export interface Wall {
  key: WallKey;
  name: string;
  /** The paint of the wall. */
  paint: string;
  /** Text on the wall. */
  ink: string;
  /** Captions and secondary text on the wall. */
  soft: string;
  /** The violet for marks and focus on this wall. */
  accent: string;
  /** The fill and text of the main action on this wall: violet in both cases. */
  actionFill: string;
  actionInk: string;
}

const LIGHT_VIOLET = "#cbb0f0";
const DEEP_VIOLET = "#5b2a86";

/** Light walls take the deep violet, dark walls a light violet, so the accent keeps its contrast. */
function onDark(fields: Omit<Wall, "accent" | "actionFill" | "actionInk">): Wall {
  return { ...fields, accent: LIGHT_VIOLET, actionFill: LIGHT_VIOLET, actionInk: "#22103a" };
}

export const WALLS: Record<WallKey, Wall> = {
  plum: onDark({ key: "plum", name: "Plum slate", paint: "#26232c", ink: "#f1ebe2", soft: "#c9bfd2" }),
  W: {
    key: "W",
    name: "Bone",
    paint: "#e6dcc6",
    ink: "#1e1a14",
    soft: "#4d4335",
    accent: DEEP_VIOLET,
    actionFill: DEEP_VIOLET,
    actionInk: "#ffffff",
  },
  U: onDark({ key: "U", name: "Harbor", paint: "#15334f", ink: "#f2ede2", soft: "#c3d1de" }),
  B: onDark({ key: "B", name: "Charcoal", paint: "#1c1b1f", ink: "#efe9dd", soft: "#bdb5a8" }),
  R: onDark({ key: "R", name: "Oxblood", paint: "#6b1f1a", ink: "#f8ede1", soft: "#ecc8ba" }),
  G: onDark({ key: "G", name: "Moss", paint: "#22392a", ink: "#eef0e1", soft: "#bfd0b6" }),
  gilt: {
    key: "gilt",
    name: "Gilt",
    paint: "#c39a3e",
    ink: "#1c1407",
    soft: "#3b2a0c",
    accent: "#3d1760",
    actionFill: "#3d1760",
    actionInk: "#ffffff",
  },
  stone: onDark({ key: "stone", name: "Stone", paint: "#55524c", ink: "#f7f4ee", soft: "#e6e0d5" }),
};

const ORDER: ColorLetter[] = ["W", "U", "B", "R", "G"];

/**
 * The walls of an identity: one field for one color, two (a split field) for two colors, gilt for three or more,
 * stone for colorless and plum when nothing is chosen yet.
 */
export function wallsOf(colors: readonly ColorLetter[], colorless = false): [Wall, Wall] {
  if (colorless) return [WALLS.stone, WALLS.stone];
  const sorted = ORDER.filter((letter) => colors.includes(letter));
  const [first, second] = sorted;
  if (first === undefined) return [WALLS.plum, WALLS.plum];
  if (sorted.length > 2) return [WALLS.gilt, WALLS.gilt];
  return [WALLS[first], WALLS[second ?? first]];
}

/** The colors named by mana symbols in a cost and in rules text, as a card's color identity. */
export function identityOf(...texts: (string | null)[]): ColorLetter[] {
  const found = new Set<ColorLetter>();
  for (const text of texts) {
    if (text === null) continue;
    for (const match of text.matchAll(/\{([^{}]+)\}/g)) {
      for (const letter of ORDER) if ((match[1] ?? "").toUpperCase().split("/").includes(letter)) found.add(letter);
    }
  }
  return ORDER.filter((letter) => found.has(letter));
}

export type WallStyle = CSSProperties & Record<`--${string}`, string>;

/** The custom properties a field of the page reads its colors from, with any further ones. */
export function wallStyle(wall: Wall, more: Record<`--${string}`, string> = {}): WallStyle {
  return {
    ...more,
    "--wall": wall.paint,
    "--ink": wall.ink,
    "--ink-soft": wall.soft,
    "--accent": wall.accent,
    "--action-fill": wall.actionFill,
    "--action-ink": wall.actionInk,
  };
}

function luminance(hex: string): number {
  const channels = [1, 3, 5].map((start) => parseInt(hex.slice(start, start + 2), 16) / 255);
  const [r = 0, g = 0, b = 0] = channels.map((value) =>
    value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4,
  );
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** The contrast ratio of two colors written as #rrggbb (WCAG 2). */
export function contrast(first: string, second: string): number {
  const [light, dark] = [luminance(first), luminance(second)].sort((a, b) => b - a) as [number, number];
  return (light + 0.05) / (dark + 0.05);
}
