// Concept D (Forge): the forge on its own, with controls for its phase, job step and colors. Task T251.
import { useState } from "react";

import type { GenerationStep } from "../../../screens/request/copy";
import { ForgeScene, type ForgePhase } from "./machine/ForgeScene";

const PHASES: ForgePhase[] = ["idle", "working", "cooling"];
const STEPS: GenerationStep[] = ["design", "search", "draft", "validation", "revision", "art"];
const COLORS = ["W", "U", "B", "R", "G"] as const;
type Letter = (typeof COLORS)[number];

const bar = { display: "flex", flexWrap: "wrap", gap: "0.5rem", alignItems: "center", margin: "0 0 0.75rem" } as const;

function Choice({ on, label, onClick }: { on: boolean; label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={onClick}
      style={{
        padding: "0.35rem 0.75rem",
        borderRadius: 4,
        border: `1px solid ${on ? "#e8b33a" : "#3a2f4a"}`,
        background: on ? "#2a2014" : "#1a1424",
        color: on ? "#f6d27a" : "#c9bfd8",
        cursor: "pointer",
      }}
    >
      {label}
    </button>
  );
}

/** The forge scene with its inputs exposed, for judging the machine before the screens use it. */
export function MachineBench() {
  const [phase, setPhase] = useState<ForgePhase>("working");
  const [step, setStep] = useState<GenerationStep>("draft");
  const [colors, setColors] = useState<Letter[]>(["R", "G"]);
  const toggle = (letter: Letter) =>
    setColors((current) => (current.includes(letter) ? current.filter((entry) => entry !== letter) : [...current, letter]));

  return (
    <div style={{ minHeight: "100%", padding: "1.5rem clamp(1rem, 3vw, 2.5rem)", background: "#110d18", color: "#ece6f5" }}>
      <h1 style={{ margin: "0 0 1rem", fontFamily: "'Bodoni 72', Didot, 'Bodoni MT', Constantia, Georgia, serif" }}>The forge</h1>
      <div style={bar} role="group" aria-label="Phase">
        {PHASES.map((entry) => (
          <Choice key={entry} on={phase === entry} label={entry} onClick={() => setPhase(entry)} />
        ))}
      </div>
      <div style={bar} role="group" aria-label="Job step">
        {STEPS.map((entry) => (
          <Choice key={entry} on={step === entry} label={entry} onClick={() => setStep(entry)} />
        ))}
      </div>
      <div style={bar} role="group" aria-label="Colors">
        {COLORS.map((entry) => (
          <Choice key={entry} on={colors.includes(entry)} label={entry} onClick={() => toggle(entry)} />
        ))}
      </div>
      <ForgeScene phase={phase} step={step} colors={colors} />
    </div>
  );
}
