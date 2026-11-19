// Goblin crew (tasks.md T251): one goblin playing one action, as a crisp inline SVG with one path per colour.
import { useEffect, useRef, useState, useSyncExternalStore, type CSSProperties, type RefObject } from "react";

import { toPaths } from "../machine/pixelArt";
import { CLOCK_FPS, clockTick, subscribeClock } from "./clock";
import { GOBLIN_PALETTE } from "./palette";
import { goblinAnimation } from "./sprites";
import { CANVAS, type GoblinAction, type GoblinName } from "./types";

export interface GoblinProps {
  who: GoblinName;
  /** Actions a goblin does not know fall back to its idle. */
  action?: GoblinAction;
  /** Screen pixels per logical pixel. */
  scale?: number;
  /** Faces left instead of right. */
  flip?: boolean;
  className?: string;
  style?: CSSProperties;
}

const QUERY = "(prefers-reduced-motion: reduce)";

function systemReduced(): boolean {
  return typeof window !== "undefined" && typeof window.matchMedia === "function" && window.matchMedia(QUERY).matches;
}

const noSubscribe = (): (() => void) => () => undefined;
const stopped = (): number => 0;

/** Whether motion is off here: the system setting, or an ancestor's data-reduced-motion switch. */
function useStill(ref: RefObject<Element | null>): boolean {
  const [still, setStill] = useState(systemReduced);
  useEffect(() => {
    const next = systemReduced() || ref.current?.closest('[data-reduced-motion="true"]') != null;
    setStill((current) => (current === next ? current : next));
  });
  useEffect(() => {
    if (typeof window.matchMedia !== "function") return undefined;
    const media = window.matchMedia(QUERY);
    const update = (): void => setStill(media.matches || ref.current?.closest('[data-reduced-motion="true"]') != null);
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, [ref]);
  return still;
}

/** A decorative goblin: hidden from assistive technology, frozen on its still frame when motion is reduced. */
export function Goblin({ who, action = "idle", scale = 3, flip = false, className, style }: GoblinProps) {
  const ref = useRef<SVGSVGElement>(null);
  const still = useStill(ref);
  const tick = useSyncExternalStore(still ? noSubscribe : subscribeClock, still ? stopped : clockTick, stopped);
  const animation = goblinAnimation(who, action);
  const frame = still ? animation.still : Math.floor((tick * animation.fps) / CLOCK_FPS) % animation.frames.length;
  const rows = animation.frames[frame] ?? animation.frames[0] ?? [];
  const size = CANVAS * scale;

  return (
    <svg
      ref={ref}
      className={className}
      style={{ imageRendering: "pixelated", display: "block", ...style }}
      width={size}
      height={size}
      viewBox={`0 0 ${CANVAS} ${CANVAS}`}
      shapeRendering="crispEdges"
      aria-hidden="true"
      focusable="false"
      data-goblin={who}
      data-action={action}
    >
      <g transform={flip ? `matrix(-1 0 0 1 ${CANVAS} 0)` : undefined}>
        {toPaths(rows).map(([ch, d]) => (
          <path key={ch} d={d} fill={GOBLIN_PALETTE[ch] ?? "#ff00ff"} />
        ))}
      </g>
    </svg>
  );
}
