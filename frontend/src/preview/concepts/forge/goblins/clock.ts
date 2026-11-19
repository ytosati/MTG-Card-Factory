// Goblin crew (tasks.md T251): one animation clock for every goblin on the page, ticking 12 times a second
// from a single requestAnimationFrame loop that runs only while some goblin is animating.

/** Ticks per second; every action's frame rate is derived from it. */
export const CLOCK_FPS = 12;

let tick = 0;
let start: number | null = null;
let handle = 0;
const listeners = new Set<() => void>();

function loop(now: number): void {
  start ??= now;
  const next = Math.floor(((now - start) / 1000) * CLOCK_FPS);
  if (next !== tick) {
    tick = next;
    listeners.forEach((listener) => listener());
  }
  handle = requestAnimationFrame(loop);
}

export function subscribeClock(listener: () => void): () => void {
  listeners.add(listener);
  if (listeners.size === 1 && typeof requestAnimationFrame === "function") handle = requestAnimationFrame(loop);
  return () => {
    listeners.delete(listener);
    if (listeners.size === 0 && typeof cancelAnimationFrame === "function") cancelAnimationFrame(handle);
  };
}

export function clockTick(): number {
  return tick;
}
