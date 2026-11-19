// Concept D "Forge" (tasks.md T251): one pixelfx effect drawn live into a small canvas scaled up with crisp pixels.
import { useEffect, useRef, type CSSProperties } from "react";

import { clearFrame, composite, createFrame, createFx } from "../../../../vendor/pixelfx/core/index.js";
import { useMotionOff } from "../screens/motion";

/** What PixelFx reads from an effect module of the vendored library; the module itself does the drawing. */
export interface PixelFxEffect {
  readonly meta: {
    readonly name?: string;
    readonly duration?: number;
    readonly loop?: boolean;
    readonly size?: readonly number[];
    readonly origin?: readonly number[];
  };
}

/** An effect's options: its palette (hex ramp, dark to bright), seed and its own knobs. */
export type PixelFxOptions = Readonly<Record<string, string | number | boolean | readonly string[]>>;

type Tick = (dt: number) => void;

// One requestAnimationFrame loop for every effect on the page; it stops while the tab is hidden or nothing plays.
const ticks = new Set<Tick>();
let frameId = 0;
let last = 0;
let listening = false;

function loop(now: number): void {
  // A long gap (a stall, a debugger) would make simulations jump; steps are capped.
  const dt = Math.min(0.05, Math.max(0, (now - last) / 1000));
  last = now;
  for (const tick of [...ticks]) tick(dt);
  frameId = ticks.size > 0 && !document.hidden ? requestAnimationFrame(loop) : 0;
}

function startClock(): void {
  if (frameId !== 0 || ticks.size === 0 || document.hidden || typeof requestAnimationFrame !== "function") return;
  last = performance.now();
  frameId = requestAnimationFrame(loop);
}

function stopClock(): void {
  if (frameId !== 0) cancelAnimationFrame(frameId);
  frameId = 0;
}

function subscribe(tick: Tick): () => void {
  if (!listening) {
    listening = true;
    document.addEventListener("visibilitychange", () => (document.hidden ? stopClock() : startClock()));
  }
  ticks.add(tick);
  startClock();
  return () => {
    ticks.delete(tick);
    if (ticks.size === 0) stopClock();
  };
}

/** Where a loop stops under reduced motion: a share of its length that shows it at full strength. */
const STILL_AT = 0.4;

export type PixelFxProps = {
  effect: PixelFxEffect;
  options?: PixelFxOptions;
  /** The canvas in effect pixels. */
  width: number;
  height: number;
  /** Screen pixels per effect pixel. */
  scale?: number;
  /** "loop" plays forever; "once" plays the effect through and leaves the canvas empty. Default: the effect's own. */
  mode?: "loop" | "once";
  /** A one-shot plays again whenever this changes. */
  playKey?: string | number;
  /** The effect's anchor in canvas pixels; by default the effect's own box is centred in the canvas. */
  origin?: { x: number; y: number };
  /** Playback rate: 1 is the effect's own timing. */
  speed?: number;
  /** Fades the canvas edges, so a glow that reaches them ends softly instead of in a straight line. */
  vignette?: boolean;
  onDone?: () => void;
  className?: string;
  style?: CSSProperties;
};

function defaultOrigin(effect: PixelFxEffect, width: number, height: number): { x: number; y: number } {
  const [sw = width, sh = height] = effect.meta.size ?? [];
  const [ox = sw / 2, oy = sh / 2] = effect.meta.origin ?? [];
  return { x: Math.round(width / 2 - sw / 2 + ox), y: Math.round(height / 2 - sh / 2 + oy) };
}

/** A pixelfx effect played live on a transparent canvas, for absolute overlays on the page. Decorative only. */
export function PixelFx({ effect, options, width, height, scale = 3, mode, playKey, origin, speed = 1, vignette = false, onDone, className, style }: PixelFxProps) {
  const [ref, motionOff] = useMotionOff<HTMLCanvasElement>();
  const done = useRef(onDone);
  done.current = onDone;
  const at = origin ?? defaultOrigin(effect, width, height);
  const once = mode ? mode === "once" : !effect.meta.loop;
  // Options arrive as fresh objects on every render; their text decides when the effect is rebuilt.
  const optionsKey = JSON.stringify(options ?? {});

  useEffect(() => {
    const canvas = ref.current;
    const context = canvas?.getContext("2d") ?? null;
    if (!canvas || !context) return undefined;
    const frame = createFrame(width, height);
    const image = context.createImageData(width, height);
    const make = () => createFx(effect, { ...(JSON.parse(optionsKey) as PixelFxOptions), x: at.x, y: at.y });
    let fx = make();
    const duration = effect.meta.duration ?? 1;
    const loops = effect.meta.loop === true;
    const paint = (): void => {
      clearFrame(frame);
      fx.draw(frame);
      composite(frame, image.data, null);
      context.putImageData(image, 0, 0);
    };

    if (motionOff) {
      context.clearRect(0, 0, width, height);
      if (once) done.current?.();
      else {
        fx.update(duration * STILL_AT);
        paint();
      }
      return undefined;
    }

    let finished = false;
    let unsubscribe: (() => void) | null = null;
    const tick = (dt: number): void => {
      fx.update(dt * speed);
      // A loop played once fades out after one pass; a one-shot played as a loop starts over.
      if (once && loops && fx.t >= duration) fx.stop();
      if (!once && fx.done()) fx = make();
      if (once && fx.done()) {
        finished = true;
        context.clearRect(0, 0, width, height);
        unsubscribe?.();
        unsubscribe = null;
        done.current?.();
        return;
      }
      paint();
    };
    const play = (on: boolean): void => {
      if (on && !finished && !unsubscribe) unsubscribe = subscribe(tick);
      else if (!on && unsubscribe) {
        unsubscribe();
        unsubscribe = null;
      }
    };

    // Offscreen effects stop ticking; where the observer is missing they always play.
    let observer: IntersectionObserver | null = null;
    if (typeof IntersectionObserver === "function") {
      observer = new IntersectionObserver((entries) => play(entries.some((entry) => entry.isIntersecting)));
      observer.observe(canvas);
    } else play(true);

    return () => {
      observer?.disconnect();
      play(false);
      context.clearRect(0, 0, width, height);
    };
    // playKey is a dependency on purpose: a new key rebuilds the effect and replays it.
  }, [ref, effect, optionsKey, width, height, at.x, at.y, once, speed, motionOff, playKey]);

  const mask = vignette ? "radial-gradient(closest-side, #000 72%, transparent 100%)" : undefined;
  return (
    <canvas
      ref={ref}
      width={width}
      height={height}
      aria-hidden="true"
      className={className}
      style={{ display: "block", width: width * scale, height: height * scale, imageRendering: "pixelated", pointerEvents: "none", maskImage: mask, WebkitMaskImage: mask, ...style }}
    />
  );
}
