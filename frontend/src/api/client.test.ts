// @vitest-environment jsdom
// Tests for the typed API client base, GET /api/status (spec RN-08; plan section 6)
// and the Milestone 2 endpoints: GET /api/setup, POST /api/setup/build and GET /api/jobs/{id} (spec RN-28).
//
// Client API under test (frontend/src/api/client.ts):
//   getSetup(): Promise<SetupResponse>
//   startBuild(): Promise<JobResponse>   (POST /api/setup/build, answered 202 with the build job)
//   getJob(id: string): Promise<JobResponse>
// Error answers reject with ApiError carrying the envelope, as getStatus does.
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, getJob, getSetup, getStatus, startBuild } from "./client";
import {
  errorNotFound,
  jobBuildDone,
  jobBuildFailed,
  setupBuildAccepted,
  setupBuildFailed,
  setupBuildRefusedForSpace,
  setupBuilding,
  setupListingUnreachable,
  setupNotReady,
  setupSettingsToFix,
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

/** Awaits a promise expected to reject and returns the reason. */
async function rejection(promise: Promise<unknown>): Promise<unknown> {
  return promise.then(
    () => null,
    (reason: unknown) => reason,
  );
}

describe("getSetup", () => {
  it("RN-28: calls GET /api/setup on the local application", async () => {
    const fetchMock = stubFetch(async () => jsonResponse(setupNotReady));

    await getSetup();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [input, init] = fetchMock.mock.calls[0]!;
    expect(calledUrl(input)).toBe("/api/setup");
    expect(init?.method ?? "GET").toBe("GET");
  });

  it.each([
    ["not ready", setupNotReady],
    ["settings to fix", setupSettingsToFix],
    ["building", setupBuilding],
    ["build failed", setupBuildFailed],
    ["listing unreachable", setupListingUnreachable],
  ])("RN-28: returns the setup body as parsed JSON (%s)", async (_name, body) => {
    stubFetch(async () => jsonResponse(body));

    expect(await getSetup()).toEqual(body);
  });

  it("RN-28: each call fetches again, so the build progress is never a cached answer", async () => {
    const fetchMock = stubFetch(
      async () => jsonResponse(setupNotReady),
      async () => jsonResponse(setupBuilding),
    );

    const first = await getSetup();
    const second = await getSetup();

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(first.job).toBeNull();
    expect(second.job?.status).toBe("running");
  });

  it("plan section 6: an error answer rejects with ApiError carrying the envelope code", async () => {
    stubFetch(async () => jsonResponse(errorNotFound, 404));

    const error = await rejection(getSetup());

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).code).toBe("not_found");
    expect((error as ApiError).status).toBe(404);
  });

  it("plan section 6: a success answer whose body is not JSON rejects", async () => {
    stubFetch(async () => textResponse("<html>index</html>", 200));

    await expect(getSetup()).rejects.toBeInstanceOf(Error);
  });
});

describe("startBuild", () => {
  it("CA-18: sends POST /api/setup/build and returns the build job of the 202 answer", async () => {
    const fetchMock = stubFetch(async () => jsonResponse(setupBuildAccepted, 202));

    const job = await startBuild();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [input, init] = fetchMock.mock.calls[0]!;
    expect(calledUrl(input)).toBe("/api/setup/build");
    expect(init?.method).toBe("POST");
    expect(job).toEqual(setupBuildAccepted);
  });

  it("plan section 6: a request body, when sent, is JSON with a JSON content type (a malformed one is refused)", async () => {
    const fetchMock = stubFetch(async () => jsonResponse(setupBuildAccepted, 202));

    await startBuild();

    const init = fetchMock.mock.calls[0]![1] ?? {};
    if (init.body !== undefined && init.body !== null) {
      expect(typeof init.body).toBe("string");
      expect(() => JSON.parse(init.body as string)).not.toThrow();
      expect(new Headers(init.headers).get("Content-Type")).toBe("application/json");
    }
  });

  it("CA-60: a build refused for lack of disk space rejects with ApiError insufficient_space (507)", async () => {
    stubFetch(async () => jsonResponse(setupBuildRefusedForSpace, 507));

    const error = await rejection(startBuild());

    expect(error).toBeInstanceOf(ApiError);
    const apiError = error as ApiError;
    expect(apiError.status).toBe(507);
    expect(apiError.code).toBe("insufficient_space");
    expect(apiError.message).toBe(setupBuildRefusedForSpace.error.message);
  });

  it("plan section 6: an error answer that is not JSON still rejects with an Error", async () => {
    stubFetch(async () => textResponse("<html>Bad gateway</html>", 502));

    await expect(startBuild()).rejects.toBeInstanceOf(Error);
  });

  it("RN-28: a network failure rejects instead of reporting a started build", async () => {
    stubFetch(async () => {
      throw new TypeError("Failed to fetch");
    });

    await expect(startBuild()).rejects.toBeInstanceOf(Error);
  });
});

describe("getJob", () => {
  it("RN-28: calls GET /api/jobs/{id} with the job id", async () => {
    const fetchMock = stubFetch(async () => jsonResponse(jobBuildDone));

    await getJob(jobBuildDone.id);

    const [input, init] = fetchMock.mock.calls[0]!;
    expect(calledUrl(input)).toBe(`/api/jobs/${jobBuildDone.id}`);
    expect(init?.method ?? "GET").toBe("GET");
  });

  it.each([
    ["queued", setupBuildAccepted],
    ["running", setupBuilding.job],
    ["done", jobBuildDone],
    ["failed with its cause", jobBuildFailed],
  ])("RN-28: returns the job as parsed JSON (%s)", async (_name, body) => {
    stubFetch(async () => jsonResponse(body));

    expect(await getJob(body.id)).toEqual(body);
  });

  it("RN-28: each call fetches again, so polling sees the job's progress", async () => {
    const fetchMock = stubFetch(
      async () => jsonResponse(setupBuilding.job),
      async () => jsonResponse(jobBuildDone),
    );

    const first = await getJob(jobBuildDone.id);
    const second = await getJob(jobBuildDone.id);

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(first.status).toBe("running");
    expect(second.status).toBe("done");
  });

  it("plan section 6: an unknown job rejects with ApiError not_found", async () => {
    stubFetch(async () => jsonResponse(errorNotFound, 404));

    const error = await rejection(getJob("00000000-0000-4000-8000-0000000000ff"));

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).code).toBe("not_found");
  });

  it.each(["../setup/build", "a/b?c=d#e", "card factory ✨"])(
    "plan section 6: an id with odd characters stays one path segment under /api/jobs/ (%s)",
    async (id) => {
      const fetchMock = stubFetch(async () => jsonResponse(errorNotFound, 404));

      await rejection(getJob(id));

      const url = calledUrl(fetchMock.mock.calls[0]![0]);
      expect(url.startsWith("/api/jobs/")).toBe(true);
      const segment = url.slice("/api/jobs/".length);
      expect(segment).not.toMatch(/[/?#\s]/);
      expect(decodeURIComponent(segment)).toBe(id);
    },
  );
});
