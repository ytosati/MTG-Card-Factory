// Preview states of concept E "Starfield" (tasks.md T251): the Request screen empty, filled and in its other forms.
import type { PreviewState } from "../../types";
import type { RequestDraft } from "./model";
import { RequestScreen } from "./RequestScreen";

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

export const starfieldStates: PreviewState[] = [
  { id: "request", name: "Request, filled", render: () => <RequestScreen initial={FILLED} /> },
  { id: "request-empty", name: "Request, empty", render: () => <RequestScreen /> },
  { id: "request-advanced", name: "Request, advanced options, base card and art", render: () => <RequestScreen initial={ADVANCED} /> },
  { id: "request-custom-art", name: "Request, custom art version", render: () => <RequestScreen initial={CUSTOM_ART} /> },
];
