// @vitest-environment jsdom
// Tests for the tab title of each screen (spec RN-52; CA-82). T139.
// Mocks are built from the contract samples (plan section 6).
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import type { RouteAnswer } from "./test/fetchMock";
import {
  cardGenerated,
  generationAccepted,
  jobGenerationDone,
  setupNotReady,
  statusNotReady,
  statusWithSources,
} from "./api/contract/samples";
import { jsonResponse, stubFetchByPath } from "./test/fetchMock";

const CARD_ID = jobGenerationDone.result.card;

function backend(ready: boolean, extra: Record<string, RouteAnswer> = {}) {
  return stubFetchByPath({
    "/api/status": ready ? statusWithSources : statusNotReady,
    "/api/setup": { ...setupNotReady, database_ready: ready },
    "/api/heartbeat": async () => new Response(null, { status: 204 }),
    "/api/generations": async () => jsonResponse(generationAccepted, 202),
    "/api/jobs/": jobGenerationDone,
    [`/api/cards/${CARD_ID}`]: cardGenerated,
    ...extra,
  });
}

function renderAt(hash: string) {
  window.location.hash = hash;
  render(<App />);
}

beforeEach(() => {
  document.title = "Not set by the application";
});

afterEach(() => {
  cleanup();
  window.location.hash = "";
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("tab title of each screen (RN-52, CA-82)", () => {
  it("RN-52: Setup sets the title Setup · Card Factory", async () => {
    backend(false);
    renderAt("#/setup");

    await screen.findByRole("heading", { level: 1, name: "Setup" });
    expect(document.title).toBe("Setup · Card Factory");
  });

  it("RN-52: Status sets the title Status · Card Factory", async () => {
    backend(true);
    renderAt("#/status");

    await screen.findByRole("heading", { level: 1, name: "Status" });
    expect(document.title).toBe("Status · Card Factory");
  });

  it("RN-52: Request sets the title Request · Card Factory", async () => {
    backend(true);
    renderAt("#/request");

    await screen.findByRole("heading", { level: 1, name: "Request" });
    expect(document.title).toBe("Request · Card Factory");
  });

  it("RN-52: Result sets the title Result · Card Factory", async () => {
    backend(true);
    renderAt(`#/result/${CARD_ID}`);

    await screen.findByRole("heading", { level: 1, name: "Result" });
    expect(document.title).toBe("Result · Card Factory");
  });

  it("RN-52: a generation that ends done moves the title from Request to Result", async () => {
    backend(true);
    renderAt("#/request");
    fireEvent.change(await screen.findByRole("textbox", { name: /idea/i }), { target: { value: "A lantern elf." } });
    fireEvent.click(screen.getByLabelText(/^\s*green\b/i));
    fireEvent.click(screen.getByRole("radio", { name: /^\s*medium\b/i }));
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /generate/i }));
    });

    await screen.findByRole("heading", { level: 1, name: "Result" });
    expect(document.title).toBe("Result · Card Factory");
  });
});

describe("tab title before a screen is shown (RN-52, CA-82)", () => {
  it("CA-82: with the database not ready, opening the Request address shows Setup · Card Factory", async () => {
    backend(false);
    renderAt("#/request");

    await screen.findByRole("heading", { level: 1, name: "Setup" });
    expect(document.title).toBe("Setup · Card Factory");
    expect(screen.queryByRole("heading", { level: 1, name: "Request" })).toBeNull();
  });

  it.each(["#/request", ""])("CA-82: while readiness loads, the title is Card Factory (address %j)", async (hash) => {
    backend(false, { "/api/status": () => new Promise<Response>(() => {}) });
    renderAt(hash);

    expect(await screen.findByText(/checking the card database/i)).toBeTruthy();
    await waitFor(() => expect(document.title).toBe("Card Factory"));
    expect(screen.queryByRole("heading", { level: 1 })).toBeNull();
  });
});
