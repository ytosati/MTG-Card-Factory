// @vitest-environment jsdom
// Tests for the shared card components (tasks.md T167; spec RN-44, CA-50, RN-49, CA-59). Behavior and
// accessibility only: roles, names and text, never class names, styles or snapshots.
//
// Contract under test (each file exports the named component):
//   components/CardText.tsx       <CardText version={CardVersion} />
//     Name, mana cost, type line, rules text (one element per line of the text) and "power/toughness"
//     (e.g. "2/3") when both exist; an absent cost, power or toughness renders nothing.
//   components/CardImageArea.tsx  <CardImageArea image={{ src, alt } | null} cardName={string} />
//     With an image: an img with the alt, and a link named "Open full resolution" whose href is the
//     unchanged src, opening in a new tab (target _blank, rel with noopener). Without: no img, no link,
//     and the visible text "No image" (the area stays).
//   components/StepIndicator.tsx  <StepIndicator label={string} steps={string[]} current={number} />
//     An ordered list named by label; one item per step; the item at index `current` has
//     aria-current="step"; earlier steps carry the text "done" and later ones "waiting" after the step
//     name (visually hidden is fine). A current outside the list marks no step.
//   components/Notice.tsx         <Notice tone="danger" | "notice" | "success" title?={string}>children</Notice>
//     danger has role "alert"; notice and success have role "status". Shows the title (if any) and the
//     children; the icon is hidden from assistive technology.
//   components/Image.tsx          <Image src alt width height />
//     An img with the alt (alt="" for decoration, then no "img" role), the width and height attributes
//     that reserve its space, and loading="lazy".
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { CardImageArea } from "./CardImageArea";
import { CardText } from "./CardText";
import { Image } from "./Image";
import { Notice } from "./Notice";
import { StepIndicator } from "./StepIndicator";
import type { CardVersion } from "../api/types";
import { cardGenerated } from "../api/contract/samples";

afterEach(cleanup);

const version: CardVersion = cardGenerated.current_version;

describe("CardText: the card text in rules format (T167)", () => {
  it("shows name, mana cost, type line, rules text and power over toughness", () => {
    render(<CardText version={version} />);
    expect(screen.getByText("Vellwood Lanternkeeper")).toBeTruthy();
    expect(screen.getByText(/\{2\}\{G\}\{W\}/)).toBeTruthy();
    expect(screen.getByText(/Creature — Elf Druid/)).toBeTruthy();
    expect(screen.getByText(/create a 1\/1 green Elf creature token/)).toBeTruthy();
    expect(screen.getByText("2/3")).toBeTruthy();
  });

  it("splits the rules text into one element per line, keeping the order", () => {
    render(<CardText version={{ ...version, rules_text: "Flying\nWhenever this attacks, scry 1.\n+1: Do a thing." }} />);
    const first = screen.getByText("Flying");
    const second = screen.getByText("Whenever this attacks, scry 1.");
    const third = screen.getByText("+1: Do a thing.");
    expect(first.compareDocumentPosition(second) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(second.compareDocumentPosition(third) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(new Set([first, second, third]).size).toBe(3);
  });

  it("a card with no cost, no power and no toughness shows none of them", () => {
    render(<CardText version={{ ...version, mana_cost: null, power: null, toughness: null }} />);
    expect(screen.queryByText(/\{2\}\{G\}\{W\}/)).toBeNull();
    expect(screen.queryByText("2/3")).toBeNull();
  });

  it("an empty rules text and odd characters render as plain text without failing", () => {
    render(<CardText version={{ ...version, name: "<b>Odd</b> & Æther ★ ½", rules_text: "" }} />);
    expect(screen.getByText("<b>Odd</b> & Æther ★ ½")).toBeTruthy();
  });

  it("a very long rules text is kept whole", () => {
    const long = "word ".repeat(2000).trim();
    const { container } = render(<CardText version={{ ...version, rules_text: long }} />);
    expect(container.textContent).toContain(long);
  });
});

describe("CardImageArea: the card-shaped image area (RN-44, CA-50, T167)", () => {
  const image = { src: "/assets/lanternkeeper-art.png", alt: "Vellwood Lanternkeeper, art" };

  it("shows the image with its alt text", () => {
    render(<CardImageArea image={image} cardName="Vellwood Lanternkeeper" />);
    expect(screen.getByRole("img", { name: image.alt }).getAttribute("src")).toBe(image.src);
  });

  it("offers the stored file unchanged at full resolution, in a new tab", () => {
    render(<CardImageArea image={image} cardName="Vellwood Lanternkeeper" />);
    const link = screen.getByRole("link", { name: /open full resolution/i });
    expect(link.getAttribute("href")).toBe(image.src);
    expect(link.getAttribute("target")).toBe("_blank");
    expect(link.getAttribute("rel") ?? "").toContain("noopener");
  });

  it("without an image the area stays, says there is no image and offers no picture or link", () => {
    render(<CardImageArea image={null} cardName="Vellwood Lanternkeeper" />);
    expect(screen.getByText(/no image/i)).toBeTruthy();
    expect(screen.queryByRole("img")).toBeNull();
    expect(screen.queryByRole("link")).toBeNull();
  });
});

describe("StepIndicator: the running step indicator (RN-49, T167)", () => {
  const steps = ["Write the card", "Check the rules", "Draw the art"];

  it("is an ordered list named by its label, one item per step", () => {
    render(<StepIndicator label="Generation steps" steps={steps} current={1} />);
    const list = screen.getByRole("list", { name: "Generation steps" });
    expect(within(list).getAllByRole("listitem")).toHaveLength(3);
    expect(list.tagName).toBe("OL");
  });

  it("marks only the current step with aria-current=step and says done and waiting in text", () => {
    render(<StepIndicator label="Generation steps" steps={steps} current={1} />);
    const items = screen.getAllByRole("listitem");
    expect(items.map((item) => item.getAttribute("aria-current"))).toEqual([null, "step", null]);
    expect(items[0]?.textContent).toMatch(/Write the card.*done/i);
    expect(items[2]?.textContent).toMatch(/Draw the art.*waiting/i);
  });

  it.each([-1, 3, 99, Number.NaN])("a current step of %s marks no step and does not fail", (current) => {
    render(<StepIndicator label="Generation steps" steps={steps} current={current} />);
    for (const item of screen.getAllByRole("listitem")) expect(item.getAttribute("aria-current")).toBeNull();
  });

  it("no steps renders no items without failing", () => {
    render(<StepIndicator label="Generation steps" steps={[]} current={0} />);
    expect(screen.queryAllByRole("listitem")).toHaveLength(0);
  });
});

describe("Notice (RN-49, T167)", () => {
  it("a danger notice is an alert with its title and text", () => {
    render(
      <Notice tone="danger" title="Could not save">
        The disk is full.
      </Notice>,
    );
    const alert = screen.getByRole("alert");
    expect(alert.textContent).toContain("Could not save");
    expect(alert.textContent).toContain("The disk is full.");
  });

  it.each(["notice", "success"] as const)("a %s notice is a status, not an alert", (tone) => {
    render(<Notice tone={tone}>Saved with a warning.</Notice>);
    expect(screen.getByRole("status").textContent).toContain("Saved with a warning.");
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("the icon is hidden from assistive technology and the title is optional", () => {
    const { container } = render(<Notice tone="notice">Plain text.</Notice>);
    expect(container.querySelector("svg")?.getAttribute("aria-hidden")).toBe("true");
    expect(screen.getByRole("status").textContent?.trim()).toBe("Plain text.");
  });
});

describe("Image: the image component (RN-49, CA-59, T167)", () => {
  it("renders an img with its alt, source and reserved size, loaded lazily", () => {
    render(<Image src="/assets/a.png" alt="A fictional lantern" width={745} height={1040} />);
    const img = screen.getByRole("img", { name: "A fictional lantern" });
    expect(img.getAttribute("src")).toBe("/assets/a.png");
    expect(img.getAttribute("width")).toBe("745");
    expect(img.getAttribute("height")).toBe("1040");
    expect(img.getAttribute("loading")).toBe("lazy");
  });

  it("an empty alt marks a decorative image, which then has no img role", () => {
    const { container } = render(<Image src="/assets/a.png" alt="" width={10} height={10} />);
    expect(screen.queryByRole("img")).toBeNull();
    expect(container.querySelector("img")?.getAttribute("alt")).toBe("");
  });
});
