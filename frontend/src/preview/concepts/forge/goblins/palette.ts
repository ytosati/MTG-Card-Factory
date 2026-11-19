// Goblin crew palette: one character per colour, grouped in dark-to-light ramps (tasks.md T251, concept D "Forge").

/** Ramps from shadow to highlight. The first character of each is also its inner line colour. */
export const RAMPS = {
  /** Olive goblin skin. */
  skin: "12345",
  /** Brown leather. */
  leather: "lbBn",
  /** Polished gold metalwork, #e8b33a at its heart. */
  gold: "dDgG",
  /** Dark iron of tools and levers. */
  iron: "jJKL",
  /** The engineer's rust-red shirt. */
  rust: "rRE",
  /** The operator's blue work cloth. */
  denim: "oOF",
  /** The sage's violet robe. */
  robe: "vVPQ",
  /** Grey-white hair, brow and beard. */
  hair: "hHiI",
  /** The operator's fiery mohawk. */
  mohawk: "qwuU",
  /** Lens glass. */
  glass: "cC",
  /** Arcane violet glow, #8b3dff at its heart. */
  arcane: "xXY",
  /** Mouth inside, from throat to gums. */
  mouth: "mM",
  /** Teeth and eye whites. */
  bone: "Tt",
} as const;

export type RampName = keyof typeof RAMPS;

/** Ink: the outline around every silhouette. */
export const INK = "0";

export const GOBLIN_PALETTE: Readonly<Record<string, string>> = {
  "0": "#0b0710",
  // Skin: deep olive to a sunlit yellow-green.
  "1": "#1a2611",
  "2": "#2f461b",
  "3": "#4f7228",
  "4": "#7f9f37",
  "5": "#c2d470",
  // Leather.
  l: "#24140c",
  b: "#4a2b17",
  B: "#7a4a26",
  n: "#b1773f",
  // Gold.
  d: "#4f330c",
  D: "#9a6a18",
  g: "#e8b33a",
  G: "#fde49a",
  // Iron.
  j: "#1e1b28",
  J: "#3f3a50",
  K: "#6f6987",
  L: "#b3adc8",
  // Rust shirt.
  r: "#3f1517",
  R: "#74281f",
  E: "#b0482b",
  // Denim.
  o: "#18213c",
  O: "#2e4272",
  F: "#5675b0",
  // Robe.
  v: "#1d1233",
  V: "#35205c",
  P: "#56368f",
  Q: "#8462c2",
  // Hair.
  h: "#38334a",
  H: "#6a6482",
  i: "#a7a1bb",
  I: "#e4dff0",
  // Mohawk.
  q: "#4a120b",
  w: "#8e2a12",
  u: "#d2501d",
  U: "#f6a03c",
  // Glass.
  c: "#1f5a66",
  C: "#76d2cb",
  // Arcane.
  x: "#8b3dff",
  X: "#c4a0ff",
  Y: "#f6efff",
  // Mouth, teeth, eyes.
  m: "#2a080e",
  M: "#7a1f26",
  T: "#a89a74",
  t: "#ece2c2",
  e: "#ffd84a",
  p: "#120a06",
  W: "#fffbe8",
};
