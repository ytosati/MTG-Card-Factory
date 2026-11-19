// Animated pixel-art forge run by goblins; motion follows the generation job (tasks.md T251, concept D "Forge").
import { useEffect, useId, useRef, useState, type ReactNode } from "react";

import type { GenerationStep } from "../../../../screens/request/copy";
import { backdrop, mouthMask } from "./backdrop";
import {
  BELLOWS_SPAN,
  EMBERS,
  FLAME_BIG,
  FLAME_FRAMES,
  FLAME_SMALL,
  GEAR,
  RUNES,
  SNORE,
  SPARKLE,
  SPARKS,
  STEAM,
  WHEEL,
  bellows,
  lever,
  needle,
  piston,
} from "./effects";
import styles from "./forge.module.css";
import {
  ENGINEER_DOZE_IN,
  ENGINEER_DOZE_OUT,
  ENGINEER_DOZE_PEEK,
  ENGINEER_RAISE,
  ENGINEER_STAND,
  ENGINEER_STRIKE,
  OPERATOR_GRIP,
  OPERATOR_PULL,
  OPERATOR_READY,
  SAGE_IDLE,
  SAGE_READ,
  SAGE_READ_NOD,
} from "./goblins";
import {
  ACTORS,
  BELLOWS,
  GAUGE,
  GEAR_AXLE,
  LEVER_PIVOT,
  MOUTH,
  PISTONS,
  SCENE_H,
  SCENE_W,
  SLOT,
  VALVE,
  VENTS,
} from "./layout";
import { FLAME_COLORS, flamePalette, type FlameRamp, type ManaLetter } from "./palette";
import { Pixels, mirror, toPaths, type PixelRows } from "./pixelArt";
import { useForgeClock } from "./useForgeClock";

export { FLAME_COLORS, type FlameRamp } from "./palette";

export type ForgePhase = "idle" | "working" | "cooling";
/** The job steps, as the Request screen names them. */
export type ForgeStep = GenerationStep;

export interface ForgeSceneProps {
  phase: ForgePhase;
  /** Which job step is running; read only while working. */
  step?: ForgeStep;
  /** Chosen colours; empty means colorless. */
  colors: ManaLetter[];
  /** Freezes the scene on a still frame; prefers-reduced-motion and an ancestor's data-reduced-motion do too. */
  reducedMotion?: boolean;
  className?: string;
}

/** The empty card slot, in percent of the scene, for overlaying the finished card. */
export const CARD_SLOT = {
  left: (SLOT.x / SCENE_W) * 100,
  top: (SLOT.y / SCENE_H) * 100,
  width: (SLOT.w / SCENE_W) * 100,
  height: (SLOT.h / SCENE_H) * 100,
} as const;

const DEFAULT_EMBER = FLAME_COLORS.R;
const ARCANE = "#8b3dff";
const ENGINEER_STAND_LEFT = mirror(ENGINEER_STAND);
const ENGINEER_RAISE_LEFT = mirror(ENGINEER_RAISE);
const ENGINEER_STRIKE_LEFT = mirror(ENGINEER_STRIKE);
const DOZE = [mirror(ENGINEER_DOZE_IN), mirror(ENGINEER_DOZE_OUT), mirror(ENGINEER_DOZE_PEEK)] as const;
const STRIKE_CYCLE = [0, 1, 1, 1, 2, 2, 0, 0] as const;
/** The last big breath of steam when the work stops: a cluster over the cradle and the machines. */
const COOLING_PUFFS = [
  { at: VENTS.crown, delay: 0, spread: -8 },
  { at: VENTS.crown, delay: 1, spread: 2 },
  { at: VENTS.crown, delay: 3, spread: 11 },
  { at: { x: VENTS.crown.x + 2, y: VENTS.crown.y + 5 }, delay: 2, spread: -2 },
  { at: VENTS.boiler, delay: 0, spread: 0 },
  { at: VENTS.chimney, delay: 1, spread: 0 },
  { at: VENTS.sidePipe, delay: 2, spread: 0 },
] as const;

function usePrefersReducedMotion(): boolean {
  const query = "(prefers-reduced-motion: reduce)";
  const [reduced, setReduced] = useState(() =>
    typeof window !== "undefined" && typeof window.matchMedia === "function" ? window.matchMedia(query).matches : false,
  );
  useEffect(() => {
    if (typeof window.matchMedia !== "function") return undefined;
    const media = window.matchMedia(query);
    const update = (): void => setReduced(media.matches);
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  return reduced;
}

function emberPalette(ramp: FlameRamp, level: number): Record<string, string> {
  if (level <= 0) return { "1": ramp.deep, "2": ramp.deep, "3": ramp.dark, "4": ramp.mid };
  if (level === 1) return { "1": ramp.deep, "2": ramp.dark, "3": ramp.mid, "4": ramp.bright };
  return { "1": ramp.dark, "2": ramp.mid, "3": ramp.bright, "4": ramp.core };
}

function Puff({ at, t, spread = 0 }: { at: { x: number; y: number }; t: number; spread?: number }) {
  if (t < 0 || t > 7) return null;
  const art = STEAM[Math.min(3, Math.floor(t / 2))] ?? [];
  const w = art[0]?.length ?? 0;
  return <Pixels art={art} x={at.x - Math.floor(w / 2) + 3 + spread} y={at.y - t} opacity={t < 6 ? 0.85 : 0.45} />;
}

/** The forge scene: furnace, cradle with the empty card slot, boiler, and three goblins. */
export function ForgeScene({ phase, step, colors, reducedMotion = false, className }: ForgeSceneProps) {
  const root = useRef<HTMLDivElement>(null);
  const prefersReduced = usePrefersReducedMotion();
  const [ancestorReduced, setAncestorReduced] = useState(false);
  useEffect(() => {
    setAncestorReduced(Boolean(root.current?.closest('[data-reduced-motion="true"]')));
  });
  const still = reducedMotion || prefersReduced || ancestorReduced;
  const activeStep = phase === "working" ? step : undefined;
  const { work: f, ambient: a, since } = useForgeClock(phase, activeStep, still);
  const id = useId().replace(/:/g, "");

  const ramps: FlameRamp[] = colors.length > 0 ? colors.map((c) => FLAME_COLORS[c]) : [FLAME_COLORS.C];
  const pick = (index: number): FlameRamp => ramps[index % ramps.length] ?? FLAME_COLORS.C;
  const emberRamps = colors.length > 0 ? ramps : [DEFAULT_EMBER];
  const breath = still ? 2 : ([0, 1, 2, 1] as const)[Math.floor(a / 3) % 4] ?? 1;

  // Fire: embers at rest, a low flame while working, a roaring one for the draft and the art.
  let flame: PixelRows | null = null;
  let ramp: FlameRamp;
  let glow: number;
  const roaring = activeStep === "draft" || activeStep === "art";
  if (phase === "working") {
    const cycle = activeStep === "art" ? 4 : activeStep === "draft" ? 12 : 20;
    ramp = pick(Math.floor(f / cycle));
    flame = (roaring ? FLAME_BIG : FLAME_SMALL)[f % FLAME_FRAMES] ?? null;
    glow = (roaring ? 0.9 : 0.62) + (f % 3 === 0 ? 0.08 : 0);
  } else if (phase === "cooling" && since < 10 && !still) {
    ramp = pick(0);
    flame = FLAME_SMALL[f % FLAME_FRAMES] ?? null;
    glow = 0.62 - since * 0.03;
  } else {
    ramp = phase === "cooling" ? pick(0) : (emberRamps[Math.floor(a / 12) % emberRamps.length] ?? DEFAULT_EMBER);
    glow = 0.2 + breath * 0.1;
  }
  const emberLevel = phase === "working" ? 2 : phase === "cooling" && since < 24 ? 2 : breath;

  const pumping = phase !== "idle" && (phase === "cooling" || roaring);
  const bellowsHeight = pumping ? ([16, 14, 11, 8, 6, 8, 11, 14] as const)[f % 8] ?? 12 : 12;
  const moving = phase !== "idle";
  const pistonExt = (offset: number): number => (moving ? ([0, 2, 4, 6, 6, 4, 2, 0] as const)[(f + offset) % 8] ?? 0 : 0);

  const gaugeValue =
    phase === "idle"
      ? 0.08
      : phase === "cooling"
        ? Math.max(0.08, 0.5 - since * 0.02)
        : activeStep === "search"
          ? Math.min(0.92, 0.45 + since * 0.03) - (f % 2) * 0.04
          : 0.5 + (f % 3 === 0 ? 0.04 : 0);
  const gaugeNeedle = needle(gaugeValue);

  const pulling = activeStep === "search" && Math.floor(f / 4) % 2 === 1;
  const grip = pulling ? OPERATOR_GRIP.pull : OPERATOR_GRIP.ready;
  const leverArm = lever(ACTORS.operator.x + grip.x - LEVER_PIVOT.x, ACTORS.operator.y + grip.y - LEVER_PIVOT.y);

  const strike = activeStep === "revision" ? (STRIKE_CYCLE[f % STRIKE_CYCLE.length] ?? 0) : 0;
  const sparkFrame = activeStep === "revision" ? (f % STRIKE_CYCLE.length) - 4 : -1;
  const reading = activeStep === "design";

  let engineer: ReactNode;
  if (phase === "idle") {
    const pose = !still && a % 29 === 28 ? 2 : Math.floor(a / 5) % 2;
    engineer = <Pixels art={DOZE[pose] ?? DOZE[0]} x={ACTORS.engineerDozing.x} y={ACTORS.engineerDozing.y} />;
  } else {
    const art = [ENGINEER_STAND_LEFT, ENGINEER_RAISE_LEFT, ENGINEER_STRIKE_LEFT][strike] ?? ENGINEER_STAND_LEFT;
    engineer = <Pixels art={art} x={ACTORS.engineer.x} y={ACTORS.engineer.y} />;
  }

  const flameTop = flame ? MOUTH.bottom - flame.length + 1 : 0;
  const snoreT = a % 12;

  return (
    <div ref={root} className={[styles.scene, className].filter(Boolean).join(" ")} aria-hidden="true">
      <svg viewBox={`0 0 ${SCENE_W} ${SCENE_H}`} shapeRendering="crispEdges" className={styles.svg}>
        <defs>
          <clipPath id={`${id}-mouth`}>
            {toPaths(mouthMask()).map(([ch, d]) => (
              <path key={ch} d={d} />
            ))}
          </clipPath>
          <radialGradient id={`${id}-fire`}>
            <stop offset="0" stopColor={ramp.mid} stopOpacity="0.9" />
            <stop offset="0.45" stopColor={ramp.dark} stopOpacity="0.35" />
            <stop offset="1" stopColor={ramp.deep} stopOpacity="0" />
          </radialGradient>
          <radialGradient id={`${id}-arcane`}>
            <stop offset="0" stopColor={ARCANE} stopOpacity="0.85" />
            <stop offset="1" stopColor={ARCANE} stopOpacity="0" />
          </radialGradient>
          <radialGradient id={`${id}-vignette`} cx="0.5" cy="0.45" r="0.75">
            <stop offset="0.55" stopColor="#08060c" stopOpacity="0" />
            <stop offset="1" stopColor="#08060c" stopOpacity="0.7" />
          </radialGradient>
        </defs>

        <Pixels art={backdrop()} />

        <g clipPath={`url(#${id}-mouth)`}>
          {flame && <Pixels art={flame} x={MOUTH.cx - 13} y={flameTop} palette={flamePalette(ramp)} />}
        </g>
        <Pixels art={EMBERS} x={MOUTH.cx - 14} y={MOUTH.bottom - 3} palette={emberPalette(ramp, emberLevel)} />

        <Pixels art={bellows(bellowsHeight)} x={BELLOWS.x} y={BELLOWS.baseTop - BELLOWS_SPAN} />
        {PISTONS.map((p, i) => {
          const ext = pistonExt(i * 4);
          return <Pixels key={p.x} art={piston(ext)} x={p.x} y={p.top - (6 + ext)} />;
        })}
        <Pixels art={GEAR[moving ? f % 4 : 0] ?? []} x={GEAR_AXLE.x - 12} y={GEAR_AXLE.y - 12} />
        <Pixels art={WHEEL[activeStep === "search" ? Math.floor(f / 2) % 2 : 0] ?? []} x={VALVE.x} y={VALVE.y} />
        <Pixels art={gaugeNeedle.rows} x={GAUGE.cx + gaugeNeedle.ox} y={GAUGE.cy + gaugeNeedle.oy} />
        <Pixels art={leverArm.rows} x={LEVER_PIVOT.x + leverArm.ox} y={LEVER_PIVOT.y + leverArm.oy} />

        <Pixels
          art={reading ? (Math.floor(f / 6) % 2 === 0 ? SAGE_READ : SAGE_READ_NOD) : SAGE_IDLE}
          x={ACTORS.sage.x}
          y={ACTORS.sage.y}
        />
        {engineer}
        <Pixels art={pulling ? OPERATOR_PULL : OPERATOR_READY} x={ACTORS.operator.x} y={ACTORS.operator.y} />

        {phase === "idle" && snoreT < 10 && (
          <Pixels art={SNORE} x={164 - Math.floor(snoreT / 3)} y={90 - Math.floor(snoreT * 1.5)} opacity={1 - snoreT / 10} />
        )}
        {reading &&
          [0, 1].map((i) => {
            const t = still ? 3 + i * 3 : (f + i * 5) % 10;
            return (
              <Pixels
                key={i}
                art={SPARKLE[t % 3 === 2 ? 1 : 0] ?? []}
                x={84 + i * 5}
                y={102 - t * 2}
                opacity={1 - t / 11}
              />
            );
          })}
        {activeStep === "validation" &&
          [0, 1, 2, 3].map((i) => {
            const t = still ? 3 + i * 4 : (f + i * 5) % 20;
            const glyph = RUNES[(i + Math.floor((f + i * 5) / 20)) % RUNES.length] ?? [];
            return (
              <Pixels
                key={i}
                art={glyph}
                x={106 + i * 8 + (t % 4 < 2 ? 0 : 1)}
                y={106 - t * 3}
                opacity={t < 2 ? 0.6 : 1 - (t - 2) / 22}
              />
            );
          })}
        {sparkFrame >= 0 && sparkFrame < 2 && <Pixels art={SPARKS[sparkFrame] ?? []} x={155} y={106} />}

        {phase === "working" && !still && (
          <>
            <Puff at={VENTS.chimney} t={f % 14} />
            <Puff at={VENTS.boiler} t={(f + 5) % 10} />
            <Puff at={VENTS.sidePipe} t={(f + 9) % 18} />
            {activeStep === "search" && <Puff at={VENTS.flange} t={f % 8} />}
          </>
        )}
        {phase === "working" && still && <Puff at={VENTS.chimney} t={4} />}
        {phase === "cooling" &&
          COOLING_PUFFS.map((p, i) => (
            <Puff key={i} at={p.at} t={still ? 4 : Math.floor((since - p.delay) / 3)} spread={p.spread} />
          ))}

        <g className={styles.light}>
          <ellipse cx={MOUTH.cx} cy={MOUTH.bottom - 10} rx={78} ry={62} fill={`url(#${id}-fire)`} opacity={glow} />
          <ellipse cx={MOUTH.cx + 6} cy={SCENE_H - 14} rx={60} ry={12} fill={`url(#${id}-fire)`} opacity={glow * 0.8} />
          {reading && <ellipse cx={87} cy={108} rx={18} ry={16} fill={`url(#${id}-arcane)`} opacity={0.75} />}
          {activeStep === "validation" && (
            <ellipse
              cx={SLOT.x + SLOT.w / 2}
              cy={SLOT.y + SLOT.h}
              rx={34}
              ry={44}
              fill={`url(#${id}-arcane)`}
              opacity={0.45 + (f % 2) * 0.1}
            />
          )}
          {sparkFrame === 0 && <ellipse cx={160} cy={112} rx={16} ry={12} fill={`url(#${id}-fire)`} />}
        </g>
        <rect width={SCENE_W} height={SCENE_H} fill={`url(#${id}-vignette)`} />
      </svg>
    </div>
  );
}
