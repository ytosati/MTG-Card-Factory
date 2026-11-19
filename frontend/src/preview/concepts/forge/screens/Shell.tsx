// Concept D "Forge" (tasks.md T251): the page of every screen, its header and manifold, and the shared controls.
import { useId, type ReactNode } from "react";

import { STEAM_VENT } from "../fx/effects";
import { PixelFx } from "../fx/PixelFx";
import { SoundToggle } from "../sound/SoundToggle";
import { Valve } from "./Forge";
import { GearMark } from "./ornaments";
import styles from "./shell.module.css";

export type Place = "Request" | "Library" | "Status";

/** Where the header's valves sit along the manifold, as shares of its width; the second shows on wide pages only. */
const VALVES = [
  { at: 44, seed: 4, wide: false },
  { at: 66, seed: 11, wide: true },
] as const;

/** The gold manifold along the header's lower edge: collars, two valves and their slow puffs of steam. */
function Manifold() {
  return (
    <span className={styles.manifold} aria-hidden="true">
      {[6, 24, 52, 81, 95].map((at) => (
        <span key={at} className={styles.joint} style={{ left: `${at}%` }} />
      ))}
      {VALVES.map((valve) => (
        <span key={valve.at} className={styles.valve} data-wide={valve.wide ? "true" : "false"} style={{ left: `${valve.at}%` }}>
          <span className={styles.steam}>
            <PixelFx
              effect={STEAM_VENT.effect}
              options={{ ...STEAM_VENT.options, seed: valve.seed, puffs: 14, burst: 0.4 }}
              width={STEAM_VENT.width}
              height={STEAM_VENT.height}
              scale={2}
              speed={0.42}
            />
          </span>
          <Valve />
        </span>
      ))}
    </span>
  );
}

/** The dark ground, the header with the wordmark, the places, the sound switch and the manifold. */
export function Shell({ current, working = false, children }: { current: Place; working?: boolean; children: ReactNode }) {
  return (
    <div className={styles.root}>
      <header className={styles.bar}>
        <Manifold />
        <span className={styles.brand}>
          <span className={styles.brandMark} data-working={working ? "true" : "false"}>
            <GearMark />
          </span>
          Card Factory
        </span>
        <nav aria-label="Main" className={styles.navWrap}>
          <ul className={styles.nav}>
            {(["Request", "Library", "Status"] as const).map((item) => (
              <li key={item}>
                <span className={styles.navItem} aria-current={item === current ? "page" : undefined}>
                  {item}
                </span>
              </li>
            ))}
          </ul>
          <SoundToggle className={styles.sound} />
        </nav>
      </header>
      <main className={styles.main}>{children}</main>
    </div>
  );
}

/** Four brass rivets in the corners of a plate. */
export function Rivets() {
  return (
    <>
      {(["tl", "tr", "bl", "br"] as const).map((at) => (
        <span key={at} className={styles.rivet} data-at={at} aria-hidden="true" />
      ))}
    </>
  );
}

/** A section heading engraved between two gold rules. */
export function Engraved({ id, children }: { id: string; children: ReactNode }) {
  return (
    <h2 id={id} className={styles.engraved}>
      <span>{children}</span>
    </h2>
  );
}

/** A choice of one, cut into a brass groove; the chosen option is a raised violet key. */
export function Segmented<T extends string>(props: {
  legend: string;
  choices: { value: T; name: string }[];
  value: T;
  onChange: (value: T) => void;
  hint?: string;
}) {
  const name = useId();
  const hintId = useId();
  return (
    <fieldset className={styles.fieldset} aria-describedby={props.hint ? hintId : undefined}>
      <legend className={styles.rubric}>{props.legend}</legend>
      <div className={styles.groove}>
        {props.choices.map((choice) => (
          <label key={choice.value} className={styles.key}>
            <input
              className={styles.srOnly}
              type="radio"
              name={name}
              value={choice.value}
              checked={props.value === choice.value}
              onChange={() => props.onChange(choice.value)}
            />
            <span>{choice.name}</span>
          </label>
        ))}
      </div>
      {props.hint && (
        <p id={hintId} className={styles.hint}>
          {props.hint}
        </p>
      )}
    </fieldset>
  );
}

export { styles as shell };
