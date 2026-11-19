// Card Factory (T251): a one-shot burst of steam, the valve thrown open once. Original, built from the pixelfx
// toolkit and the fire library's soft discs and drift (fire/_lib.js).
import { fit, mix, rng, clamp, ease, WHITE } from "../../core/index.js";
import { soft, drift } from "../fire/_lib.js";

export const meta = {
  name: "Steam burst",
  desc: "A valve thrown open: a white hiss, then a fan of steam puffs blasts up and out, rolls, swells and thins away.",
  tags: ["steam", "vapour", "burst", "one-shot"],
  size: [136, 128],
  origin: [68, 116],
  duration: 2,
  loop: false,
  fps: 30,
  bg: "ground",
  options: {
    palette: ["#3a3450", "#6a6488", "#9c96b8", "#cdc8e0", "#efecf8", "#ffffff"],
    glow: "#e8b33a",
    puffs: 40,
    spread: 1,
    seed: 6,
  },
};

const D = meta.duration;

export function draw(p, t, o) {
  const C = fit(o.palette, 6), G = typeof o.glow === "string" ? o.glow : "#e8b33a";
  if (t < 0.18) {
    const k = 1 - t / 0.18;
    p.glow(0, -2, 16 * k + 4, mix(C[4], WHITE, 0.5), 0.6 * k);
    p.glow(0, 0, 30, G, 0.18 * k);
    // jets of hiss: thin white lines shooting out of the mouth
    for (let i = 0; i < 5; i++) {
      const a = -Math.PI / 2 + (i - 2) * 0.32 * o.spread, L = 30 * ease.outCubic(t / 0.18);
      p.line(Math.cos(a) * L * 0.3, -2 + Math.sin(a) * L * 0.3, Math.cos(a) * L, -2 + Math.sin(a) * L, (u) => (u < 0.5 ? WHITE : C[4]), (u) => Math.min(1, k * 1.6) * (1 - u * 0.8));
    }
  }
  for (let i = 0; i < o.puffs; i++) {
    const r = rng(o.seed, i), born = r.range(0, 0.22), life = Math.min(D - born - 0.02, r.range(1.0, 1.75));
    const a0 = -Math.PI / 2 + r.range(-0.75, 0.75) * o.spread, sp = r.range(60, 210) * (i % 4 === 0 ? 1.2 : 1);
    const age = t - born;
    if (age <= 0 || age >= life) continue;
    const [x, y] = drift(0, -2, Math.cos(a0) * sp, Math.sin(a0) * sp, age, 0, -22, 3.2, 3.4), k = 1 - age / life;
    const rr = r.range(2.4, 4) * (0.5 + Math.min(1, age * 4) * 0.7 + age * 4.2);
    const a = Math.min(1, age * 16) * Math.pow(k, 1.2);
    soft(p, x, y, rr, C[2], a * 0.38);
    soft(p, x + rr * 0.08, y + rr * 0.14, rr * 0.7, C[1], a * 0.3);
    soft(p, x - rr * 0.2, y - rr * 0.32, rr * 0.55, C[4], a * 0.42 * clamp(k * 1.6));
    if (age < 0.4 && rr > 3) soft(p, x - rr * 0.25, y - rr * 0.45, rr * 0.25, WHITE, a * 0.4 * (1 - age / 0.4));
  }
}
