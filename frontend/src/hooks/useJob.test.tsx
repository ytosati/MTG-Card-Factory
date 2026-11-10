// @vitest-environment jsdom
// Tests for the job polling hook (spec RN-28, CA-18; plan section 6, "Jobs").
//
// Hook API under test (frontend/src/hooks/useJob.ts):
//   useJob(jobId: string | null, options?: { intervalMs?: number }):
//     { job: JobResponse | null; error: ApiError | null }
// With an id it reads GET /api/jobs/{id} at once and then every `intervalMs`
// until the job is done or failed; then it stops. A job that does not exist
// (not_found) stops polling and sets `error`; a dropped connection is retried
// at the next interval. With a null id it reads nothing. It never polls after
// unmount, not even when an answer arrives late, and never returns the job of
// an earlier id.
import { act, cleanup, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useJob } from "./useJob";
import type { JobResponse } from "../api/types";
import {
  errorNotFound,
  jobBuildDone,
  jobBuildFailed,
  setupBuildAccepted,
  setupBuilding,
} from "../api/contract/samples";
import { calledUrl, jsonResponse, stubFetch } from "../test/fetchMock";

const INTERVAL_MS = 1_000;
const JOB_ID = jobBuildDone.id;
const JOB_URL = `/api/jobs/${JOB_ID}`;

const queued: JobResponse = setupBuildAccepted;
const running: JobResponse = setupBuilding.job;
const runningLater: JobResponse = { ...setupBuilding.job, progress: 0.5 };

function answer(job: JobResponse) {
  return async () => jsonResponse(job);
}

/** Advances the fake clock and lets pending promises and React updates settle. */
async function advance(ms: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

function jobCalls(fetchMock: ReturnType<typeof stubFetch>, url = JOB_URL) {
  return fetchMock.mock.calls.filter((call) => calledUrl(call[0]) === url);
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("useJob", () => {
  it("RN-28: reads GET /api/jobs/{id} at once and then once per interval, showing the progress", async () => {
    const fetchMock = stubFetch(answer(queued), answer(running), answer(runningLater));

    const { result } = renderHook(() => useJob(JOB_ID, { intervalMs: INTERVAL_MS }));
    await advance(0);

    expect(jobCalls(fetchMock)).toHaveLength(1);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(result.current.job?.status).toBe("queued");

    await advance(INTERVAL_MS - 1);
    expect(jobCalls(fetchMock)).toHaveLength(1);

    await advance(1);
    expect(jobCalls(fetchMock)).toHaveLength(2);
    expect(result.current.job?.status).toBe("running");
    expect(result.current.job?.progress).toBe(0.05);

    await advance(INTERVAL_MS);
    expect(jobCalls(fetchMock)).toHaveLength(3);
    expect(result.current.job?.progress).toBe(0.5);
  });

  it("RN-28, CA-18: stops polling once the job is done and keeps the finished job", async () => {
    const fetchMock = stubFetch(answer(queued), answer(running), answer(jobBuildDone));

    const { result } = renderHook(() => useJob(JOB_ID, { intervalMs: INTERVAL_MS }));
    await advance(0);
    await advance(INTERVAL_MS);
    await advance(INTERVAL_MS);

    expect(jobCalls(fetchMock)).toHaveLength(3);
    expect(result.current.job).toEqual(jobBuildDone);

    await advance(INTERVAL_MS * 20);

    expect(jobCalls(fetchMock)).toHaveLength(3);
    expect(result.current.job).toEqual(jobBuildDone);
  });

  it("RN-28: stops polling once the job failed and exposes its cause from the error envelope", async () => {
    const fetchMock = stubFetch(answer(running), answer(jobBuildFailed));

    const { result } = renderHook(() => useJob(JOB_ID, { intervalMs: INTERVAL_MS }));
    await advance(0);
    await advance(INTERVAL_MS);

    expect(result.current.job?.status).toBe("failed");
    expect(result.current.job?.error?.error.code).toBe(jobBuildFailed.error.error.code);
    expect(result.current.job?.error?.error.message).toBe(jobBuildFailed.error.error.message);

    await advance(INTERVAL_MS * 20);

    expect(jobCalls(fetchMock)).toHaveLength(2);
  });

  it("RN-28: a job that is already done on the first answer is read exactly once", async () => {
    const fetchMock = stubFetch(answer(jobBuildDone));

    const { result } = renderHook(() => useJob(JOB_ID, { intervalMs: INTERVAL_MS }));
    await advance(0);
    await advance(INTERVAL_MS * 10);

    expect(jobCalls(fetchMock)).toHaveLength(1);
    expect(result.current.job?.status).toBe("done");
  });

  it("RN-28: a job that is already failed on the first answer is read exactly once", async () => {
    const fetchMock = stubFetch(answer(jobBuildFailed));

    renderHook(() => useJob(JOB_ID, { intervalMs: INTERVAL_MS }));
    await advance(0);
    await advance(INTERVAL_MS * 10);

    expect(jobCalls(fetchMock)).toHaveLength(1);
  });

  it("CA-18: with no job id nothing is read and there is no job", async () => {
    const fetchMock = stubFetch(answer(running));

    const { result } = renderHook(() => useJob(null, { intervalMs: INTERVAL_MS }));
    await advance(INTERVAL_MS * 10);

    expect(fetchMock).not.toHaveBeenCalled();
    expect(result.current.job).toBeNull();
  });

  it("RN-28: no polling after unmount (no timer left behind)", async () => {
    const fetchMock = stubFetch(answer(running));

    const { unmount } = renderHook(() => useJob(JOB_ID, { intervalMs: INTERVAL_MS }));
    await advance(0);
    await advance(INTERVAL_MS);
    expect(jobCalls(fetchMock)).toHaveLength(2);

    unmount();
    await advance(INTERVAL_MS * 20);

    expect(jobCalls(fetchMock)).toHaveLength(2);
  });

  it("RN-28: an answer that arrives after unmount schedules no further request", async () => {
    let release: (response: Response) => void = () => {};
    const fetchMock = stubFetch(
      () =>
        new Promise<Response>((resolve) => {
          release = resolve;
        }),
    );

    const { unmount } = renderHook(() => useJob(JOB_ID, { intervalMs: INTERVAL_MS }));
    await advance(0);
    expect(jobCalls(fetchMock)).toHaveLength(1);

    unmount();
    await act(async () => {
      release(jsonResponse(running));
    });
    await advance(INTERVAL_MS * 20);

    expect(jobCalls(fetchMock)).toHaveLength(1);
  });

  it("RN-28: a new job id polls the new job and the old one is no longer read", async () => {
    const otherId = "00000000-0000-4000-8000-000000000002";
    const otherUrl = `/api/jobs/${otherId}`;
    const fetchMock = stubFetch(answer(running));

    const { rerender } = renderHook(({ id }: { id: string }) => useJob(id, { intervalMs: INTERVAL_MS }), {
      initialProps: { id: JOB_ID },
    });
    await advance(0);
    expect(jobCalls(fetchMock)).toHaveLength(1);

    rerender({ id: otherId });
    await advance(0);
    await advance(INTERVAL_MS * 3);

    expect(jobCalls(fetchMock)).toHaveLength(1);
    expect(jobCalls(fetchMock, otherUrl).length).toBeGreaterThanOrEqual(1);
  });

  it("RN-28: a job that does not exist (404 not_found) is read once, sets the error and stops polling", async () => {
    const fetchMock = stubFetch(async () => jsonResponse(errorNotFound, 404));

    const { result } = renderHook(() => useJob(JOB_ID, { intervalMs: INTERVAL_MS }));
    await advance(0);

    expect(jobCalls(fetchMock)).toHaveLength(1);
    expect(result.current.error?.code).toBe("not_found");
    expect(result.current.job).toBeNull();

    await advance(INTERVAL_MS * 20);

    expect(jobCalls(fetchMock)).toHaveLength(1);
    expect(result.current.job).toBeNull();
  });

  it("RN-28: a dropped connection is read again at the next interval and the job then shows", async () => {
    const fetchMock = stubFetch(async () => {
      throw new TypeError("Failed to fetch");
    }, answer(running));

    const { result } = renderHook(() => useJob(JOB_ID, { intervalMs: INTERVAL_MS }));
    await advance(0);

    expect(jobCalls(fetchMock)).toHaveLength(1);
    expect(result.current.job).toBeNull();

    await advance(INTERVAL_MS);

    expect(jobCalls(fetchMock)).toHaveLength(2);
    expect(result.current.job?.status).toBe("running");
  });

  it("RN-28: after the id changes, no render returns the job of the earlier id", async () => {
    const otherId = "00000000-0000-4000-8000-000000000002";
    const otherUrl = `/api/jobs/${otherId}`;
    const fetchMock = stubFetch(answer(jobBuildDone), () => new Promise<Response>(() => {}));
    const renders: Array<{ id: string; job: JobResponse | null }> = [];

    const { rerender, result } = renderHook(
      ({ id }: { id: string }) => {
        const state = useJob(id, { intervalMs: INTERVAL_MS });
        renders.push({ id, job: state.job });
        return state;
      },
      { initialProps: { id: JOB_ID } },
    );
    await advance(0);
    expect(result.current.job?.id).toBe(JOB_ID);

    rerender({ id: otherId });
    await advance(0);

    expect(jobCalls(fetchMock, otherUrl)).toHaveLength(1);
    const afterChange = renders.filter((entry) => entry.id === otherId);
    expect(afterChange.length).toBeGreaterThan(0);
    expect(afterChange[0]!.job).toBeNull();
    for (const entry of afterChange) {
      expect(entry.job).toBeNull();
    }
  });
});
