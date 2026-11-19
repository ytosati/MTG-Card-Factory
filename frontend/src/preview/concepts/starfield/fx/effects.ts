// Concept E "Starfield" (tasks.md T251): the curated pixelfx effects, recolored to the forge's palette and the five colors.
import * as collectBurst from "../../../../vendor/pixelfx/fx/pickups/collect-burst.js";
import * as embers from "../../../../vendor/pixelfx/fx/forge/embers.js";
import * as fireBurst from "../../../../vendor/pixelfx/fx/forge/fire-burst.js";
import * as holyBurst from "../../../../vendor/pixelfx/fx/forge/holy-burst.js";
import * as leafSwirl from "../../../../vendor/pixelfx/fx/forge/leaf-swirl.js";
import * as runeWrite from "../../../../vendor/pixelfx/fx/forge/rune-write.js";
import * as steamBurst from "../../../../vendor/pixelfx/fx/forge/steam-burst.js";
import * as steamVent from "../../../../vendor/pixelfx/fx/forge/steam-vent.js";
import * as brazier from "../../../../vendor/pixelfx/fx/fire/brazier.js";
import * as manaBurst from "../../../../vendor/pixelfx/fx/arcane/mana-burst.js";
import * as runeCircle from "../../../../vendor/pixelfx/fx/arcane/rune-circle.js";
import * as plasmaExplosion from "../../../../vendor/pixelfx/fx/explosions/plasma-explosion.js";
import * as parry from "../../../../vendor/pixelfx/fx/impacts/parry.js";
import * as poof from "../../../../vendor/pixelfx/fx/spawn/poof.js";
import * as splash from "../../../../vendor/pixelfx/fx/water/splash.js";
import type { ManaColor } from "../symbols/manaSymbols";
import type { PixelFxEffect, PixelFxOptions } from "./PixelFx";

/** An effect ready to play: the module, its options and the canvas it needs, in effect pixels. */
export interface FxSpec {
  effect: PixelFxEffect;
  options: PixelFxOptions;
  width: number;
  height: number;
  /** The anchor in canvas pixels, when the effect's own box is not centred. */
  origin?: { x: number; y: number };
  /** Playback rate. */
  speed?: number;
  /** Fades the canvas edges, for effects whose glow reaches them. */
  vignette?: boolean;
}

/** A layer of a composed effect: a spec, its scale against the base and its centre's offset in screen pixels. */
export interface FxLayer extends FxSpec {
  scale?: number;
  dx?: number;
  dy?: number;
}

// Ramps, dark to bright, nine steps (effects resample them to the steps they use).
const RAMP: Record<ManaColor, readonly string[]> = {
  W: ["#2a1c08", "#5a3e10", "#9a6c18", "#d8a428", "#e8b33a", "#ffd84a", "#fff09a", "#fffbe6", "#ffffff"],
  U: ["#081830", "#0e2e5a", "#14508c", "#1c76bc", "#36a2e0", "#78ccf4", "#a8e0ff", "#d8f4ff", "#ffffff"],
  B: ["#0b0712", "#1c1230", "#2c1a4a", "#432468", "#5e3290", "#8048b8", "#a970e0", "#d6c2f2", "#ffffff"],
  R: ["#4a1712", "#8a1f17", "#c9281f", "#f2561d", "#ff8a2a", "#ffc23d", "#ffe26b", "#fff3a6", "#ffffff"],
  G: ["#0c1a0e", "#163418", "#225224", "#357530", "#4f9a3a", "#7cc048", "#b4e070", "#e4ffb0", "#ffffff"],
  C: ["#140a26", "#2b1252", "#481c88", "#6b2cc0", "#8b3dff", "#b07cff", "#d8b8ff", "#f0e4ff", "#ffffff"],
};

/** The forge's own fire: gold and ember. */
const FORGE_RAMP = ["#2a0f0c", "#6a1c12", "#b0361a", "#e8641e", "#f59a2a", "#e8b33a", "#ffd86a", "#fff3c0", "#ffffff"];
const ARCANE = RAMP.C;
const STEAM = ["#3a3450", "#6a6488", "#9c96b8", "#cdc8e0", "#efecf8", "#ffffff"];
const GOLD = ["#1e1206", "#4a2c08", "#86520c", "#c48412", "#e8b33a", "#ffe066", "#fff6c4", "#ffffff"];

/**
 * The flame's ramp for the chosen colors. One color tints the whole fire; several split it by heat, the first
 * color in the cool rims and the last in the hot heart, so a blue-red fire has blue edges round an orange core.
 */
export function flameFor(colors: readonly ManaColor[]): string[] {
  if (colors.length === 0) return [...FORGE_RAMP];
  const steps = FORGE_RAMP.length;
  return Array.from({ length: steps }, (_, step) => {
    const owner = colors[Math.min(colors.length - 1, Math.floor((step * colors.length) / steps))] ?? "R";
    return RAMP[owner][step] ?? "#ffffff";
  });
}

/** The furnace flame without its brazier, anchored at the coals; pass flameFor(colors) as the palette to tint it. */
export function forgeFire(colors: readonly ManaColor[] = []): FxSpec {
  return { effect: brazier, options: { prop: false, palette: flameFor(colors), light: 0.75 }, width: 128, height: 128, origin: { x: 64, y: 118 }, vignette: true };
}

/** The whole brazier, iron and all, for a standalone fire. */
export const FORGE_FIRE: FxSpec = { effect: brazier, options: { palette: FORGE_RAMP }, width: 128, height: 156, vignette: true };

export const STEAM_VENT: FxSpec = { effect: steamVent, options: { palette: STEAM }, width: 96, height: 96 };
export const STEAM_BURST: FxSpec = { effect: steamBurst, options: { palette: STEAM }, width: 136, height: 128 };

export const EMBERS: FxSpec = { effect: embers, options: { palette: FORGE_RAMP }, width: 96, height: 128 };
/** A hammer on the anvil: gold sparks spray up from the strike and rain down. */
export const SPARKS_HIT: FxSpec = { effect: parry, options: { palette: GOLD, height: 8 }, width: 200, height: 112, origin: { x: 100, y: 100 } };

export const RUNE_CIRCLE: FxSpec = { effect: runeCircle, options: { palette: ARCANE }, width: 136, height: 100 };
export const RUNE_WRITE: FxSpec = { effect: runeWrite, options: { palette: ARCANE }, width: 136, height: 56 };

/** The burst round a color's symbol when it is picked; every one is centred on the symbol. */
export const PICK_BURST: Record<ManaColor, FxSpec> = {
  W: { effect: holyBurst, options: { palette: RAMP.W, radius: 30, glints: 10 }, width: 80, height: 80 },
  // The splash stands on its water line: the anchor sits a little under the symbol's middle.
  U: { effect: splash, options: { palette: RAMP.U, stone: false }, width: 128, height: 88, origin: { x: 64, y: 54 } },
  B: { effect: poof, options: { palette: ["#0b0712", "#2c1a4a", "#5e3290", "#8048b8", "#b48ae6", "#e6d8fa"], stars: ["#8b3dff", "#c79bff", "#f0e4ff"] }, width: 112, height: 92, origin: { x: 56, y: 64 } },
  R: { effect: fireBurst, options: { palette: RAMP.R, radius: 22 }, width: 104, height: 104, origin: { x: 52, y: 50 } },
  G: { effect: leafSwirl, options: { palette: RAMP.G, radius: 30, leaves: 14 }, width: 80, height: 80 },
  C: { effect: collectBurst, options: { palette: ["#140a26", "#2b1252", "#481c88", "#8b3dff", "#b07cff", "#d8c8f0", "#efeaf6", "#ffffff"] }, width: 96, height: 96, origin: { x: 48, y: 78 } },
};

export type RevealTier = "casual" | "medium" | "strong";

/** The reveal of a finished card, by tier: layers drawn over each other, centred on the card. */
export const REVEAL: Record<RevealTier, FxLayer[]> = {
  casual: [{ effect: collectBurst, options: { palette: GOLD }, width: 112, height: 108, origin: { x: 56, y: 84 } }],
  medium: [
    { effect: steamBurst, options: { palette: STEAM, spread: 1.4 }, width: 136, height: 128, origin: { x: 68, y: 112 }, dy: 36 },
    { effect: manaBurst, options: { palette: [...GOLD.slice(0, 4), "#c79bff", "#e8b33a", "#fff6c4", "#ffffff"] }, width: 208, height: 150, origin: { x: 104, y: 103 } },
  ],
  strong: [
    { effect: plasmaExplosion, options: { palette: ["#0e0618", "#2b1252", "#481c88", "#8b3dff", "#c79bff", "#f0e4ff", "#ffffff"], accent: ["#2a0f0c", "#86520c", "#e8b33a", "#ffd86a", "#fff3c0"] }, width: 224, height: 200 },
    { effect: holyBurst, options: { palette: GOLD, radius: 92, rays: 16, glints: 24 }, width: 200, height: 200 },
    { effect: fireBurst, options: { palette: FORGE_RAMP, radius: 40 }, width: 184, height: 160, origin: { x: 92, y: 96 } },
  ],
};
