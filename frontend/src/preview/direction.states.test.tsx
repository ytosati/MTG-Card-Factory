// @vitest-environment jsdom
// Tests for the design direction sample (tasks.md T180; spec RN-49): the list and table sample opens by its
// address, has one level-1 heading, and its deck table names its columns.
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { approvedCard, planeswalkerCard } from "./fixtures";
import { PreviewGallery } from "./PreviewGallery";
import { previewScreens } from "./registry";

function openSample(): HTMLElement {
  window.location.hash = "#/preview/direction/card-list";
  render(<PreviewGallery />);
  return screen.getByRole("region", { name: "Preview" });
}

beforeEach(() => {
  window.location.hash = "";
});
afterEach(cleanup);

describe("design direction sample (T180, RN-49)", () => {
  it("is listed in the gallery index at its address", () => {
    expect(previewScreens.find((entry) => entry.id === "direction")?.states.map((state) => state.id)).toContain(
      "card-list",
    );
    window.location.hash = "#/preview";
    render(<PreviewGallery />);
    expect(document.querySelector('a[href="#/preview/direction/card-list"]')).not.toBeNull();
  });

  it("opens by its address with a single level-1 heading in the gallery", () => {
    const frame = openSample();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(within(frame).getAllByRole("heading", { level: 2 }).length).toBeGreaterThan(0);
  });

  it("lists saved fixture cards with their mana cost read as words and a text alternative for each image", () => {
    const frame = openSample();
    const list = within(frame).getByRole("list");
    expect(within(list).getAllByText(planeswalkerCard.current_version.name).length).toBeGreaterThan(0);
    expect(within(list).getAllByRole("img", { name: /^Mana cost:/ }).length).toBeGreaterThan(0);
    const images = [...list.querySelectorAll("img")];
    expect(images.length).toBeGreaterThan(0);
    for (const image of images) expect(image.getAttribute("alt")).toMatch(/\S/);
  });

  it("shows the deck as a table named by its heading, with count, name, cost and type column headers", () => {
    const frame = openSample();
    const table = within(frame).getByRole("table", { name: "Deck list" });
    const headers = within(table)
      .getAllByRole("columnheader")
      .map((header) => header.textContent?.trim());
    expect(headers).toEqual(["Count", "Name", "Cost", "Type"]);
    expect(within(table).getByRole("rowheader", { name: new RegExp(approvedCard.current_version.name) })).toBeTruthy();
  });
});
