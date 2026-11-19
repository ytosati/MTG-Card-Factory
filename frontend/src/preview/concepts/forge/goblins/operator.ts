// The operator goblin (tasks.md T251): a spiky mohawk, beady eyes under a heavy brow and a huge mouth full of
// jagged teeth, stocky in denim overalls, after the maintainer's sketch.
import { arm, between, boot, joint, keys, paintTube, type P } from "./kit";
import { RAMPS } from "./palette";
import { cylinder, lit, Raster, sphere } from "./raster";
import { CANVAS, FLOOR, type GoblinSpecs } from "./types";

interface Face {
  /** How wide the mouth opens: 0 a clenched grin, 1 open, 2 a roar. */
  open: number;
  blink: boolean;
  /** Mohawk spikes leaning back (+) or forward (-), for follow-through. */
  sway: number;
  sweat: boolean;
}

const FACE: Face = { open: 1, blink: false, sway: 0, sweat: false };

/** Mohawk spikes, back ones first: [base x offset, tip x offset, tip height, half base width, light]. */
const SPIKES: ReadonlyArray<readonly [number, number, number, number, number]> = [
  [-4, -12, 9, 3.2, -0.25],
  [4, 11, 10, 3.2, -0.2],
  [-2, -7, 15, 3.4, -0.05],
  [2, 5, 16, 3.4, 0],
  [0, -1, 19, 3.6, 0.15],
];

/** The crest: a fan of thick spikes running front to back over a shaved skull. */
function mohawk(r: Raster, cx: number, cy: number, sway: number): void {
  SPIKES.forEach(([base, tipX, height, half, light]) => {
    const bx = cx + base;
    const by = cy - 6;
    const tip: P = [cx + tipX - sway * (1 + height / 9), cy - 6 - height + Math.abs(sway) * 0.6];
    const mask = r.poly([
      [bx - half, by + 2],
      [tip[0], tip[1]],
      [bx + half, by + 2],
    ]);
    r.paint(mask, lit(cylinder(bx, by, tip[0], tip[1], half), RAMPS.mohawk, light));
    r.dot(tip[0], tip[1] + 1, "U");
  });
}

function ear(r: Raster, cx: number, cy: number, side: 1 | -1, near: boolean): void {
  const tip: P = [cx + side * 17, cy - 9];
  const mask = r.poly([
    [cx + side * 7, cy - 4],
    [tip[0], tip[1]],
    [cx + side * 12, cy + 1],
    [cx + side * 8, cy + 3],
  ]);
  r.paint(mask, lit(cylinder(cx + side * 7, cy, tip[0], tip[1], 3.5), RAMPS.skin, near ? 0.05 : -0.2));
  if (near) {
    r.paint(
      r.poly([
        [cx + side * 9, cy - 3],
        [tip[0] - side * 3, tip[1] + 2.5],
        [cx + side * 11, cy],
      ]),
      () => "2",
      "none",
    );
    // A gold ring through the lobe.
    r.stamp([".dg.", "d..G", ".dg."], Math.round(cx + side * 10 - 1.5), Math.round(cy + 2));
  }
}

const MOUTHS: Record<number, readonly string[]> = {
  0: [
    ".000000000000000.",
    "0tTtTtTtTtTtTtTt0",
    "0TtTtTtTtTtTtTtT0",
    ".000000000000000.",
  ],
  1: [
    "00000000000000000",
    "0tTt0tTt0tTt0tTt0",
    "0mtmmmtmmmtmmmtm0",
    "0mmmMmmmMmmmMmmm0",
    "0mmtmmmtMmmtmmtm0",
    "0tTt0tTt0tTt0tTt0",
    ".000000000000000.",
  ],
  2: [
    "00000000000000000",
    "0tTt0tTt0tTt0tTt0",
    "0mtmmmtmmmtmmmtm0",
    "0mmmMMmmmmmMMmmm0",
    "0mmMMMMMMMMMMmmm0",
    "0mmmMMmmmmmMMmmm0",
    "0mmtmmmtmmmtmmtm0",
    "0tTt0tTt0tTt0tTt0",
    ".000000000000000.",
  ],
};

function head(r: Raster, cx: number, cy: number, face: Face): void {
  mohawk(r, cx, cy, face.sway);
  ear(r, cx, cy, 1, false);
  ear(r, cx, cy, -1, true);
  // A low skull and a jaw wider than it: all mouth.
  const skull = r.ellipse(cx, cy - 1, 9.5, 7.5).union(r.ellipse(cx + 0.5, cy + 5, 11, 7.2));
  r.paint(skull, lit(sphere(cx - 3, cy - 1, 14, 13), RAMPS.skin, 0));
  // Shaved sides: stubble either side of the crest.
  for (const [x, y] of [
    [-6, -5],
    [-4, -6],
    [-7, -3],
    [5, -6],
    [7, -4],
  ] as const)
    r.dot(cx + x, cy + y, "2");
  // Angry brows driven down towards the nose, beady eyes in their shadow.
  paintTube(r, [[cx - 8, cy - 5], [cx - 2, cy - 2.5]], [1.4, 1.2], RAMPS.skin, "ink", 0.3);
  paintTube(r, [[cx + 1, cy - 2.5], [cx + 6, cy - 4.5]], [1.2, 1.3], RAMPS.skin, "ink", 0.2);
  for (const ex of [cx - 5, cx + 3]) {
    if (face.blink) {
      r.stamp(["000"], ex, cy - 1);
    } else {
      r.stamp(["0ee0", "0ep0", ".00."], ex - 1, cy - 1);
    }
  }
  // A squashed, upturned nose.
  r.paint(r.ellipse(cx + 1.5, cy + 1.5, 2.6, 1.8), lit(sphere(cx + 1.5, cy + 1, 3, 2.5), RAMPS.skin, 0.15));
  r.dot(cx + 1, cy + 2, "1");
  r.dot(cx + 3, cy + 2, "1");
  const mouth = MOUTHS[face.open] ?? MOUTHS[1] ?? [];
  r.stamp(mouth, cx - 8, cy + 4);
  if (face.sweat) r.stamp(["C", "C", "W"], cx - 10, cy - 3);
}

interface Body {
  dx: number;
  dy: number;
  /** Extra torso height lost when squashing (+) or gained stretching (-). */
  squash: number;
  near: { elbow: P; hand: P; kind?: "fist" | "open" | "grip"; reach?: P };
  far: { elbow: P; hand: P; kind?: "fist" | "open" | "grip"; reach?: P };
  feet: { near: number; far: number; lift: number };
  face: Face;
  /** The lever handle's grip point, when he is working it. */
  lever?: P;
}

const LEVER_PIVOT: P = [58, 57];

function lever(r: Raster, grip: P): void {
  const [gx, gy] = grip;
  paintTube(r, [LEVER_PIVOT, [gx + 1, gy]], [1.4, 1.1], RAMPS.iron, "ink", 0.1);
  r.paint(r.ellipse(LEVER_PIVOT[0], LEVER_PIVOT[1], 3, 3), lit(sphere(LEVER_PIVOT[0], LEVER_PIVOT[1], 3, 3), RAMPS.gold));
  r.dot(LEVER_PIVOT[0], LEVER_PIVOT[1], "d");
}

function leverKnob(r: Raster, [gx, gy]: P): void {
  // The red knob at the end of the handle, beyond his fists.
  r.paint(r.ellipse(gx - 3.5, gy, 2.3, 2.3), lit(sphere(gx - 3.5, gy, 2.3, 2.3), "rRE", 0.2));
}

function draw(b: Body): string[] {
  const r = new Raster(CANVAS, CANVAS);
  const x = b.dx;
  const y = b.dy;
  const floor = FLOOR - b.feet.lift;
  if (b.lever) lever(r, b.lever);
  arm(r, [38 + x, 36 + y + b.squash], b.far.elbow, b.far.hand, { hand: b.far.kind, reach: b.far.reach, lift: -0.2, thick: 1.35 });
  // Legs: short, bowed, planted wide.
  const hipNear: P = [27 + x, 49 + y];
  const hipFar: P = [35 + x, 49 + y];
  const ankleNear: P = [b.feet.near, floor - 4];
  const ankleFar: P = [b.feet.far, floor - 4];
  paintTube(r, [hipFar, joint(hipFar, ankleFar, 4.6, -1), ankleFar], [2.6, 2.2, 2], RAMPS.denim, "ink", -0.15);
  boot(r, ankleFar, 1, floor, "jJK");
  paintTube(r, [hipNear, joint(hipNear, ankleNear, 4.6, 1), ankleNear], [2.6, 2.2, 2], RAMPS.denim);
  boot(r, ankleNear, -1, floor, "jJK");
  // A barrel chest, bare green shoulders above a denim bib with straps and gold buttons.
  const top = 34 + y + b.squash;
  const chest = r.poly([
    [23 + x, top],
    [39 + x, top],
    [42 + x, top + 6],
    [40 + x, 50 + y],
    [22 + x, 50 + y],
    [20 + x, top + 6],
  ]);
  r.paint(chest, lit(sphere(30 + x, top + 6, 12, 11), RAMPS.skin, 0.05));
  const bib = r.poly([
    [25 + x, top + 5],
    [37 + x, top + 5],
    [38 + x, 51 + y],
    [24 + x, 51 + y],
  ]);
  r.paint(bib, lit(sphere(30 + x, top + 8, 12, 12), RAMPS.denim, 0.1));
  r.line(25 + x, top + 5, 24 + x, top, "o");
  r.line(37 + x, top + 5, 38 + x, top, "o");
  r.stamp(["g", "d"], 26 + x, top + 5);
  r.stamp(["g", "d"], 36 + x, top + 5);
  // A patched pocket and a rag hanging from it.
  r.paint(r.rect(28 + x, top + 8, 6, 4), lit(() => [0, 0.2, 1], RAMPS.denim, -0.15));
  r.line(28 + x, top + 8, 33 + x, top + 8, "F");
  r.stamp(["EE", "RE", "R.", "r."], 33 + x, top + 10);
  head(r, 31 + x, 22 + y + b.squash, b.face);
  arm(r, [23 + x, 36 + y + b.squash], b.near.elbow, b.near.hand, { hand: b.near.kind, reach: b.near.reach, thick: 1.35 });
  if (b.lever) leverKnob(r, b.lever);
  return r.toRows();
}

const REST: Body = {
  dx: 0,
  dy: 0,
  squash: 0,
  near: { elbow: [19, 43], hand: [19, 49], reach: [0, 1] },
  far: { elbow: [42, 43], hand: [43, 49], reach: [0, 1] },
  feet: { near: 25, far: 37, lift: 0 },
  face: FACE,
};

function idle(f: number): string[] {
  // A restless bounce on the knees, the crest flicking a beat behind, the jaw working.
  const down = between(f, 0, 2) || between(f, 8, 10) ? 1 : 0;
  const sway = f === 2 || f === 10 ? 1 : f === 3 || f === 11 ? -1 : 0;
  return draw({
    ...REST,
    dy: down,
    near: { elbow: [19, 43 + down], hand: [19, 49 + down], reach: [0, 1] },
    far: { elbow: [42, 43 + down], hand: [43, 49 + down], reach: [0, 1] },
    face: { ...FACE, open: between(f, 4, 8) ? 0 : 1, sway, blink: f === 13 },
  });
}

function pull(f: number): string[] {
  // Reach up, rise on the toes (wind-up), haul down in two frames, hold straining, let it ride back up.
  const gy = keys(f, [
    [0, 34],
    [3, 31],
    [5, 30],
    [6, 39],
    [7, 47],
    [13, 47],
    [16, 41],
    [18, 34],
  ]);
  const gx = keys(f, [
    [0, 44],
    [5, 45],
    [7, 47],
    [13, 47],
    [18, 44],
  ]);
  const windUp = between(f, 3, 6);
  const hold = between(f, 7, 14);
  const shake = hold && f % 2 === 0 ? 1 : 0;
  const dy = windUp ? -2 : hold ? 3 : f === 6 ? 1 : 0;
  const grip: P = [gx + shake, gy];
  return draw({
    ...REST,
    dx: hold ? 2 : 0,
    dy,
    squash: hold ? 1 : 0,
    near: { elbow: [26, Math.min(48, gy + 9) + dy], hand: [grip[0] - 1, grip[1] + 1], kind: "grip", reach: [1, 0] },
    far: { elbow: [44, (36 + gy) / 2 + 3 + dy], hand: [grip[0] + 2, grip[1]], kind: "grip", reach: [1, 0] },
    feet: { near: 24, far: 37, lift: windUp ? 1 : 0 },
    face: { ...FACE, open: hold ? 0 : f === 6 ? 2 : 1, sway: f === 6 ? -1 : f === 7 ? 1 : 0, sweat: hold && f >= 10 },
    lever: grip,
  });
}

function cheer(f: number): string[] {
  // Three fist pumps with a hop, roaring.
  const beat = f % 6;
  const upFist = beat < 3;
  const hop = beat === 1 || beat === 2 ? 2 : 0;
  return draw({
    ...REST,
    dy: -hop,
    near: upFist
      ? { elbow: [17, 31 - hop], hand: [18, 23 - hop], reach: [0, -1] }
      : { elbow: [16, 36 - hop], hand: [17, 29 - hop], reach: [0, -1] },
    far: { elbow: [44, 42 - hop], hand: [42, 37 - hop], reach: [-1, 0] },
    feet: { near: 25, far: 37, lift: hop },
    face: { ...FACE, open: 2, sway: beat === 1 ? 1 : beat === 3 ? -1 : 0 },
  });
}

export const OPERATOR: GoblinSpecs = {
  idle: { count: 16, fps: 10, still: 4, draw: idle },
  pull: { count: 18, fps: 12, still: 9, draw: pull },
  cheer: { count: 12, fps: 12, still: 1, draw: cheer },
};
