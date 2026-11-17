// UI text of the Request screen (spec "Screens", Request).
import type { ColorLetter, PowerLevel } from "../../api/types";

export type RequestField = "idea" | "color_identity" | "power_level";

/** Draft until the request carries it (RN-53). */
export type GenerationEffort = "low" | "medium" | "high";

/** Draft until the request carries it (RN-30). */
export type CardLanguage = "en" | "pt-BR";

/** The running step of a generation, as the job names it (plan section 6; RN-55). */
export type GenerationStep = "design" | "search" | "draft" | "validation" | "revision" | "art";

const COUNT_FORMAT = new Intl.NumberFormat("en-US");

export const requestCopy = {
  title: "Request",
  summary:
    "Describe the card, choose its color identity and power level, then generate it. These three are required; " +
    "everything else is optional.",
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
  colorHint: "Choose one or more colors, or Colorless for a card with no color.",
  powerLevels: [
    { value: "casual", name: "Casual", meaning: "Fun and fair in a relaxed game, without efficient staples." },
    { value: "medium", name: "Medium", meaning: "Solid and synergistic, at home at a typical Commander table." },
    { value: "strong", name: "Strong", meaning: "Efficient and competitive, close to the best cards of its role." },
  ] as { value: PowerLevel; name: string; meaning: string }[],
  effortLabel: "Generation effort",
  efforts: [
    { value: "low", name: "Low", meaning: "Compares with up to 8 related cards. The quickest." },
    { value: "medium", name: "Medium", meaning: "Compares with up to 20 related cards." },
    { value: "high", name: "High", meaning: "Compares with up to 40 related cards and adds design notes." },
  ] as { value: GenerationEffort; name: string; meaning: string }[],
  languageLabel: "Card language",
  languageHint: "The language of the card text. The idea can be written in any language.",
  languages: [
    { value: "en", name: "English" },
    { value: "pt-BR", name: "Portuguese (Brazil)" },
  ] as { value: CardLanguage; name: string }[],
  advancedToggle: "Advanced options",
  advancedHint: "Every option is optional. Leave one empty and the card is free in that part.",
  cardTypesLabel: "Card types",
  // Battle is not offered (RN-54).
  cardTypes: ["Artifact", "Creature", "Enchantment", "Instant", "Kindred", "Land", "Planeswalker", "Sorcery"],
  supertypesLabel: "Supertypes",
  supertypes: ["Basic", "Legendary", "Snow", "World"],
  subtypesLabel: "Subtypes",
  subtypesHint: "Separate them with commas, for example Elf, Druid.",
  manaValueLabel: "Mana value",
  manaValueHint: "A whole number from 0 to 16.",
  powerLabel: "Power",
  toughnessLabel: "Toughness",
  powerToughnessHint: "Whole numbers from 0 to 99, chosen together, for a creature, a Vehicle or a Spacecraft.",
  loyaltyLabel: "Starting loyalty",
  loyaltyHint: "A whole number from 1 to 99, for a planeswalker.",
  stepsLabel: "Generation steps",
  stepOf: (number: number, total: number, name: string): string => `Step ${number} of ${total}: ${name}`,
  steps: [
    { value: "design", name: "Design intent" },
    { value: "search", name: "Search for related cards" },
    { value: "draft", name: "Draft" },
    { value: "validation", name: "Validation" },
    { value: "revision", name: "Revision" },
    { value: "art", name: "Art" },
  ] as { value: GenerationStep; name: string }[],
  editRequest: "Edit the request",
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
  alreadyRunning: "A generation is already running. Wait for it to finish, then generate this card.",
  providerRefused:
    "The provider refused the request. Card Factory sends the idea as you wrote it; edit it and try again.",
  lost: "Card Factory lost track of the generation. Try again.",
  unreadableResult: "The generation finished, but Card Factory could not read which card it saved. Try again.",
  unknownFailure: "Something went wrong in Card Factory. Try again.",
};
