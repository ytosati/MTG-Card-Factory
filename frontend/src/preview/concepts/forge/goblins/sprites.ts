// Goblin crew (tasks.md T251): every frame of every action, drawn once on first use and kept.
import { ENGINEER } from "./engineer";
import { OPERATOR } from "./operator";
import { SAGE } from "./sage";
import { GOBLIN_PALETTE } from "./palette";
import type { GoblinAction, GoblinName, GoblinSpecs } from "./types";

export { GOBLIN_PALETTE };

const SPECS: Record<GoblinName, GoblinSpecs> = { engineer: ENGINEER, operator: OPERATOR, sage: SAGE };

/** The actions each goblin can play; any other action falls back to idle. */
export const ACTIONS_OF: Record<GoblinName, readonly GoblinAction[]> = {
  engineer: ["idle", "sit", "work", "cheer"],
  operator: ["idle", "pull", "cheer"],
  sage: ["idle", "cast", "nod"],
};

export interface GoblinAnimation {
  frames: ReadonlyArray<readonly string[]>;
  fps: number;
  /** The frame shown when motion is reduced. */
  still: number;
}

const cache = new Map<string, GoblinAnimation>();

export function goblinAnimation(who: GoblinName, action: GoblinAction): GoblinAnimation {
  const specs = SPECS[who];
  const name = ACTIONS_OF[who].includes(action) ? action : "idle";
  const key = `${who}:${name}`;
  const known = cache.get(key);
  if (known) return known;
  const spec = specs[name] ?? specs.idle;
  const animation: GoblinAnimation = spec
    ? { frames: Array.from({ length: spec.count }, (_, i) => spec.draw(i)), fps: spec.fps, still: spec.still }
    : { frames: [[]], fps: 1, still: 0 };
  cache.set(key, animation);
  return animation;
}
