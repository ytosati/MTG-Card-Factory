// Goblin crew (tasks.md T251): names, actions and the shape of an animation.

export type GoblinName = "engineer" | "operator" | "sage";
export type GoblinAction = "idle" | "sit" | "work" | "pull" | "cast" | "cheer" | "nod";

/** Every goblin is drawn on a square canvas of this many logical pixels, feet on FLOOR. */
export const CANVAS = 64;
export const FLOOR = 61;
/** In the "sit" action, the row of the ledge top the engineer sits on. */
export const SEAT_ROW = 50;

/** How one action is drawn: its frame count, its speed and the frame shown when motion is reduced. */
export interface ActionSpec {
  count: number;
  fps: number;
  still: number;
  draw: (frame: number) => string[];
}

export type GoblinSpecs = Partial<Record<GoblinAction, ActionSpec>>;
