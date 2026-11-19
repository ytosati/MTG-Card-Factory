// Goblin crew (tasks.md T251): a small layered pixel painter. Shapes become masks, masks are lit from the top left
// in hard ramp steps and wrapped in one ink line. The method (masks, one light direction, hard steps, a clean ink
// line, inner lines where parts overlap) follows pixelfx by patch-gg (MIT licence); this code is written for the project.
import { INK, RAMPS } from "./palette";

export type Vec3 = readonly [number, number, number];
/** A surface normal at a pixel, z towards the viewer. */
export type Normal = (x: number, y: number) => Vec3;
/** The colour character of a pixel, or null to leave it as it is. */
export type Shade = (x: number, y: number) => string | null;
/** How a part is wrapped: an ink line outside and darker lines over parts beneath, only outside, or nothing. */
export type Line = "ink" | "out" | "none";

/** One light for every goblin: from the top left, a little in front. */
const LIGHT: Vec3 = normalize([-0.55, -0.72, 0.55]);

function normalize([x, y, z]: Vec3): Vec3 {
  const length = Math.hypot(x, y, z) || 1;
  return [x / length, y / length, z / length];
}

/** The first (darkest) step of the ramp a character belongs to, used for inner lines. */
const DARKEST = new Map<string, string>();
for (const ramp of Object.values(RAMPS)) for (const ch of ramp) DARKEST.set(ch, ramp.charAt(0));

function innerLine(under: string): string {
  const dark = DARKEST.get(under);
  return dark === undefined || dark === under ? INK : dark;
}

/** A set of pixels of a raster. */
export class Mask {
  readonly bits: Uint8Array;

  constructor(
    readonly w: number,
    readonly h: number,
  ) {
    this.bits = new Uint8Array(w * h);
  }

  has(x: number, y: number): boolean {
    return x >= 0 && y >= 0 && x < this.w && y < this.h && this.bits[y * this.w + x] === 1;
  }

  add(x: number, y: number): void {
    if (x >= 0 && y >= 0 && x < this.w && y < this.h) this.bits[y * this.w + x] = 1;
  }

  remove(x: number, y: number): void {
    if (x >= 0 && y >= 0 && x < this.w && y < this.h) this.bits[y * this.w + x] = 0;
  }

  union(...others: Mask[]): Mask {
    for (const other of others) other.bits.forEach((bit, i) => bit === 1 && (this.bits[i] = 1));
    return this;
  }

  minus(...others: Mask[]): Mask {
    for (const other of others) other.bits.forEach((bit, i) => bit === 1 && (this.bits[i] = 0));
    return this;
  }

  forEach(fn: (x: number, y: number) => void): void {
    for (let i = 0; i < this.bits.length; i += 1) if (this.bits[i] === 1) fn(i % this.w, Math.floor(i / this.w));
  }
}

/** A sphere or ellipsoid normal: big round forms such as heads, noses and bellies. */
export function sphere(cx: number, cy: number, rx: number, ry: number): Normal {
  return (x, y) => {
    let nx = (x + 0.5 - cx) / rx;
    let ny = (y + 0.5 - cy) / ry;
    const d = nx * nx + ny * ny;
    if (d > 1) {
      nx /= Math.sqrt(d);
      ny /= Math.sqrt(d);
    }
    return [nx, ny, Math.sqrt(Math.max(0, 1 - nx * nx - ny * ny))];
  };
}

/** A cylinder normal around the segment a-b: limbs, handles, rolled cloth. */
export function cylinder(ax: number, ay: number, bx: number, by: number, r: number): Normal {
  const dx = bx - ax;
  const dy = by - ay;
  const length = Math.hypot(dx, dy) || 1;
  const px = -dy / length;
  const py = dx / length;
  return (x, y) => {
    const offset = Math.max(-1, Math.min(1, ((x + 0.5 - ax) * px + (y + 0.5 - ay) * py) / r));
    return [px * offset, py * offset, Math.sqrt(Math.max(0, 1 - offset * offset))];
  };
}

/** Bends a normal towards a direction, for planes that face up, down or sideways. */
export function tilt(normal: Normal, by: Vec3): Normal {
  return (x, y) => {
    const [nx, ny, nz] = normal(x, y);
    return normalize([nx + by[0], ny + by[1], nz + by[2]]);
  };
}

/** Lights a normal into a ramp in hard steps. `lift` brightens or darkens the whole part. */
export function lit(normal: Normal, ramp: string, lift = 0): Shade {
  const steps = ramp.length;
  return (x, y) => {
    const [nx, ny, nz] = normal(x, y);
    const light = nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2] + lift;
    const v = Math.max(0, Math.min(0.999, (light + 0.15) / 1.1));
    return ramp.charAt(Math.floor(v * steps));
  };
}

export function flat(ch: string): Shade {
  return () => ch;
}

/** A pixel canvas painted part by part, back to front. */
export class Raster {
  private readonly px: string[];
  private readonly owner: Int16Array;
  private parts = 0;

  constructor(
    readonly w: number,
    readonly h: number,
  ) {
    this.px = Array.from({ length: w * h }, () => "");
    this.owner = new Int16Array(w * h).fill(-1);
  }

  get(x: number, y: number): string {
    return x >= 0 && y >= 0 && x < this.w && y < this.h ? (this.px[y * this.w + x] ?? "") : "";
  }

  /** Sets one pixel directly: detail, no line. */
  dot(x: number, y: number, ch: string): void {
    const ix = Math.round(x);
    const iy = Math.round(y);
    if (ix >= 0 && iy >= 0 && ix < this.w && iy < this.h) this.px[iy * this.w + ix] = ch;
  }

  /** Draws a 1 px line of one character (Bresenham), for creases, strands and straps. */
  line(x0: number, y0: number, x1: number, y1: number, ch: string): void {
    let x = Math.round(x0);
    let y = Math.round(y0);
    const ex = Math.round(x1);
    const ey = Math.round(y1);
    const dx = Math.abs(ex - x);
    const dy = -Math.abs(ey - y);
    const sx = x < ex ? 1 : -1;
    const sy = y < ey ? 1 : -1;
    let err = dx + dy;
    for (;;) {
      this.dot(x, y, ch);
      if (x === ex && y === ey) break;
      const e2 = 2 * err;
      if (e2 >= dy) {
        err += dy;
        x += sx;
      }
      if (e2 <= dx) {
        err += dx;
        y += sy;
      }
    }
  }

  /** Stamps hand-placed pixels: one string per row, "." transparent. Only over painted pixels when `onto`. */
  stamp(rows: readonly string[], x: number, y: number, onto = false): void {
    rows.forEach((row, j) => {
      for (let i = 0; i < row.length; i += 1) {
        const ch = row.charAt(i);
        if (ch === "." || ch === " ") continue;
        if (onto && this.get(x + i, y + j) === "") continue;
        this.dot(x + i, y + j, ch);
      }
    });
  }

  /** Paints one part: its line first, then its pixels lit by `shade`. */
  paint(mask: Mask, shade: Shade, line: Line = "ink"): void {
    this.parts += 1;
    const id = this.parts;
    if (line !== "none") {
      mask.forEach((x, y) => {
        for (const [nx, ny] of [
          [x + 1, y],
          [x - 1, y],
          [x, y + 1],
          [x, y - 1],
        ] as const) {
          if (mask.has(nx, ny) || nx < 0 || ny < 0 || nx >= this.w || ny >= this.h) continue;
          const i = ny * this.w + nx;
          const under = this.px[i] ?? "";
          if (under === "") {
            this.px[i] = INK;
            this.owner[i] = id;
          } else if (line === "ink" && this.owner[i] !== id) {
            this.px[i] = innerLine(under);
            this.owner[i] = id;
          }
        }
      });
    }
    mask.forEach((x, y) => {
      const ch = shade(x, y);
      if (ch === null) return;
      const i = y * this.w + x;
      this.px[i] = ch;
      this.owner[i] = id;
    });
  }

  // Shapes. A pixel belongs to a shape when its centre is inside.

  mask(): Mask {
    return new Mask(this.w, this.h);
  }

  ellipse(cx: number, cy: number, rx: number, ry: number): Mask {
    const m = this.mask();
    for (let y = Math.floor(cy - ry - 1); y <= cy + ry + 1; y += 1)
      for (let x = Math.floor(cx - rx - 1); x <= cx + rx + 1; x += 1) {
        const nx = (x + 0.5 - cx) / rx;
        const ny = (y + 0.5 - cy) / ry;
        if (nx * nx + ny * ny <= 1) m.add(x, y);
      }
    return m;
  }

  rect(x: number, y: number, w: number, h: number): Mask {
    const m = this.mask();
    for (let j = 0; j < h; j += 1) for (let i = 0; i < w; i += 1) m.add(Math.round(x) + i, Math.round(y) + j);
    return m;
  }

  /** A polygon by its corners, even-odd fill. */
  poly(points: ReadonlyArray<readonly [number, number]>): Mask {
    const m = this.mask();
    const ys = points.map((p) => p[1]);
    for (let y = Math.floor(Math.min(...ys)); y <= Math.max(...ys); y += 1) {
      const cy = y + 0.5;
      const xs: number[] = [];
      points.forEach(([ax, ay], i) => {
        const [bx, by] = points[(i + 1) % points.length] ?? points[0] ?? [0, 0];
        if (ay <= cy === by <= cy) return;
        xs.push(ax + ((cy - ay) / (by - ay)) * (bx - ax));
      });
      xs.sort((a, b) => a - b);
      for (let k = 0; k + 1 < xs.length; k += 2) {
        const from = xs[k] ?? 0;
        const to = xs[k + 1] ?? 0;
        for (let x = Math.ceil(from - 0.5); x + 0.5 <= to; x += 1) m.add(x, y);
      }
    }
    return m;
  }

  /** A segment with round ends, its radius going from r0 to r1: limbs, beard locks, ears. */
  capsule(ax: number, ay: number, bx: number, by: number, r0: number, r1 = r0): Mask {
    const m = this.mask();
    const dx = bx - ax;
    const dy = by - ay;
    const l2 = dx * dx + dy * dy || 1;
    const pad = Math.max(r0, r1) + 1;
    for (let y = Math.floor(Math.min(ay, by) - pad); y <= Math.max(ay, by) + pad; y += 1)
      for (let x = Math.floor(Math.min(ax, bx) - pad); x <= Math.max(ax, bx) + pad; x += 1) {
        const px = x + 0.5;
        const py = y + 0.5;
        const t = Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / l2));
        const r = r0 + (r1 - r0) * t;
        if (Math.hypot(px - (ax + dx * t), py - (ay + dy * t)) <= r) m.add(x, y);
      }
    return m;
  }

  /** The pixels of hand-placed rows that are not "." */
  pixels(rows: readonly string[], x: number, y: number): Mask {
    const m = this.mask();
    rows.forEach((row, j) => {
      for (let i = 0; i < row.length; i += 1) if (row.charAt(i) !== ".") m.add(x + i, y + j);
    });
    return m;
  }

  toRows(): string[] {
    const rows: string[] = [];
    for (let y = 0; y < this.h; y += 1) {
      let row = "";
      for (let x = 0; x < this.w; x += 1) row += this.px[y * this.w + x] || ".";
      rows.push(row);
    }
    return rows;
  }
}
