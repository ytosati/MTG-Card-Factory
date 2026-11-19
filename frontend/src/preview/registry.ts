// The screens of the preview gallery and their states. Screen previews add their entries here.
import { forgeStates } from "./concepts/forge/forge.states";
import { starfieldStates } from "./concepts/starfield/starfield.states";
import { draftingStates } from "./concepts/drafting/drafting.states";
import { galleryStates } from "./concepts/gallery/gallery.states";
import { nocturneStates } from "./concepts/nocturne/nocturne.states";
import { directionStates } from "./direction.states";
import type { PreviewScreen } from "./types";
import { requestStates } from "./request.states";
import { sharedComponentStates } from "./sharedComponents.states";

export const previewScreens: PreviewScreen[] = [
  { id: "concept-starfield", name: "Concept E: Starfield", states: starfieldStates },
  { id: "concept-forge", name: "Concept D: Forge", states: forgeStates },
  { id: "concept-nocturne", name: "Concept A: Nocturne", states: nocturneStates },
  { id: "concept-drafting", name: "Concept B: Drafting Table", states: draftingStates },
  { id: "concept-gallery", name: "Concept C: Gallery Wall", states: galleryStates },
  { id: "direction", name: "Design direction", states: directionStates },
  { id: "components", name: "Shared components", states: sharedComponentStates },
  { id: "request", name: "Request", states: requestStates },
];
