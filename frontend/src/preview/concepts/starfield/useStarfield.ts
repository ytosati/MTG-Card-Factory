// Concept E "Starfield" (tasks.md T251): the canvas loop of the starfield, sized to its box and sharp on dense screens.
import { useEffect, useRef } from "react";

import { useMotionOff } from "../forge/screens/motion";

/** How fast the field travels: a slow drift at rest, a steady warp while a card is generated. */
export type StarfieldSpeed = "rest" | "generating";

/** Depth units per second; a star crosses the whole depth in about 45 s at rest. */
const SPEEDS: Record<StarfieldSpeed, number> = { rest: 0.022, generating: 0.11 };

/** How quickly the travel speed follows a change, per second; it eases instead of jumping. */
const EASE = 1.6;

/** Stars per square pixel of the box, and the bounds of their number. */
const DENSITY = 1 / 2600;
const MIN_STARS = 140;
const MAX_STARS = 520;

/** Depth a new star is born at, and the depth at which a passing star is recycled. */
const FAR = 1;
const NEAR = 0.04;

type Star = { x: number; y: number; z: number; tone: number; shine: number };

type Palette = { ink: string; cyan: string; violet: string };

function spawn(z: number): Star {
  return { x: Math.random() * 2 - 1, y: Math.random() * 2 - 1, z, tone: Math.random(), shine: 0.55 + Math.random() * 0.45 };
}

function readPalette(element: HTMLElement): Palette {
  const style = getComputedStyle(element);
  const read = (name: string, fallback: string) => style.getPropertyValue(name).trim() || fallback;
  return { ink: read("--sf-ink", "#e9f1fb"), cyan: read("--sf-cyan", "#5bd2fe"), violet: read("--sf-violet-text", "#b98eff") };
}

/** Most stars are starlight; a few are cyan and fewer violet. */
function colorOf(star: Star, palette: Palette): string {
  if (star.tone > 0.95) return palette.violet;
  if (star.tone > 0.88) return palette.cyan;
  return palette.ink;
}

/**
 * Draws the field into the returned canvas. The vanishing point sits up and to the right, so the travel opens
 * towards the card stage. Under reduced motion the field is one still frame; the loop pauses while the tab is hidden.
 */
export function useStarfield(speed: StarfieldSpeed) {
  const [ref, motionOff] = useMotionOff<HTMLCanvasElement>();
  const target = useRef(SPEEDS[speed]);
  target.current = SPEEDS[speed];

  useEffect(() => {
    const canvas = ref.current;
    const context = canvas?.getContext("2d") ?? null;
    if (!canvas || !context) return undefined;

    const palette = readPalette(canvas);
    let stars: Star[] = [];
    let width = 0;
    let height = 0;
    let velocity = target.current;
    let frameId = 0;
    let last = 0;

    const draw = (): void => {
      context.clearRect(0, 0, width, height);
      const cx = width * 0.64;
      const cy = height * 0.36;
      const reach = Math.max(width, height) * 0.3;
      // A resting field shows points; trails appear only as the travel speeds up, and stay short.
      const trail = Math.max(0, velocity - SPEEDS.rest) * 0.35;
      context.lineCap = "round";
      for (const star of stars) {
        const near = 1 - star.z;
        const x = cx + (star.x / star.z) * reach;
        const y = cy + (star.y / star.z) * reach;
        const tailZ = Math.min(FAR, star.z + trail);
        const tx = cx + (star.x / tailZ) * reach;
        const ty = cy + (star.y / tailZ) * reach;
        const size = 0.7 + near * near * 2;
        // Newborn stars fade in from the depth instead of appearing at once.
        const birth = Math.min(1, near * 5);
        context.globalAlpha = (0.22 + near * 0.7) * star.shine * birth;
        const color = colorOf(star, palette);
        if (Math.hypot(x - tx, y - ty) < 1) {
          context.fillStyle = color;
          context.beginPath();
          context.arc(x, y, size * 0.6, 0, Math.PI * 2);
          context.fill();
        } else {
          context.strokeStyle = color;
          context.lineWidth = size;
          context.beginPath();
          context.moveTo(tx, ty);
          context.lineTo(x, y);
          context.stroke();
        }
      }
      context.globalAlpha = 1;
    };

    const advance = (dt: number): void => {
      velocity += (target.current - velocity) * Math.min(1, dt * EASE);
      const cx = width * 0.64;
      const cy = height * 0.36;
      const reach = Math.max(width, height) * 0.3;
      for (let index = 0; index < stars.length; index += 1) {
        const star = stars[index]!;
        star.z -= velocity * dt;
        const x = cx + (star.x / star.z) * reach;
        const y = cy + (star.y / star.z) * reach;
        if (star.z <= NEAR || x < -24 || x > width + 24 || y < -24 || y > height + 24) stars[index] = spawn(FAR);
      }
    };

    const resize = (): void => {
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      width = canvas.clientWidth;
      height = canvas.clientHeight;
      canvas.width = Math.round(width * ratio);
      canvas.height = Math.round(height * ratio);
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
      const count = Math.max(MIN_STARS, Math.min(MAX_STARS, Math.round(width * height * DENSITY)));
      if (stars.length !== count) stars = Array.from({ length: count }, () => spawn(NEAR + Math.random() * (FAR - NEAR)));
      draw();
    };

    const loop = (now: number): void => {
      const dt = Math.min(0.05, Math.max(0, (now - last) / 1000));
      last = now;
      advance(dt);
      draw();
      frameId = requestAnimationFrame(loop);
    };

    const start = (): void => {
      if (motionOff || frameId !== 0 || document.hidden) return;
      last = performance.now();
      frameId = requestAnimationFrame(loop);
    };

    const stop = (): void => {
      if (frameId !== 0) cancelAnimationFrame(frameId);
      frameId = 0;
    };

    const onVisibility = (): void => (document.hidden ? stop() : start());

    resize();
    const observer = typeof ResizeObserver === "function" ? new ResizeObserver(resize) : null;
    observer?.observe(canvas);
    document.addEventListener("visibilitychange", onVisibility);
    start();

    return () => {
      stop();
      observer?.disconnect();
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [ref, motionOff]);

  return ref;
}
