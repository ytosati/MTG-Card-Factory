// Concept D "Forge" (tasks.md T251): the Request screen; the form feeds the forge, whose embers follow the colors.
import { useEffect, useId, useRef, useState, type FormEvent } from "react";

import type { PowerLevel } from "../../../../api/types";
import { requestCopy, type GenerationEffort } from "../../../../screens/request/copy";
import { ForgeScene } from "../machine/ForgeScene";
import type { ManaLetter } from "../machine/palette";
import { playLever } from "../sound/forgeAudio";
import { ManaPick } from "../symbols/ManaPick";
import { ManaSymbol } from "../symbols/ManaSymbol";
import type { ManaColor } from "../symbols/manaSymbols";
import { Rivets, Segmented, Shell, shell } from "./Shell";
import styles from "./request.module.css";

export const IDEA =
  "A lantern-bearing spirit that keeps watch at the city gate and steadies the soldiers who stand beside it.";

/** Where the demo goes when the lever is pulled: the Generating state of this concept. */
const GENERATING_HASH = "#/preview/concept-forge/generating";
/** Time for the lever to swing down before the demo moves on. */
const LEVER_MS = 650;

const PICKS: { letter: ManaColor; name: string }[] = [
  ...requestCopy.colors.map(({ letter, name }) => ({ letter, name })),
  { letter: "C", name: requestCopy.colorless },
];

function LeverArm() {
  return (
    <svg className={styles.leverArt} viewBox="0 0 48 72" aria-hidden="true" focusable="false">
      <rect x="20" y="8" width="8" height="56" rx="4" fill="#0b0810" stroke="#a8761c" strokeWidth="1.5" />
      <g className={styles.leverArm}>
        <rect x="22" y="12" width="4" height="30" rx="2" fill="#e8b33a" />
        <circle cx="24" cy="12" r="8" fill="#7c3aed" stroke="#f6d78a" strokeWidth="2" />
        <circle cx="21.5" cy="9.5" r="2.2" fill="#c9a6ff" />
      </g>
      <circle cx="24" cy="42" r="5.5" fill="#e8b33a" stroke="#4a3410" strokeWidth="1.5" />
    </svg>
  );
}

/** The Request screen: the idea as the hero, colors as mana picks, power and effort as engraved keys. */
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
    setPulled(true);
    playLever();
    timer.current = window.setTimeout(() => {
      window.location.hash = GENERATING_HASH;
    }, LEVER_MS);
  }

  const embers = colors.filter((entry): entry is ManaLetter => entry !== "C");
  const powerMeaning = requestCopy.powerLevels.find((level) => level.value === power)?.meaning;
  const effortMeaning = requestCopy.efforts.find((level) => level.value === effort)?.meaning;
  const powerName = requestCopy.powerLevels.find((level) => level.value === power)?.name ?? "";
  const effortName = requestCopy.efforts.find((level) => level.value === effort)?.name ?? "";

  return (
    <Shell current="Request">
      <div className={styles.grid}>
        <div className={styles.head}>
          <p className={shell.rubric}>New card</p>
          <h1 className={shell.display}>Request a card</h1>
        </div>
        <div className={styles.formCol}>
          <form className={styles.form} onSubmit={submit}>
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

            <div className={styles.leverRow}>
              <button type="submit" className={styles.lever} data-pulled={pulled ? "true" : "false"}>
                <span className={styles.leverFace}>
                  <Rivets />
                  <span className={styles.leverLabel}>{requestCopy.generate}</span>
                </span>
                <span className={styles.leverSlot}>
                  <LeverArm />
                </span>
              </button>
            </div>
          </form>
        </div>

        <div className={styles.forgeCol}>
          <div className={styles.scenePlate}>
            <Rivets />
            <ForgeScene phase="idle" colors={embers} className={styles.scene} />
          </div>
          <span className={styles.pipeShort} aria-hidden="true" />
          <div className={styles.ticket}>
            <Rivets />
            <p className={shell.rubric}>Work order</p>
            <p className={styles.ticketIdea}>{idea.trim() === "" ? "No idea written yet." : idea}</p>
            <div className={styles.ticketRow}>
              <span className={styles.ticketSymbols}>
                {colors.length === 0 ? (
                  <span className={styles.ticketEmpty}>No color</span>
                ) : (
                  colors.map((letter) => <ManaSymbol key={letter} symbol={`{${letter}}`} size={22} />)
                )}
              </span>
              <span>
                {powerName} power · {effortName} effort
              </span>
            </div>
          </div>
          <div className={styles.feed} aria-hidden="true">
            <span className={styles.pipeDown} />
            <span className={styles.elbow} />
            <span className={styles.pipeAcross} />
          </div>
        </div>
      </div>
    </Shell>
  );
}
