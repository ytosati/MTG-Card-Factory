// Concept D "Forge" (tasks.md T251): the anvil every screen shares, with its light, fire, embers and floating card.
import { useId, type ReactNode, type Ref } from "react";

import { EMBERS, RUNE_CIRCLE, forgeFire } from "../fx/effects";
import { PixelFx } from "../fx/PixelFx";
import type { ManaColor } from "../symbols/manaSymbols";
import styles from "./forge.module.css";

export type Fire = "off" | "low" | "roar";

/** Where the three tongues of the fire bed stand, as shares of the anvil's width from its centre. */
const TONGUES = [
  { at: -0.34, seed: 8 },
  { at: 0.34, seed: 21 },
  { at: 0, seed: 34 },
] as const;

/** An anvil on a stone plinth, in profile, horn to the left; drawn crisp so it reads as part of the page. */
export function Anvil({ className }: { className?: string }) {
  const id = useId().replace(/:/g, "");
  return (
    <svg className={className} viewBox="0 0 360 164" aria-hidden="true" focusable="false">
      <defs>
        <linearGradient id={`${id}-iron`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#5d4f6e" />
          <stop offset="0.2" stopColor="#3a2f48" />
          <stop offset="0.55" stopColor="#241c2e" />
          <stop offset="1" stopColor="#15101c" />
        </linearGradient>
        <linearGradient id={`${id}-stone`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#2b2235" />
          <stop offset="1" stopColor="#15111c" />
        </linearGradient>
        <linearGradient id={`${id}-face`} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#f6d78a" stopOpacity="0" />
          <stop offset="0.35" stopColor="#f6d78a" stopOpacity="0.9" />
          <stop offset="0.7" stopColor="#e8b33a" stopOpacity="0.9" />
          <stop offset="1" stopColor="#a8761c" stopOpacity="0.6" />
        </linearGradient>
      </defs>
      {/* The plinth: a dressed stone block, gold-edged. */}
      <path d="M44 134 H316 L326 160 H34 Z" fill={`url(#${id}-stone)`} />
      <path d="M44 134 H316" stroke="#a8761c" strokeWidth="1.5" />
      <path d="M70 147 H130 M160 147 H250 M276 147 H300" stroke="#0b0810" strokeWidth="1.5" strokeLinecap="round" />
      {/* The anvil: horn, face, heel, waist and feet in one outline. */}
      <path
        d="M4 26 C30 20 52 17 82 17 H330 L334 21 V40 L304 46 C270 51 254 62 250 98 L268 112 L284 134 H76 L92 112 L112 98 C110 66 98 52 72 47 C44 42 22 36 4 26 Z"
        fill={`url(#${id}-iron)`}
        stroke="#0b0810"
        strokeWidth="1.5"
      />
      <path d="M8 25 C32 20 54 18 82 18 H330" fill="none" stroke={`url(#${id}-face)`} strokeWidth="2.5" strokeLinecap="round" />
      <path d="M82 23 H330" stroke="#ece6f5" strokeOpacity="0.08" strokeWidth="5" />
      <path d="M90 112 H270" stroke="#a8761c" strokeOpacity="0.7" strokeWidth="1.5" />
      {/* Rim light: violet from the room on the left edges, warm from the fire on the right. */}
      <path d="M8 29 C30 37 50 43 72 48 C98 53 110 66 112 97" fill="none" stroke="#8b3dff" strokeOpacity="0.55" strokeWidth="1.6" />
      <path d="M333 22 V39 L304 45 C270 50 255 61 251 97 L267 111" fill="none" stroke="#f2a03a" strokeOpacity="0.6" strokeWidth="1.6" />
      {/* An engraved violet rune on the waist. */}
      <path d="M181 66 L190 78 L181 90 L172 78 Z" fill="none" stroke="#8b3dff" strokeWidth="1.8" />
      <path d="M181 72 V84" stroke="#b48bff" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

/** A brass valve wheel seen from the front, for pipes on the page. */
export function Valve({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <circle cx="12" cy="12" r="9.5" fill="none" stroke="#e8b33a" strokeWidth="3" />
      <circle cx="12" cy="12" r="9.5" fill="none" stroke="#4a3410" strokeWidth="0.8" strokeOpacity="0.8" />
      <path d="M12 3.5 V20.5 M3.5 12 H20.5" stroke="#c99428" strokeWidth="2.4" />
      <circle cx="12" cy="12" r="3.4" fill="#8b3dff" stroke="#f6d78a" strokeWidth="1.4" />
    </svg>
  );
}

type AnvilStageProps = {
  /** What floats over the anvil: an empty frame, the card being forged, the card itself. */
  card: ReactNode;
  colors: readonly ManaColor[];
  fire?: Fire;
  embers?: "off" | "faint" | "full";
  /** A rune circle turning on the anvil's face, under the card. */
  runes?: boolean;
  /** A slow bob of the card; off while it turns over. */
  float?: boolean;
  size?: "md" | "lg" | "xl";
  /** Goblins, pipes and one-shot effects, placed by each screen against the stage's floor. */
  children?: ReactNode;
  stageRef?: Ref<HTMLDivElement>;
  className?: string;
  data?: Record<`data-${string}`, string>;
};

/**
 * The stage: no frame, only light on the page, an anvil on the floor line and the card above it. Everything
 * decorative ignores the pointer and is hidden from assistive technology; the card keeps its own semantics.
 */
export function AnvilStage(props: AnvilStageProps) {
  const { card, colors, fire = "off", embers = "faint", runes = false, float = true, size = "lg", children } = props;
  const flame = forgeFire(colors);
  return (
    <div
      ref={props.stageRef}
      className={[styles.stage, props.className].filter(Boolean).join(" ")}
      data-size={size}
      data-fire={fire}
      {...props.data}
    >
      <span className={styles.light} aria-hidden="true" />
      <div className={styles.floatArea}>
        <div className={styles.float} data-float={float ? "true" : "false"}>
          {card}
        </div>
      </div>
      <div className={styles.anvilArea}>
        {fire !== "off" && (
          <span className={styles.fireBed} aria-hidden="true">
            {TONGUES.map((tongue) => (
              <span key={tongue.seed} className={styles.tongue} style={{ left: `${50 + tongue.at * 100}%` }}>
                <PixelFx
                  effect={flame.effect}
                  options={{ ...flame.options, seed: tongue.seed }}
                  width={flame.width}
                  height={flame.height}
                  origin={flame.origin}
                  vignette
                  speed={0.9}
                  scale={3}
                />
              </span>
            ))}
          </span>
        )}
        <span className={styles.cardShadow} aria-hidden="true" />
        {runes && (
          <span className={styles.runes} aria-hidden="true">
            <PixelFx effect={RUNE_CIRCLE.effect} options={RUNE_CIRCLE.options} width={RUNE_CIRCLE.width} height={RUNE_CIRCLE.height} scale={2} />
          </span>
        )}
        <Anvil className={styles.anvil} />
        {embers !== "off" && (
          <span className={styles.embers} data-level={embers} aria-hidden="true">
            <PixelFx
              effect={EMBERS.effect}
              options={{ ...EMBERS.options, count: embers === "full" ? 40 : 12, width: 56 }}
              width={EMBERS.width * 2}
              height={EMBERS.height}
              scale={3}
              speed={embers === "full" ? 1 : 0.6}
            />
          </span>
        )}
      </div>
      {children}
    </div>
  );
}
