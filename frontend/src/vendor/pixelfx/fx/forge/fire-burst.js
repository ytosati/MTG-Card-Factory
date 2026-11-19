// Card Factory (T251): a one-shot burst of fire, flame balls thrown out in a ring that climb and cool. Original,
// built from the pixelfx toolkit (Particles, Lights) and the fire library's flame puffs (fire/_lib.js), whose recipe
// adapts Sprite Fusion's open-source fire (https://www.spritefusion.com/pixel-art-vfx/fire), MIT License,
// Copyright (c) 2026 Hugo Duprez.
import { Particles, Lights, P, Rng, fit, clamp, ease, TAU, WHITE } from "../../core/index.js";
import { hotFirst, simDraw } from "../fire/_lib.js";

export const meta = {
  name: "Fire burst",
  desc: "A white pop, then balls of flame burst out in a ring, brake, climb and cool through orange to red, while sparks streak off and fall.",
  tags: ["fire", "burst", "explosion", "one-shot"],
  size: [184, 160],
  origin: [92, 96],
  duration: 1.5,
  loop: false,
  fps: 30,
  bg: "ground",
  options: {
    palette: ["#4a1712", "#8a1f17", "#c9281f", "#f2561d", "#ff8a2a", "#ffc23d", "#ffe26b", "#fff3a6", "#ffffff"],
    radius: 34,
    seed: 7,
  },
};

export function create(o) {
  const F = fit(o.palette, 9), H = hotFirst(F), R = new Rng(o.seed), RAD = o.radius;
  const ps = new Particles({ rng: R, sparks: [H[0], H[2], H[4], H[6]], ground: () => RAD * 1.5 }), lights = new Lights();
  lights.add(0, 0, RAD * 1.4, H[3], 0.9, 0.5);
  lights.add(0, 0, RAD * 0.5, WHITE, 0.8, 0.1);
  const n = 26;
  for (let i = 0; i < n; i++) {
    const a = (i / n) * TAU + R.range(-0.25, 0.25), sp = RAD * R.range(2.6, 6.4);
    ps.spawn(P.FIRE, Math.cos(a) * 3, Math.sin(a) * 3, Math.cos(a) * sp, Math.sin(a) * sp * 0.8 - 20, R.range(0.6, 1.1), 0, R.range(4, 7), R.range(0, 0.06));
  }
  // a column of flame climbing off the heart of it
  for (let i = 0; i < 12; i++) ps.spawn(P.FIRE, R.range(-5, 5), R.range(-3, 3), R.range(-30, 30), -R.range(50, 150), R.range(0.6, 1.15), 0, R.range(4.5, 7.5), R.range(0, 0.12));
  for (let i = 0; i < 26; i++) {
    const a = R.range(0, TAU), sp = RAD * R.range(5, 9);
    ps.spawn(P.SPARK, 0, 0, Math.cos(a) * sp, Math.sin(a) * sp - 60, R.range(0.35, 0.8));
  }
  for (let i = 0; i < 10; i++) ps.spawn(P.EMBER, R.range(-8, 8), R.range(-6, 4), R.range(-20, 20), -R.range(30, 70), R.range(0.6, 1.1), H[3]);
  let t = 0;
  return {
    update(dt) {
      t += dt;
      ps.update(dt);
      lights.update(dt);
    },
    draw(p) {
      if (t < 0.08) p.circle(0, 0, RAD * 0.3 * (1 - t / 0.08) + 2, WHITE);
      const u = t / 0.35;
      if (u < 1) {
        const r = RAD * (0.25 + 0.9 * ease.outExpo(u));
        p.ring(0, 0, r, Math.max(1, 2.5 * (1 - u)), u < 0.3 ? WHITE : H[2], clamp(1.2 - u));
        p.glowRing(0, 0, r, 5, H[3], 0.4 * (1 - u));
      }
      simDraw(p, ps, H);
      lights.draw(p);
    },
  };
}
