// Concept D "Forge" (tasks.md T251): a color toggle drawn as a large mana symbol, with a pixel burst per color.
import { useState } from "react";

import { PICK_BURST } from "../fx/effects";
import { PixelFx } from "../fx/PixelFx";
import { playPick } from "../sound/forgeAudio";
import { ManaSymbol } from "./ManaSymbol";
import type { ManaColor } from "./manaSymbols";
import styles from "./ManaPick.module.css";

/** Screen pixels per effect pixel: the bursts reach about twice the symbol's size. */
const BURST_SCALE = 2;

/** The pixel burst round a symbol that has just been checked, themed per color. */
function Burst({ letter }: { letter: ManaColor }) {
  const spec = PICK_BURST[letter];
  return (
    <span className={styles.burst} aria-hidden="true">
      <PixelFx
        effect={spec.effect}
        options={spec.options}
        width={spec.width}
        height={spec.height}
        origin={spec.origin}
        scale={BURST_SCALE}
        mode="once"
        style={{ position: "absolute", left: (-spec.width * BURST_SCALE) / 2, top: (-spec.height * BURST_SCALE) / 2 }}
      />
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
