// Tests for the preview fixtures (tasks.md T167; plan sections 6 and 14; spec RN-44, RN-14, RN-22).
//
// Contract under test, frontend/src/preview/fixtures.ts exports:
//   approvedCard, rejectedCard, planeswalkerCard, designNotesCard, cardWithImage, cardWithoutImage: PreviewCard
//   customArtVersion: PreviewArtVersion
// and frontend/src/preview/fixtureTypes.ts exports the types:
//   PreviewImage      = { src: string; alt: string }
//   PreviewCard       = CardResponse & { image: PreviewImage | null }
//   PreviewArtVersion = { id: string; number: number; origin: string; image: PreviewImage }
// Fixtures are fictional and written by hand; the shapes follow the contract samples of plan section 6.
import { describe, expect, it } from "vitest";

import {
  approvedCard,
  cardWithImage,
  cardWithoutImage,
  customArtVersion,
  designNotesCard,
  planeswalkerCard,
  rejectedCard,
} from "./fixtures";
import type { PreviewCard } from "./fixtureTypes";
import { cardGenerated } from "../api/contract/samples";

const cards: [string, PreviewCard][] = [
  ["approvedCard", approvedCard],
  ["rejectedCard", rejectedCard],
  ["planeswalkerCard", planeswalkerCard],
  ["designNotesCard", designNotesCard],
  ["cardWithImage", cardWithImage],
  ["cardWithoutImage", cardWithoutImage],
];

describe("preview fixtures: shape of the contract (T167)", () => {
  it.each(cards)("%s has every field of the card response contract", (_name, card) => {
    expect(typeof card.id).toBe("string");
    expect(Object.keys(card.current_version).sort()).toEqual(Object.keys(cardGenerated.current_version).sort());
    expect(Array.isArray(card.usage.text)).toBe(true);
    expect(["approved", "rejected"]).toContain(card.current_version.status);
    expect(card.current_version.validation.status).toBe(card.current_version.status);
    expect(["too_strong", "in_range", "too_weak"]).toContain(card.current_version.power_indicator);
    expect(card.current_version.name.length).toBeGreaterThan(0);
  });

  it("every card has its own id and its own name", () => {
    expect(new Set(cards.map(([, card]) => card.id)).size).toBe(cards.length);
    expect(new Set(cards.map(([, card]) => card.current_version.name)).size).toBe(cards.length);
  });
});

describe("preview fixtures: the cases the screens need (T167)", () => {
  it("approved card: approved, no causes", () => {
    expect(approvedCard.current_version.status).toBe("approved");
    expect(approvedCard.current_version.validation.causes).toEqual([]);
  });

  it("rejected card: rejected, with causes that each name a check, a code and a message", () => {
    expect(rejectedCard.current_version.status).toBe("rejected");
    const causes = rejectedCard.current_version.validation.causes;
    expect(causes.length).toBeGreaterThan(0);
    for (const cause of causes) {
      expect(cause.check).not.toBe("");
      expect(cause.code).not.toBe("");
      expect(cause.message).not.toBe("");
    }
  });

  it("planeswalker: a Planeswalker type line, loyalty abilities on separate lines, no power and toughness", () => {
    const version = planeswalkerCard.current_version;
    expect(version.type_line).toMatch(/Planeswalker/);
    expect(version.power).toBeNull();
    expect(version.toughness).toBeNull();
    const lines = version.rules_text.split("\n");
    expect(lines.length).toBeGreaterThanOrEqual(2);
    expect(lines.some((line) => /^[+−-]?\d+:/.test(line))).toBe(true);
  });

  it("card with design notes: design intent, rationale, justification and a comparable are filled", () => {
    const version = designNotesCard.current_version;
    expect(version.design_intent.length).toBeGreaterThan(0);
    expect(version.rationale.length).toBeGreaterThan(0);
    expect(version.power_justification.length).toBeGreaterThan(0);
    expect(version.comparables.length).toBeGreaterThan(0);
  });

  it("card with an image: a local source and an alt that names the card and says it is art", () => {
    expect(cardWithImage.image).not.toBeNull();
    const image = cardWithImage.image as NonNullable<PreviewCard["image"]>;
    expect(image.src.length).toBeGreaterThan(0);
    expect(image.src).not.toMatch(/^(https?:)?\/\//i);
    expect(image.alt).toContain(cardWithImage.current_version.name);
    expect(image.alt.toLowerCase()).toContain("art");
  });

  it("custom art version: a numbered version with a local image that has an alt", () => {
    expect(customArtVersion.number).toBeGreaterThanOrEqual(1);
    expect(customArtVersion.image.src.length).toBeGreaterThan(0);
    expect(customArtVersion.image.src).not.toMatch(/^(https?:)?\/\//i);
    expect(customArtVersion.image.alt.length).toBeGreaterThan(0);
    expect(customArtVersion.origin.length).toBeGreaterThan(0);
  });

  it("card with no image: the image is null", () => {
    expect(cardWithoutImage.image).toBeNull();
  });
});
