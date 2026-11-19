// Concept E "Starfield" (tasks.md T251): the Request mockup's draft, its own words and the fictional base cards.
import type { PowerLevel } from "../../../api/types";
import type { CardLanguage, GenerationEffort } from "../../../screens/request/copy";
import type { ManaColor } from "../forge/symbols/manaSymbols";

/** A request for a new card, or for a custom art version of an existing card (RN-59). */
export type RequestKind = "new" | "custom-art";

export type ArtChoice = "none" | "generated" | "uploaded";

/** The draft the screen edits; nothing is sent. */
export interface RequestDraft {
  kind: RequestKind;
  idea: string;
  colors: ManaColor[];
  powerLevel: PowerLevel | null;
  effort: GenerationEffort;
  language: CardLanguage;
  advancedOpen: boolean;
  cardTypes: string[];
  supertypes: string[];
  subtypes: string;
  manaValue: string;
  power: string;
  toughness: string;
  loyalty: string;
  baseQuery: string;
  baseCardId: string | null;
  printingId: string | null;
  faceIndex: number;
  art: ArtChoice;
  artDescription: string;
  uploadName: string | null;
  /** A reference image for generated art: elements of it are used in the art. */
  referenceName: string | null;
}

export const EMPTY_DRAFT: RequestDraft = {
  kind: "new",
  idea: "",
  colors: [],
  powerLevel: null,
  effort: "medium",
  language: "en",
  advancedOpen: false,
  cardTypes: [],
  supertypes: [],
  subtypes: "",
  manaValue: "",
  power: "",
  toughness: "",
  loyalty: "",
  baseQuery: "",
  baseCardId: null,
  printingId: null,
  faceIndex: 0,
  art: "none",
  artDescription: "",
  uploadName: null,
  referenceName: null,
};

export const IDEA_MAX = 1000;
export const ART_DESCRIPTION_MAX = 500;

/** Words of this mockup that the Request copy does not have yet. */
export const starfieldCopy = {
  kindLabel: "Request kind",
  kinds: [
    { value: "new", name: "New card" },
    { value: "custom-art", name: "Custom art version" },
  ] as { value: RequestKind; name: string }[],
  customSummary: "Choose an existing card with one face and its printing, then give it new art.",
  required: "Required",
  optional: "Optional",
  baseCardLabel: "Base card",
  baseCardHint:
    "An existing card as a design example: the new card may follow a similar effect or strategy, in your colors. " +
    "With generated art, the image copies its frame and layout. Search by name, then choose the printing and the face.",
  oneFaceHint: "Only cards with one face can have a custom art version.",
  searchLabel: "Card name",
  searchPlaceholder: "Search by name",
  resultsLabel: "Matching cards",
  noMatch: "No card matches this name.",
  change: "Change",
  printingLabel: "Printing",
  faceLabel: "Face",
  artLabel: "Art",
  arts: [
    { value: "none", name: "No art" },
    { value: "generated", name: "Generated" },
    { value: "uploaded", name: "Uploaded" },
  ] as { value: ArtChoice; name: string }[],
  artDescriptionLabel: "Additional instructions",
  artDescriptionHint:
    "Optional. Added to your idea. Left empty, the art follows what the idea describes.",
  referenceLabel: "Reference image",
  referenceHint: "Optional. Elements of this image are used in the art, for example your face on the character.",
  noArtHint: "No art: the card is text only.",
  summary: "Describe the card, choose its color identity and power level, then generate it.",
  tokens: {
    low: "Uses the fewest tokens.",
    medium: "Uses more tokens than Low.",
    high: "Uses the most tokens: more cards compared, and design notes.",
  },
  billing: "Art is billed by the image provider, separately from the text.",
  uploadAction: "Choose an image",
  uploadHint:
    "Your image is the art. Card Factory makes only the card's frame and text around it. " +
    "PNG, JPEG or WebP, up to 10 MB. Checked when chosen.",
  uploadNone: "No file chosen",
  outlineLabel: "Card outline",
  untitled: "Name comes with the card",
  freeType: "Type line left to the card",
  noIdea: "The idea appears here as you write it.",
  noArt: "No art",
  generatedArt: "Generated art",
  uploadedArt: "Uploaded image",
  readings: { power: "Power level", effort: "Effort", language: "Language", base: "Base card", none: "None", unset: "Not chosen" },
  customMark: "Custom art version",
  ready: "Ready to generate.",
};

export interface BaseCard {
  id: string;
  name: string;
  faces: { name: string; typeLine: string; cost: string }[];
  printings: { id: string; label: string }[];
}

/** Fictional cards and printings standing in for the reference database's search. */
export const BASE_CARDS: BaseCard[] = [
  {
    id: "lanternwing",
    name: "Lanternwing Sentry",
    faces: [{ name: "Lanternwing Sentry", typeLine: "Creature — Bird Soldier", cost: "{1}{W}" }],
    printings: [
      { id: "lmr-112", label: "Lumen Reaches · 112" },
      { id: "cmx-031", label: "Commander Vault · 31" },
    ],
  },
  {
    id: "tidebound",
    name: "Tidebound Archivist",
    faces: [{ name: "Tidebound Archivist", typeLine: "Creature — Merfolk Wizard", cost: "{2}{U}" }],
    printings: [
      { id: "dpt-064", label: "Deep Tides · 64" },
      { id: "dpt-301", label: "Deep Tides, extended art · 301" },
    ],
  },
  {
    id: "tidal-ledger",
    name: "Tidal Ledger",
    faces: [{ name: "Tidal Ledger", typeLine: "Artifact", cost: "{3}" }],
    printings: [{ id: "dpt-221", label: "Deep Tides · 221" }],
  },
  {
    id: "vigil",
    name: "Hollow Moon Vigil // Dawnbreak Vigil",
    faces: [
      { name: "Hollow Moon Vigil", typeLine: "Enchantment", cost: "{1}{W}{B}" },
      { name: "Dawnbreak Vigil", typeLine: "Enchantment — Aura", cost: "" },
    ],
    printings: [{ id: "ecl-019", label: "Eclipse Rites · 19" }],
  },
  {
    id: "cartographer",
    name: "Ashen Cartographer",
    faces: [{ name: "Ashen Cartographer", typeLine: "Creature — Human Scout", cost: "{1}{R}" }],
    printings: [{ id: "ecl-140", label: "Eclipse Rites · 140" }],
  },
];

export function baseCardOf(id: string | null): BaseCard | undefined {
  return BASE_CARDS.find((card) => card.id === id);
}

/** The cards whose name holds the query; a custom art version searches only cards with one face. */
export function searchBaseCards(query: string, kind: RequestKind): BaseCard[] {
  const needle = query.trim().toLowerCase();
  if (needle.length === 0) return [];
  return BASE_CARDS.filter((card) => card.name.toLowerCase().includes(needle) && (kind === "new" || card.faces.length === 1));
}

/** Unicode characters, as RN-11 counts them. */
export function lengthOf(text: string): number {
  return [...text].length;
}
