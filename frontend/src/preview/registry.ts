// The screens of the preview gallery and their states. Screen previews add their entries here.
import type { PreviewScreen } from "./types";
import { sharedComponentStates } from "./sharedComponents.states";

export const previewScreens: PreviewScreen[] = [
  { id: "components", name: "Shared components", states: sharedComponentStates },
];
