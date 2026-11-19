// Concept C, "Gallery Wall" (tasks.md T251): the gallery states of the concept, with fictional cards and art.
import lanternArt from "../../../assets/images/preview-art-lantern.svg";
import { approvedCard, designNotesCard } from "../../fixtures";
import type { PreviewCard } from "../../fixtureTypes";
import type { PreviewState } from "../../types";
import { GalleryConcept } from "./GalleryConcept";
import { GalleryGenerating } from "./GalleryGenerating";
import { GalleryRequest } from "./GalleryRequest";
import { GalleryResult } from "./GalleryResult";

/** A green card with art and design notes, so the wall turns moss and the spread has every part. */
const mossCard: PreviewCard = {
  ...approvedCard,
  current_version: {
    ...approvedCard.current_version,
    design_intent:
      "A ramp creature for green decks that play many lands, with reach so it still blocks fliers late in the game.",
    rationale:
      "Three mana and a land from the hand, not from the library, keep it below the scouts that search for lands.",
    comparables: [
      {
        oracle_id: "00000000-0000-4000-8000-0000000000d1",
        name: "Brackenwood Guide",
        role: "land from hand at three mana",
      },
      { oracle_id: "00000000-0000-4000-8000-0000000000d2", name: "Hollowfen Ranger", role: "reach on a ramp body" },
    ],
  },
  image: { src: lanternArt, alt: "Mossgate Pathfinder, card art" },
};

/** A green-white card with art, so the wall splits into moss and bone. */
const splitCard: PreviewCard = {
  ...designNotesCard,
  image: { src: lanternArt, alt: "Thornveil Archivist, card art" },
};

export const galleryStates: PreviewState[] = [
  { id: "request", name: "Request", render: () => <GalleryRequest /> },
  { id: "generating", name: "Generating", render: () => <GalleryGenerating /> },
  { id: "result", name: "Result", render: () => <GalleryResult card={mossCard} /> },
  { id: "result-split", name: "Result, two colors", render: () => <GalleryResult card={splitCard} /> },
  { id: "concept", name: "Concept", render: () => <GalleryConcept /> },
];
