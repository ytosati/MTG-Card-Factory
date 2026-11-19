// Concept E "Starfield" (tasks.md T251): the words of the screens after Request that their copy does not have yet,
// and the reveal's bursts recolored to the concept's starlight.
import * as collectBurst from "../../../vendor/pixelfx/fx/pickups/collect-burst.js";
import * as holyBurst from "../../../vendor/pixelfx/fx/forge/holy-burst.js";
import * as manaBurst from "../../../vendor/pixelfx/fx/arcane/mana-burst.js";
import * as plasmaExplosion from "../../../vendor/pixelfx/fx/explosions/plasma-explosion.js";
import type { PowerLevel } from "../../../api/types";
import type { FxLayer } from "../forge/fx/effects";

export const sceneCopy = {
  generatingTitle: "Generating",
  generatedTitle: "Drawn",
  generatedRubric: "Every step done",
  generatedStatus: "The card is ready.",
  toReady: "Go to the card",
  replay: "Replay",
  readyTitle: "Card ready",
  readyRubric: (tier: string): string => `${tier} power`,
  readyLede: "The card lies face down. Turn it over when you are ready.",
  readyRevealedLede: "Its page holds the validation, the power indicator and the design.",
  reveal: "Reveal card",
  seeResult: "See result",
  revealed: (name: string): string => `Revealed: ${name}.`,
  rulesLabel: "Card text",
  rarity: "Rarity",
  artist: "Art",
  artGenerated: (model: string): string => `Generated with ${model}`,
  noArt: "No art yet",
  actionsLabel: "Actions",
  generateArt: "Generate art",
  retryArt: "Generate the art again",
  uploadArt: "Upload art",
  newRequest: "New request from this card",
  fullResolution: "Open the image at full resolution",
  validationHeading: "Validation",
  checksRun: "Checks run",
  skippedHeading: "Skipped checks",
  noSkipped: "No check was skipped.",
  notesHeading: "Design notes",
  baseHeading: "Base card",
  noBase: "None. The card was designed from the idea alone.",
  artUsageHeading: "Art usage",
  artUsageImages: "Images",
  noArtUsage: "No art was generated for this card.",
  powerScale: { too_weak: "Weak", in_range: "In range", too_strong: "Strong" },
  testConnection: "Test the connection",
  statusLede: "What Card Factory runs on: the providers it calls and the reference database it checks cards against.",
  firstRun: "First run",
  setupBuildingTitle: "Building",
  percent: (share: number): string => `${Math.round(share * 100)}%`,
};

const VIOLET = ["#140a26", "#2b1252", "#481c88", "#6b2cc0", "#8b3dff", "#b07cff", "#d8b8ff", "#f0e4ff", "#ffffff"];
const CYAN = ["#04121c", "#0a2a40", "#0e4a6c", "#1a7aa8", "#3aa8dc", "#5bd2fe", "#a8e8ff", "#e0f8ff", "#ffffff"];
const STARLIGHT = ["#141626", "#2c3050", "#565c88", "#8c94c0", "#c0c8e8", "#e9f1fb", "#f6faff", "#ffffff"];

/** The reveal of a finished card by power level: a small violet burst, a violet and cyan nova, a supernova. */
export const STAR_REVEAL: Record<PowerLevel, FxLayer[]> = {
  casual: [{ effect: collectBurst, options: { palette: VIOLET }, width: 112, height: 108, origin: { x: 56, y: 84 } }],
  medium: [
    { effect: holyBurst, options: { palette: CYAN, radius: 44, rays: 10, glints: 12 }, width: 128, height: 128 },
    { effect: manaBurst, options: { palette: [...VIOLET.slice(0, 5), "#5bd2fe", "#c8f0ff", "#ffffff"] }, width: 208, height: 150, origin: { x: 104, y: 103 } },
  ],
  strong: [
    { effect: plasmaExplosion, options: { palette: ["#0e0618", "#2b1252", "#481c88", "#8b3dff", "#c79bff", "#f0e4ff", "#ffffff"], accent: ["#04121c", "#0e4a6c", "#3aa8dc", "#5bd2fe", "#e0f8ff"] }, width: 224, height: 200 },
    { effect: holyBurst, options: { palette: STARLIGHT, radius: 96, rays: 20, glints: 28 }, width: 208, height: 208 },
  ],
};
