// @vitest-environment jsdom
// Tests for the hash-based screen switch (spec RN-08, RN-40; plan section 13: no router library).
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import { statusFullConfiguration } from "./api/contract/samples";
import { calledUrl, jsonResponse, stubFetch } from "./test/fetchMock";

afterEach(() => {
  cleanup();
  window.location.hash = "";
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("App", () => {
  it("RN-40: the #/status route opens the Status screen, which reads GET /api/status", async () => {
    window.location.hash = "#/status";
    const fetchMock = stubFetch(async () => jsonResponse(statusFullConfiguration));

    render(<App />);

    expect(await screen.findByRole("heading", { level: 1, name: "Status" })).toBeTruthy();
    expect(await screen.findByText("Text provider")).toBeTruthy();
    expect(fetchMock.mock.calls.some((call) => calledUrl(call[0]) === "/api/status")).toBe(true);
  });
});
