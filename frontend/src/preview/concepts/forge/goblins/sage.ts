// The arcane sage goblin (tasks.md T251): one huge bushy brow that hides both eyes, a long face, a long nose,
// drooping ears and a beard to the belly, in a violet robe with arcane light, after the maintainer's sketch.
import { between, keys, paintHand, paintTube, type P } from "./kit";
import { RAMPS } from "./palette";
import { cylinder, lit, Raster, sphere } from "./raster";
import { CANVAS, FLOOR, type GoblinSpecs } from "./types";

interface Face {
  /** Brow ends raised: near (left) and far (right), in pixels. */
  browNear: number;
  browFar: number;
  /** Beard tip swing, in pixels. */
  beard: number;
  /** Eyes glowing violet under the brow while he casts. */
  glow: boolean;
}

const FACE: Face = { browNear: 0, browFar: 0, beard: 0, glow: false };

function ear(r: Raster, cx: number, cy: number, side: 1 | -1, near: boolean): void {
  // Long ears that droop with age.
  const tip: P = [cx + side * 16, cy + 6];
  const mask = r.poly([
    [cx + side * 5, cy - 3],
    [cx + side * 11, cy - 1],
    [tip[0], tip[1]],
    [cx + side * 10, cy + 3],
    [cx + side * 5, cy + 3],
  ]);
  r.paint(mask, lit(cylinder(cx + side * 5, cy, tip[0], tip[1], 3.5), RAMPS.skin, near ? 0 : -0.25));
  if (near) r.line(cx + side * 7, cy, tip[0] - side * 3, tip[1] - 2, "2");
}

/** The brow: one bushy, lumpy shelf right across the face and past it, its fringe hanging over the eyes. */
function brow(r: Raster, cx: number, cy: number, face: Face): void {
  const mask = r.mask();
  // Tufts along a shallow arch; the outer ones lift when the brow twitches.
  const tufts: ReadonlyArray<readonly [number, number, number, number]> = [
    [-11, -3 - face.browNear, 2.8, 2.4],
    [-7.5, -2.6 - face.browNear * 0.6, 3.2, 3],
    [-3.5, -3, 3.2, 3.3],
    [0.5, -3.2, 3.2, 3.4],
    [4.5, -3, 3.2, 3.3],
    [8, -2.6 - face.browFar * 0.6, 3.2, 3],
    [11, -3.2 - face.browFar, 2.6, 2.4],
  ];
  for (const [dx, dy, rx, ry] of tufts) mask.union(r.ellipse(cx + dx, cy + dy, rx, ry));
  // The fringe: points hanging down where the eyes would be.
  for (const dx of [-6, -3, 0.5, 4, 7]) mask.union(r.poly([[cx + dx - 1.6, cy - 0.5], [cx + dx + 0.4, cy + 2.8], [cx + dx + 1.6, cy - 0.5]]));
  // Wild ends flicking out and up.
  mask.union(r.poly([[cx - 12, cy - 5 - face.browNear], [cx - 15.5, cy - 7 - face.browNear * 1.5], [cx - 12.5, cy - 2.5]]));
  mask.union(r.poly([[cx + 12, cy - 5.5 - face.browFar], [cx + 15, cy - 8 - face.browFar * 1.5], [cx + 12.5, cy - 3]]));
  r.paint(mask, lit(sphere(cx - 3, cy - 5, 15, 8), RAMPS.hair, 0.3));
  // Strands combed out from the middle.
  for (const i of [-9, -6, -3, 3, 6, 9]) r.line(cx + i, cy - 4, cx + i + Math.sign(i), cy - 2, "H");
  r.dot(cx + 0.5, cy - 4, "H");
  r.dot(cx + 0.5, cy - 3, "H");
}

/** The cowl's inside, framing the face down to the shoulders. */
function hoodBack(r: Raster, cx: number, cy: number): void {
  const back = r.poly([
    [cx - 9, cy - 9],
    [cx + 9, cy - 9],
    [cx + 11, cy + 3],
    [cx + 10, cy + 13],
    [cx - 11, cy + 13],
    [cx - 12, cy + 3],
  ]);
  r.paint(back, lit(sphere(cx + 2, cy + 2, 13, 16), RAMPS.robe, -0.35));
}

/** The cowl over the crown, its point flopping back, a gold trim on its rim. */
function hoodTop(r: Raster, cx: number, cy: number, flop: number): void {
  const top = r.ellipse(cx, cy - 4, 10, 10.5);
  top.forEach((x, y) => y > cy - 6 && top.remove(x, y));
  top.union(
    r.poly([
      [cx - 3, cy - 14],
      [cx - 10 - flop, cy - 17 + flop * 0.5],
      [cx - 13 - flop * 1.5, cy - 13 + flop],
      [cx - 8, cy - 9],
    ]),
  );
  r.paint(top, lit(sphere(cx - 2, cy - 6, 12, 11), RAMPS.robe, 0.15));
  for (let x = cx - 10; x <= cx + 10; x += 1) {
    if (top.has(x, cy - 6)) r.dot(x, cy - 6, x % 4 === 0 ? "G" : "g");
    if (top.has(x, cy - 7)) r.dot(x, cy - 7, "D");
  }
  // A gold star stitched on the cowl.
  r.stamp([".g.", "gGg", ".g."], cx + 2, cy - 12);
}

function head(r: Raster, cx: number, cy: number, face: Face): void {
  hoodBack(r, cx, cy);
  ear(r, cx, cy, 1, false);
  ear(r, cx, cy, -1, true);
  // A long face.
  const skull = r.ellipse(cx, cy - 3, 8.5, 10.5).union(r.ellipse(cx, cy + 6, 6.5, 7.5));
  r.paint(skull, lit(sphere(cx - 2, cy, 10.5, 16), RAMPS.skin, 0.2));
  hoodTop(r, cx, cy, face.beard);
  // The shadow the brow casts, and the eyes in it, lit only by magic.

  if (face.glow) {
    r.stamp(["xYx"], cx - 5, cy + 2);
    r.stamp(["xYx"], cx + 2, cy + 2);
  }
  // Sunken cheeks.
  r.dot(cx - 4, cy + 6, "2");
  r.dot(cx - 4, cy + 7, "2");
  beard(r, cx, cy, face.beard);
  // A long, thin nose drooping out from under the brow over the moustache.
  paintTube(
    r,
    [
      [cx + 0.5, cy + 1],
      [cx + 2, cy + 7],
      [cx + 2.5, cy + 10],
    ],
    [1.2, 1.5, 2.1],
    RAMPS.skin,
    "ink",
    0.15,
  );
  r.dot(cx + 1, cy + 6, "5");
  r.dot(cx + 1, cy + 11, "1");
  brow(r, cx, cy, face);
}

function beard(r: Raster, cx: number, cy: number, swing: number): void {
  // From the cheeks to a long point at the belly; the tip swings, the root stays.
  const tip: P = [cx + 1 + swing, cy + 32];
  const mask = r.poly([
    [cx - 6, cy + 8],
    [cx - 2, cy + 11],
    [cx + 4, cy + 11],
    [cx + 6, cy + 8],
    [cx + 6.5, cy + 13],
    [cx + 4.5 + swing * 0.4, cy + 21],
    [tip[0] + 1.5, tip[1] - 3],
    [tip[0], tip[1]],
    [tip[0] - 2, tip[1] - 4],
    [cx - 4 + swing * 0.4, cy + 20],
    [cx - 6.5, cy + 12],
  ]);
  r.paint(mask, lit(sphere(cx - 3, cy + 10, 10, 18), RAMPS.hair, 0.4));
  // Strands running down the beard.
  for (const dx of [-4, -1, 2, 4]) r.line(cx + dx, cy + 12, cx + dx * 0.5 + swing * 0.6, cy + 22, "H");
  // The moustache drooping either side of the nose into the beard.
  r.stamp(["..IIi....iII..", ".IiiHh..hHiiI.", "IiH........HiI", "iH..........Hi"], cx - 6, cy + 9);
}

interface Body {
  dy: number;
  headDy: number;
  face: Face;
  /** The hand holding the book (near) and the free hand (far). */
  book: { hand: P; open: boolean };
  free: { elbow: P; hand: P; glow: boolean; kind: "fist" | "open" | "point" };
  /** Runes rising, by age in frames. */
  runes: readonly number[];
}

const RUNES: ReadonlyArray<readonly string[]> = [
  [".X.", "XYX", ".X."],
  ["X.X", ".Y.", "X.X"],
  ["XX.", ".Y.", ".XX"],
  ["X..", "XYX", "..X"],
];

function rune(r: Raster, age: number, index: number, from: P): void {
  // Each rune rises, drifts and fades from white-hot to deep violet.
  const art = RUNES[index % RUNES.length] ?? [];
  const x = Math.round(from[0] - 1 + Math.sin(age * 0.9 + index) * 1.5);
  const y = Math.round(from[1] - 4 - age * 1.5);
  const fade = age < 4 ? null : age < 7 ? { Y: "X", X: "x" } : { Y: "x", X: "V" };
  const tinted = fade ? art.map((row) => row.replace(/[XY]/g, (ch) => (ch === "Y" ? fade.Y : fade.X))) : art;
  r.stamp(tinted, x, y);
}

function book(r: Raster, [hx, hy]: P, open: boolean): void {
  if (open) {
    // Two pages fanned open, scribbled with lines, in a leather binding.
    r.paint(r.poly([[hx - 7, hy - 3], [hx, hy - 1], [hx + 7, hy - 3], [hx + 7, hy + 2], [hx, hy + 4], [hx - 7, hy + 2]]), lit(() => [0, 0.6, 0.8], RAMPS.leather));
    r.paint(r.poly([[hx - 6, hy - 4], [hx, hy - 2], [hx + 6, hy - 4], [hx + 6, hy + 1], [hx, hy + 3], [hx - 6, hy + 1]]), (x) => (x === Math.round(hx) ? "T" : "t"), "out");
    for (const dy of [-2, 0]) {
      r.line(hx - 5, hy + dy - 1, hx - 2, hy + dy, "H");
      r.line(hx + 2, hy + dy, hx + 5, hy + dy - 1, "H");
    }
    return;
  }
  r.paint(r.rect(hx - 4, hy - 4, 8, 7), lit((x, y) => [(x - hx) / 8, (y - hy) / 8, 0.9], RAMPS.leather, 0.1));
  r.line(hx - 4, hy + 2, hx + 3, hy + 2, "t");
  r.stamp(["dg", "gG"], Math.round(hx) - 1, Math.round(hy) - 2);
}

function draw(b: Body): string[] {
  const r = new Raster(CANVAS, CANVAS);
  const y = b.dy;
  // The free (far) arm in its wide sleeve, behind the robe.
  const shoulderFar: P = [37, 35 + y];
  paintTube(r, [shoulderFar, b.free.elbow, b.free.hand], [2.6, 3, 3.4], RAMPS.robe, "ink", -0.15);
  paintHand(r, b.free.hand, b.free.kind, [b.free.hand[0] - b.free.elbow[0], b.free.hand[1] - b.free.elbow[1]], b.free.glow ? 0.3 : -0.1);
  if (b.free.glow) {
    const [hx, hy] = b.free.hand;
    // The hand burns violet: a ring of arcane light round it.
    for (const [dx, dy, ch] of [
      [-3, -1, "x"],
      [3, -2, "X"],
      [0, -4, "Y"],
      [-2, 3, "x"],
      [3, 2, "x"],
      [-4, -3, "X"],
    ] as const)
      r.dot(hx + dx, hy + dy, ch);
  }
  // A long robe to the floor, its gold-trimmed hem flaring.
  const robe = r.poly([
    [25, 32 + y],
    [37, 32 + y],
    [40, 42 + y],
    [43, FLOOR - 1],
    [19, FLOOR - 1],
    [22, 42 + y],
  ]);
  r.paint(robe, lit(sphere(29, 42, 14, 20), RAMPS.robe, 0.05));
  for (let x = 18; x <= 44; x += 1) {
    if (robe.has(x, FLOOR - 2)) r.dot(x, FLOOR - 2, x % 3 === 0 ? "D" : "g");
  }
  r.line(31, 36 + y, 33, FLOOR - 3, "v");
  // Boot tips peeking out under the hem.
  r.stamp(["0BBn0", ".0000"], 24, FLOOR - 1);
  r.stamp(["0bBB0", ".0000"], 34, FLOOR - 1);
  // A rope belt with a gold clasp.
  r.line(23, 44 + y, 40, 44 + y, "B");
  r.stamp(["dgd"], 30, 44 + y);
  r.stamp(["B", "b", "n"], 28, 45 + y);
  head(r, 31, 20 + y + b.headDy, b.face);
  // The near arm holds the book against the chest.
  const shoulderNear: P = [25, 35 + y];
  const elbowNear: P = [20, 42 + y];
  paintTube(r, [shoulderNear, elbowNear, [b.book.hand[0] - 2, b.book.hand[1] + 1]], [2.6, 3, 3.4], RAMPS.robe, "ink");
  book(r, b.book.hand, b.book.open);
  paintHand(r, [b.book.hand[0] - 4, b.book.hand[1] + 1], "grip", [1, 0]);
  b.runes.forEach((age, i) => age >= 0 && rune(r, age, i, [b.free.hand[0], b.free.hand[1] - 2]));
  return r.toRows();
}

const REST: Body = {
  dy: 0,
  headDy: 0,
  face: FACE,
  book: { hand: [24, 47], open: false },
  free: { elbow: [41, 43], hand: [41, 49], glow: false, kind: "fist" },
  runes: [],
};

function idle(f: number): string[] {
  // Slow breath, the brow ends twitching one after the other, the beard swaying a beat behind the body.
  const breath = between(f, 4, 16) ? -1 : 0;
  const swing = Math.round(Math.sin(((f - 2) / 24) * Math.PI * 2) * 1.4);
  return draw({
    ...REST,
    dy: breath,
    book: { hand: [24, 47 + breath], open: false },
    free: { elbow: [41, 43 + breath], hand: [41, 49], glow: false, kind: "fist" },
    face: {
      ...FACE,
      browNear: f === 6 || f === 7 ? 2 : f === 8 ? 1 : 0,
      browFar: f === 15 || f === 16 ? 2 : f === 17 ? 1 : 0,
      beard: swing,
    },
  });
}

function cast(f: number): string[] {
  // The book opens, the free hand rises and burns violet, runes rise and fade one after another.
  const raise = keys(f, [
    [0, 0],
    [3, 1],
    [15, 1],
  ]);
  const hand: P = [Math.round(41 + raise * 4), Math.round(49 - raise * 18 + (f % 4 === 0 ? 1 : 0))];
  const elbow: P = [Math.round(41 + raise * 5), Math.round(43 - raise * 6)];
  return draw({
    ...REST,
    dy: f >= 3 ? -1 : 0,
    book: { hand: [24, 46], open: f >= 1 },
    free: { elbow, hand, glow: f >= 3, kind: "open" },
    face: { ...FACE, glow: f >= 4, browNear: f >= 4 ? 1 : 0, browFar: f >= 4 ? 1 : 0, beard: f % 8 < 4 ? 1 : 0 },
    runes: f < 4 ? [] : [f - 4, f - 8, f - 12, (f + 4) % 16 - 4].map((age) => (age >= 0 && age < 10 ? age : -1)),
  });
}

function nod(f: number): string[] {
  // A slow approving nod: the head dips twice, the beard and brow follow a frame late.
  const dip = keys(f, [
    [0, 0],
    [2, 2],
    [4, 0],
    [6, 2],
    [8, 0],
    [11, 0],
  ]);
  const lagged = keys(f - 1, [
    [0, 0],
    [2, 2],
    [4, 0],
    [6, 2],
    [8, 0],
  ]);
  return draw({
    ...REST,
    headDy: Math.round(dip),
    face: { ...FACE, beard: Math.round(lagged) > 1 ? -1 : 0, browNear: f >= 9 ? 1 : 0, browFar: f >= 9 ? 1 : 0 },
  });
}

export const SAGE: GoblinSpecs = {
  idle: { count: 24, fps: 10, still: 0, draw: idle },
  cast: { count: 16, fps: 12, still: 8, draw: cast },
  nod: { count: 12, fps: 10, still: 0, draw: nod },
};
