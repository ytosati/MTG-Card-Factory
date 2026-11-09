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

/** Configuration part of GET /api/status. */
export interface StatusResponse {
  text_provider: string | null;
  text_model: string | null;
  text_key_configured: boolean;
  image_provider: string | null;
  image_model: string | null;
  settings: SettingIssue[];
  next_start_port: number | null;
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
