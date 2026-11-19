// Card Factory (T251): a one-shot swirl of leaves on a gust of green light. Original, built from the pixelfx toolkit
// and the nature library's leaves (nature/_lib.js).
import { Rng, fit, clamp, ease, sparkle, TAU, WHITE } from "../../core/index.js";
import { drawLeaf } from "../nature/_lib.js";

export const meta = {
  name: "Leaf swirl",
  desc: "A green pop, then leaves spin out on a spiral gust, flipping as they turn, wrapped in bright bands of wind, and drift down as they fade.",
  tags: ["nature", "leaves", "wind", "burst", "one-shot"],
  size: [128, 128],
  origin: [64, 64],
  duration: 1.5,
  loop: false,
  fps: 30,
  bg: "ground",
  options: {
    palette: ["#0c1a0e", "#163418", "#225224", "#357530", "#4f9a3a", "#7cc048", "#b4e070", "#e4ffb0"],
    radius: 40,
    leaves: 16,
    seed: 4,
  },
};

const D = meta.duration;

export function create(o) {
  const C = fit(o.palette, 8), R = new Rng(o.seed), RAD = o.radius;
  const leaves = Array.from({ length: o.leaves }, (_, i) => ({
    a: (i / o.leaves) * TAU + R.range(-0.2, 0.2),
    reach: RAD * R.range(0.55, 1.05),
    spin: R.range(2.2, 3.4),
    flip: R.range(8, 16),
    len: R.range(7, 11),
    life: R.range(0.9, D - 0.1),
    d: R.range(0, 0.1),
    pal: R.chance(0.3) ? [C[1], C[3], C[5], C[7]] : [C[0], C[2], C[4], C[6]],
  }));
  let t = 0;
  return {
    update(dt) {
      t += dt;
    },
    draw(p) {
      if (t < 0.09) p.circle(0, 0, 8 * (1 - t / 0.09) + 1, C[7]);
      if (t < 0.4) p.glow(0, 0, RAD * 0.8, C[5], 0.5 * (1 - t / 0.4));
      // bands of wind: arcs that sweep round and open out
      for (let b = 0; b < 3; b++) {
        const u = (t - b * 0.06) / 0.7;
        if (u <= 0 || u >= 1) continue;
        const r = RAD * (0.3 + 0.7 * ease.outCubic(u)), a0 = b * 2.1 + u * 3.2;
        p.arc(0, 0, r, 1.5, a0, a0 + 1.6, (v) => (v > 0.7 ? WHITE : C[6]), (v) => clamp((1 - u) * Math.sin(v * Math.PI) * 2));
        p.glowRing(0, 0, r, 3, C[5], 0.14 * (1 - u));
      }
      for (const l of leaves) {
        const age = t - l.d;
        if (age <= 0 || age >= l.life) continue;
        const u = age / l.life, k = 1 - u, out = ease.outCubic(Math.min(1, u * 1.6));
        const a = l.a + out * l.spin, r = l.reach * out;
        const x = Math.cos(a) * r, y = Math.sin(a) * r * 0.85 + u * u * 14;
        drawLeaf(p, x, y, l.len, l.len * 0.36, a + Math.PI / 2, age * l.flip, l.pal, clamp(k * 2.2));
        p.glow(x, y, 5, C[5], 0.3 * k);
      }
      if (t < 0.5) sparkle(p, 0, 0, Math.round(5 * (1 - t / 0.5)), C[7], C[5], 0.5);
    },
  };
}
