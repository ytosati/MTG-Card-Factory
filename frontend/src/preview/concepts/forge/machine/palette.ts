// Pixel palette of the forge scene and its flame ramps (tasks.md T251, concept D "Forge").

/** One character per pixel colour; "." is transparent. Flame slots "1"–"5" are filled per ramp. */
export const BASE_PALETTE: Readonly<Record<string, string>> = {
  // Ground and shadow, from Nocturne.
  k: "#08060c",
  z: "#110d18",
  K: "#1a1424",
  v: "#241a31",
  V: "#33263f",
  w: "#4a3a5c",
  // Polished gold metalwork.
  d: "#4a2f0c",
  D: "#8a5f16",
  g: "#e8b33a",
  G: "#f8d77c",
  W: "#fff6d8",
  // Dark iron.
  i: "#262230",
  I: "#433d52",
  J: "#6e6884",
  // Brick.
  h: "#22141c",
  H: "#3a2129",
  j: "#5a3138",
  // Goblin skin.
  a: "#1f3216",
  s: "#38591f",
  S: "#5e8a2c",
  L: "#9cc24e",
  // Leather and wood.
  l: "#2e1b12",
  b: "#56341f",
  B: "#83552f",
  n: "#b67d48",
  // Cloth.
  o: "#2c3858",
  O: "#4a6090",
  F: "#7a93c4",
  r: "#2a1d44",
  R: "#463172",
  P: "#6a51a8",
  // Arcane violet.
  x: "#8b3dff",
  X: "#c4a0ff",
  Y: "#f1e6ff",
  // Eyes, teeth, lenses, hair.
  e: "#efe8d6",
  y: "#ffd23f",
  c: "#2f7f8c",
  C: "#a8ecea",
  q: "#b8321f",
  Q: "#f36a2c",
  u: "#8a8398",
  U: "#dcd6e6",
  // Steam.
  m: "#7d7590",
  M: "#bdb5cf",
  N: "#ece8f4",
};

export type ManaLetter = "W" | "U" | "B" | "R" | "G";

/** A flame from its deepest shade to its white-hot core. */
export interface FlameRamp {
  deep: string;
  dark: string;
  mid: string;
  bright: string;
  core: string;
}

/** Flame palette per colour letter, plus colorless ("C"): a pale silver-violet arcane flame. */
export const FLAME_COLORS: Readonly<Record<ManaLetter | "C", FlameRamp>> = {
  W: { deep: "#6e4a17", dark: "#c98b26", mid: "#f3c94a", bright: "#fff0a6", core: "#fffdf2" },
  U: { deep: "#0f2766", dark: "#1d5bd0", mid: "#3a9cff", bright: "#9ddcff", core: "#ecfdff" },
  B: { deep: "#1d0a33", dark: "#4b1a86", mid: "#8b3dff", bright: "#c99bff", core: "#f6edff" },
  R: { deep: "#5a1007", dark: "#b62a17", mid: "#f2662a", bright: "#ffb347", core: "#fff2b3" },
  G: { deep: "#0d3a18", dark: "#1e8a39", mid: "#4cd05a", bright: "#b4f27a", core: "#f3ffd8" },
  C: { deep: "#2a2238", dark: "#6c6190", mid: "#b2a8d6", bright: "#e2dbf6", core: "#ffffff" },
};

/** Palette overrides that paint the flame slots "1"–"5" with one ramp. */
export function flamePalette(ramp: FlameRamp): Record<string, string> {
  return { "1": ramp.deep, "2": ramp.dark, "3": ramp.mid, "4": ramp.bright, "5": ramp.core };
}
