// Job polling: reads a background job until it is done or failed.
// Details: specs/plan.md, section 6 (Jobs); spec RN-28.
import { useEffect, useState } from "react";

import { ApiError, getJob } from "../api/client";
import type { JobResponse } from "../api/types";

const DEFAULT_INTERVAL_MS = 1_000;

interface JobState {
  id: string | null;
  job: JobResponse | null;
  error: ApiError | null;
}

function isFinished(job: JobResponse): boolean {
  return job.status === "done" || job.status === "failed";
}

/**
 * Polls GET /api/jobs/{id}: at once, then every `intervalMs` until the job finishes.
 * `error` is set only when polling stopped because the job does not exist.
 */
export function useJob(
  jobId: string | null,
  options: { intervalMs?: number } = {},
): { job: JobResponse | null; error: ApiError | null } {
  const intervalMs = options.intervalMs ?? DEFAULT_INTERVAL_MS;
  // The id is kept with the answer, so a new id never shows the previous job, not even for one render.
  const [state, setState] = useState<JobState>({ id: jobId, job: null, error: null });

  useEffect(() => {
    if (jobId === null) return;
    const id = jobId;

    let active = true;
    let timer: number | undefined;
    const scheduleNext = () => {
      timer = window.setTimeout(read, intervalMs);
    };
    function read() {
      getJob(id).then(
        (answer) => {
          if (!active) return;
          setState({ id, job: answer, error: null });
          if (!isFinished(answer)) scheduleNext();
        },
        (reason: unknown) => {
          if (!active) return;
          if (reason instanceof ApiError && reason.code === "not_found") {
            setState((previous) => ({ id, job: previous.id === id ? previous.job : null, error: reason }));
            return;
          }
          // A dropped connection or a busy answer is transient: the next tick tries again.
          scheduleNext();
        },
      );
    }

    read();
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [jobId, intervalMs]);

  return state.id === jobId ? { job: state.job, error: state.error } : { job: null, error: null };
}
