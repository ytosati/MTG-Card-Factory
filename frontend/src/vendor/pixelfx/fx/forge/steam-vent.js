// Card Factory (T251): a short puff of steam from a pipe outlet, on a loop. Original, built from the pixelfx toolkit
// and the fire library's soft discs and drift (fire/_lib.js).
import { fit, mix, rng, wrap, clamp, WHITE } from "../../core/index.js";
import { soft, drift } from "../fire/_lib.js";

export const meta = {
  name: "Steam vent",
  desc: "A pipe outlet hisses a short burst of steam every few seconds: soft puffs shoot up, swell, drift and thin, lit on top.",
  tags: ["steam", "vapour", "pipe", "loop"],
  size: [96, 96],
  origin: [40, 88],
  duration: 2.4,
  loop: true,
  fps: 30,
  bg: "ground",
  options: {
    palette: ["#3a3450", "#6a6488", "#9c96b8", "#cdc8e0", "#efecf8", "#ffffff"],
    glow: "#e8b33a",
    puffs: 26,
    burst: 0.7,
    seed: 4,
  },
};

const D = meta.duration;

/** One puff with life left k: a soft body, a denser core sitting low, a lit cap on top. */
function puff(p, x, y, r, a, C) {
  soft(p, x, y, r, C[2], a * 0.4);
  soft(p, x + r * 0.08, y + r * 0.12, r * 0.72, C[1], a * 0.35);
  soft(p, x - r * 0.18, y - r * 0.32, r * 0.55, C[4], a * 0.45);
  if (r > 2.5) soft(p, x - r * 0.25, y - r * 0.45, r * 0.25, WHITE, a * 0.35);
}

export function draw(p, t, o) {
  const C = fit(o.palette, 6), G = typeof o.glow === "string" ? o.glow : "#e8b33a";
  // the hiss: a hot point at the mouth while the valve is open
  const open = clamp(1 - Math.abs(wrap(t, D) - o.burst * 0.5) / (o.burst * 0.6));
  if (open > 0) {
    p.glow(0, -1, 7, mix(C[4], WHITE, 0.4), 0.35 * open);
    p.glow(0, 2, 14, G, 0.12 * open);
  }
  for (let i = 0; i < o.puffs; i++) {
    // a steady stream while the valve is open: early puffs fly fastest, the last ones barely leave the mouth
    const r = rng(o.seed, i), u = i / o.puffs, born = u * o.burst, life = r.range(0.9, 1.5) * (1 - u * 0.35);
    const vx = r.range(-10, 10), vy = -r.range(110, 170) * (1 - u * 0.5), size = r.range(1.6, 2.8), sway = r.range(0, 6.3);
    const age = wrap(t - born, D);
    if (age >= life) continue;
    const [x, y] = drift(0, -2, vx, vy, age, 0, -18, 3, 3.4), k = 1 - age / life;
    const rr = size * (0.5 + Math.min(1, age * 4) * 0.5 + age * 3.4);
    const a = Math.min(1, age * 14) * Math.pow(k, 1.1) * 0.95;
    // the plume leans and curls as it slows: a shared drift plus each puff's own sway
    puff(p, x + age * age * 9 + Math.sin(age * 3.4 + sway) * age * 5, y, rr, a, C);
  }
}
