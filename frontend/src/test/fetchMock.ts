// Test helpers that stand in for the backend: fetch mocks built from the contract samples.
// Details: specs/plan.md, section 6 (Contract samples).
import { vi } from "vitest";

/** A fresh JSON response; a Response body can be read only once. */
export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

/** A fresh response with a body that is not JSON. */
export function textResponse(body: string, status: number): Response {
  return new Response(body, {
    status,
    headers: { "Content-Type": "text/html" },
  });
}

/** Replaces globalThis.fetch with a mock that answers each call with the next factory, repeating the last one. */
export function stubFetch(...answers: Array<() => Promise<Response>>) {
  let call = 0;
  const fetchMock = vi.fn((_input: RequestInfo | URL, _init?: RequestInit) => {
    const answer = answers[Math.min(call, answers.length - 1)]!;
    call += 1;
    return answer();
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

/** The URL of a recorded fetch call, as a string. */
export function calledUrl(input: RequestInfo | URL): string {
  if (typeof input === "string") return input;
  if (input instanceof URL) return input.toString();
  return input.url;
}

/** An answer for one API path: a fixed JSON body (status 200) or a factory that builds the response. */
export type RouteAnswer = unknown | ((url: string, init?: RequestInit) => Promise<Response>);

/**
 * Replaces globalThis.fetch with a mock that answers by path (query string ignored).
 * A key ending in "/" matches every path under it; the longest matching key wins.
 * Unknown paths answer 404 with the error envelope, as the backend does.
 */
export function stubFetchByPath(routes: Record<string, RouteAnswer>) {
  const keys = Object.keys(routes).sort((a, b) => b.length - a.length);
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = calledUrl(input);
    const path = url.split("?")[0] ?? url;
    const key = keys.find((candidate) => (candidate.endsWith("/") ? path.startsWith(candidate) : path === candidate));
    if (key === undefined) {
      return Promise.resolve(
        jsonResponse(
          { error: { code: "not_found", message: "Not found.", setting: null, fields: null } },
          404,
        ),
      );
    }
    const answer = routes[key];
    if (typeof answer === "function") {
      return (answer as (url: string, init?: RequestInit) => Promise<Response>)(url, init);
    }
    return Promise.resolve(jsonResponse(answer));
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}
