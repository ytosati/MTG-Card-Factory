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
