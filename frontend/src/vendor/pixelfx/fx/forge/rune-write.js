// Card Factory (T251): runes written in lines by an unseen pen, on a loop. Original, built from the arcane
// library's rune alphabets (arcane/_lib.js) and the pixelfx toolkit.
import { fit, rng, clamp, sparkle, WHITE } from "../../core/index.js";
import { SIGILS, sigil, glyph } from "../arcane/_lib.js";

export const meta = {
  name: "Rune writing",
  desc: "Line after line, runes burn into the air left to right: each flares white at the pen's tip and cools to violet, then the page fades and is written again.",
  tags: ["arcane", "runes", "writing", "loop"],
  size: [136, 56],
  origin: [68, 50],
  duration: 4.2,
  loop: true,
  fps: 30,
  bg: "ground",
  options: {
    palette: ["#140a26", "#2b1252", "#481c88", "#6b2cc0", "#8b3dff", "#b07cff", "#e2ccff", "#ffffff"],
    lines: 3,
    perLine: 13,
    seed: 2,
  },
};

const D = meta.duration, WRITE = 2.9, FADE_AT = 3.5, FADE = 0.55;

export function draw(p, t, o) {
  const C = fit(o.palette, 8), n = o.lines * o.perLine, gapX = 9, gapY = 14;
  const fade = 1 - clamp((t - FADE_AT) / FADE);
  for (let i = 0; i < n; i++) {
    const line = Math.floor(i / o.perLine), col = i % o.perLine, r = rng(o.seed, i);
    const big = r.chance(0.3), at = (i / n) * WRITE, age = t - at;
    if (age < 0 || fade <= 0) continue;
    const x = (col - (o.perLine - 1) / 2) * gapX + r.range(-0.5, 0.5), y = -(o.lines - 1 - line) * gapY;
    // white at the pen's tip, cooling through lilac to the line's violet
    const c = age < 0.08 ? WHITE : age < 0.25 ? C[6] : age < 0.6 ? C[5] : C[4];
    const pulse = 0.9 + 0.1 * Math.sin(t * 5 + i);
    if (big) sigil(p, r.int(0, SIGILS.length - 1), x, y - 3, c, fade);
    else glyph(p, r.int(0, 7), x, y, c, fade, C[2]);
    p.glow(x, y - 3, 6, C[4], (age < 0.3 ? 0.5 : 0.16 * pulse) * fade);
    if (age < 0.12) sparkle(p, x + 3, y - 6, 3 * (1 - age / 0.12) + 1, C[6], C[5], 0.5);
  }
  // the pen: a hot point riding ahead of the last rune while it writes
  if (t < WRITE) {
    const i = Math.floor((t / WRITE) * n), line = Math.floor(i / o.perLine), col = i % o.perLine;
    const x = (col - (o.perLine - 1) / 2) * gapX + 4, y = -(o.lines - 1 - line) * gapY - 6;
    p.px(x, y, WHITE);
    p.glow(x, y, 9, C[5], 0.55);
  }
}
