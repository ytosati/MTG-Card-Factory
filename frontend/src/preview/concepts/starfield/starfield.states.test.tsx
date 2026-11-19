// @vitest-environment jsdom
// Smoke test of concept E "Starfield" (tasks.md T251): each state renders one level-1 heading, the footer notice
// (RN-69) and a decorative starfield; Colorless excludes the colors; a custom art version asks only for card and art;
// generation announces its step; the reveal turns into the way to the result; the build shows its progress; the
// Studio keeps one card in place while its phases swap only the elements around it.
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { starfieldStates } from "./starfield.states";

afterEach(cleanup);

function renderState(id: string) {
  const state = starfieldStates.find((entry) => entry.id === id);
  return render(<>{state?.render()}</>);
}

describe("Starfield concept (T251)", () => {
  it.each(starfieldStates.map((state) => [state.id, state] as const))("%s has one level-1 heading and a decorative sky", (_id, state) => {
    const { container } = render(<>{state.render()}</>);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("contentinfo").textContent).toMatch(/Fan content notice/);
    container.querySelectorAll("canvas").forEach((canvas) => expect(canvas.closest('[aria-hidden="true"]')).not.toBeNull());
  });

  it("clears the colors when Colorless is chosen", () => {
    renderState("request");
    const white = screen.getByRole("checkbox", { name: "White" }) as HTMLInputElement;
    expect(white.checked).toBe(true);
    fireEvent.click(screen.getByRole("checkbox", { name: "Colorless" }));
    expect(white.checked).toBe(false);
  });

  it("names the missing required fields instead of generating an empty request", () => {
    renderState("request-empty");
    fireEvent.click(screen.getByRole("button", { name: "Generate card" }));
    expect(screen.getByText(/Fill in before generating: Idea or theme, Color identity, Power level/)).toBeTruthy();
  });

  it("keeps the advanced options collapsed until asked", () => {
    renderState("request");
    const toggle = screen.getByRole("button", { name: "Advanced options" });
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByLabelText("Mana value")).toBeNull();
    fireEvent.click(toggle);
    expect(screen.getByLabelText("Mana value")).toBeTruthy();
  });

  it("asks a custom art version only for the card and its art", () => {
    renderState("request-custom-art");
    expect(screen.queryByRole("group", { name: "Color identity" })).toBeNull();
    expect(screen.getByLabelText("Printing")).toBeTruthy();
    expect(screen.queryByRole("radio", { name: "No art" })).toBeNull();
  });

  it("announces the running generation step", () => {
    renderState("generating");
    expect(screen.getByRole("status").textContent).toBe("Step 1 of 6: Design intent");
    expect(screen.getByRole("listitem", { current: "step" }).textContent).toMatch(/Design intent/);
  });

  it("reveals the card on demand, then leads to the result", () => {
    renderState("ready-strong");
    fireEvent.click(screen.getByRole("button", { name: "Reveal card" }));
    expect(screen.getByRole("link", { name: "See result" }).getAttribute("href")).toBe("#/preview/concept-starfield/result");
    expect(screen.getByRole("status").textContent).toBe("Revealed: Ilvara, Keeper of Tides.");
  });

  it("shows a rejected card's causes and an approved card's art with its text alternative", () => {
    renderState("result-rejected");
    expect(screen.getByText("Rejected.")).toBeTruthy();
    expect(screen.getByText(/does not match the cost/)).toBeTruthy();
    cleanup();
    renderState("result");
    expect(screen.getByRole("img", { name: "Lanternhollow Sentry, card art" })).toBeTruthy();
  });

  it("starts the database build and shows its progress", () => {
    renderState("setup");
    expect(screen.queryByRole("navigation")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Start the build" }));
    expect(screen.getByRole("progressbar", { name: "Building the card database" })).toBeTruthy();
  });

  it("keeps the Studio's card in place when Generate swaps the settings for the steps", async () => {
    const { container } = renderState("studio");
    const card = container.querySelector("[data-studio-card]");
    fireEvent.click(screen.getByRole("button", { name: "Generate card" }));
    expect(screen.getByRole("status").textContent).toBe("Step 1 of 6: Design intent");
    expect(await screen.findByRole("list", { name: "Generation steps" })).toBeTruthy();
    expect(screen.queryByRole("group", { name: "Color identity" })).toBeNull();
    expect(container.querySelector("[data-studio-card]")).toBe(card);
  });

  it("reveals the Studio's card in place, then shows its page around it and returns to the request", async () => {
    const { container } = renderState("studio-ready");
    const card = container.querySelector("[data-studio-card]");
    fireEvent.click(screen.getByRole("button", { name: "Reveal card" }));
    const again = await screen.findByRole("button", { name: "New request from this card" }, { timeout: 3000 });
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Result");
    expect(screen.getByRole("heading", { name: "Validation" })).toBeTruthy();
    expect(container.querySelector("[data-studio-card]")).toBe(card);
    fireEvent.click(again);
    await waitFor(() => expect(screen.getByRole("group", { name: "Color identity" })).toBeTruthy());
    expect(container.querySelector("[data-studio-card]")).toBe(card);
  });
});
