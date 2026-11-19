// Card Factory (T251): sparks and embers rising off a hot bed, on a loop. Built from the brazier's spark stream and
// the fire library's sparks and embers (fire/_lib.js), whose recipes adapt Sprite Fusion's open-source fire
// (https://www.spritefusion.com/pixel-art-vfx/fire), MIT License, Copyright (c) 2026 Hugo Duprez.
import { fit } from "../../core/index.js";
import { hotFirst, looped, drift, spark, ember } from "../fire/_lib.js";

export const meta = {
  name: "Embers",
  desc: "Sparks shoot up off a hot bed, slow in the draught, wander and cool into embers that wink out high above.",
  tags: ["fire", "embers", "sparks", "ambient", "loop"],
  size: [96, 128],
  origin: [48, 120],
  duration: 3,
  loop: true,
  fps: 30,
  bg: "ground",
  options: {
    palette: ["#4a1712", "#8a1f17", "#c9281f", "#f2561d", "#ff8a2a", "#ffc23d", "#ffe26b", "#fff3a6", "#ffffff"],
    count: 46,
    width: 30,
    seed: 5,
  },
};

const D = meta.duration;

export function draw(p, t, o) {
  const H = hotFirst(fit(o.palette, 9)), SPARKS = [H[2], H[3], H[4], H[6]], EMB = [H[2], H[4], H[5], H[7]];
  // the hot bed they leave: a low warm glow
  p.glow(0, 0, o.width, H[4], 0.18);
  looped(t, D, o.count, o.seed, (r) => {
    const side = r.range(-1, 1);
    return { x: side * o.width * 0.5, vx: side * r.range(5, 30), vy: -r.range(60, 150), life: r.range(0.9, 2.2), a: r.range(0, 6.3), w: r.range(1.6, 3.4), m: r.range(3, 9), big: r.chance(0.15) };
  }, (q, age) => {
    const [x, y, vx, vy] = drift(q.x, 0, q.vx, q.vy, age, 0, -20, 1.9, 1.9), k = 1 - age / q.life;
    const ramp = Math.min(1, age * 1.5), wob = q.m * (Math.sin(age * q.w + q.a) - Math.sin(q.a)) * ramp;
    const wv = q.m * q.w * Math.cos(age * q.w + q.a) * ramp;
    if (Math.hypot(vx + wv, vy) > 40) spark(p, x + wob, y, vx + wv, vy, k, SPARKS);
    else ember(p, x + wob, y, k, q.big ? 2 : 1, EMB, age * 40 + q.a);
  });
}
