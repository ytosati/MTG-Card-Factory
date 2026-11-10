// Client types that mirror the API serializers.
// Details: specs/plan.md, section 6 (Endpoints, Contract samples).

/** Stable codes of a settings list item (plan section 6). */
export type SettingCode = "config_invalid" | "ignored";

/** A setting to fix or a setting ignored with a notice (spec RN-08). */
export interface SettingIssue {
  setting: string;
  code: SettingCode;
  message: string;
}

/** Origin, publication date and download date of a data source (spec RN-01). */
export interface SourceInfo {
  source: string;
  url: string;
  published_at: string;
  downloaded_at: string;
}

/** GET /api/status: configuration, database readiness and data sources. */
export interface StatusResponse {
  text_provider: string | null;
  text_model: string | null;
  text_key_configured: boolean;
  image_provider: string | null;
  image_model: string | null;
  settings: SettingIssue[];
  next_start_port: number | null;
  database_ready: boolean;
  sources: SourceInfo[];
}

/** GET /api/instance: identifies a running Card Factory and its home (spec RN-47). */
export interface InstanceResponse {
  app: string;
  version: string;
  home: string;
}

/** Body of POST /api/heartbeat: an empty JSON object (spec RN-41). */
export type HeartbeatRequest = Record<string, never>;

/** The single error envelope of every error response. */
export interface ErrorEnvelope {
  error: {
    code: string;
    message: string;
    setting: string | null;
    fields: Record<string, string[]> | null;
  };
}

/** Kinds of a background job. */
export type JobKind = "build" | "generate" | "adjust" | "art";

/** States of a background job. */
export type JobStatus = "queued" | "running" | "done" | "failed";

/** GET /api/jobs/{id}: progress, result (a card id) and error of a long operation (spec RN-10). */
export interface JobResponse {
  id: string;
  kind: JobKind;
  status: JobStatus;
  progress: number;
  result: string | null;
  error: ErrorEnvelope | null;
}

/** GET /api/setup: build state, sizes in bytes and settings to fix (spec RN-28). */
export interface SetupResponse {
  database_ready: boolean;
  job: JobResponse | null;
  download_size: number | null;
  space_needed: number | null;
  free_space: number | null;
  listing_error: ErrorEnvelope | null;
  settings: SettingIssue[];
}
