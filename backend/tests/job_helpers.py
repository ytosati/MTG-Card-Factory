"""Test helpers for the job runner (task T13): an inline executor, runner installation,
a fake clock for the watchdog and the error envelope stored in a job.

Details: specs/plan.md, sections 6 (Jobs) and 7 (Concurrency, jobs, orphans).
"""

import time
from concurrent.futures import Executor, Future
from contextlib import contextmanager

JOB_TABLE = "core_job"

ENVELOPE_FIELDS = {"code", "message", "setting", "fields"}

JOB_FIELDS = {"id", "kind", "status", "progress", "result", "error"}

GENERATION_KINDS = ("generate", "adjust", "art")
BUILD_KIND = "build"

# Polling limit for jobs run on a real thread pool.
WAIT_SECONDS = 10.0


class InlineExecutor(Executor):
    """An executor that runs each submitted callable at once, in the calling thread."""

    def submit(self, fn, /, *args, **kwargs):
        future = Future()
        try:
            result = fn(*args, **kwargs)
        except BaseException as error:
            future.set_exception(error)
        else:
            future.set_result(result)
        return future


@contextmanager
def runner_installed(executor):
    """Install a fresh `core.jobs.JobRunner` on `executor` for the block, then put back the previous one."""
    from core.jobs import JobRunner, get_runner, set_runner

    previous = get_runner()
    runner = JobRunner(executor=executor)
    set_runner(runner)
    try:
        yield runner
    finally:
        set_runner(previous)


def inline_runner():
    """A fresh runner whose jobs run inline, inside `submit`."""
    return runner_installed(InlineExecutor())


def envelope_error(error):
    """The `{code, message, setting, fields}` object of a job's error envelope (plan section 6).

    `Job.error` and the `error` field of GET /api/jobs/{id} hold the envelope
    `{"error": {code, message, setting, fields}}` (plan section 6, "Jobs").
    """
    assert isinstance(error, dict), error
    assert set(error) == {"error"}, error
    inner = error["error"]
    assert isinstance(inner, dict), inner
    assert set(inner) == ENVELOPE_FIELDS, inner
    assert isinstance(inner["code"], str) and inner["code"]
    assert isinstance(inner["message"], str) and inner["message"].strip()
    assert inner["setting"] is None or isinstance(inner["setting"], str)
    assert inner["fields"] is None or isinstance(inner["fields"], dict)
    return inner


def wait_for_end(job_id, timeout=WAIT_SECONDS):
    """Poll `core.jobs.get_job` until the job is done or failed; fail after `timeout` seconds."""
    from core.jobs import get_job

    deadline = time.monotonic() + timeout
    while True:
        job = get_job(job_id)
        if job is not None and job.status in ("done", "failed"):
            return job
        if time.monotonic() > deadline:
            raise AssertionError(f"Job did not end within {timeout} s (last status: {getattr(job, 'status', None)}).")
        time.sleep(0.01)


class FakeClock:
    """A monotonic clock the test moves by hand."""

    def __init__(self, start=1000.0):
        self.now = float(start)

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class StopRecorder:
    """The stop callback of a watchdog: counts its calls."""

    def __init__(self):
        self.calls = 0

    def __call__(self):
        self.calls += 1


def run_checks(watchdog, clock, seconds, step=5):
    """Advance the clock by `seconds` in steps, calling `watchdog.check()` after each step."""
    elapsed = 0
    while elapsed < seconds:
        move = min(step, seconds - elapsed)
        clock.advance(move)
        elapsed += move
        watchdog.check()


@contextmanager
def job_updates_failing(statuses, message="database is locked"):
    """Make every UPDATE of the job table that writes one of `statuses` raise OperationalError.

    Works at the SQL level on the connection of the calling thread, so it does not
    depend on how the runner issues its updates. Yields the list of refused statements.
    """
    from django.db import OperationalError, connection

    statuses = {str(status) for status in statuses}
    refused = []

    def wrapper(execute, sql, params, many, context):
        text = str(sql).lstrip().upper()
        values = params or ()
        if many:
            values = [value for row in values for value in row]
        if (
            text.startswith("UPDATE")
            and JOB_TABLE.upper() in text
            and any(isinstance(value, str) and value in statuses for value in values)
        ):
            refused.append(sql)
            raise OperationalError(message)
        return execute(sql, params, many, context)

    with connection.execute_wrapper(wrapper):
        yield refused


@contextmanager
def watchdog_calls_counted():
    """Count the calls of `core.watchdog.hold` and `core.watchdog.release` during the block."""
    import core.watchdog

    counts = {"hold": 0, "release": 0}
    original_hold, original_release = core.watchdog.hold, core.watchdog.release

    def hold():
        counts["hold"] += 1
        return original_hold()

    def release():
        counts["release"] += 1
        return original_release()

    core.watchdog.hold, core.watchdog.release = hold, release
    try:
        yield counts
    finally:
        core.watchdog.hold, core.watchdog.release = original_hold, original_release
