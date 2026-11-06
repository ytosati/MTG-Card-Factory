// @vitest-environment jsdom
// Tests for the typed API client base and GET /api/status (spec RN-08; plan section 6).
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, getStatus } from "./client";
import {
  errorNotFound,
  statusFullConfiguration,
  statusMissingTextKey,
} from "./contract/samples";
import { calledUrl, jsonResponse, stubFetch, textResponse } from "../test/fetchMock";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("getStatus", () => {
  it("RN-08: calls the relative URL /api/status with GET, so it reaches only the local application", async () => {
    const fetchMock = stubFetch(async () => jsonResponse(statusFullConfiguration));

    await getStatus();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [input, init] = fetchMock.mock.calls[0]!;
    expect(calledUrl(input)).toBe("/api/status");
    expect(init?.method ?? "GET").toBe("GET");
  });

  it("RN-08: returns the status body as parsed JSON", async () => {
    stubFetch(async () => jsonResponse(statusMissingTextKey));

    const status = await getStatus();

    expect(status).toEqual(statusMissingTextKey);
  });

  it("CA-73: each call fetches again instead of reusing an earlier answer", async () => {
    const fetchMock = stubFetch(
      async () => jsonResponse(statusMissingTextKey),
      async () => jsonResponse(statusFullConfiguration),
    );

    const first = await getStatus();
    const second = await getStatus();

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(first.text_key_configured).toBe(false);
    expect(second.text_key_configured).toBe(true);
  });

  it("plan section 6: an error response rejects with ApiError carrying the envelope code, message and setting", async () => {
    stubFetch(async () => jsonResponse(errorNotFound, 404));

    const error = await getStatus().then(
      () => null,
      (reason: unknown) => reason,
    );

    expect(error).toBeInstanceOf(ApiError);
    const apiError = error as ApiError;
    expect(apiError.status).toBe(404);
    expect(apiError.code).toBe(errorNotFound.error.code);
    expect(apiError.message).toBe(errorNotFound.error.message);
    expect(apiError.setting).toBeNull();
  });

  it("RN-08: an error envelope that names a setting keeps the setting on the ApiError", async () => {
    const envelope = {
      ...errorNotFound,
      error: {
        ...errorNotFound.error,
        code: "config_invalid",
        message: "Set LLM_API_KEY to the API key of the text provider.",
        setting: "LLM_API_KEY",
      },
    };
    stubFetch(async () => jsonResponse(envelope, 400));

    const error = await getStatus().then(
      () => null,
      (reason: unknown) => reason,
    );

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).code).toBe("config_invalid");
    expect((error as ApiError).setting).toBe("LLM_API_KEY");
  });

  it("plan section 6: an error response whose body is not JSON still rejects with an Error", async () => {
    stubFetch(async () => textResponse("<html><body>Bad gateway</body></html>", 502));

    await expect(getStatus()).rejects.toBeInstanceOf(Error);
  });

  it("plan section 6: a success response whose body is not JSON rejects instead of returning garbage", async () => {
    stubFetch(async () => textResponse("not json {", 200));

    await expect(getStatus()).rejects.toBeInstanceOf(Error);
  });

  it("RN-08: a network failure rejects", async () => {
    stubFetch(async () => {
      throw new TypeError("Failed to fetch");
    });

    await expect(getStatus()).rejects.toBeInstanceOf(Error);
  });
});
