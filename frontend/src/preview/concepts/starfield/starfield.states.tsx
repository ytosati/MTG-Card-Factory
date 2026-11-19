// Preview states of concept E "Starfield" (tasks.md T251): the Request screen in its forms, the Studio layout test (the
// same steps as one page), then the generation, the reveal by power level, the Result page, Status and Setup.
import { setupBuilding, setupNotReady, statusFullConfiguration, statusWithSources } from "../../../api/contract/samples";
import type { SetupResponse, StatusResponse } from "../../../api/types";
import { cardWithImage, cardWithoutImage, planeswalkerCard, rejectedCard } from "../../fixtures";
import type { PreviewCard } from "../../fixtureTypes";
import type { PreviewState } from "../../types";
import { GeneratingScreen } from "./GeneratingScreen";
import type { RequestDraft } from "./model";
import { ReadyScreen } from "./ReadyScreen";
import { RequestScreen } from "./RequestScreen";
import { ResultScreen, type ResultExtras } from "./ResultScreen";
import { SetupScreen } from "./SetupScreen";
import { StatusScreen } from "./StatusScreen";
import { StudioScreen } from "./StudioScreen";

const FILLED: Partial<RequestDraft> = {
  idea: "A lighthouse keeper who trades memories with the tide, drawing a card whenever the sea takes something back.",
  colors: ["W", "U"],
  powerLevel: "medium",
  effort: "medium",
};

const ADVANCED: Partial<RequestDraft> = {
  ...FILLED,
  effort: "high",
  advancedOpen: true,
  cardTypes: ["Creature"],
  supertypes: ["Legendary"],
  subtypes: "Human, Wizard",
  manaValue: "4",
  power: "3",
  toughness: "4",
  baseCardId: "tidebound",
  printingId: "dpt-064",
  art: "generated",
  artDescription: "A keeper on a spiral stair at dusk, lantern raised over a dark tide full of drifting lights.",
};

const CUSTOM_ART: Partial<RequestDraft> = {
  kind: "custom-art",
  baseCardId: "lanternwing",
  printingId: "lmr-112",
  art: "uploaded",
  uploadName: "lanternwing-dusk.webp",
};

/** The card with art, given the design fields its fixture leaves empty. Fictional text, written by hand. */
const RESULT_CARD: PreviewCard = {
  ...cardWithImage,
  current_version: {
    ...cardWithImage.current_version,
    rarity: "uncommon",
    design_intent: "A patient defender for a white tokens deck: it holds the line at night and makes every small creature a little harder to remove.",
    rationale: "Four mana for a 2/4 with vigilance sits at the common rate; the +0/+1 anthem is the reason to play it, and toughness alone does not end games.",
    power_justification: "In line with other four-mana anthems on a body; it protects a board more than it grows one.",
    comparables: [
      { oracle_id: "00000000-0000-4000-8000-0000000000b3", name: "Bellwarden of the Ward", role: "toughness anthem at four mana" },
      { oracle_id: "00000000-0000-4000-8000-0000000000b4", name: "Dawnwatch Captain", role: "vigilant defender for tokens" },
      { oracle_id: "00000000-0000-4000-8000-0000000000b5", name: "Gloamspire Bulwark", role: "cheaper wall, no anthem" },
    ],
    validation: { ...cardWithImage.current_version.validation, checks_run: ["mana_cost", "color_identity", "rules_wording", "uniqueness"], skipped: ["similar_names"] },
  },
};

const RESULT_EXTRAS: ResultExtras = {
  notes: [
    "Keep the anthem on toughness only; a power anthem at this cost would outclass the comparables.",
    "Vigilance lets it attack in a pinch without leaving the board open.",
  ],
  base: null,
  art: { provider: "google", model: "fake-image-model-1", images: 1 },
  comparableFaces: {
    "00000000-0000-4000-8000-0000000000b3": { cost: "{2}{W}{W}", typeLine: "Creature — Human Cleric" },
    "00000000-0000-4000-8000-0000000000b4": { cost: "{3}{W}", typeLine: "Creature — Human Soldier" },
    "00000000-0000-4000-8000-0000000000b5": { cost: "{1}{W}{W}", typeLine: "Creature — Spirit Wall" },
  },
};

const REJECTED_EXTRAS: ResultExtras = { notes: [], base: null, art: null };

/** Status as configured with both providers and a built database: the two samples' parts together. */
const STATUS: StatusResponse = {
  ...statusWithSources,
  image_provider: statusFullConfiguration.image_provider,
  image_model: statusFullConfiguration.image_model,
};

/** The samples' sizes are tiny test files; the mockup shows sizes of the real order. */
const REAL_SIZES = { download_size: 168_400_000, space_needed: 1_420_000_000, free_space: 212_700_000_000 };
const SETUP: SetupResponse = { ...setupNotReady, ...REAL_SIZES };
const SETUP_BUILDING: SetupResponse = { ...setupBuilding, ...REAL_SIZES, job: setupBuilding.job ? { ...setupBuilding.job, progress: 0.42 } : null };

export const starfieldStates: PreviewState[] = [
  { id: "request", name: "Request, filled", render: () => <RequestScreen initial={FILLED} /> },
  { id: "request-empty", name: "Request, empty", render: () => <RequestScreen /> },
  { id: "request-advanced", name: "Request, advanced options, base card and art", render: () => <RequestScreen initial={ADVANCED} /> },
  { id: "request-custom-art", name: "Request, custom art version", render: () => <RequestScreen initial={CUSTOM_ART} /> },
  { id: "studio", name: "Studio, one page: compose, filled", render: () => <StudioScreen initial={FILLED} entry={RESULT_CARD} extras={RESULT_EXTRAS} /> },
  { id: "studio-generating", name: "Studio, generating", render: () => <StudioScreen phase="generating" initial={FILLED} entry={RESULT_CARD} extras={RESULT_EXTRAS} /> },
  { id: "studio-ready", name: "Studio, ready face down", render: () => <StudioScreen phase="ready" initial={FILLED} entry={RESULT_CARD} extras={RESULT_EXTRAS} /> },
  { id: "studio-result", name: "Studio, result", render: () => <StudioScreen phase="result" initial={FILLED} entry={RESULT_CARD} extras={RESULT_EXTRAS} /> },
  { id: "generating", name: "Generating, the steps walked automatically", render: () => <GeneratingScreen /> },
  { id: "ready-casual", name: "Ready, casual power", render: () => <ReadyScreen tier="casual" entry={cardWithoutImage} /> },
  { id: "ready-medium", name: "Ready, medium power", render: () => <ReadyScreen tier="medium" entry={RESULT_CARD} /> },
  { id: "ready-strong", name: "Ready, strong power", render: () => <ReadyScreen tier="strong" entry={planeswalkerCard} loyalty="4" /> },
  { id: "result", name: "Result, approved with art", render: () => <ResultScreen entry={RESULT_CARD} extras={RESULT_EXTRAS} /> },
  { id: "result-rejected", name: "Result, rejected without art", render: () => <ResultScreen entry={rejectedCard} extras={REJECTED_EXTRAS} /> },
  { id: "status", name: "Status", render: () => <StatusScreen status={STATUS} /> },
  { id: "setup", name: "Setup, database not built", render: () => <SetupScreen setup={SETUP} /> },
  { id: "setup-building", name: "Setup, building", render: () => <SetupScreen setup={SETUP_BUILDING} /> },
];
