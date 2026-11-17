// UI text of the Request screen (spec "Screens", Request).
import type { ColorLetter, PowerLevel } from "../../api/types";

export type RequestField = "idea" | "color_identity" | "power_level";

const COUNT_FORMAT = new Intl.NumberFormat("en-US");

export const requestCopy = {
  title: "Request",
  summary: "Describe the card, choose its color identity and power level, then generate it.",
  fieldLabels: {
    idea: "Idea or theme",
    color_identity: "Color identity",
    power_level: "Power level",
  } as Record<RequestField, string>,
  colors: [
    { letter: "W", name: "White" },
    { letter: "U", name: "Blue" },
    { letter: "B", name: "Black" },
    { letter: "R", name: "Red" },
    { letter: "G", name: "Green" },
  ] as { letter: ColorLetter; name: string }[],
  or: "or",
  colorless: "Colorless",
  powerLevels: [
    { value: "casual", name: "Casual" },
    { value: "medium", name: "Medium" },
    { value: "strong", name: "Strong" },
  ] as { value: PowerLevel; name: string }[],
  characterCount: (count: number, max: number): string =>
    `${COUNT_FORMAT.format(count)} / ${COUNT_FORMAT.format(max)} characters`,
  ideaMissing: "Write the idea or theme of the card.",
  ideaTooLong: (max: number): string => `Shorten the idea to ${COUNT_FORMAT.format(max)} characters or fewer.`,
  colorMissing: "Choose one or more colors, or Colorless.",
  powerMissing: "Choose a power level.",
  generate: "Generate card",
  sending: "Sending the request…",
  waiting: "Waiting to start…",
  generating: "Generating the card…",
  refusedPrefix: "Card Factory refused the request. Check: ",
  missingPrefix: "Fill in before generating: ",
  settingLabel: "Setting:",
  checkOnStatusBefore: ". Check it on the",
  statusLink: "Status",
  checkOnStatusAfter: "screen.",
  failed: "The generation failed. Try again.",
  lost: "Card Factory lost track of the generation. Try again.",
  unreadableResult: "The generation finished, but Card Factory could not read which card it saved. Try again.",
  unknownFailure: "Something went wrong in Card Factory. Try again.",
};
