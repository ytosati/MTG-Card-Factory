// The engineer goblin (tasks.md T251): leather cap, round brass goggles over magnified eyes, long pointed ears,
// a big hooked nose and a toothy grin, after the maintainer's sketch.
import { arm, between, boot, joint, keys, paintTube, type P } from "./kit";
import { RAMPS } from "./palette";
import { cylinder, flat, lit, Raster, sphere } from "./raster";
import { CANVAS, FLOOR, SEAT_ROW, type GoblinSpecs } from "./types";

interface Face {
  blink: boolean;
  flash: boolean;
  /** Ear tips raised (+) or dropped (-), near and far. */
  earNear: number;
  earFar: number;
  mouth: "grin" | "open" | "grit";
  /** Pupils looking: -1 left, 0 ahead, 1 right, 2 down-right. */
  look: number;
}

const FACE: Face = { blink: false, flash: false, earNear: 0, earFar: 0, mouth: "grin", look: 1 };

function ear(r: Raster, cx: number, cy: number, side: 1 | -1, raise: number, near: boolean): void {
  const tipX = cx + side * 22;
  const tipY = cy - 10 - raise;
  const mask = r.poly([
    [cx + side * 5, cy - 4],
    [cx + side * 12, cy - 7 - raise * 0.4],
    [tipX, tipY],
    [cx + side * 15, cy - 2 - raise * 0.3],
    [cx + side * 10, cy + 1],
    [cx + side * 6, cy + 3],
  ]);
  r.paint(mask, lit(cylinder(cx + side * 6, cy - 1, tipX, tipY, 4), RAMPS.skin, near ? 0.05 : -0.2));
  if (near) {
    // The inside of the near ear, a darker groove running to the tip.
    const inner = r.poly([
      [cx + side * 7, cy - 2],
      [cx + side * 13, cy - 5 - raise * 0.4],
      [tipX - side * 3, tipY + 2],
      [cx + side * 13, cy - 2 - raise * 0.3],
      [cx + side * 8, cy + 1],
    ]);
    r.paint(inner, (x) => (Math.abs(x - (cx + side * 9)) < 2 ? "1" : "2"), "none");
  }
  // A nick in the rim.
  r.dot(cx + side * 16, cy - 7 - raise * 0.6, "0");
}

function lens(r: Raster, x: number, y: number, rx: number, ry: number, face: Face): void {
  r.paint(r.ellipse(x, y, rx + 1.3, ry + 1.3), lit(sphere(x, y, rx + 1.3, ry + 1.3), RAMPS.gold, 0.1));
  const glass = r.ellipse(x, y, rx, ry);
  if (face.flash) {
    r.paint(glass, (px, py) => ((px - py) % 4 === 0 || (px - py) % 4 === 1 ? "W" : "C"), "out");
    return;
  }
  r.paint(glass, lit(sphere(x + 1, y + 1, rx + 2, ry + 2), RAMPS.glass, -0.25), "out");
  const ex = Math.round(x - 1.5 + (face.look === -1 ? -1 : face.look >= 1 ? 1 : 0));
  const ey = Math.round(y - 1.5 + (face.look === 2 ? 1 : 0));
  if (face.blink) {
    // The lid fills the lens; its lashes make a dark crease.
    r.paint(glass, (_, py) => (py < y + 1 ? "3" : py < y + 2 ? "1" : "c"), "none");
    return;
  }
  // A goggle-magnified yellow eye, the pupil looking where he works.
  r.stamp([".tt.", "teet", "tepe", ".TT."], ex, ey);
  r.dot(ex + 1, ey + 1, "W");
  r.dot(Math.round(x - rx * 0.6), Math.round(y - ry * 0.6), "W");
}

/** The head, with the cranium centred on (cx, cy). */
function head(r: Raster, cx: number, cy: number, face: Face): void {
  ear(r, cx, cy, 1, face.earFar, false);
  ear(r, cx, cy, -1, face.earNear, true);
  const skull = r.ellipse(cx, cy, 9.5, 8.6).union(r.ellipse(cx + 0.5, cy + 6.5, 8.4, 6.8));
  r.paint(skull, lit(sphere(cx - 0.5, cy + 2, 10.5, 12), RAMPS.skin, 0.05));
  // Jowl crease and a wart on the cheek.
  r.line(cx - 7, cy + 5, cx - 6, cy + 8, "2");
  r.dot(cx - 5, cy + 4, "4");
  r.dot(cx - 5, cy + 5, "2");
  // Leather aviator cap down to the goggle strap, a seam and a rivet.
  const cap = r.ellipse(cx, cy - 0.5, 10.2, 9.2);
  cap.forEach((x, y) => y > cy - 3 && cap.remove(x, y));
  r.paint(cap, lit(sphere(cx - 1, cy, 10.5, 10), RAMPS.leather, 0.05));
  r.line(cx + 1, cy - 9, cx + 2, cy - 4, "b");
  r.dot(cx - 5, cy - 6, "G");
  // The goggle strap round the head.
  for (let x = cx - 10; x <= cx + 10; x += 1) {
    if (r.get(x, cy - 2) !== "" && r.get(x, cy - 2) !== "0") r.dot(x, cy - 2, "l");
    if (r.get(x, cy - 1) !== "" && r.get(x, cy - 1) !== "0") r.dot(x, cy - 1, "b");
  }
  lens(r, cx + 5.5, cy, 3, 3.6, face);
  lens(r, cx - 2.5, cy, 3.8, 3.8, face);
  // The bridge between the lenses.
  r.dot(cx + 1.5, cy - 1, "D");
  r.dot(cx + 2.5, cy - 1, "g");
  mouth(r, cx - 7, cy + 6, face.mouth);
  // The nose: long, bulbous, hooked down past the face and over the grin.
  paintTube(
    r,
    [
      [cx + 2.5, cy + 3],
      [cx + 6.5, cy + 5],
      [cx + 9.5, cy + 8.5],
    ],
    [1.7, 2.3, 3],
    RAMPS.skin,
    "ink",
    0.1,
  );
  r.dot(cx + 7, cy + 4, "5");
  r.dot(cx + 9, cy + 7, "4");
  r.dot(cx + 8, cy + 10, "1");
}

const GRIN = [
  "00.............00",
  ".0000000000000000",
  ".0tTtgtTttTtTtTt0",
  ".0mMmtmmMmmtmMm0.",
  "..0mtTmmmmmtTm0..",
  "...00000000000...",
];
const GRIT = [
  ".00000000000000.",
  "0tTtgtTttTtTtTt0",
  "0TtTtTtTtTtTtTt0",
  ".00000000000000.",
];
const OPEN = [
  "..000000000000..",
  ".0tTtgtTttTtTt0.",
  "0mmmMmmmmmmMmmm0",
  "0mmMMmmmmmmMMmm0",
  "0tmMMMMMMMMMMmt0",
  ".0tTt000000tTt0.",
  "..000......000..",
];

function mouth(r: Raster, x: number, y: number, kind: Face["mouth"]): void {
  r.stamp(kind === "open" ? OPEN : kind === "grit" ? GRIT : GRIN, x, y);
}

interface Body {
  /** Torso and head offset (negative up). */
  dy: number;
  dx: number;
  headDx: number;
  headDy: number;
  near: { elbow: P; hand: P; kind?: "fist" | "open" | "grip"; reach?: P };
  far: { elbow: P; hand: P; kind?: "fist" | "open" | "grip"; reach?: P };
  /** Feet: standing at x positions, sitting with dangling ankles, or tucked in the air. */
  feet: { kind: "stand"; near: number; far: number } | { kind: "sit"; near: P; far: P } | { kind: "air"; lift: number };
  face: Face;
  wrench?: { grip: P; angle: number };
}

const SHOULDER_NEAR: P = [26, 36];
const SHOULDER_FAR: P = [36, 36];

function legs(r: Raster, b: Body): void {
  const hipNear: P = [28 + b.dx, 47 + b.dy];
  const hipFar: P = [34 + b.dx, 47 + b.dy];
  const pants = "jJK";
  if (b.feet.kind === "sit") {
    const kneeNear: P = [hipNear[0] + 7, SEAT_ROW - 1];
    const kneeFar: P = [hipFar[0] + 6, SEAT_ROW - 1];
    paintTube(r, [hipFar, kneeFar, b.feet.far], [2.4, 2, 1.8], pants, "ink", -0.15);
    boot(r, b.feet.far, 1, Math.round(b.feet.far[1]) + 4);
    paintTube(r, [hipNear, kneeNear, b.feet.near], [2.4, 2, 1.8], pants);
    boot(r, b.feet.near, 1, Math.round(b.feet.near[1]) + 4);
    return;
  }
  const floor = b.feet.kind === "air" ? FLOOR - b.feet.lift : FLOOR;
  const ankleNear: P = b.feet.kind === "stand" ? [b.feet.near, floor - 4] : [hipNear[0] - 1, floor - 4];
  const ankleFar: P = b.feet.kind === "stand" ? [b.feet.far, floor - 4] : [hipFar[0] + 1, floor - 4];
  const kneeFar = joint(hipFar, ankleFar, 5.6, -1);
  paintTube(r, [hipFar, kneeFar, ankleFar], [2.3, 2, 1.8], pants, "ink", -0.15);
  boot(r, ankleFar, 1, floor);
  const kneeNear = joint(hipNear, ankleNear, 5.6, 1);
  paintTube(r, [hipNear, kneeNear, ankleNear], [2.3, 2, 1.8], pants);
  boot(r, ankleNear, 1, floor);
}

function torso(r: Raster, b: Body): void {
  const x = b.dx;
  const y = b.dy;
  const shirt = r.poly([
    [26 + x, 33 + y],
    [36 + x, 33 + y],
    [39 + x, 39 + y],
    [40 + x, 45 + y],
    [37 + x, 49 + y],
    [25 + x, 49 + y],
    [22 + x, 45 + y],
    [23 + x, 39 + y],
  ]);
  r.paint(shirt, lit(sphere(30 + x, 39 + y, 11, 11), RAMPS.rust));
  // Leather apron with a bib, a pocket holding a screwdriver, and a belt with a gold buckle.
  const apron = r.poly([
    [27 + x, 35 + y],
    [35 + x, 35 + y],
    [36 + x, 41 + y],
    [38 + x, 50 + y],
    [25 + x, 50 + y],
    [26 + x, 41 + y],
  ]);
  r.paint(apron, lit(sphere(30 + x, 41 + y, 10, 12), RAMPS.leather, 0.1));
  r.line(28 + x, 35 + y, 25 + x, 33 + y, "l");
  r.line(34 + x, 35 + y, 37 + x, 33 + y, "l");
  for (let i = 23; i <= 39; i += 1) {
    if (r.get(i + x, 43 + y) !== "" && r.get(i + x, 43 + y) !== "0") r.dot(i + x, 43 + y, "l");
  }
  r.stamp(["0gG0", "0dg0"], 29 + x, 42 + y);
  r.paint(r.rect(32 + x, 45 + y, 5, 4), lit(() => [0, 0.3, 0.9], RAMPS.leather, -0.1));
  r.dot(33 + x, 45 + y, "g");
  paintTube(r, [[34 + x, 44.5 + y], [35 + x, 40.5 + y]], [0.9, 0.9], RAMPS.iron, "ink", 0.2);
  r.dot(35 + x, 40 + y, "E");
}

function wrench(r: Raster, [gx, gy]: P, angle: number): void {
  const ux = Math.cos(angle);
  const uy = Math.sin(angle);
  const end: P = [gx + ux * 9, gy + uy * 9];
  paintTube(r, [[gx - ux * 2, gy - uy * 2], end], [1, 1.2], RAMPS.iron, "ink", 0.15);
  r.paint(r.ellipse(end[0], end[1], 2.6, 2.6), lit(sphere(end[0], end[1], 2.6, 2.6), RAMPS.iron, 0.1));
  // The jaw opening of the open-ended wrench.
  r.paint(r.capsule(end[0] + ux, end[1] + uy, end[0] + ux * 3, end[1] + uy * 3, 0.9), flat("."), "none");
}

function draw(b: Body): string[] {
  const r = new Raster(CANVAS, CANVAS);
  const sN: P = [SHOULDER_NEAR[0] + b.dx, SHOULDER_NEAR[1] + b.dy];
  const sF: P = [SHOULDER_FAR[0] + b.dx, SHOULDER_FAR[1] + b.dy];
  arm(r, sF, b.far.elbow, b.far.hand, { sleeve: RAMPS.rust, hand: b.far.kind, reach: b.far.reach, lift: -0.2 });
  // Sitting, the thighs come forward over the apron's hem; standing, the apron hangs over them.
  if (b.feet.kind !== "sit") legs(r, b);
  torso(r, b);
  if (b.feet.kind === "sit") legs(r, b);
  head(r, 31 + b.dx + b.headDx, 22 + b.dy + b.headDy, b.face);
  if (b.wrench) wrench(r, b.wrench.grip, b.wrench.angle);
  arm(r, sN, b.near.elbow, b.near.hand, { sleeve: RAMPS.rust, hand: b.near.kind, reach: b.near.reach });
  return r.toRows();
}

const REST: Body = {
  dy: 0,
  dx: 0,
  headDx: 0,
  headDy: 0,
  near: { elbow: [22, 43], hand: [21, 50], reach: [0, 1] },
  far: { elbow: [40, 43], hand: [41, 50], reach: [0, 1] },
  feet: { kind: "stand", near: 27, far: 36 },
  face: FACE,
};

function idle(f: number): string[] {
  // Two-second breath: the chest rises on the in-breath, the head follows a frame later.
  const breath = between(f, 3, 13) ? -1 : 0;
  const headBreath = between(f, 4, 14) ? -1 : 0;
  const hand = between(f, 5, 15) ? 1 : 0;
  return draw({
    ...REST,
    dy: breath,
    headDy: headBreath - breath,
    near: { elbow: [22, 43 + breath], hand: [21, 50 + hand], reach: [0, 1] },
    far: { elbow: [40, 43 + breath], hand: [41, 50 + hand], reach: [0, 1] },
    face: {
      ...FACE,
      blink: f === 18 || f === 19,
      earNear: f === 8 ? 3 : f === 9 ? 1 : f === 10 ? 2 : 0,
      look: between(f, 20, 24) ? 0 : 1,
    },
  });
}

function sit(f: number): string[] {
  // Feet swing out of step, slow at the ends of the swing.
  const swing = Math.sin((f / 16) * Math.PI * 2);
  const swing2 = Math.sin((f / 16) * Math.PI * 2 + Math.PI * 0.9);
  const bob = between(f, 4, 8) || between(f, 12, 16) ? 1 : 0;
  return draw({
    ...REST,
    dy: 1 + bob,
    headDy: bob ? 0 : 0,
    near: { elbow: [21, 45], hand: [23, 50], kind: "grip", reach: [0, 1] },
    far: { elbow: [41, 45], hand: [40, 50], kind: "grip", reach: [0, 1] },
    feet: { kind: "sit", near: [36 + swing * 2.5, 56], far: [41 + swing2 * 2.5, 55] },
    face: { ...FACE, blink: f === 10, look: 2, earNear: f === 2 ? 2 : 0, earFar: f === 3 ? 1 : 0 },
  });
}

function work(f: number): string[] {
  // The wrench turns a nut to his right: a quarter turn per cycle, a click with a goggle flash at the top.
  const turn = keys(f, [
    [0, 0.9],
    [3, -0.6],
    [4, -0.75],
    [8, 0.6],
    [12, 0.9],
  ]);
  const pivot: P = [50, 40];
  const grip: P = [pivot[0] - Math.cos(turn) * 9, pivot[1] - Math.sin(turn) * 9];
  const lean = f >= 1 && f <= 4 ? 1 : 0;
  return draw({
    ...REST,
    dx: lean,
    headDx: lean,
    headDy: f === 4 ? 1 : 0,
    near: { elbow: [30 + lean, 43], hand: grip, kind: "grip", reach: [1, 0] },
    far: { elbow: [41 + lean, 39], hand: [grip[0] + 2, grip[1] - 1], kind: "grip", reach: [1, 0] },
    feet: { kind: "stand", near: 25, far: 36 },
    face: { ...FACE, flash: f === 4 || f === 5, mouth: "grit", look: 1, earNear: f === 4 ? 2 : 0, earFar: f === 4 ? 2 : 0 },
    wrench: { grip, angle: turn },
  });
}

function cheer(f: number): string[] {
  // Anticipation crouch, launch, hang with fists up, fall, a squash on landing, recover.
  const lift = keys(f, [
    [0, 0],
    [2, -3],
    [3, 5],
    [5, 9],
    [7, 9],
    [9, 4],
    [10, 0],
    [11, -2],
    [13, 0],
  ]);
  const up = lift > 2;
  const crouch = lift < 0 ? -lift : 0;
  const dy = up ? -Math.round(lift) : Math.round(crouch);
  const armsUp = f >= 3 && f <= 9;
  return draw({
    ...REST,
    dy,
    headDy: crouch > 0 ? 1 : f === 4 ? 1 : f === 9 ? -1 : 0,
    near: armsUp
      ? { elbow: [19, 35 + dy], hand: [14, 28 + dy + (f % 2)], kind: "open", reach: [-0.4, -1] }
      : { elbow: [22, 42 + dy], hand: [19, 47 + dy], reach: [-0.3, 1] },
    far: armsUp
      ? { elbow: [43, 35 + dy], hand: [48, 28 + dy + ((f + 1) % 2)], kind: "open", reach: [0.4, -1] }
      : { elbow: [40, 42 + dy], hand: [43, 47 + dy], reach: [0.3, 1] },
    feet: up ? { kind: "air", lift: Math.round(lift) - 1 } : { kind: "stand", near: 26 - Math.round(crouch), far: 37 + Math.round(crouch) },
    face: {
      ...FACE,
      mouth: armsUp ? "open" : "grin",
      // The ears lag the jump: down on the way up, up on the way down.
      earNear: f === 3 || f === 4 ? -3 : f === 9 || f === 10 ? 3 : 0,
      earFar: f === 3 || f === 4 ? -3 : f === 9 || f === 10 ? 3 : 0,
      look: 0,
    },
  });
}

export const ENGINEER: GoblinSpecs = {
  idle: { count: 24, fps: 12, still: 0, draw: idle },
  sit: { count: 16, fps: 10, still: 0, draw: sit },
  work: { count: 12, fps: 12, still: 4, draw: work },
  cheer: { count: 14, fps: 12, still: 6, draw: cheer },
};
