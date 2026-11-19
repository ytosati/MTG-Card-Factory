// Concept D "Forge" (tasks.md T251): a color toggle drawn as a large mana symbol, with a burst themed per color.
import { useState, type CSSProperties, type ReactElement } from "react";

import { playPick } from "../sound/forgeAudio";
import { ManaSymbol } from "./ManaSymbol";
import type { ManaColor } from "./manaSymbols";
import styles from "./ManaPick.module.css";

type Vars = CSSProperties & Record<`--${string}`, string>;

const RAYS = Array.from({ length: 12 }, (_, index) => index * 30);
const RIPPLES = [0, 130, 260];
const WISPS = [
  { x: -0.3, drift: -0.18, delay: 0 },
  { x: -0.08, drift: 0.2, delay: 70 },
  { x: 0.16, drift: -0.12, delay: 30 },
  { x: 0.32, drift: 0.16, delay: 110 },
  { x: 0.02, drift: -0.05, delay: 150 },
];
const EMBERS = [
  [-0.62, -0.95, 0], [-0.3, -1.15, 40], [0.05, -1.25, 10], [0.36, -1.1, 60], [0.66, -0.88, 20],
  [-0.48, -0.6, 90], [0.52, -0.62, 80], [-0.15, -0.85, 120], [0.2, -0.78, 140], [0.78, -0.4, 50],
  [-0.8, -0.38, 70], [0.0, -0.55, 160],
] as const;
const LEAVES = [0, 52, 104, 156, 208, 260, 312];
const GLINTS = [
  { x: -0.42, y: -0.36, delay: 120 },
  { x: 0.44, y: -0.2, delay: 220 },
  { x: 0.3, y: 0.42, delay: 300 },
  { x: -0.36, y: 0.34, delay: 380 },
];

const ms = (value: number) => `${value}ms`;

/** The short animation around a symbol that has just been checked, themed per color. */
function Burst({ letter }: { letter: ManaColor }) {
  const parts: Record<ManaColor, () => ReactElement[]> = {
    W: () => [<span key="flash" className={styles.flash} />, ...RAYS.map((angle) => <span key={angle} className={styles.ray} style={{ "--a": `${angle}deg` } as Vars} />)],
    U: () => RIPPLES.map((delay) => <span key={delay} className={styles.ripple} style={{ animationDelay: ms(delay) }} />),
    B: () =>
      WISPS.map((wisp, index) => (
        <span key={index} className={styles.wisp} style={{ "--x": String(wisp.x), "--drift": String(wisp.drift), animationDelay: ms(wisp.delay) } as Vars} />
      )),
    R: () =>
      EMBERS.map(([dx, dy, delay], index) => (
        <span key={index} className={styles.ember} style={{ "--dx": String(dx), "--dy": String(dy), animationDelay: ms(delay) } as Vars} />
      )),
    G: () => LEAVES.map((angle, index) => <span key={angle} className={styles.leaf} style={{ "--a": `${angle}deg`, animationDelay: ms(index * 25) } as Vars} />),
    C: () => [
      <span key="sweep" className={styles.sweepClip}>
        <span className={styles.sweep} />
      </span>,
      ...GLINTS.map((glint, index) => (
        <span key={index} className={styles.glint} style={{ "--x": String(glint.x), "--y": String(glint.y), animationDelay: ms(glint.delay) } as Vars} />
      )),
    ],
  };
  return (
    <span className={styles.burst} aria-hidden="true">
      {parts[letter]()}
    </span>
  );
}

type ManaPickProps = {
  letter: ManaColor;
  checked: boolean;
  onChange: (checked: boolean) => void;
  /** The visible name under the symbol, which is also the toggle's accessible name. */
  label: string;
  /** Plays the color's pick sound when checked; the sound store's mute still applies. */
  sound?: boolean;
};

/** A color toggle: a native checkbox shown as the color's large mana symbol and its name. */
export function ManaPick({ letter, checked, onChange, label, sound = true }: ManaPickProps) {
  const [bursts, setBursts] = useState(0);
  return (
    <label className={styles.pick} data-color={letter}>
      <input
        type="checkbox"
        className={styles.input}
        checked={checked}
        onChange={(event) => {
          const next = event.target.checked;
          if (next) {
            setBursts((count) => count + 1);
            if (sound) playPick(letter);
          }
          onChange(next);
        }}
      />
      <span className={styles.face}>
        <span key={bursts} className={checked && bursts > 0 ? styles.pop : undefined}>
          <ManaSymbol symbol={`{${letter}}`} size="var(--pick-size)" decorative />
        </span>
        {checked && bursts > 0 ? <Burst key={bursts} letter={letter} /> : null}
      </span>
      <span className={styles.name}>{label}</span>
    </label>
  );
}
