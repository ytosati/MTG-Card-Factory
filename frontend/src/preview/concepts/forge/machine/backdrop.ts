// The still parts of the forge scene, built once into one sprite (tasks.md T251, concept D "Forge").
import { BOILER, GEAR_AXLE, FLOOR_Y, GAUGE, LEVER_PIVOT, MOUTH, PISTONS, SCENE_H, SCENE_W, SLOT } from "./layout";
import { PixelCanvas, type PixelRows } from "./pixelArt";

/** Small deterministic hash, so brick and plank variation is the same on every render. */
function hash(a: number, b: number): number {
  let h = (a * 374761393 + b * 668265263) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) >>> 0) % 100;
}

/** Gold run shading for a band of rows, lit from above. */
const GOLD_BAND = "kGgDdk";

function wall(c: PixelCanvas): void {
  for (let y = 0; y < FLOOR_Y; y += 1) {
    const course = Math.floor(y / 6);
    const offset = course % 2 === 1 ? 8 : 0;
    for (let x = 0; x < SCENE_W; x += 1) {
      const bx = (x + offset) % 16;
      const brick = Math.floor((x + offset) / 16);
      if (y % 6 === 5 || bx === 15) c.set(x, y, "k");
      else if (y % 6 === 0 && bx < 12 && hash(course, brick) < 35) c.set(x, y, "K");
      else c.set(x, y, hash(course, brick) < 12 ? "K" : "z");
    }
  }
}

function floor(c: PixelCanvas): void {
  c.rect(0, FLOOR_Y, SCENE_W, 1, "w");
  c.rect(0, FLOOR_Y + 1, SCENE_W, 1, "V");
  for (let y = FLOOR_Y + 2; y < SCENE_H; y += 1) {
    const row = Math.floor((y - FLOOR_Y - 2) / 6);
    const offset = row % 2 === 1 ? 13 : 0;
    for (let x = 0; x < SCENE_W; x += 1) {
      const seam = (y - FLOOR_Y - 2) % 6 === 5 || (x + offset) % 26 === 0;
      const plank = hash(row + 50, Math.floor((x + offset) / 26));
      c.set(x, y, seam ? "z" : plank < 30 ? "K" : "v");
    }
  }
}

function furnace(c: PixelCanvas): void {
  // Chimney with two flanges, gold lit from the left.
  c.columns(37, 0, 30, "kDgGWGgggggDDdk");
  for (const fy of [5, 19]) {
    c.rect(35, fy, 19, 1, "k");
    c.rect(35, fy + 1, 19, 1, "G");
    c.rect(35, fy + 2, 19, 1, "D");
    c.rect(35, fy + 3, 19, 1, "k");
    c.set(35, fy + 1, "k");
    c.set(35, fy + 2, "k");
    c.set(53, fy + 1, "k");
    c.set(53, fy + 2, "k");
    for (let x = 38; x < 52; x += 4) c.set(x, fy + 1, "W");
  }
  // Iron hood narrowing up to the chimney.
  for (let y = 28; y <= 37; y += 1) {
    const t = (y - 28) / 9;
    const left = Math.round(34 - t * 16);
    const right = Math.round(54 + t * 16);
    c.rect(left, y, right - left + 1, 1, "I");
    c.set(left, y, "k");
    c.set(right, y, "k");
    c.set(left + 1, y, "J");
    c.set(right - 1, y, "i");
    c.set(right - 2, y, "i");
  }
  c.rect(34, 27, 21, 1, "k");
  c.rect(30, 32, 29, 1, "i");
  for (let x = 30; x < 59; x += 5) c.set(x, 31, "J");
  // Brick body.
  for (let y = 44; y < 118; y += 1) {
    const course = Math.floor((y - 44) / 5);
    const offset = course % 2 === 1 ? 4 : 0;
    for (let x = 18; x <= 70; x += 1) {
      const bx = (x - 18 + offset) % 9;
      let ch = (y - 44) % 5 === 4 || bx === 8 ? "h" : (y - 44) % 5 === 0 && bx < 6 ? "j" : "H";
      if (x >= 63 && ch !== "h") ch = ch === "j" ? "H" : "h";
      if (x <= 20 && ch === "H") ch = "j";
      c.set(x, y, ch);
    }
    c.set(17, y, "k");
    c.set(71, y, "k");
  }
  // Gold cornice and middle band with rivets.
  c.rows(14, 38, 61, GOLD_BAND);
  c.set(14, 39, "k");
  c.set(74, 39, "k");
  for (let x = 17; x < 73; x += 6) c.set(x, 40, "W");
  c.rows(17, 68, 55, "kGgDk");
  for (let x = 20; x < 70; x += 7) c.set(x, 70, "W");
  // Plaque with a violet gem between the bands.
  const plaque = [
    "...kkkkk...",
    "..kGgggDk..",
    ".kGgkkkgDk.",
    "kGgkxXxkgDk",
    "kggkXYXkgDk",
    ".kgkxxxkDk.",
    "..kgkkkDk..",
    "...kDDDk...",
    "....kkk....",
  ];
  c.stamp(plaque, MOUTH.cx - 5, 51);
  mouth(c);
  // Stone plinth.
  c.rows(14, 118, 61, "JIIiik");
  c.set(14, 118, "k");
  c.set(74, 118, "k");
  bellowsBase(c);
}

/** The bellows' wooden box, its nozzle into the furnace, and the cylinder that drives its rod. */
function bellowsBase(c: PixelCanvas): void {
  c.rows(0, 106, 16, "kGgDbbbbbbbblk");
  c.rect(0, 106, 1, 14, "k");
  c.rect(15, 106, 1, 14, "k");
  for (let y = 109; y < 118; y += 1) c.set(1, y, "B");
  c.stamp(["kGk", "kWk", "kDk"], 6, 111);
  c.rect(1, 120, 3, 4, "b");
  c.rect(12, 120, 3, 4, "b");
  c.rect(0, 120, 1, 4, "k");
  c.rect(4, 120, 1, 4, "k");
  c.rect(11, 120, 1, 4, "k");
  c.rect(15, 120, 1, 4, "k");
  c.rows(15, 109, 3, "kGgDk");
  // Rod cylinder bracketed to the furnace wall.
  c.columns(3, 60, 13, "kJJIIiik");
  c.rows(2, 58, 10, "kGgDk");
  c.rows(2, 72, 10, "kGgDk");
  c.rows(11, 64, 7, "kIik");
}

function insideMouth(x: number, y: number): boolean {
  if (y < MOUTH.archTop || y > MOUTH.bottom) return false;
  const dy = Math.max(0, MOUTH.springLine - y);
  const hw = Math.floor(Math.sqrt(MOUTH.halfWidth * MOUTH.halfWidth - dy * dy));
  return Math.abs(x - MOUTH.cx) <= hw;
}

/** The mouth opening as a sprite, used to clip the flame to the arch. */
export function mouthMask(): PixelRows {
  const c = new PixelCanvas(SCENE_W, MOUTH.bottom + 1);
  for (let y = MOUTH.archTop; y <= MOUTH.bottom; y += 1)
    for (let x = MOUTH.cx - MOUTH.halfWidth; x <= MOUTH.cx + MOUTH.halfWidth; x += 1)
      if (insideMouth(x, y)) c.set(x, y, "k");
  return c.toRows();
}

/** The arched furnace mouth: dark inside, ringed in gold, with a keystone and a grate. */
function mouth(c: PixelCanvas): void {
  const inside = insideMouth;
  const ring = ["d", "g", "D", "k"];
  for (let y = MOUTH.archTop - 5; y <= MOUTH.bottom; y += 1) {
    for (let x = MOUTH.cx - MOUTH.halfWidth - 5; x <= MOUTH.cx + MOUTH.halfWidth + 5; x += 1) {
      if (inside(x, y)) {
        c.set(x, y, "k");
        continue;
      }
      for (let d = 1; d <= ring.length; d += 1) {
        let near = false;
        for (let j = -d; j <= d && !near; j += 1)
          for (let i = -d; i <= d && !near; i += 1) if (inside(x + i, y + j)) near = true;
        if (near) {
          let ch = ring[d - 1] ?? "k";
          if (ch === "g" && x < MOUTH.cx - 2 && y < MOUTH.springLine + 6) ch = "G";
          if (ch === "g" && x > MOUTH.cx + 6) ch = "D";
          c.set(x, y, ch);
          break;
        }
      }
    }
  }
  c.stamp(["kkkkkkk", "kGgggDk", "kgxXxDk", "kgxxxDk", ".kgDDk.", "..kkk.."], MOUTH.cx - 3, MOUTH.archTop - 6);
  c.rect(MOUTH.cx - MOUTH.halfWidth, MOUTH.bottom + 1, MOUTH.halfWidth * 2 + 1, 1, "J");
  for (let x = MOUTH.cx - MOUTH.halfWidth; x <= MOUTH.cx + MOUTH.halfWidth; x += 3) c.set(x, MOUTH.bottom, "I");
}

function pipes(c: PixelCanvas): void {
  // Main pipe from the chimney across to the boiler, with flanged joints.
  c.rows(52, 10, 151, "kGggDdk");
  for (const fx of [84, 134, 158]) {
    c.rect(fx, 8, 4, 11, "k");
    c.rect(fx + 1, 9, 2, 9, "g");
    c.rect(fx + 1, 9, 1, 9, "G");
    c.set(fx + 1, 10, "W");
    c.set(fx + 1, 16, "W");
  }
  // Elbow down the boiler's side and into it.
  c.columns(196, 10, 44, "kGggDdk");
  c.rect(196, 10, 7, 1, "k");
  c.rect(202, 11, 1, 6, "k");
  c.rows(196, 47, 11, "kGggDdk");
  c.rect(196, 48, 1, 6, "k");
  c.rect(194, 30, 11, 4, "k");
  c.rect(195, 31, 9, 2, "g");
  c.rect(195, 31, 9, 1, "G");
  // Side pipe from the furnace to the cradle, with a joint.
  c.rows(72, 60, 21, "kGggDdk");
  c.rect(80, 58, 4, 11, "k");
  c.rect(81, 59, 2, 9, "g");
  c.rect(81, 59, 1, 9, "G");
  // Gear axle on the wall.
  c.stamp([".kkk.", "kIJIk", "kJiik", "kIiik", ".kkk."], GEAR_AXLE.x - 2, GEAR_AXLE.y - 2);
  // Drop pipe into the cradle crown.
  c.columns(117, 17, 3, "kGggDdk");
  // Valve stem rising from the pipe.
  c.rect(175, 5, 3, 5, "k");
  c.rect(176, 5, 1, 5, "D");
}

/** The gold cradle that holds the finished card, on an iron pedestal with a rune font. */
function cradle(c: PixelCanvas): void {
  // Crest with a violet gem.
  for (let y = 18; y <= 23; y += 1) {
    const hw = 4 + (y - 18) * 3;
    c.rect(120 - hw, y, hw * 2 + 1, 1, "g");
    c.set(120 - hw, y, "k");
    c.set(120 + hw, y, "k");
    c.set(120 - hw + 1, y, "G");
    c.set(120 + hw - 1, y, "D");
  }
  c.rect(116, 17, 9, 1, "k");
  c.stamp([".kkk.", "kxXxk", "kXYxk", "kxxxk", ".kkk."], 118, 18);
  c.rows(90, 24, 61, GOLD_BAND);
  c.set(90, 25, "k");
  c.set(150, 25, "k");
  for (let x = 93; x < 150; x += 6) c.set(x, 26, "W");
  // Columns either side of the slot, and the frame around it.
  for (const cx of [92, 143]) {
    c.columns(cx, 30, 67, "kgGgDk");
    c.rows(cx - 1, 30, 8, "kGDk");
    c.set(cx - 1, 31, "k");
    c.set(cx + 6, 31, "k");
    c.set(cx - 1, 32, "k");
    c.set(cx + 6, 32, "k");
  }
  c.rows(98, 30, 45, "kGgD");
  // The empty slot: dark, with a dashed edge and gold corner brackets.
  c.rect(SLOT.x, SLOT.y, SLOT.w, SLOT.h, "z");
  for (let i = 0; i < SLOT.w; i += 1) {
    if (i % 4 < 2) {
      c.set(SLOT.x + i, SLOT.y, "D");
      c.set(SLOT.x + i, SLOT.y + SLOT.h - 1, "D");
    }
  }
  for (let j = 0; j < SLOT.h; j += 1) {
    if (j % 4 < 2) {
      c.set(SLOT.x, SLOT.y + j, "D");
      c.set(SLOT.x + SLOT.w - 1, SLOT.y + j, "D");
    }
  }
  const right = SLOT.x + SLOT.w - 1;
  const bottom = SLOT.y + SLOT.h - 1;
  for (const [x, y, dx, dy] of [
    [SLOT.x, SLOT.y, 1, 1],
    [right, SLOT.y, -1, 1],
    [SLOT.x, bottom, 1, -1],
    [right, bottom, -1, -1],
  ] as const) {
    for (let i = 0; i < 6; i += 1) {
      c.set(x + i * dx, y, "G");
      c.set(x, y + i * dy, "G");
    }
  }
  // Sill and pedestal.
  c.rows(88, 97, 65, "kGgDk");
  for (let y = 102; y < FLOOR_Y; y += 1) {
    const grow = Math.floor((y - 102) / 6);
    const left = 92 - grow;
    const width = 57 + grow * 2;
    c.rect(left, y, width, 1, "I");
    c.set(left, y, "k");
    c.set(left + width - 1, y, "k");
    c.set(left + 1, y, "J");
    c.set(left + 2, y, "J");
    c.rect(left + width - 7, y, 6, 1, "i");
  }
  c.rows(88, 118, 65, "GgDk");
  c.set(88, 118, "k");
  c.set(152, 118, "k");
  // Rune font in the pedestal front.
  c.rect(108, 105, 25, 10, "k");
  c.rect(109, 106, 23, 8, "K");
  c.rect(109, 106, 23, 1, "D");
  c.rect(109, 113, 23, 1, "v");
  for (let x = 111; x < 131; x += 5) c.stamp(["kv", "vk"], x, 109);
}

function boiler(c: PixelCanvas): void {
  const shades = "kJJJIIIIIIIIIIIiiiiiiiiiiiiiiiik";
  // Dome between the two piston cylinders.
  const domeX = BOILER.x + 16;
  for (let y = 29; y < 40; y += 1) {
    const hw = Math.round(Math.sqrt(Math.max(0, 81 - (39 - y) * (39 - y))));
    for (let x = domeX - hw; x <= domeX + hw; x += 1) {
      const u = (x - domeX) / Math.max(hw, 1);
      c.set(x, y, u < -0.45 ? "J" : u < 0.35 ? "I" : "i");
    }
    c.set(domeX - hw, y, "k");
    c.set(domeX + hw, y, "k");
    if (y === 29) c.rect(domeX - hw, y, hw * 2 + 1, 1, "k");
  }
  c.set(domeX - 4, 32, "W");
  c.set(domeX - 5, 33, "J");
  c.columns(BOILER.x, 40, FLOOR_Y - 40, shades);
  c.rows(BOILER.x - 1, 38, BOILER.w + 2, "kGgDk");
  for (const by of [82, 106]) {
    c.rows(BOILER.x - 1, by, BOILER.w + 2, "kGgDk");
    for (let x = BOILER.x + 2; x < BOILER.x + BOILER.w; x += 5) c.set(x, by + 2, "W");
  }
  for (let y = 50; y < 104; y += 6) c.set(BOILER.x + 26, y, "J");
  // Pressure gauge.
  for (let y = GAUGE.cy - GAUGE.r - 1; y <= GAUGE.cy + GAUGE.r + 1; y += 1) {
    for (let x = GAUGE.cx - GAUGE.r - 1; x <= GAUGE.cx + GAUGE.r + 1; x += 1) {
      const d = Math.hypot(x - GAUGE.cx, y - GAUGE.cy);
      if (d <= GAUGE.r - 1.6) c.set(x, y, x + y > GAUGE.cx + GAUGE.cy + 3 ? "U" : "e");
      else if (d <= GAUGE.r + 0.4) c.set(x, y, x + y < GAUGE.cx + GAUGE.cy - 2 ? "G" : x + y > GAUGE.cx + GAUGE.cy + 4 ? "D" : "g");
      else if (d <= GAUGE.r + 1.4) c.set(x, y, "k");
    }
  }
  for (const [dx, dy] of [
    [-3, 2],
    [-3, -1],
    [-1, -3],
    [2, -3],
  ] as const)
    c.set(GAUGE.cx + dx, GAUGE.cy + dy, "u");
  c.set(GAUGE.cx + 3, GAUGE.cy - 1, "q");
  c.set(GAUGE.cx + 3, GAUGE.cy, "q");
  c.set(GAUGE.cx + 3, GAUGE.cy - 2, "q");
  // Piston cylinders on the shoulders.
  for (const p of PISTONS) {
    c.columns(p.x, p.top, 38 - p.top, "kJJIIIiik");
    c.rows(p.x - 1, p.top, 11, "kGgDk");
    c.rows(p.x - 1, p.top + 9, 11, "kgDk");
    c.set(p.x + 2, p.top + 6, "W");
  }
  // Safety whistle on the dome.
  c.stamp(["..kk..", ".kGDk.", ".kgDk.", ".kgDk.", "kGggDk", "kkkkkk"], BOILER.x + 13, 24);
  // Lever pivot.
  c.stamp(["kkkkk", "kGgDk", "kgWDk", "kDDdk", "kkkkk"], LEVER_PIVOT.x - 2, LEVER_PIVOT.y - 2);
}

const ANVIL: PixelRows = [
  "kkkkk.............",
  "kJJJJkkkkkkkkkkkk.",
  ".kkJJJJJJJJJJJJIIk",
  "...kkIIIIIIIIIIiik",
  "......kkIIIIIiikk.",
  "........kIIIik....",
  "........kiIIik....",
  ".......kJIIIiik...",
  "......kJIIIIIiik..",
  "......kkkkkkkkkk..",
];

let cached: PixelRows | undefined;

/** Builds the backdrop once; every render reuses the same rows (and so the same paths). */
export function backdrop(): PixelRows {
  if (cached) return cached;
  const c = new PixelCanvas(SCENE_W, SCENE_H);
  wall(c);
  floor(c);
  pipes(c);
  furnace(c);
  cradle(c);
  boiler(c);
  c.stamp(ANVIL, 146, FLOOR_Y - ANVIL.length);
  cached = c.toRows();
  return cached;
}
