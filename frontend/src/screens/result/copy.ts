// UI text of the Result screen (spec "Screens", Result).
import type { PowerIndicator } from "../../api/types";

export const resultCopy = {
  title: "Result",
  loading: "Loading the card…",
  tryAgain: "Try again",
  unreadableCard: "Card Factory sent a card that could not be read. Try again.",
  unknownFailure: "The card could not be loaded. Try again.",
  revisionFailureTitle: "The automatic revision did not complete.",
  approved: "Approved.",
  checksPassed: (count: number): string =>
    count > 0 ? `${count} ${count === 1 ? "check" : "checks"} passed.` : "No check found a problem.",
  rejected: "Rejected.",
  causesCount: (count: number): string =>
    count > 0 ? `${count} ${count === 1 ? "cause" : "causes"}:` : "No cause was recorded.",
  powerHeading: "Power indicator",
  powerWords: { too_weak: "Too weak", in_range: "In range", too_strong: "Too strong" } as Record<PowerIndicator, string>,
  noJustification: "No justification was recorded.",
  powerHint: "Assessed by the text model against the comparables. It does not affect validation.",
  designHeading: "Design",
  intentHeading: "Intent",
  noIntent: "No design intent was recorded.",
  rationaleHeading: "Rationale",
  noRationale: "No rationale was recorded.",
  comparablesHeading: "Comparables",
  noComparables: "No comparables are recorded for this card.",
  usageHeading: "Text usage",
  noUsage: "No text usage is recorded for this card.",
  usageCall: "Call",
  usageProviderModel: "Provider and model",
  usageInput: "Input tokens",
  usageOutput: "Output tokens",
  usageFailed: "Failed",
  usageTotal: "Total",
};
