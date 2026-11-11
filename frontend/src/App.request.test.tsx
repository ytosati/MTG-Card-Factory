// @vitest-environment jsdom
// Tests for the move from the Request screen to the Result screen in the shell (spec RN-11, RN-15,
// RN-49; CA-26). T65, T67.
//
// Assumed shell behavior: with a ready database the navigation offers Request at "#/request". When the
// Request screen's generation job ends done, the shell opens the Result screen (level-1 heading
// "Result") for the card of the job result, and hands it the job's revision failure, if any.
// Mocks are built from the contract samples (plan section 6).
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import type { GenerationJobResponse } from "./api/types";
import {
  cardGenerated,
  generationAccepted,
  jobGenerationDone,
  jobGenerationRevisionFailed,
  statusWithSources,
} from "./api/contract/samples";
import { calledUrl, jsonResponse, stubFetchByPath } from "./test/fetchMock";

/** The card id of the done job's result; GET /api/cards/{id} answers it with the card sample. */
const CARD_ID = jobGenerationDone.result.card;

function installBackend(job: GenerationJobResponse) {
  return stubFetchByPath({
    "/api/status": statusWithSources,
    "/api/heartbeat": async () => new Response(null, { status: 204 }),
    "/api/generations": async () => jsonResponse(generationAccepted, 202),
    "/api/jobs/": async () => jsonResponse(job),
    [`/api/cards/${CARD_ID}`]: cardGenerated,
  });
}

async function sendRequest() {
  const idea = await screen.findByRole("textbox", { name: /idea/i });
  fireEvent.change(idea, { target: { value: "A clockwork lantern that builds small servants." } });
  fireEvent.click(screen.getByLabelText(/^\s*colorless\b/i));
  const select = screen.queryByRole("combobox", { name: /power level/i }) as HTMLSelectElement | null;
  if (select !== null) {
    const option = Array.from(select.options).find((item) => item.textContent?.trim().toLowerCase() === "casual");
    fireEvent.change(select, { target: { value: option?.value } });
  } else {
    fireEvent.click(screen.getByRole("radio", { name: /^\s*casual\b/i }));
  }
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: /generate/i }));
  });
}

afterEach(() => {
  cleanup();
  window.location.hash = "";
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("App: Request to Result (RN-11, RN-49)", () => {
  it("RN-11: with a ready database the navigation offers Request, which opens the Request screen", async () => {
    installBackend(jobGenerationDone);
    window.location.hash = "#/request";
    render(<App />);

    expect(await screen.findByRole("heading", { level: 1, name: /request/i })).toBeTruthy();
    const nav = screen.getByRole("navigation", { name: "Screens" });
    const request = within(nav).getByRole("link", { name: "Request" });
    expect(request.getAttribute("href")).toBe("#/request");
  });

  it("RN-11: a generation job that ends done opens the Result screen with the generated card", async () => {
    const fetchMock = installBackend(jobGenerationDone);
    window.location.hash = "#/request";
    render(<App />);
    await sendRequest();

    expect(await screen.findByRole("heading", { level: 1, name: /result/i })).toBeTruthy();
    expect((await screen.findAllByText(cardGenerated.current_version.name, { exact: false })).length).toBeGreaterThan(0);
    const reads = fetchMock.mock.calls.map((call) => calledUrl(call[0]).split("?")[0]);
    expect(reads).toContain(`/api/cards/${CARD_ID}`);
    expect(screen.queryByRole("heading", { level: 1, name: /request/i })).toBeNull();
  });

  it("RN-15: the revision failure of the job result is shown on the Result screen", async () => {
    installBackend(jobGenerationRevisionFailed);
    window.location.hash = "#/request";
    render(<App />);
    await sendRequest();

    expect(await screen.findByRole("heading", { level: 1, name: /result/i })).toBeTruthy();
    const message = jobGenerationRevisionFailed.result.revision_failure.message;
    await waitFor(() =>
      expect(
        screen
          .getAllByRole("alert")
          .map((element) => element.textContent ?? "")
          .join(" "),
      ).toContain(message),
    );
  });
});
