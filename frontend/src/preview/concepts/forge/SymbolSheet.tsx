// Concept D (Forge): the mana symbol sheet and the color picks with their bursts and sounds. Task T251.
import { useState } from "react";

import { SoundToggle } from "./sound/SoundToggle";
import { ManaPick } from "./symbols/ManaPick";
import { ManaCostSymbols, ManaSymbol } from "./symbols/ManaSymbol";
import type { ManaColor } from "./symbols/manaSymbols";

const ROWS: string[][] = [
  Array.from({ length: 10 }, (_, n) => `{${n}}`),
  Array.from({ length: 10 }, (_, n) => `{${n + 10}}`),
  ["{20}", "{X}", "{Y}", "{Z}", "{W}", "{U}", "{B}", "{R}", "{G}", "{C}"],
  ["{W/U}", "{W/B}", "{U/B}", "{U/R}", "{B/R}", "{B/G}", "{R/G}", "{R/W}", "{G/W}", "{G/U}"],
  ["{2/W}", "{2/U}", "{2/B}", "{2/R}", "{2/G}", "{W/P}", "{U/P}", "{B/P}", "{R/P}", "{G/P}"],
  ["{T}", "{Q}", "{S}", "{E}", "{P}", "{C/P}"],
];

const PICKS: { letter: ManaColor; label: string }[] = [
  { letter: "W", label: "White" },
  { letter: "U", label: "Blue" },
  { letter: "B", label: "Black" },
  { letter: "R", label: "Red" },
  { letter: "G", label: "Green" },
  { letter: "C", label: "Colorless" },
];

const page = {
  minHeight: "100%",
  padding: "2rem clamp(1rem, 4vw, 3rem)",
  background: "#110d18",
  color: "#ece6f5",
  fontFamily: "'Segoe UI Variable Text', 'Segoe UI', system-ui, sans-serif",
} as const;

const caption = {
  margin: "2.5rem 0 1rem",
  color: "#e8b33a",
  fontSize: "0.75rem",
  letterSpacing: "0.16em",
  textTransform: "uppercase",
} as const;

/** Every symbol of the set, then the five colors and colorless as picks. */
export function SymbolSheet() {
  const [picked, setPicked] = useState<ManaColor[]>(["R"]);
  const toggle = (letter: ManaColor, checked: boolean) =>
    setPicked((current) => (checked ? [...current, letter] : current.filter((entry) => entry !== letter)));

  return (
    <div style={page}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem" }}>
        <h1 style={{ margin: 0, fontFamily: "'Bodoni 72', Didot, 'Bodoni MT', Constantia, Georgia, serif" }}>
          Mana symbols
        </h1>
        <SoundToggle />
      </div>

      <h2 style={caption}>Color picks</h2>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "1.5rem 2rem" }}>
        {PICKS.map(({ letter, label }) => (
          <ManaPick
            key={letter}
            letter={letter}
            label={label}
            checked={picked.includes(letter)}
            onChange={(checked) => toggle(letter, checked)}
          />
        ))}
      </div>

      <h2 style={caption}>The set</h2>
      <div style={{ display: "grid", gap: "0.75rem" }}>
        {ROWS.map((row) => (
          <div key={row.join("")} style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem" }}>
            {row.map((symbol) => (
              <ManaSymbol key={symbol} symbol={symbol} size={44} />
            ))}
          </div>
        ))}
      </div>

      <h2 style={caption}>In a cost, at text size</h2>
      <p style={{ display: "flex", flexWrap: "wrap", gap: "1.5rem", margin: 0 }}>
        <ManaCostSymbols cost="{2}{G}{G}" size={18} />
        <ManaCostSymbols cost="{1}{W}{U}" size={18} />
        <ManaCostSymbols cost="{X}{R}{R}" size={18} />
        <ManaCostSymbols cost="{3}{B/G}{B/G}" size={18} />
      </p>
    </div>
  );
}
