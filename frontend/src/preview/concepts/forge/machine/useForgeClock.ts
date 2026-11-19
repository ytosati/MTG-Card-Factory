// Shared animation clock of the forge scene: stepped frames from one requestAnimationFrame loop (tasks.md T251).
import { useEffect, useRef, useState } from "react";

export const WORK_FPS = 10;
const AMBIENT_FPS = 4;
/** Seconds the machines take to wind down once cooling starts. */
const WIND_DOWN_S = 1.6;
/** Frames after which the cooling scene is at rest and only the ambient loop runs. */
const SINCE_CAP = 60;

export interface ForgeClock {
  /** Machine frame: advances at full speed while working, slows to a stop while cooling. */
  work: number;
  /** Slow frame for embers and breathing, running in every phase. */
  ambient: number;
  /** Frames since the phase or the step last changed, capped. */
  since: number;
}

const STILL: ForgeClock = { work: 2, ambient: 0, since: SINCE_CAP };

/** Ticks while mounted; `still` freezes it on a fixed frame (reduced motion). */
export function useForgeClock(phase: "idle" | "working" | "cooling", step: string | undefined, still: boolean): ForgeClock {
  const [clock, setClock] = useState<ForgeClock>({ work: 0, ambient: 0, since: 0 });
  const work = useRef(0);
  const ambientStart = useRef<number | null>(null);

  useEffect(() => {
    if (still || typeof requestAnimationFrame !== "function") return undefined;
    let frame = 0;
    let start: number | null = null;
    let last = 0;
    const tick = (now: number): void => {
      if (start === null) {
        start = now;
        last = now;
      }
      ambientStart.current ??= now;
      const elapsed = (now - start) / 1000;
      const dt = Math.min(0.1, (now - last) / 1000);
      last = now;
      const speed = phase === "working" ? 1 : phase === "cooling" ? Math.max(0, 1 - elapsed / WIND_DOWN_S) : 0;
      work.current += dt * speed;
      const next: ForgeClock = {
        work: Math.floor(work.current * WORK_FPS),
        ambient: Math.floor(((now - ambientStart.current) / 1000) * AMBIENT_FPS),
        // Idle needs no fast counter, so it re-renders only at the ambient rate.
        since: phase === "idle" ? 0 : Math.min(SINCE_CAP, Math.floor(elapsed * WORK_FPS)),
      };
      setClock((prev) =>
        prev.work === next.work && prev.ambient === next.ambient && prev.since === next.since ? prev : next,
      );
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [phase, step, still]);

  return still ? STILL : clock;
}
