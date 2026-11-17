// The screens of the preview gallery and their states. Screen previews add their entries here.
import { directionStates } from "./direction.states";
import type { PreviewScreen } from "./types";
import { requestStates } from "./request.states";
import { sharedComponentStates } from "./sharedComponents.states";

export const previewScreens: PreviewScreen[] = [
  { id: "direction", name: "Design direction", states: directionStates },
  { id: "components", name: "Shared components", states: sharedComponentStates },
  { id: "request", name: "Request", states: requestStates },
];
