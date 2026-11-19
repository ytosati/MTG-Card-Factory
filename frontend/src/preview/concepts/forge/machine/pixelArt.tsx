// Pixel sprites as SVG: rows of palette characters merged into one path per colour (tasks.md T251).
import { BASE_PALETTE } from "./palette";

/** A sprite: one string per row, one palette character per pixel, "." for transparent. */
export type PixelRows = readonly string[];

type CharPaths = ReadonlyArray<readonly [string, string]>;

const pathCache = new WeakMap<PixelRows, CharPaths>();

/** Merges each horizontal run of one character into a rectangle; one path per character. */
export function toPaths(rows: PixelRows): CharPaths {
  const cached = pathCache.get(rows);
  if (cached) return cached;
  const byChar = new Map<string, string[]>();
  rows.forEach((row, y) => {
    let x = 0;
    while (x < row.length) {
      const ch = row.charAt(x);
      let end = x + 1;
      while (end < row.length && row.charAt(end) === ch) end += 1;
      if (ch !== "." && ch !== " ") {
        const parts = byChar.get(ch) ?? [];
        parts.push(`M${x} ${y}h${end - x}v1h${x - end}z`);
        byChar.set(ch, parts);
      }
      x = end;
    }
  });
  const result = [...byChar.entries()].map(([ch, parts]) => [ch, parts.join("")] as const);
  pathCache.set(rows, result);
  return result;
}

export function spriteWidth(rows: PixelRows): number {
  return rows.reduce((max, row) => Math.max(max, row.length), 0);
}

/** Mirrors a sprite left to right, so one drawing serves both facings. */
const mirrorCache = new WeakMap<PixelRows, PixelRows>();
export function mirror(rows: PixelRows): PixelRows {
  const cached = mirrorCache.get(rows);
  if (cached) return cached;
  const width = spriteWidth(rows);
  const result = rows.map((row) => row.padEnd(width, ".").split("").reverse().join(""));
  mirrorCache.set(rows, result);
  return result;
}

interface PixelsProps {
  art: PixelRows;
  x?: number;
  y?: number;
  palette?: Readonly<Record<string, string>>;
  opacity?: number;
}

/** Places a sprite at logical pixel (x, y) of the scene. */
export function Pixels({ art, x = 0, y = 0, palette, opacity }: PixelsProps) {
  return (
    <g transform={`translate(${x} ${y})`} opacity={opacity}>
      {toPaths(art).map(([ch, d]) => (
        <path key={ch} d={d} fill={palette?.[ch] ?? BASE_PALETTE[ch] ?? "#ff00ff"} />
      ))}
    </g>
  );
}

/** A mutable pixel canvas for building large static pieces from shapes and stamped sprites. */
export class PixelCanvas {
  private readonly grid: string[][];

  constructor(
    readonly width: number,
    readonly height: number,
    fill = ".",
  ) {
    this.grid = Array.from({ length: height }, () => Array.from({ length: width }, () => fill));
  }

  set(x: number, y: number, ch: string): void {
    const row = this.grid[y];
    if (row && x >= 0 && x < this.width) row[x] = ch;
  }

  get(x: number, y: number): string {
    return this.grid[y]?.[x] ?? ".";
  }

  rect(x: number, y: number, w: number, h: number, ch: string): void {
    for (let j = y; j < y + h; j += 1) for (let i = x; i < x + w; i += 1) this.set(i, j, ch);
  }

  /** Fills a rectangle with a vertical stripe pattern, one character per column (cylinder shading). */
  columns(x: number, y: number, h: number, shades: string): void {
    for (let i = 0; i < shades.length; i += 1) this.rect(x + i, y, 1, h, shades.charAt(i));
  }

  /** Fills a rectangle with a horizontal stripe pattern, one character per row. */
  rows(x: number, y: number, w: number, shades: string): void {
    for (let j = 0; j < shades.length; j += 1) this.rect(x, y + j, w, 1, shades.charAt(j));
  }

  stamp(art: PixelRows, x: number, y: number): void {
    art.forEach((row, j) => {
      for (let i = 0; i < row.length; i += 1) {
        const ch = row.charAt(i);
        if (ch !== "." && ch !== " ") this.set(x + i, y + j, ch);
      }
    });
  }

  toRows(): PixelRows {
    return this.grid.map((row) => row.join(""));
  }
}
