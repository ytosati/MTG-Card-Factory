// Fictional cards for the screen previews, written by hand; no real card name, text or image.
// Details: specs/plan.md, sections 6 and 14 ("Screen previews").
import lanternArt from "../assets/images/preview-art-lantern.svg";
import tideArt from "../assets/images/preview-art-tide.svg";
import type { CardVersion, TextUsageRecord } from "../api/types";
import type { PreviewArtVersion, PreviewCard } from "./fixtureTypes";

const CREATED_AT = "2000-01-01T00:00:00Z";

const usage: TextUsageRecord[] = [
  {
    provider: "openai",
    model: "fake-text-model-1",
    input_tokens: 1204,
    output_tokens: 236,
    outcome: "ok",
    created_at: CREATED_AT,
  },
];

/** A version with every field of the contract; each fixture changes what it needs. */
function version(fields: Partial<CardVersion> & Pick<CardVersion, "name">): CardVersion {
  return {
    mana_cost: "{1}{G}",
    mana_value: 2,
    type_line: "Creature — Elf Scout",
    rules_text: "When this creature enters, look at the top two cards of your library.",
    power: "2",
    toughness: "2",
    rarity: "common",
    design_intent: "",
    rationale: "",
    comparables: [],
    power_indicator: "in_range",
    power_justification: "",
    origin: "generated",
    status: "approved",
    validation: { status: "approved", checks_run: ["mana_cost", "color_identity"], causes: [], skipped: [] },
    ...fields,
  };
}

export const approvedCard: PreviewCard = {
  id: "00000000-0000-4000-8000-0000000000a1",
  current_version: version({
    name: "Mossgate Pathfinder",
    mana_cost: "{2}{G}",
    mana_value: 3,
    type_line: "Creature — Elf Scout",
    rules_text: "Reach\nWhen this creature enters, you may put a land card from your hand onto the battlefield tapped.",
    power: "2",
    toughness: "3",
    rarity: "uncommon",
    power_justification: "Ramp on a body, in line with other three-mana scouts.",
  }),
  usage: { text: usage },
  image: null,
};

export const rejectedCard: PreviewCard = {
  id: "00000000-0000-4000-8000-0000000000a2",
  current_version: version({
    name: "Cinderwake Hound",
    mana_cost: "{1}{R}{U}",
    mana_value: 2,
    type_line: "Creature — Elemental Hound",
    rules_text: "Haste\n{G}: This creature gets +1/+0 until end of turn.",
    power: "3",
    toughness: "1",
    power_indicator: "too_strong",
    status: "rejected",
    validation: {
      status: "rejected",
      checks_run: ["mana_cost", "color_identity"],
      causes: [
        {
          check: "mana_cost",
          code: "mana_value_mismatch",
          message: "The stated mana value 2 does not match the cost {1}{R}{U}, which is 3.",
        },
        {
          check: "color_identity",
          code: "outside_identity",
          message: "The rules text uses {G}, which is outside the requested identity of blue and red.",
        },
      ],
      skipped: [],
    },
  }),
  usage: {
    text: [
      ...usage,
      { ...usage[0]!, input_tokens: 1530, output_tokens: 0, outcome: "failed" },
    ],
  },
  image: null,
};

export const planeswalkerCard: PreviewCard = {
  id: "00000000-0000-4000-8000-0000000000a3",
  current_version: version({
    name: "Ilvara, Keeper of Tides",
    mana_cost: "{3}{U}{U}",
    mana_value: 5,
    type_line: "Legendary Planeswalker — Ilvara",
    rules_text:
      "+1: Draw a card, then discard a card.\n−2: Return target nonland permanent to its owner's hand.\n−7: You get an emblem with \"At the beginning of your upkeep, draw two cards.\"",
    power: null,
    toughness: null,
    rarity: "mythic",
  }),
  usage: { text: usage },
  image: null,
};

export const designNotesCard: PreviewCard = {
  id: "00000000-0000-4000-8000-0000000000a4",
  current_version: version({
    name: "Thornveil Archivist",
    mana_cost: "{1}{G}{W}",
    mana_value: 3,
    type_line: "Creature — Human Druid",
    rules_text: "Whenever another creature you control enters, put a +1/+1 counter on target creature you control.",
    power: "2",
    toughness: "2",
    rarity: "rare",
    design_intent: "A counters engine for a go-wide green-white deck that rewards a steady stream of small creatures.",
    rationale: "Three mana keeps it below the token makers it feeds, and one counter per trigger limits the swing.",
    power_justification: "Close to the comparables in value; stronger only in decks with many creatures.",
    comparables: [
      { oracle_id: "00000000-0000-4000-8000-0000000000b1", name: "Fernhollow Warden", role: "counters at three mana" },
      { oracle_id: "00000000-0000-4000-8000-0000000000b2", name: "Brightfield Herald", role: "go-wide payoff" },
    ],
  }),
  usage: { text: [...usage, { ...usage[0]!, input_tokens: 2310, output_tokens: 402 }] },
  image: null,
};

export const cardWithImage: PreviewCard = {
  id: "00000000-0000-4000-8000-0000000000a5",
  current_version: version({
    name: "Lanternhollow Sentry",
    mana_cost: "{3}{W}",
    mana_value: 4,
    type_line: "Creature — Spirit Soldier",
    rules_text: "Vigilance\nOther creatures you control get +0/+1.",
    power: "2",
    toughness: "4",
  }),
  usage: { text: usage },
  image: { src: lanternArt, alt: "Lanternhollow Sentry, card art" },
};

export const cardWithoutImage: PreviewCard = {
  id: "00000000-0000-4000-8000-0000000000a6",
  current_version: version({
    name: "Quietbrook Ferryman",
    mana_cost: "{1}{U}",
    mana_value: 2,
    type_line: "Creature — Merfolk Wizard",
    rules_text: "When this creature enters, tap target creature an opponent controls.",
    power: "1",
    toughness: "3",
  }),
  usage: { text: usage },
  image: null,
};

export const customArtVersion: PreviewArtVersion = {
  id: "00000000-0000-4000-8000-0000000000c1",
  number: 2,
  origin: "generated",
  image: { src: tideArt, alt: "Ilvara, Keeper of Tides, custom art version 2" },
};
