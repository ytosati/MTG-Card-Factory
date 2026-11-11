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

/** GET /api/jobs/{id}: progress, result and error of a long operation (spec RN-10). */
export interface JobResponse {
  id: string;
  kind: JobKind;
  status: JobStatus;
  progress: number;
  /** JSON whose shape depends on the job kind; read it through the type of that kind. */
  result: unknown;
  error: ErrorEnvelope | null;
}

/** A failed automatic revision reported with a saved card (spec RN-15). */
export interface RevisionFailure {
  code: string;
  message: string;
}

/** The result of a generation job: the saved card and the revision failure, if any. */
export interface GenerationResult {
  card: string;
  revision_failure: RevisionFailure | null;
}

/** A generation job: POST /api/generations answers it, GET /api/jobs/{id} follows it. */
export interface GenerationJobResponse extends Omit<JobResponse, "result"> {
  result: GenerationResult | null;
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

/** Power levels of a request (spec RN-11). */
export type PowerLevel = "casual" | "medium" | "strong";

/** Color letters of a color identity; the empty list is colorless chosen explicitly (spec CA-26). */
export type ColorLetter = "W" | "U" | "B" | "R" | "G";

/** Body of POST /api/generations (spec RN-11). */
export interface GenerationRequest {
  idea: string;
  color_identity: ColorLetter[];
  power_level: PowerLevel;
}

/** A comparable card cited by the text model (spec RN-12, RN-13). */
export interface Comparable {
  oracle_id: string;
  name: string;
  role: string;
}

/** A failed check of a card and its cause (spec RN-14). */
export interface ValidationCause {
  check: string;
  code: string;
  message: string;
}

/** The validation result stored with a card version. */
export interface ValidationResult {
  status: CardStatus;
  checks_run: string[];
  causes: ValidationCause[];
  skipped: string[];
}

/** Validation status of a card version (spec RN-14). */
export type CardStatus = "approved" | "rejected";

/** Power indicator assessed by the text model (spec RN-22). */
export type PowerIndicator = "too_strong" | "in_range" | "too_weak";

/** The fields of a card version; an empty or null cost, power or toughness is absent. */
export interface CardVersion {
  name: string;
  mana_cost: string | null;
  mana_value: number;
  type_line: string;
  rules_text: string;
  power: string | null;
  toughness: string | null;
  rarity: string;
  design_intent: string;
  rationale: string;
  comparables: Comparable[];
  power_indicator: PowerIndicator;
  power_justification: string;
  origin: string;
  status: CardStatus;
  validation: ValidationResult;
}

/** One text provider call linked to a card (spec RN-09). */
export interface TextUsageRecord {
  provider: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  outcome: "ok" | "failed";
  created_at: string;
}

/** GET /api/cards/{id}: a card with its current version and its usage. */
export interface CardResponse {
  id: string;
  current_version: CardVersion;
  usage: { text: TextUsageRecord[] };
}
