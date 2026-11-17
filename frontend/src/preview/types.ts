// Types of the preview gallery: screens and their named states.
import type { ReactNode } from "react";

/** One state of a screen, opened at #/preview/<screen id>/<state id>. */
export interface PreviewState {
  id: string;
  name: string;
  render: () => ReactNode;
}

/** A screen of the gallery and its states. */
export interface PreviewScreen {
  id: string;
  name: string;
  states: PreviewState[];
}
