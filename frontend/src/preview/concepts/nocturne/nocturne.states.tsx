// Concept A "Nocturne" (tasks.md T251): its states in the preview gallery.
import type { PreviewState } from "../../types";
import { ConceptSheet } from "./ConceptSheet";
import { GeneratingMockup, RequestMockup, ResultMockup } from "./screens";

export const nocturneStates: PreviewState[] = [
  { id: "concept", name: "Concept sheet", render: () => <ConceptSheet /> },
  { id: "request", name: "Request", render: () => <RequestMockup /> },
  { id: "generating", name: "Generating", render: () => <GeneratingMockup /> },
  { id: "result", name: "Result", render: () => <ResultMockup /> },
];
