// Concept D (Forge): every pixel effect in use on the forge's dark ground, with replay buttons. Task T251.
import { useState, type ReactNode } from "react";

import {
  EMBERS,
  FORGE_FIRE,
  PICK_BURST,
  REVEAL,
  RUNE_CIRCLE,
  RUNE_WRITE,
  SPARKS_HIT,
  STEAM_BURST,
  STEAM_VENT,
  forgeFire,
  type FxSpec,
  type RevealTier,
} from "./fx/effects";
import { FxLayers } from "./fx/FxLayers";
import { PixelFx } from "./fx/PixelFx";
import { ManaPick } from "./symbols/ManaPick";
import type { ManaColor } from "./symbols/manaSymbols";

const GROUND = "#110d18";
const LETTERS: ManaColor[] = ["W", "U", "B", "R", "G", "C"];
const NAMES: Record<ManaColor, string> = { W: "White", U: "Blue", B: "Black", R: "Red", G: "Green", C: "Colorless" };
const FLAMES: { label: string; colors: ManaColor[] }[] = [
  { label: "Forge", colors: [] },
  { label: "White", colors: ["W"] },
  { label: "Blue", colors: ["U"] },
  { label: "Black", colors: ["B"] },
  { label: "Green", colors: ["G"] },
  { label: "Blue and red", colors: ["U", "R"] },
  { label: "White, black, green", colors: ["W", "B", "G"] },
];

const page = { background: GROUND, color: "#e9e1f2", minHeight: "100%", padding: "2rem clamp(1rem, 4vw, 3rem) 4rem" } as const;
const grid = { display: "flex", flexWrap: "wrap", gap: "1.25rem", alignItems: "flex-end" } as const;
const heading = { font: "600 0.8rem/1.2 inherit", letterSpacing: "0.14em", textTransform: "uppercase", color: "#e8b33a", margin: "2.5rem 0 1rem" } as const;

function Tile({ label, children, onReplay }: { label: string; children: ReactNode; onReplay?: () => void }) {
  return (
    <figure style={{ margin: 0, display: "grid", justifyItems: "center", gap: "0.5rem" }}>
      {children}
      <figcaption style={{ display: "flex", gap: "0.6rem", alignItems: "center", fontSize: "0.8rem", color: "#b3abbf" }}>
        {label}
        {onReplay ? (
          <button
            type="button"
            onClick={onReplay}
            style={{ padding: "0.2rem 0.6rem", borderRadius: 4, border: "1px solid #4a3a5e", background: "#1a1424", color: "#f6d27a", cursor: "pointer" }}
          >
            Replay
          </button>
        ) : null}
      </figcaption>
    </figure>
  );
}

/** A loop or a one-shot on its own canvas; one-shots get a replay button. */
function Single({ label, spec, scale = 3, once = false }: { label: string; spec: FxSpec; scale?: number; once?: boolean }) {
  const [play, setPlay] = useState(0);
  return (
    <Tile label={label} onReplay={once ? () => setPlay((count) => count + 1) : undefined}>
      <PixelFx
        effect={spec.effect}
        options={spec.options}
        width={spec.width}
        height={spec.height}
        origin={spec.origin}
        scale={scale}
        vignette={spec.vignette}
        mode={once ? "once" : "loop"}
        playKey={play}
      />
    </Tile>
  );
}

function Reveal({ tier, size }: { tier: RevealTier; size: number }) {
  const [play, setPlay] = useState(0);
  return (
    <Tile label={`Reveal, ${tier}`} onReplay={() => setPlay((count) => count + 1)}>
      <div style={{ position: "relative", width: size, height: size }}>
        <div
          style={{ position: "absolute", left: "50%", top: "50%", width: 120, height: 168, transform: "translate(-50%, -50%)", borderRadius: 8, background: "linear-gradient(160deg, #2a2236, #17121f)", border: "1px solid #4a3a5e" }}
        />
        <FxLayers layers={REVEAL[tier]} scale={2} mode="once" playKey={play} style={{ left: "50%", top: "50%" }} />
      </div>
    </Tile>
  );
}

function Picks() {
  const [picked, setPicked] = useState<ManaColor[]>([]);
  return (
    <div style={{ ...grid, gap: "3rem", padding: "4rem 2rem" }}>
      {LETTERS.map((letter) => (
        <ManaPick
          key={letter}
          letter={letter}
          label={NAMES[letter]}
          checked={picked.includes(letter)}
          sound={false}
          onChange={(next) => setPicked((current) => (next ? [...current, letter] : current.filter((entry) => entry !== letter)))}
        />
      ))}
    </div>
  );
}

/** The gallery's effects bench: every effect of the forge, labelled, on its dark ground. */
export function FxBench() {
  return (
    <div style={page}>
      <h1 style={{ fontSize: "1.4rem", margin: 0 }}>Pixel effects of the forge</h1>
      <p style={{ color: "#b3abbf", maxWidth: "60ch" }}>
        Drawn live from code on a transparent canvas. Loops pause offscreen; with reduced motion, loops hold a still frame and one-shots do
        not play.
      </p>

      <h2 style={heading}>Fire</h2>
      <div style={grid}>
        <Single label="Brazier" spec={FORGE_FIRE} />
        {FLAMES.map((flame) => (
          <Single key={flame.label} label={flame.label} spec={forgeFire(flame.colors)} scale={2} />
        ))}
      </div>

      <h2 style={heading}>Steam, embers and sparks</h2>
      <div style={grid}>
        <Single label="Steam vent" spec={STEAM_VENT} />
        <Single label="Steam burst" spec={STEAM_BURST} once />
        <Single label="Embers" spec={EMBERS} />
        <Single label="Hammer on anvil" spec={SPARKS_HIT} scale={2} once />
      </div>

      <h2 style={heading}>Runes</h2>
      <div style={grid}>
        <Single label="Rune circle" spec={RUNE_CIRCLE} />
        <Single label="Rune writing" spec={RUNE_WRITE} />
      </div>

      <h2 style={heading}>Color picks (click a symbol)</h2>
      <Picks />
      <div style={grid}>
        {LETTERS.map((letter) => (
          <Single key={letter} label={`Pick burst, ${NAMES[letter]}`} spec={PICK_BURST[letter]} scale={2} once />
        ))}
      </div>

      <h2 style={heading}>Card reveal</h2>
      <div style={grid}>
        <Reveal tier="casual" size={300} />
        <Reveal tier="medium" size={440} />
        <Reveal tier="strong" size={480} />
      </div>
    </div>
  );
}
