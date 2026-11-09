// @vitest-environment jsdom
// Tests for the tab heartbeat (spec RN-41, CA-47; plan sections 6 and 9.4 step 8; T85).
//
// Hook API under test (frontend/src/hooks/useHeartbeat.ts):
//   useHeartbeat(): { stopped: boolean }
// It sends POST /api/heartbeat (JSON body {}, Content-Type application/json,
// fetch with keepalive: true, never navigator.sendBeacon) on mount, every
// 15 seconds, when the tab becomes visible again and on pagehide. `stopped`
// turns true after a failed heartbeat (network error or non-2xx answer) and
// false again after a later one that succeeds. App mounts it once and, while
// `stopped` is true, shows a role="alert" notice that says the application
// stopped and how to start it again (double-click the launcher or start file).
import { act, cleanup, render, renderHook, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useHeartbeat } from "./useHeartbeat";
import { App } from "../App";
import { heartbeatRequest, statusFullConfiguration } from "../api/contract/samples";
import { calledUrl, jsonResponse } from "../test/fetchMock";

const HEARTBEAT_URL = "/api/heartbeat";
const INTERVAL_MS = 15_000;

type Answer = () => Promise<Response>;

const noContent: Answer = async () => new Response(null, { status: 204 });
const networkError: Answer = async () => {
  throw new TypeError("Failed to fetch");
};
const serverError: Answer = async () =>
  new Response("<html>Bad gateway</html>", { status: 502, headers: { "Content-Type": "text/html" } });

/**
 * Stubs fetch: heartbeats take the next queued answer (repeating the last one),
 * any other request (the Status screen) gets the full configuration sample.
 */
function stubBackend(...heartbeatAnswers: Answer[]) {
  const answers = heartbeatAnswers.length > 0 ? heartbeatAnswers : [noContent];
  let call = 0;
  const fetchMock = vi.fn((input: RequestInfo | URL, _init?: RequestInit) => {
    if (calledUrl(input) === HEARTBEAT_URL) {
      const answer = answers[Math.min(call, answers.length - 1)]!;
      call += 1;
      return answer();
    }
    return Promise.resolve(jsonResponse(statusFullConfiguration));
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function heartbeatCalls(fetchMock: ReturnType<typeof stubBackend>) {
  return fetchMock.mock.calls.filter((call) => calledUrl(call[0]) === HEARTBEAT_URL);
}

let visibility: DocumentVisibilityState = "visible";

function setVisibility(state: DocumentVisibilityState) {
  visibility = state;
  document.dispatchEvent(new Event("visibilitychange"));
}

/** Advances the fake clock and lets pending promises and React updates settle. */
async function advance(ms: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

/** The alert that says the application stopped, or null. */
function stoppedNotice(): HTMLElement | null {
  return screen.queryAllByRole("alert").find((element) => /stopped/i.test(element.textContent ?? "")) ?? null;
}

beforeEach(() => {
  vi.useFakeTimers();
  visibility = "visible";
  Object.defineProperty(document, "visibilityState", { configurable: true, get: () => visibility });
  Object.defineProperty(navigator, "sendBeacon", { configurable: true, writable: true, value: vi.fn(() => true) });
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  window.location.hash = "";
});

describe("useHeartbeat", () => {
  it("RN-41: sends one heartbeat on mount as a JSON POST fetch with keepalive, never sendBeacon (T85)", async () => {
    const fetchMock = stubBackend();

    renderHook(() => useHeartbeat());
    await advance(0);

    const calls = heartbeatCalls(fetchMock);
    expect(calls).toHaveLength(1);
    const init = calls[0]![1] ?? {};
    expect(init.method).toBe("POST");
    expect(init.keepalive).toBe(true);
    expect(new Headers(init.headers).get("Content-Type")).toBe("application/json");
    expect(typeof init.body).toBe("string");
    expect(JSON.parse(init.body as string)).toEqual(heartbeatRequest);
    expect(navigator.sendBeacon).not.toHaveBeenCalled();
  });

  it("RN-41: sends a heartbeat every 15 seconds", async () => {
    const fetchMock = stubBackend();

    renderHook(() => useHeartbeat());
    await advance(0);
    expect(heartbeatCalls(fetchMock)).toHaveLength(1);

    await advance(INTERVAL_MS - 1);
    expect(heartbeatCalls(fetchMock)).toHaveLength(1);

    await advance(1);
    expect(heartbeatCalls(fetchMock)).toHaveLength(2);

    await advance(INTERVAL_MS * 2);
    expect(heartbeatCalls(fetchMock)).toHaveLength(4);
  });

  it("RN-41: sends a heartbeat when the tab becomes visible again, not when it is hidden", async () => {
    const fetchMock = stubBackend();

    renderHook(() => useHeartbeat());
    await advance(0);
    expect(heartbeatCalls(fetchMock)).toHaveLength(1);

    await act(async () => setVisibility("hidden"));
    await advance(0);
    expect(heartbeatCalls(fetchMock)).toHaveLength(1);

    await act(async () => setVisibility("visible"));
    await advance(0);
    expect(heartbeatCalls(fetchMock)).toHaveLength(2);
  });

  it("RN-41: sends a keepalive heartbeat on pagehide", async () => {
    const fetchMock = stubBackend();

    renderHook(() => useHeartbeat());
    await advance(0);
    expect(heartbeatCalls(fetchMock)).toHaveLength(1);

    await act(async () => {
      window.dispatchEvent(new Event("pagehide"));
    });
    await advance(0);

    const calls = heartbeatCalls(fetchMock);
    expect(calls).toHaveLength(2);
    expect(calls[1]![1]?.keepalive).toBe(true);
    expect(navigator.sendBeacon).not.toHaveBeenCalled();
  });

  it("RN-41: stops sending after unmount (no timer or listener left behind)", async () => {
    const fetchMock = stubBackend();

    const { unmount } = renderHook(() => useHeartbeat());
    await advance(0);
    unmount();

    await advance(INTERVAL_MS * 3);
    document.dispatchEvent(new Event("visibilitychange"));
    window.dispatchEvent(new Event("pagehide"));
    await advance(0);

    expect(heartbeatCalls(fetchMock)).toHaveLength(1);
  });

  it("CA-47: reports stopped after a failed heartbeat and clears it after a later success", async () => {
    stubBackend(noContent, networkError, noContent);

    const { result } = renderHook(() => useHeartbeat());
    await advance(0);
    expect(result.current.stopped).toBe(false);

    await advance(INTERVAL_MS);
    expect(result.current.stopped).toBe(true);

    await advance(INTERVAL_MS);
    expect(result.current.stopped).toBe(false);
  });

  it("CA-47: a non-2xx answer with a body that is not JSON counts as a failed heartbeat", async () => {
    stubBackend(serverError);

    const { result } = renderHook(() => useHeartbeat());
    await advance(0);

    expect(result.current.stopped).toBe(true);
  });
});

describe("App heartbeat notice", () => {
  it("RN-41: the application root sends exactly one heartbeat on mount", async () => {
    window.location.hash = "#/status";
    const fetchMock = stubBackend();

    render(<App />);
    await advance(0);

    expect(heartbeatCalls(fetchMock)).toHaveLength(1);
    expect(stoppedNotice()).toBeNull();
  });

  it("CA-47: a network failure shows that the application stopped and how to start it again", async () => {
    window.location.hash = "#/status";
    stubBackend(networkError);

    render(<App />);
    await advance(0);

    const notice = stoppedNotice();
    expect(notice).not.toBeNull();
    expect(notice!.textContent).toMatch(/start/i);
    expect(notice!.textContent).toMatch(/double-click/i);
  });

  it("CA-47: a non-2xx heartbeat shows the notice and a later success clears it", async () => {
    window.location.hash = "#/status";
    stubBackend(noContent, serverError, noContent);

    render(<App />);
    await advance(0);
    expect(stoppedNotice()).toBeNull();

    await advance(INTERVAL_MS);
    expect(stoppedNotice()).not.toBeNull();

    await advance(INTERVAL_MS);
    expect(stoppedNotice()).toBeNull();
  });

  it("CA-47: a heartbeat on returning to the tab also clears the notice", async () => {
    window.location.hash = "#/status";
    stubBackend(networkError, noContent);

    render(<App />);
    await advance(0);
    expect(stoppedNotice()).not.toBeNull();

    await act(async () => setVisibility("hidden"));
    await act(async () => setVisibility("visible"));
    await advance(0);

    expect(stoppedNotice()).toBeNull();
  });
});
