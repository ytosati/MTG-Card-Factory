// Goblin crew (tasks.md T251): the parts the three goblins share, limbs, hands and boots, drawn on a Raster.
import { RAMPS } from "./palette";
import { cylinder, lit, type Line, type Mask, type Normal, type Raster } from "./raster";

export type P = readonly [number, number];

/** A chain of round segments through `pts`, lit as one tube: arms, legs, locks of hair. */
export function tube(r: Raster, pts: readonly P[], radii: readonly number[]): { mask: Mask; normal: Normal } {
  const mask = r.mask();
  const segments: Array<{ a: P; b: P; normal: Normal }> = [];
  for (let i = 0; i + 1 < pts.length; i += 1) {
    const a = pts[i] ?? [0, 0];
    const b = pts[i + 1] ?? a;
    const ra = radii[i] ?? radii[radii.length - 1] ?? 1;
    const rb = radii[i + 1] ?? ra;
    mask.union(r.capsule(a[0], a[1], b[0], b[1], ra, rb));
    segments.push({ a, b, normal: cylinder(a[0], a[1], b[0], b[1], Math.max(ra, rb)) });
  }
  const normal: Normal = (x, y) => {
    let best = segments[0];
    let bestD = Infinity;
    for (const segment of segments) {
      const [ax, ay] = segment.a;
      const [bx, by] = segment.b;
      const dx = bx - ax;
      const dy = by - ay;
      const t = Math.max(0, Math.min(1, ((x + 0.5 - ax) * dx + (y + 0.5 - ay) * dy) / (dx * dx + dy * dy || 1)));
      const d = Math.hypot(x + 0.5 - ax - dx * t, y + 0.5 - ay - dy * t);
      if (d < bestD) {
        bestD = d;
        best = segment;
      }
    }
    return best ? best.normal(x, y) : [0, 0, 1];
  };
  return { mask, normal };
}

export function paintTube(r: Raster, pts: readonly P[], radii: readonly number[], ramp: string, line: Line = "ink", lift = 0): void {
  const { mask, normal } = tube(r, pts, radii);
  r.paint(mask, lit(normal, ramp, lift), line);
}

export type Hand = "fist" | "open" | "grip" | "point";

/**
 * A skinny goblin arm from shoulder to hand, with an optional sleeve on the upper arm and a three-fingered hand.
 * `reach` is the direction the fingers point, as a unit-ish vector.
 */
export function arm(
  r: Raster,
  shoulder: P,
  elbow: P,
  hand: P,
  options: { sleeve?: string; hand?: Hand; reach?: P; lift?: number; thick?: number } = {},
): void {
  const skin = RAMPS.skin;
  const lift = options.lift ?? 0;
  const k = options.thick ?? 1;
  paintTube(r, [shoulder, elbow, hand], [1.9 * k, 1.5 * k, 1.6 * k], skin, "ink", lift);
  if (options.sleeve) {
    const mid: P = [shoulder[0] + (elbow[0] - shoulder[0]) * 0.7, shoulder[1] + (elbow[1] - shoulder[1]) * 0.7];
    paintTube(r, [shoulder, mid], [2.2 * k, 1.9 * k], options.sleeve, "ink", lift);
  }
  paintHand(r, hand, options.hand ?? "fist", options.reach ?? [0, 1], lift, k);
}

/** A knobbly three-fingered hand with dark claws. */
export function paintHand(r: Raster, [hx, hy]: P, kind: Hand, [rx, ry]: P, lift = 0, size = 1): void {
  const skin = RAMPS.skin;
  const length = Math.hypot(rx, ry) || 1;
  const ux = rx / length;
  const uy = ry / length;
  if (kind === "open" || kind === "point") {
    const spread = kind === "open" ? [-0.75, 0, 0.75] : [0];
    for (const angle of spread) {
      const c = Math.cos(angle);
      const s = Math.sin(angle);
      const fx = ux * c - uy * s;
      const fy = ux * s + uy * c;
      const tip: P = [hx + fx * 3.6, hy + fy * 3.6];
      paintTube(r, [[hx + fx, hy + fy], tip], [1, 0.75], skin, "out", lift);
      r.dot(tip[0] + fx * 0.6, tip[1] + fy * 0.6, "T");
    }
  }
  r.paint(r.ellipse(hx, hy, 2.1 * size, 2 * size), lit(cylinder(hx - 2, hy - 2, hx + 2, hy + 2, 2.2 * size), skin, lift + 0.1), "ink");
  if (kind === "fist" || kind === "grip") {
    // Knuckles catch the light along the side the fingers curl towards.
    r.dot(hx + ux * 1.4 - uy, hy + uy * 1.4 + ux * 0.4, "4");
    r.dot(hx + ux * 1.4, hy + uy * 1.4, "2");
  }
}

/** A goblin boot: pointed, the toe curling up, facing `dir` (1 right, -1 left). */
export function boot(r: Raster, [ax, ay]: P, dir: 1 | -1, floor: number, ramp: string = RAMPS.leather): void {
  const toe = ax + dir * 7;
  const mask = r.poly([
    [ax - dir * 2.6, ay - 1],
    [ax + dir * 2, ay - 1],
    [ax + dir * 4.5, floor - 2.6],
    [toe - dir * 0.5, floor - 4],
    [toe + dir * 0.5, floor - 6],
    [toe + dir * 1.3, floor - 5],
    [toe + dir * 0.8, floor - 2],
    [ax + dir * 4, floor + 0.4],
    [ax - dir * 3, floor + 0.4],
  ]);
  r.paint(mask, lit((x, y) => [((x + 0.5 - ax) / 6) * dir * 0.3, (y + 0.5 - (floor - 3)) / 4, 0.8], ramp));
  // Sole and a strap with a gold buckle.
  for (let x = Math.min(ax - dir * 3, ax + dir * 4); x <= Math.max(ax - dir * 3, ax + dir * 4); x += 1) {
    if (mask.has(Math.round(x), floor)) r.dot(x, floor, "l");
  }
  r.dot(ax + dir * 0.5, ay + 1, "d");
  r.dot(ax + dir * 1.5, ay + 1, "g");
}

/** Whether a frame index falls in [from, to). */
export function between(frame: number, from: number, to: number): boolean {
  return frame >= from && frame < to;
}

/** Linear blend of two numbers, for keyframes. */
export function mix(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

/** Interpolates numbered keys at a frame: keys are [frame, value] pairs in order, the last one held. */
export function keys(frame: number, list: ReadonlyArray<readonly [number, number]>): number {
  const first = list[0];
  if (!first) return 0;
  if (frame <= first[0]) return first[1];
  for (let i = 0; i + 1 < list.length; i += 1) {
    const [fa, va] = list[i] ?? first;
    const [fb, vb] = list[i + 1] ?? first;
    if (frame <= fb) return mix(va, vb, (frame - fa) / (fb - fa || 1));
  }
  return list[list.length - 1]?.[1] ?? first[1];
}

/** The knee or elbow between `a` and `b` for two bones of `length` each, bent towards `side` (1 right, -1 left). */
export function joint(a: P, b: P, length: number, side: 1 | -1): P {
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const d = Math.hypot(dx, dy) || 1;
  const h = Math.sqrt(Math.max(0, length * length - (d / 2) * (d / 2)));
  return [a[0] + dx / 2 + (-dy / d) * h * side, a[1] + dy / 2 + (dx / d) * h * side];
}
