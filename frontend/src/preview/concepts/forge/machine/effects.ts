// Moving parts of the forge scene: flames, steam, runes, sparks and machine parts (tasks.md T251).
import type { PixelRows } from "./pixelArt";

const TAU = Math.PI * 2;

/** Flame tongues: centre and half-width as a share of the width, relative height, sway speed. */
const TONGUES = [
  { c: 0.5, w: 0.3, h: 1, k: 1 },
  { c: 0.3, w: 0.2, h: 0.74, k: 2 },
  { c: 0.7, w: 0.2, h: 0.8, k: 1 },
  { c: 0.16, w: 0.14, h: 0.48, k: 3 },
  { c: 0.84, w: 0.14, h: 0.52, k: 2 },
  { c: 0.41, w: 0.11, h: 0.9, k: 3 },
  { c: 0.6, w: 0.11, h: 0.86, k: 2 },
] as const;

export const FLAME_FRAMES = 6;

/** A looping flame frame banded into the five ramp slots "1" (edge) to "5" (core). */
function flameFrame(width: number, height: number, frame: number): PixelRows {
  const ph = (frame / FLAME_FRAMES) * TAU;
  const tops = Array.from({ length: width }, (_, x) => {
    const u = x / (width - 1);
    let top = 0;
    TONGUES.forEach((t, i) => {
      const cx = t.c + 0.05 * Math.sin(ph * t.k + i * 1.3);
      const d = (u - cx) / t.w;
      const lift = 0.72 + 0.28 * Math.sin(ph * t.k + i * 2.1);
      top = Math.max(top, t.h * height * lift * (1 - d * d));
    });
    // A low bed of fire across the whole grate under the tongues.
    const edge = Math.abs(u - 0.5) * 2;
    top = Math.max(top, height * 0.28 * (1 - edge * edge * edge));
    return top;
  });
  const rows: string[] = [];
  for (let y = 0; y < height; y += 1) {
    const from = height - y;
    let row = "";
    for (let x = 0; x < width; x += 1) {
      const top = tops[x] ?? 0;
      if (from > top) {
        // A loose ember above the tallest tongue, on alternate frames.
        row += from - top < 3 && from - top > 2 && (x + frame) % 7 === 0 ? "2" : ".";
        continue;
      }
      const t = from / top;
      const centre = Math.abs(x - (width - 1) / 2) / (width / 2);
      const heat = (1 - t) * (1 - 0.55 * centre) + 0.12;
      row += heat > 0.78 ? "5" : heat > 0.6 ? "4" : heat > 0.4 ? "3" : heat > 0.22 ? "2" : "1";
    }
    rows.push(row);
  }
  return rows;
}

export const FLAME_SMALL: readonly PixelRows[] = Array.from({ length: FLAME_FRAMES }, (_, f) => flameFrame(27, 20, f));
export const FLAME_BIG: readonly PixelRows[] = Array.from({ length: FLAME_FRAMES }, (_, f) => flameFrame(27, 35, f));

/** The coal bed; its glow breathes by repainting the slots, not by new frames. */
export const EMBERS: PixelRows = [
  ".....12...1..121....21...1...",
  "..1232..121.2321..1232.1221..",
  ".123432123212343212343223321.",
  "12234332343223443234433234321",
];

export const STEAM: readonly PixelRows[] = [
  ["..MN..", ".MNNM.", "MNNMNm", ".mMm.."],
  ["...MNN...", "..MNNNM..", ".MNNMNNM.", "MNNNNNNMm", "mMNNNMMm.", ".mmMm...."],
  [
    "....MNNM.....",
    "..MNNNNNM.M..",
    ".MNNMNNNNMNM.",
    "MNNNNNMNNNNNM",
    "mMNNNNNNNMMm.",
    ".mMMMNNMMm...",
    "...mm..mm....",
  ],
  [
    ".....m..mM.....",
    "...mMM...Mm.m..",
    "..mM..mMm..MMm.",
    ".m..M..m..mM..m",
    "...m..m....m.m.",
    ".....m...m.....",
  ],
];

export const RUNES: readonly PixelRows[] = [
  ["..x..", ".xXx.", "xXYXx", ".xXx.", "..x.."],
  ["xXXx.", "...X.", ".xYx.", ".X...", ".xXXx"],
  ["x...x", ".X.X.", "..Y..", ".X.X.", "x...x"],
  [".xXx.", "x...x", "X.Y.X", "x...x", ".xXx."],
];

export const SPARKS: readonly PixelRows[] = [
  ["....W......", ".y..G...y..", "..G.W.G....", "Q.GWWWG.Q..", "..yGWGy...."],
  ["y.........Q", "...y...G...", ".G.......y.", "....Q.Q....", "G.........G"],
];

export const SNORE: PixelRows = ["UUUU", "..U.", ".U..", "UUUU"];

export const SPARKLE: readonly PixelRows[] = [[".X.", "XYX", ".X."], ["Y"]];

/** A gold piston head on its rod, rod raised `ext` pixels out of the housing. */
const pistonCache = new Map<number, PixelRows>();
export function piston(ext: number): PixelRows {
  const cached = pistonCache.get(ext);
  if (cached) return cached;
  const rows = [".kkkkkkk.", "kGggggDdk", "kDDDDDddk", ".kkkkkkk."];
  for (let i = 0; i < ext + 2; i += 1) rows.push("...kWIk..");
  pistonCache.set(ext, rows);
  return rows;
}

/** A pixel line from (0, 0) to (dx, dy), on a canvas offset so it never goes negative. */
function line(dx: number, dy: number, body: string, tip: string): { rows: PixelRows; ox: number; oy: number } {
  const ox = Math.min(0, dx) - 1;
  const oy = Math.min(0, dy) - 1;
  const w = Math.abs(dx) + 3;
  const h = Math.abs(dy) + 3;
  const grid = Array.from({ length: h }, () => Array.from({ length: w }, () => "."));
  const steps = Math.max(Math.abs(dx), Math.abs(dy), 1);
  for (let s = 0; s <= steps; s += 1) {
    const x = Math.round((dx * s) / steps) - ox;
    const y = Math.round((dy * s) / steps) - oy;
    const row = grid[y];
    if (row) row[x] = s === steps ? tip : body;
  }
  return { rows: grid.map((r) => r.join("")), ox, oy };
}

const needleCache = new Map<number, ReturnType<typeof line>>();
/** Gauge needle for a reading from 0 to 1, swept clockwise from lower left to lower right. */
export function needle(value: number): ReturnType<typeof line> {
  const step = Math.round(Math.min(1, Math.max(0, value)) * 12);
  const cached = needleCache.get(step);
  if (cached) return cached;
  const angle = Math.PI * 1.25 - (step / 12) * Math.PI * 1.5;
  const result = line(Math.round(Math.cos(angle) * 4), -Math.round(Math.sin(angle) * 4), "q", "q");
  needleCache.set(step, result);
  return result;
}

const leverCache = new Map<string, ReturnType<typeof line>>();
/** Lever arm from its pivot to the grip, ending in a red knob. */
export function lever(dx: number, dy: number): ReturnType<typeof line> {
  const key = `${dx},${dy}`;
  const cached = leverCache.get(key);
  if (cached) return cached;
  const result = line(dx, dy, "G", "Q");
  leverCache.set(key, result);
  return result;
}

/** A turning gear: `frame` advances it by a quarter of one tooth. */
function gearFrame(radius: number, teeth: number, frame: number): PixelRows {
  const size = radius * 2 + 3;
  const c = size / 2 - 0.5;
  const rows: string[] = [];
  for (let y = 0; y < size; y += 1) {
    let row = "";
    for (let x = 0; x < size; x += 1) {
      const dx = x - c;
      const dy = y - c;
      const r = Math.hypot(dx, dy);
      const a = Math.atan2(dy, dx) + (frame / 4) * (TAU / teeth);
      const tooth = Math.cos(a * teeth) > 0.1;
      const outer = tooth ? radius + 1 : radius - 1;
      if (r > outer + 0.5) row += ".";
      else if (r > outer - 0.6) row += "k";
      else if (r < 2.2) row += r < 1.2 ? "k" : "D";
      else if (r < radius * 0.42) row += "k";
      else if (r < radius * 0.55) row += dx + dy < 0 ? "G" : "D";
      else {
        const spoke = Math.abs(Math.sin(a * 2)) < 0.24 && r < radius - 2;
        const lit = dx + dy < -radius * 0.4 ? "G" : dx + dy > radius * 0.5 ? "D" : "g";
        row += r > radius - 3 ? lit : spoke ? lit : "k";
      }
    }
    rows.push(row);
  }
  return rows;
}

export const GEAR: readonly PixelRows[] = Array.from({ length: 4 }, (_, f) => gearFrame(11, 10, f));
const WHEEL_RING: PixelRows = [
  "...kkkkk...",
  "..kGgggDk..",
  ".kGk...kDk.",
  "kGk.....kDk",
  "kgk.....kDk",
  "kgk.....kDk",
  "kgk.....kDk",
  "kgk.....kDk",
  ".kgk...kDk.",
  "..kDDDDdk..",
  "...kkkkk...",
];

function wheelFrame(spokes: ReadonlyArray<readonly [number, number]>): PixelRows {
  const grid = WHEEL_RING.map((row) => row.split(""));
  for (const [x, y] of spokes) {
    const row = grid[y];
    if (row) row[x] = "g";
  }
  const hub = grid[5];
  if (hub) hub[5] = "W";
  return grid.map((row) => row.join(""));
}

/** Valve handwheel in two turns: spokes upright, then diagonal. */
export const WHEEL: readonly PixelRows[] = [
  wheelFrame([[5, 2], [5, 3], [5, 4], [5, 6], [5, 7], [5, 8], [3, 5], [4, 5], [6, 5], [7, 5]]),
  wheelFrame([[3, 3], [4, 4], [6, 6], [7, 7], [7, 3], [6, 4], [4, 6], [3, 7]]),
];

/** Rows from the top of the bellows rod to the bottom pleat; the rod top stays in its cylinder. */
export const BELLOWS_SPAN = 29;
const PLEATS = ["kbBnBBbbbbbbllk", ".kbBnBbbbbbllk.", "..klbbbbbbblk.."];

/** Accordion bellows of `height` pleat rows under a gold plate, driven by a rod from above. */
const bellowsCache = new Map<number, PixelRows>();
export function bellows(height: number): PixelRows {
  const cached = bellowsCache.get(height);
  if (cached) return cached;
  const rows: string[] = [];
  for (let i = 0; i < BELLOWS_SPAN - 3 - height; i += 1) rows.push("......kWk......");
  rows.push("kkkkkkkkkkkkkkk", "kGgggggggggDDdk", "kkkkkkkkkkkkkkk");
  for (let i = 0; i < height; i += 1) rows.push(PLEATS[i % 3] ?? "");
  bellowsCache.set(height, rows);
  return rows;
}
