// @vitest-environment jsdom
// Tests for the move from Setup to the normal screens when the build finishes (spec RN-28, CA-18).
//
// The shell passes the Setup screen an `onReady` callback (SetupScreen props: { onReady: () => void }).
// When Setup calls it, the shell reads GET /api/status again, drops Setup from the navigation and opens
// the home screen (Status for now), without waiting for a hashchange. The Setup screen is replaced here
// by a stand-in whose button calls `onReady`, so only the shell's part is under test.
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import { setupNotReady, statusNotReady, statusWithSources } from "./api/contract/samples";
import { jsonResponse, stubFetchByPath } from "./test/fetchMock";

vi.mock("./screens/SetupScreen", () => ({
  SetupScreen: ({ onReady }: { onReady?: () => void }) => (
    <main className="screen">
      <h1>Setup</h1>
      <button type="button" onClick={() => onReady?.()}>
        Finish the build
      </button>
    </main>
  ),
}));

function navLinkNames(): string[] {
  const nav = screen.getByRole("navigation", { name: "Screens" });
  return within(nav)
    .queryAllByRole("link")
    .map((link) => (link.textContent ?? "").trim());
}

afterEach(() => {
  cleanup();
  window.location.hash = "";
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("App when the Setup screen reports the database ready", () => {
  it("CA-18: onReady drops Setup from the navigation and opens the home screen without a hashchange", async () => {
    let ready = false;
    window.location.hash = "#/setup";
    stubFetchByPath({
      "/api/status": async () => jsonResponse(ready ? statusWithSources : statusNotReady),
      "/api/setup": async () => jsonResponse({ ...setupNotReady, database_ready: ready }),
      "/api/heartbeat": async () => new Response(null, { status: 204 }),
    });
    render(<App />);

    expect(await screen.findByRole("heading", { level: 1, name: "Setup" })).toBeTruthy();
    await waitFor(() => expect(navLinkNames()).toEqual(["Setup", "Status"]));

    // The test fires no hashchange: the shell must react to onReady alone.
    ready = true;
    fireEvent.click(screen.getByRole("button", { name: "Finish the build" }));

    expect(await screen.findByRole("heading", { level: 1, name: "Status" })).toBeTruthy();
    await waitFor(() => expect(navLinkNames()).not.toContain("Setup"));
    expect(navLinkNames()).toContain("Status");
    expect(screen.queryByRole("heading", { level: 1, name: "Setup" })).toBeNull();
  });
});
