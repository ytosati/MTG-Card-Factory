// Concept B "Drafting Table" (tasks.md T251): the gallery states of the concept, static mockups with local state.
import type { PreviewState } from "../../types";
import { ConceptSheet } from "./ConceptSheet";
import { GeneratingMockup } from "./GeneratingMockup";
import { RequestMockup } from "./RequestMockup";
import { ResultMockup } from "./ResultMockup";

export const draftingStates: PreviewState[] = [
  { id: "concept", name: "Concept sheet", render: () => <ConceptSheet /> },
  { id: "request", name: "Request, filled", render: () => <RequestMockup /> },
  { id: "generating", name: "Request, generating", render: () => <GeneratingMockup /> },
  { id: "result", name: "Result with art", render: () => <ResultMockup /> },
];
