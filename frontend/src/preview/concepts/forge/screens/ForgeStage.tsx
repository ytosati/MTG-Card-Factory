// Concept D "Forge" (tasks.md T251): the forge in its riveted plate, with a layer laid exactly on the card slot.
import type { CSSProperties, ReactNode, Ref } from "react";

import type { GenerationStep } from "../../../../screens/request/copy";
import { CARD_SLOT, ForgeScene, type ForgePhase } from "../machine/ForgeScene";
import type { ManaLetter } from "../machine/palette";
import { Rivets } from "./Shell";
import styles from "./stage.module.css";

const SLOT_STYLE: CSSProperties = {
  left: `${CARD_SLOT.left}%`,
  top: `${CARD_SLOT.top}%`,
  width: `${CARD_SLOT.width}%`,
  height: `${CARD_SLOT.height}%`,
};

type ForgeStageProps = {
  phase: ForgePhase;
  step?: GenerationStep;
  colors: ManaLetter[];
  /** What sits in the card slot. */
  slot: ReactNode;
  /** Effects drawn over the whole scene, under the slot. */
  effects?: ReactNode;
  stageRef?: Ref<HTMLDivElement>;
  className?: string;
  data?: Record<`data-${string}`, string>;
};

/** The scene, the effects over it and the card slot, in one plate. */
export function ForgeStage({ phase, step, colors, slot, effects, stageRef, className, data }: ForgeStageProps) {
  return (
    <div className={[styles.plate, className].filter(Boolean).join(" ")}>
      <Rivets />
      <div ref={stageRef} className={styles.stage} {...data}>
        <ForgeScene phase={phase} step={step} colors={colors} className={styles.scene} />
        {effects}
        <div className={styles.slot} style={SLOT_STYLE}>
          {slot}
        </div>
      </div>
    </div>
  );
}

export { SLOT_STYLE };
