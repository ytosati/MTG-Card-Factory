// Concept D "Forge" (tasks.md T251): the Request screen; the form is the hero and the goblin crew works around it.
import { useEffect, useId, useRef, useState, type CSSProperties, type FormEvent } from "react";

import type { PowerLevel } from "../../../../api/types";
import { requestCopy, type GenerationEffort } from "../../../../screens/request/copy";
import { flameFor, forgeFire } from "../fx/effects";
import { PixelFx } from "../fx/PixelFx";
import { Goblin } from "../goblins/Goblin";
import { playLever } from "../sound/forgeAudio";
import { ManaPick } from "../symbols/ManaPick";
import type { ManaColor } from "../symbols/manaSymbols";
import { AnvilStage } from "./Forge";
import { EmptyCard } from "./ForgeCard";
import { SmallGauge } from "./ornaments";
import forge from "./forge.module.css";
import { Rivets, Segmented, Shell, shell } from "./Shell";
import styles from "./request.module.css";

type Vars = CSSProperties & Record<`--${string}`, string>;

export const IDEA =
  "A lantern-bearing spirit that keeps watch at the city gate and steadies the soldiers who stand beside it.";

/** Where the demo goes when the furnace is lit: the Generating state of this concept. */
const GENERATING_HASH = "#/preview/concept-forge/generating";
/** Time for the lever to swing and the fire to roar before the demo moves on. */
const PULL_MS = 950;

const PICKS: { letter: ManaColor; name: string }[] = [
  ...requestCopy.colors.map(({ letter, name }) => ({ letter, name })),
  { letter: "C", name: requestCopy.colorless },
];

/**
 * The fire behind the furnace door's grate, in the picked colors; it roars once the lever is pulled. The roar is
 * drawn by scaling the canvas, so the running flame is never rebuilt.
 */
function FurnaceFire({ colors, roaring }: { colors: readonly ManaColor[]; roaring: boolean }) {
  const flame = forgeFire(colors);
  return (
    <span className={styles.fire} data-roaring={roaring ? "true" : "false"}>
      <PixelFx
        effect={flame.effect}
        options={flame.options}
        width={flame.width}
        height={flame.height}
        origin={flame.origin}
        vignette
        scale={2}
        speed={0.8}
      />
    </span>
  );
}

/** The Request screen: the idea, the colors as mana picks, power and effort, and the furnace door that starts it. */
export function RequestScreen() {
  const [idea, setIdea] = useState(IDEA);
  const [colors, setColors] = useState<ManaColor[]>(["W"]);
  const [power, setPower] = useState<PowerLevel>("medium");
  const [effort, setEffort] = useState<GenerationEffort>("medium");
  const [pulled, setPulled] = useState(false);
  const timer = useRef<number | undefined>(undefined);
  const ideaId = useId();
  const hintId = useId();

  useEffect(() => () => window.clearTimeout(timer.current), []);

  function pick(letter: ManaColor, checked: boolean) {
    if (letter === "C") {
      setColors(checked ? ["C"] : []);
      return;
    }
    setColors((current) => {
      const colored = current.filter((entry) => entry !== "C");
      return checked ? [...colored, letter] : colored.filter((entry) => entry !== letter);
    });
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (pulled) return;
    setPulled(true);
    playLever();
    timer.current = window.setTimeout(() => {
      window.location.hash = GENERATING_HASH;
    }, PULL_MS);
  }

  const powerMeaning = requestCopy.powerLevels.find((level) => level.value === power)?.meaning;
  const effortMeaning = requestCopy.efforts.find((level) => level.value === effort)?.meaning;
  const glow = flameFor(colors)[4] ?? "#f59a2a";

  return (
    <Shell current="Request">
      <div className={styles.grid}>
        <div className={styles.head}>
          <p className={shell.rubric}>New card</p>
          <h1 className={shell.display}>Request a card</h1>
        </div>

        <form className={styles.form} onSubmit={submit}>
          <div className={styles.panel}>
            <Goblin who="engineer" action="sit" scale={3} className={styles.sitter} />
            <Rivets />
            <div>
              <label className={`${shell.rubric} ${styles.ideaLabel}`} htmlFor={ideaId}>
                {requestCopy.fieldLabels.idea}
              </label>
              <textarea
                id={ideaId}
                className={styles.idea}
                value={idea}
                onChange={(event) => setIdea(event.target.value)}
                aria-describedby={hintId}
                rows={4}
              />
              <p id={hintId} className={shell.hint}>
                A mechanic, a creature or a moment, in a sentence or two.
              </p>
            </div>

            <fieldset className={shell.fieldset}>
              <legend className={shell.rubric}>Colors</legend>
              <div className={styles.picks}>
                {PICKS.map(({ letter, name }) => (
                  <span key={letter} className={letter === "C" ? styles.colorless : undefined}>
                    <ManaPick
                      letter={letter}
                      label={name}
                      checked={colors.includes(letter)}
                      onChange={(checked) => pick(letter, checked)}
                    />
                  </span>
                ))}
              </div>
            </fieldset>

            <Segmented legend="Power" choices={requestCopy.powerLevels} value={power} onChange={setPower} hint={powerMeaning} />
            <Segmented legend="Effort" choices={requestCopy.efforts} value={effort} onChange={setEffort} hint={effortMeaning} />
          </div>

          <div className={styles.furnaceRow}>
            <button
              type="submit"
              className={styles.furnace}
              data-pulled={pulled ? "true" : "false"}
              style={{ "--glow": glow } as Vars}
            >
              <span className={styles.door} aria-hidden="true">
                <FurnaceFire colors={colors} roaring={pulled} />
                <span className={styles.bars} />
              </span>
              <span className={styles.plate}>
                <Rivets />
                <span className={styles.label}>{requestCopy.generate}</span>
              </span>
            </button>
            <span className={styles.crew} aria-hidden="true">
              <Goblin who="operator" action={pulled ? "pull" : "idle"} scale={3} flip className={styles.operator} />
            </span>
          </div>
        </form>

        <div className={styles.stageCol}>
          <span className={styles.drop} aria-hidden="true">
            <span className={styles.dropPipe}>
              <span className={styles.dropCollar} style={{ top: "14%" }} />
              <span className={styles.dropCollar} style={{ bottom: "8px" }} />
            </span>
            <SmallGauge className={styles.gauge} value={0.34} />
            <span className={styles.nozzle} />
            <span className={styles.pilot} />
          </span>
          <AnvilStage size="md" className={styles.stage} colors={colors} card={<EmptyCard colors={colors} />} embers="faint">
            <span className={`${forge.pipe} ${styles.feed}`} aria-hidden="true">
              <span className={forge.collar} style={{ left: "18%" }} />
              <span className={forge.collar} style={{ right: "12%" }} />
            </span>
            <Goblin who="sage" scale={3} flip className={`${forge.goblin} ${styles.sage}`} />
          </AnvilStage>
        </div>
      </div>
    </Shell>
  );
}
