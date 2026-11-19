// Concept D (Forge): the goblin crew with every action, next to the notes of the sketch they come from. Task T251.
import type { CSSProperties } from "react";

import { Goblin } from "./Goblin";
import { ACTIONS_OF } from "./sprites";
import { CANVAS, SEAT_ROW, type GoblinAction, type GoblinName } from "./types";

const SCALE = 4;

const CREW: ReadonlyArray<{ who: GoblinName; name: string; notes: string }> = [
  { who: "engineer", name: "Engineer", notes: "Round goggles, long pointed ears, a big nose over a toothy grin." },
  { who: "operator", name: "Operator", notes: "Mohawk. A wide mouth full of teeth under angry brows." },
  { who: "sage", name: "Arcane sage", notes: "One bushy brow hiding both eyes, a long face, a beard to the belly." },
];

const ACTION_NAMES: Record<GoblinAction, string> = {
  idle: "Idle",
  sit: "Sitting on a ledge",
  work: "Turning a nut",
  pull: "Pulling the lever",
  cast: "Reading and casting",
  cheer: "Cheering",
  nod: "Nodding",
};

const serif = "'Bodoni 72', Didot, 'Bodoni MT', Constantia, Georgia, serif";

const tile: CSSProperties = {
  position: "relative",
  margin: 0,
  padding: "0.5rem 0.5rem 0.75rem",
  borderRadius: 6,
  background: "radial-gradient(ellipse at 50% 85%, #2a1f22 0%, #17111f 55%, #110d18 100%)",
  border: "1px solid #2a2136",
};

/** A rough stone ledge for the engineer to sit on, its top under his seat. */
function Ledge() {
  return (
    <div
      aria-hidden="true"
      style={{
        position: "absolute",
        left: "0.5rem",
        top: `calc(0.5rem + ${(SEAT_ROW + 1) * SCALE}px)`,
        width: 34 * SCALE,
        height: (CANVAS - SEAT_ROW - 1) * SCALE,
        background: "linear-gradient(#5a4a5e 0 3px, #3a2f44 3px 9px, #261e2e 9px)",
        boxShadow: "inset -6px 0 0 #1a1420",
      }}
    />
  );
}

/** The three goblins side by side, each with all of its actions. */
export function GoblinSheet() {
  return (
    <div style={{ minHeight: "100%", padding: "1.5rem clamp(1rem, 3vw, 2.5rem)", background: "#110d18", color: "#ece6f5" }}>
      <h1 style={{ margin: "0 0 0.25rem", fontFamily: serif }}>The goblin crew</h1>
      <p style={{ margin: "0 0 1.5rem", color: "#b9aecb", maxWidth: "60ch" }}>
        Drawn from the sketch: one sprite each, {CANVAS} pixels square, shown at {SCALE}× and lit from the top left.
      </p>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "2rem" }}>
        {CREW.map(({ who, name, notes }) => (
          <section key={who} aria-labelledby={`goblin-${who}`} style={{ flex: "1 1 18rem" }}>
            <h2 id={`goblin-${who}`} style={{ margin: "0 0 0.25rem", fontFamily: serif, color: "#f6d27a" }}>
              {name}
            </h2>
            <p style={{ margin: "0 0 0.75rem", color: "#c9bfd8", fontStyle: "italic" }}>{notes}</p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem" }}>
              {ACTIONS_OF[who].map((action) => (
                <figure key={action} style={tile}>
                  {action === "sit" && <Ledge />}
                  <Goblin who={who} action={action} scale={SCALE} style={{ position: "relative" }} />
                  <figcaption style={{ marginTop: "0.25rem", fontSize: "0.85rem", color: "#c9bfd8", textAlign: "center" }}>
                    {ACTION_NAMES[action]}
                  </figcaption>
                </figure>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
