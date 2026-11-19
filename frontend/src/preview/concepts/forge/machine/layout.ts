// Geometry of the forge scene in logical pixels (tasks.md T251, concept D "Forge").

export const SCENE_W = 240;
export const SCENE_H = 144;
export const FLOOR_Y = 124;

/** The empty card slot at the centre of the scene, 45 × 63 pixels (about 63:88). */
export const SLOT = { x: 98, y: 34, w: 45, h: 63 } as const;

/** The furnace mouth: an arch whose flame sits on the grate at `bottom`. */
export const MOUTH = { cx: 44, halfWidth: 14, archTop: 80, springLine: 94, bottom: 116 } as const;

export const BOILER = { x: 206, w: 32, top: 34 } as const;
export const GAUGE = { cx: 222, cy: 58, r: 6 } as const;
export const LEVER_PIVOT = { x: 211, y: 116 } as const;
export const PISTONS = [
  { x: 205, top: 24 },
  { x: 230, top: 24 },
] as const;
export const GEAR_AXLE = { x: 176, y: 60 } as const;
export const BELLOWS = { x: 0, baseTop: 106 } as const;
export const VALVE = { x: 171, y: 0 } as const;

export const ACTORS = {
  sage: { x: 69, y: FLOOR_Y - 28 },
  engineer: { x: 158, y: FLOOR_Y - 28 },
  engineerDozing: { x: 158, y: FLOOR_Y - 30 },
  operator: { x: 182, y: FLOOR_Y - 28 },
} as const;

/** Where steam escapes: chimney top, boiler valve, pipe flange, cradle crown. */
export const VENTS = {
  chimney: { x: 38, y: -2 },
  boiler: { x: 219, y: 18 },
  flange: { x: 156, y: 2 },
  crown: { x: 112, y: 12 },
  sidePipe: { x: 76, y: 50 },
} as const;
