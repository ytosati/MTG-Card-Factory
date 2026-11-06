// Typed API client base: every request goes to the local application under /api/.
// Details: specs/plan.md, section 6.
import type { ErrorEnvelope, StatusResponse } from "./types";

/** An error response that carried the error envelope; callers branch on `code`, never on `message`. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly setting: string | null;

  constructor(status: number, envelope: ErrorEnvelope["error"]) {
    super(envelope.message);
    this.name = "ApiError";
    this.status = status;
    this.code = envelope.code;
    this.setting = envelope.setting;
  }
}

const UNREACHABLE_MESSAGE = "Card Factory could not be reached. Check that it is still running.";
const UNREADABLE_MESSAGE = "Card Factory sent a response that could not be read.";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function envelopeError(body: unknown): ErrorEnvelope["error"] | null {
  if (!isRecord(body) || !isRecord(body.error)) return null;
  const { code, message, setting, fields } = body.error;
  if (typeof code !== "string" || typeof message !== "string") return null;
  return {
    code,
    message,
    setting: typeof setting === "string" ? setting : null,
    fields: isRecord(fields) ? (fields as Record<string, string[]>) : null,
  };
}

function parseJson(text: string): { ok: true; value: unknown } | { ok: false } {
  try {
    return { ok: true, value: JSON.parse(text) as unknown };
  } catch {
    return { ok: false };
  }
}

/** Sends a GET request and returns the JSON body, or rejects with ApiError or a readable Error. */
async function getJson<T>(path: string): Promise<T> {
  let response: Response;
  let text: string;
  try {
    // no-store: each screen visit must see the configuration as it is now (spec RN-08, CA-73).
    response = await fetch(path, { cache: "no-store", headers: { Accept: "application/json" } });
    text = await response.text();
  } catch {
    throw new Error(UNREACHABLE_MESSAGE);
  }

  const parsed = parseJson(text);
  if (!response.ok) {
    const envelope = parsed.ok ? envelopeError(parsed.value) : null;
    if (envelope) throw new ApiError(response.status, envelope);
    throw new Error(`${UNREADABLE_MESSAGE} (HTTP ${response.status})`);
  }
  if (!parsed.ok) throw new Error(UNREADABLE_MESSAGE);
  return parsed.value as T;
}

/** GET /api/status: the current configuration, read again on every call. */
export function getStatus(): Promise<StatusResponse> {
  return getJson<StatusResponse>("/api/status");
}
