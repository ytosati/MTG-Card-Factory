// Card Factory (T251): a one-shot burst of holy light, rays shooting out round a white core. Original, built from
// the pixelfx toolkit (sparkle, Lights) and the pickup library's glint (pickups/_lib.js).
import { Lights, Rng, fit, clamp, ease, sparkle, TAU, WHITE } from "../../core/index.js";
import { glint } from "../pickups/_lib.js";

export const meta = {
  name: "Holy burst",
  desc: "A white flash, then long and short rays of gold light shoot out round the core, a halo ring swells, glints are flung wide and drift, and the light breathes out.",
  tags: ["holy", "light", "rays", "burst", "one-shot"],
  size: [128, 128],
  origin: [64, 64],
  duration: 1.4,
  loop: false,
  fps: 30,
  bg: "ground",
  options: {
    palette: ["#2a1c08", "#5a3e10", "#9a6c18", "#d8a428", "#ffd84a", "#fff09a", "#fffbe6", "#ffffff"],
    radius: 44,
    rays: 12,
    glints: 12,
    seed: 3,
  },
};

const D = meta.duration;

export function create(o) {
  const C = fit(o.palette, 8), R = new Rng(o.seed), RAD = o.radius, lights = new Lights();
  lights.add(0, 0, RAD * 1.2, C[4], 1, 0.6);
  lights.add(0, 0, RAD * 0.35, WHITE, 0.9, 0.12);
  const rays = Array.from({ length: o.rays }, (_, i) => ({
    a: (i / o.rays) * TAU + R.range(-0.08, 0.08) - Math.PI / 2,
    len: (i % 2 ? R.range(0.5, 0.7) : R.range(0.9, 1.1)) * RAD,
    d: (i % 2) * 0.04 + R.range(0, 0.03),
    life: R.range(0.55, 0.8),
  }));
  const sparks = Array.from({ length: o.glints }, () => {
    const a = R.range(0, TAU), sp = R.range(0.9, 1.6) * RAD * 3;
    return { x: 0, y: 0, vx: Math.cos(a) * sp, vy: Math.sin(a) * sp, life: R.range(0.7, D - 0.1), age: 0, size: R.range(1, 3), ph: R.range(0, TAU) };
  });
  let t = 0;
  return {
    update(dt) {
      t += dt;
      for (const s of sparks) {
        s.age += dt;
        s.vx -= s.vx * 5 * dt;
        s.vy -= s.vy * 5 * dt + 14 * dt;
        s.x += s.vx * dt;
        s.y += s.vy * dt;
      }
      lights.update(dt);
    },
    draw(p) {
      // the hero frame: a white disc that shrinks into the core
      if (t < 0.1) p.circle(0, 0, RAD * 0.22 * (1 - t / 0.1) + 2, WHITE);
      // rays: thin beams that shoot out fast, hold, and thin from the root outward
      for (const r of rays) {
        const u = (t - r.d) / r.life;
        if (u <= 0 || u >= 1) continue;
        const reach = r.len * ease.outExpo(Math.min(1, u * 2.2)), from = r.len * 0.18 + reach * ease.inCubic(u) * 0.85;
        const ca = Math.cos(r.a), sa = Math.sin(r.a), k = 1 - u;
        // long rays are two pixels thick while young; every ray stays solid until it starts to thin
        const col = (v) => (v < 0.35 ? WHITE : v < 0.7 ? C[6] : C[5]), alpha = (v) => (k > 0.45 ? 1 : clamp(k * 2.2) * (1 - v * 0.5));
        p.line(ca * from, sa * from, ca * reach, sa * reach, col, alpha);
        if (r.len > RAD * 0.8 && k > 0.4) p.line(ca * from - sa, sa * from + ca, ca * reach * 0.8 - sa, sa * reach * 0.8 + ca, col, alpha);
        p.glowLine(ca * from, sa * from, ca * reach, sa * reach, 4, C[4], 0.4 * k);
      }
      // the halo: a ring that swells and thins
      const h = t / 0.55;
      if (h < 1) {
        const r = RAD * (0.2 + 0.55 * ease.outCubic(h));
        p.ring(0, 0, r, Math.max(1, 2.4 * (1 - h)), h < 0.25 ? WHITE : C[6], 1.2 - h);
        p.glowRing(0, 0, r, 4, C[4], 0.35 * (1 - h));
      }
      // the core keeps a little star while the light lasts
      const c = 1 - t / 0.7;
      if (c > 0) sparkle(p, 0, 0, Math.round(2 + 5 * c), C[6], C[5], 0.6 * c);
      for (const s of sparks) {
        if (s.age >= s.life) continue;
        const k = 1 - s.age / s.life, tw = 0.6 + 0.4 * Math.sin(s.age * 24 + s.ph);
        if (k < 0.3 && Math.sin(s.age * 40 + s.ph) < 0) continue;
        glint(p, s.x, s.y, Math.round(s.size * tw * Math.min(1, k * 2)), k > 0.5 ? C[7] : C[6], 0.4 * k);
      }
      lights.draw(p);
    },
  };
}
