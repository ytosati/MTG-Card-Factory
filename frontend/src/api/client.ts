// Typed API client base: every request goes to the local application under /api/.
// Details: specs/plan.md, section 6.
import type {
  ErrorEnvelope,
  GenerationJobResponse,
  GenerationRequest,
  HeartbeatRequest,
  JobResponse,
  SetupResponse,
  StatusResponse,
} from "./types";

/** An error response that carried the error envelope; callers branch on `code`, never on `message`. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly setting: string | null;
  /** Each invalid request field with its messages (code `validation`), or null. */
  readonly fields: Record<string, string[]> | null;

  constructor(status: number, envelope: ErrorEnvelope["error"]) {
    super(envelope.message);
    this.name = "ApiError";
    this.status = status;
    this.code = envelope.code;
    this.setting = envelope.setting;
    this.fields = envelope.fields;
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

/** Sends a GET, or a POST when there is a body, and returns the JSON body, or rejects with ApiError or a readable Error. */
async function requestJson<T>(path: string, body?: object): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  let response: Response;
  let text: string;
  try {
    // no-store: each screen visit must see the configuration as it is now (spec RN-08, CA-73).
    response = await fetch(path, {
      method: body === undefined ? "GET" : "POST",
      cache: "no-store",
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
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

function getJson<T>(path: string): Promise<T> {
  return requestJson<T>(path);
}

function postJson<T>(path: string, body: object): Promise<T> {
  return requestJson<T>(path, body);
}

/** GET /api/status: the current configuration, read again on every call. */
export function getStatus(): Promise<StatusResponse> {
  return getJson<StatusResponse>("/api/status");
}

/** GET /api/setup: database readiness, build job, sizes and settings to fix (spec RN-28). */
export function getSetup(): Promise<SetupResponse> {
  return getJson<SetupResponse>("/api/setup");
}

/** POST /api/setup/build: starts the database build, or returns the one that runs (spec RN-28). */
export function startBuild(): Promise<JobResponse> {
  return postJson<JobResponse>("/api/setup/build", {});
}

/** GET /api/jobs/{id}: progress, result and error of a long operation. */
export function getJob(id: string): Promise<JobResponse> {
  return getJson<JobResponse>(`/api/jobs/${encodeURIComponent(id)}`);
}

/** POST /api/generations: starts a card generation job (spec RN-11). */
export function startGeneration(request: GenerationRequest): Promise<GenerationJobResponse> {
  return postJson<GenerationJobResponse>("/api/generations", request);
}

/** GET /api/cards/{id}: the card with its current version and usage, as sent; callers check its shape. */
export function getCard(id: string): Promise<unknown> {
  return getJson<unknown>(`/api/cards/${encodeURIComponent(id)}`);
}

const HEARTBEAT_BODY: HeartbeatRequest = {};

/** POST /api/heartbeat: tells the application a tab is still open (spec RN-41). Rejects when it fails. */
export async function sendHeartbeat(): Promise<void> {
  // keepalive lets the request outlive the page on pagehide; sendBeacon cannot send JSON (see plan section 6).
  const response = await fetch("/api/heartbeat", {
    method: "POST",
    keepalive: true,
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(HEARTBEAT_BODY),
  });
  if (!response.ok) throw new Error(`Heartbeat failed (HTTP ${response.status})`);
}
