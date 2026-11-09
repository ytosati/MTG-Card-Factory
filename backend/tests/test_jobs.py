"""Job model and in-process runner (task T13, spec RN-03, RN-10, RN-41, RN-50, CA-70).

Details: specs/plan.md, sections 4 (`Job`), 6 (Jobs, error envelope) and 7
(Concurrency, orphans, usage queue).

API under test:

    core.models.Job
        id        UUID4, primary key
        kind      "build", "generate", "adjust" or "art"
        status    "queued", "running", "done" or "failed"
        progress  the last progress reported by the job
        result    what the job function returned (a card id), or None
        error     None, or the error envelope of plan section 6:
                  {"error": {"code", "message", "setting", "fields"}}
        created_at

    core.jobs.JobRunner(executor=None)
        `executor` is a concurrent.futures.Executor; None means the real thread
        pool. The runner remembers the ids of the jobs it submitted.
        .submit(kind, fn) -> Job      persists the job, then runs it on the executor
        .get_job(job_id) -> Job | None

    core.jobs.get_runner() / core.jobs.set_runner(runner)
        the runner of this process (created on first use with the thread pool)
    core.jobs.submit(kind, fn) and core.jobs.get_job(job_id)
        the same calls on get_runner()
    core.jobs.fail_orphan_jobs()
        startup housekeeping: every job stored as queued or running becomes failed

    `fn` is called with one argument, `report(progress)`, which records the
    progress in memory; its return value becomes `result`. While it runs, the
    job holds the watchdog (`core.watchdog.hold()` / `release()`).
    An exception raised by `fn` fails the job: `error` is the envelope with
    code `internal` and a fixed message, `result` stays None, and the text of
    the exception is never stored (it goes only to the redacted log).

    `get_job(job_id)` returns None for an id with no job. A job stored as queued
    or running whose id the runner does not know (an orphan of an earlier
    process) is stored and returned as failed, with an error envelope.

    RN-50: while a "generate", "adjust" or "art" job is queued or running,
    `submit` of another one of those kinds raises `core.jobs.GenerationRunning`,
    whose `code` is "generation_running" and `message` says one is already
    running; no job is stored for the refused submission. "build" is not a
    generation job.

    core.jobs.enqueue_usage(write)
        `write` is a callable with no arguments (the usage record of a
        connection test). With no build running it runs at once; while a build
        runs it waits in memory and runs when the build ends, whatever the outcome.

Jobs run inline (tests.job_helpers.InlineExecutor) unless the test uses the
real thread pool, in which case it runs with `transaction=True`.
"""

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from tests.config_files import FAKE_TEXT_KEY
from tests.isolation import TEST_HOME
from tests.job_helpers import (
    BUILD_KIND,
    GENERATION_KINDS,
    WAIT_SECONDS,
    FakeClock,
    InlineExecutor,
    StopRecorder,
    envelope_error,
    inline_runner,
    job_updates_failing,
    run_checks,
    runner_installed,
    wait_for_end,
    watchdog_calls_counted,
)

ALL_KINDS = (BUILD_KIND, *GENERATION_KINDS)
FICTIONAL_CARD_ID = "5d0c7a52-3b8e-4f1a-9c26-7e41b9d0a3f8"

# Exception texts that must never be stored in a job (RN-10, plan section 6).
FAILURE_TEXTS = [
    pytest.param(f"provider said: invalid key {FAKE_TEXT_KEY}", id="key-like"),
    pytest.param("Traceback marker ZEPHYR-ORCHID-4471", id="plain-marker"),
    pytest.param("ção ✓ ギ {W/U} {2/B} {G/P} 'quote' \"dq\" <tag>", id="odd-characters"),
    pytest.param("HUGE-" + "x" * 200_000, id="huge"),
    pytest.param("line one\nline two\r\n\ttab", id="control-whitespace"),
]


class FictionalFailure(Exception):
    """An exception outside any mapped error set."""


def _jobs():
    from core import jobs

    return jobs


def _job_model():
    from core.models import Job

    return Job


def _stored(job_id):
    """The job row read straight from the database."""
    return _job_model().objects.get(pk=job_id)


def _stored_text(job_id):
    """Every column of the stored job as text."""
    row = _stored(job_id)
    return repr({field.name: getattr(row, field.name) for field in row._meta.concrete_fields})


def _succeed(value=FICTIONAL_CARD_ID):
    def fn(report):
        return value

    return fn


def _fail(text="Traceback marker ZEPHYR-ORCHID-4471", error_class=FictionalFailure):
    def fn(report):
        raise error_class(text)

    return fn


@pytest.fixture
def inline():
    with inline_runner() as runner:
        yield runner


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def stop():
    return StopRecorder()


@pytest.fixture
def installed_watchdog(clock, stop):
    """A registered, armed watchdog with one heartbeat at the current fake time."""
    import core.watchdog
    from core.watchdog import Watchdog

    watchdog = Watchdog(stop=stop, clock=clock)
    core.watchdog.install(watchdog)
    watchdog.arm()
    watchdog.heartbeat()
    try:
        yield watchdog
    finally:
        core.watchdog.uninstall()


def _assert_stops_exactly_180_seconds_from_now(watchdog, clock, stop):
    run_checks(watchdog, clock, 179, step=1)
    assert stop.calls == 0, "The watchdog stopped before 180 s had passed since the job ended."
    clock.advance(1)
    watchdog.check()
    assert stop.calls == 1, "The watchdog did not stop 180 s after the job ended."


# --- Test database (T13) ---


@pytest.mark.django_db
def test_t13_test_database_is_a_file_in_the_temporary_home():
    """T13 / RN-03: the test database is a SQLite file in the temporary home, so job threads share it."""
    from django.db import connection

    name = connection.settings_dict["NAME"]

    assert isinstance(name, (str, Path))
    assert "memory" not in str(name).lower()
    assert Path(name).resolve().is_relative_to(TEST_HOME)
    assert Path(name).is_file()


# --- Successful job ---


@pytest.mark.django_db
@pytest.mark.parametrize("kind", ALL_KINDS)
def test_t13_rn10_successful_job_is_done_with_its_result(inline, kind):
    """RN-10 / T13: a job whose function returns is done, with the returned value as result and no error."""
    jobs = _jobs()

    submitted = jobs.submit(kind, _succeed())
    job = jobs.get_job(submitted.id)

    assert isinstance(submitted.id, uuid.UUID)
    assert submitted.id.version == 4
    assert job.kind == kind
    assert job.status == "done"
    assert str(job.result) == FICTIONAL_CARD_ID
    assert job.error is None


@pytest.mark.django_db
def test_t13_rn10_successful_job_is_persisted_as_done(inline):
    """RN-10 / T13: the end state is written to the database, not only kept in memory."""
    jobs = _jobs()

    job_id = jobs.submit("generate", _succeed()).id
    row = _stored(job_id)

    assert row.status == "done"
    assert str(row.result) == FICTIONAL_CARD_ID
    assert row.error is None
    assert row.created_at is not None


@pytest.mark.django_db
def test_t13_rn03_job_with_no_result_is_done_with_result_none(inline):
    """RN-03 / T13: a build returns nothing; its job is done with result None."""
    jobs = _jobs()

    job = jobs.get_job(jobs.submit(BUILD_KIND, _succeed(None)).id)

    assert job.status == "done"
    assert job.result is None
    assert job.error is None


@pytest.mark.django_db
def test_t13_rn03_progress_reported_while_running_is_read_by_get_job(inline):
    """RN-03 / T13: progress is kept in memory by the runner and returned by get_job while the job runs."""
    jobs = _jobs()
    seen = {}

    def fn(report):
        report(0.5)
        running = _job_model().objects.get(status="running")
        job = jobs.get_job(running.pk)
        seen["status"] = job.status
        seen["progress"] = job.progress

    jobs.submit(BUILD_KIND, fn)

    assert seen == {"status": "running", "progress": 0.5}


@pytest.mark.django_db
def test_t13_rn10_job_is_persisted_as_running_before_its_function_runs(inline):
    """RN-10 / T13: the state change to running is written before the work starts (plan section 7)."""
    jobs = _jobs()
    seen = []

    def fn(report):
        seen.extend(_job_model().objects.values_list("status", flat=True))

    jobs.submit("generate", fn)

    assert seen == ["running"]


@pytest.mark.django_db
def test_t13_get_job_returns_none_for_an_unknown_id(inline):
    """RN-10 / T13: an id with no job is reported as missing, never as a made-up job."""
    assert _jobs().get_job(uuid.uuid4()) is None


@pytest.mark.django_db
def test_t13_get_job_accepts_the_id_as_text(inline):
    """RN-10 / T13: the API passes the id from the URL; get_job accepts the UUID as a string too."""
    jobs = _jobs()
    job_id = jobs.submit("generate", _succeed()).id

    assert jobs.get_job(str(job_id)).status == "done"


# --- Failing job ---


@pytest.mark.django_db
@pytest.mark.parametrize("text", FAILURE_TEXTS)
def test_t13_rn10_failing_job_stores_the_internal_envelope_and_no_exception_text(inline, text):
    """RN-10 / T13: an unmapped exception fails the job with the `internal` envelope; its text is never stored."""
    jobs = _jobs()

    job_id = jobs.submit("generate", _fail(text)).id
    job = jobs.get_job(job_id)

    assert job.status == "failed"
    error = envelope_error(job.error)
    assert error["code"] == "internal"
    assert error["setting"] is None
    assert error["fields"] is None
    for stored in (repr(job.error), _stored_text(job_id)):
        assert text not in stored
        assert text[:40] not in stored
        assert FAKE_TEXT_KEY not in stored
        assert "FictionalFailure" not in stored
        assert "Traceback" not in stored


@pytest.mark.django_db
def test_t13_rn10_failing_job_has_no_partial_result(inline):
    """RN-10 / T13: a job that reported progress and then failed leaves no result."""
    jobs = _jobs()

    def fn(report):
        report(0.9)
        raise FictionalFailure("half way through")

    job_id = jobs.submit("generate", fn).id

    assert jobs.get_job(job_id).result is None
    row = _stored(job_id)
    assert row.status == "failed"
    assert row.result is None


@pytest.mark.django_db
def test_t13_rn10_failure_is_persisted_with_the_envelope(inline):
    """RN-10 / T13: the failed state and its envelope are written to the database."""
    jobs = _jobs()

    job_id = jobs.submit(BUILD_KIND, _fail()).id
    row = _stored(job_id)

    assert row.status == "failed"
    assert envelope_error(row.error)["code"] == "internal"


@pytest.mark.django_db
def test_t13_rn10_internal_message_is_fixed(inline):
    """RN-10 / T13: two different exceptions give the same fixed message, so no detail leaks through it."""
    jobs = _jobs()

    first = jobs.get_job(jobs.submit("generate", _fail("first detail AAA-111")).id)
    second = jobs.get_job(jobs.submit("generate", _fail("second detail BBB-222", ValueError)).id)

    assert envelope_error(first.error)["message"] == envelope_error(second.error)["message"]


@pytest.mark.django_db
def test_t13_rn10_exception_with_empty_text_still_fails_with_an_envelope(inline):
    """RN-10 / T13: an exception with no text still gives the full envelope."""
    jobs = _jobs()

    job = jobs.get_job(jobs.submit("generate", _fail("")).id)

    assert job.status == "failed"
    assert envelope_error(job.error)["code"] == "internal"


@pytest.mark.django_db
def test_t13_rn10_failing_job_does_not_raise_in_the_caller(inline):
    """RN-10 / T13: a job's failure is reported through the job, not raised into `submit`."""
    jobs = _jobs()

    job = jobs.submit("generate", _fail())

    assert jobs.get_job(job.id).status == "failed"


@pytest.mark.django_db
def test_t13_rn10_exception_detail_goes_to_the_log(inline, caplog):
    """RN-10 / T13 (plan section 6): the detail of an unmapped exception goes to the redacted log."""
    marker = "LOG-ONLY-MARKER-QUARTZ-9081"

    with caplog.at_level("ERROR"):
        _jobs().submit("generate", _fail(marker))

    logged = "\n".join(
        record.getMessage() + "\n" + (record.exc_text or "") + "\n" + repr(record.exc_info) for record in caplog.records
    )
    assert marker in logged


# --- Orphans ---


@pytest.mark.django_db
@pytest.mark.parametrize("status", ["queued", "running"])
def test_t13_rn03_orphan_is_reported_and_stored_as_failed_by_get_job(inline, status):
    """RN-03 / RN-10 / T13: a job stored as queued or running that this runner does not know is failed."""
    orphan = _job_model().objects.create(kind=BUILD_KIND, status=status)

    job = _jobs().get_job(orphan.pk)

    assert job.status == "failed"
    envelope_error(job.error)
    assert job.result is None
    row = _stored(orphan.pk)
    assert row.status == "failed"
    envelope_error(row.error)


@pytest.mark.django_db
@pytest.mark.parametrize("status", ["done", "failed"])
def test_t13_rn03_ended_job_unknown_to_the_runner_is_left_as_it_is(inline, status):
    """RN-03 / T13: a job that already ended in an earlier process is not an orphan."""
    Job = _job_model()
    error = None if status == "done" else {"error": {"code": "internal", "message": "Fixed.", "setting": None, "fields": None}}
    ended = Job.objects.create(kind="generate", status=status, result=None, error=error)

    job = _jobs().get_job(ended.pk)

    assert job.status == status
    assert _stored(ended.pk).status == status


@pytest.mark.django_db
def test_t13_rn03_fail_orphan_jobs_cleans_every_queued_or_running_job():
    """RN-03 / RN-10 / T13: the startup housekeeping fails stored queued and running jobs and leaves ended ones."""
    Job = _job_model()
    queued = Job.objects.create(kind=BUILD_KIND, status="queued")
    running = Job.objects.create(kind="generate", status="running")
    done = Job.objects.create(kind="art", status="done")

    _jobs().fail_orphan_jobs()

    assert _stored(queued.pk).status == "failed"
    assert _stored(running.pk).status == "failed"
    envelope_error(_stored(queued.pk).error)
    envelope_error(_stored(running.pk).error)
    assert _stored(done.pk).status == "done"
    assert _stored(done.pk).error is None


@pytest.mark.django_db
def test_t13_rn03_fail_orphan_jobs_with_no_jobs_does_nothing():
    """RN-03 / T13: the housekeeping on an empty table succeeds and creates nothing."""
    _jobs().fail_orphan_jobs()

    assert _job_model().objects.count() == 0


# --- Watchdog held while a job runs (CA-70) ---


@pytest.mark.django_db
@pytest.mark.parametrize("kind", ALL_KINDS)
def test_t13_ca70_watchdog_held_while_a_job_runs_and_released_after_success(inline, installed_watchdog, clock, stop, kind):
    """CA-70 / RN-41 / T13: no stop while a job runs with no tab; stop 180 s after it succeeds."""

    def fn(report):
        run_checks(installed_watchdog, clock, 3600)
        return None

    _jobs().submit(kind, fn)

    assert stop.calls == 0, "The watchdog stopped while a job was running."
    _assert_stops_exactly_180_seconds_from_now(installed_watchdog, clock, stop)


@pytest.mark.django_db
@pytest.mark.parametrize("kind", ALL_KINDS)
def test_t13_ca70_watchdog_released_after_a_job_fails(inline, installed_watchdog, clock, stop, kind):
    """CA-70 / RN-41 / T13: a failing job also releases its hold: stop 180 s after it fails."""

    def fn(report):
        run_checks(installed_watchdog, clock, 3600)
        raise FictionalFailure("fictional failure")

    job = _jobs().submit(kind, fn)

    assert _jobs().get_job(job.id).status == "failed"
    assert stop.calls == 0
    _assert_stops_exactly_180_seconds_from_now(installed_watchdog, clock, stop)


@pytest.mark.django_db
def test_t13_ca70_watchdog_held_until_the_last_of_two_jobs_ends(inline, installed_watchdog, clock, stop):
    """CA-70 / RN-41 / T13: a build and a generation run together; the end of one keeps the other's hold."""
    jobs = _jobs()

    def generation(report):
        run_checks(installed_watchdog, clock, 600)

    def build(report):
        jobs.submit("generate", generation)
        run_checks(installed_watchdog, clock, 3600)

    jobs.submit(BUILD_KIND, build)

    assert stop.calls == 0
    _assert_stops_exactly_180_seconds_from_now(installed_watchdog, clock, stop)


@pytest.mark.django_db
def test_t13_rn50_ca70_refused_submission_leaves_no_hold(inline, installed_watchdog, clock, stop):
    """RN-50 / CA-70 / T13: a refused generation never holds the watchdog."""
    jobs = _jobs()

    def fn(report):
        with pytest.raises(jobs.GenerationRunning):
            jobs.submit("art", _succeed())

    jobs.submit("generate", fn)

    _assert_stops_exactly_180_seconds_from_now(installed_watchdog, clock, stop)


# --- One generation at a time (RN-50) ---


@pytest.mark.django_db
@pytest.mark.parametrize("running_kind", GENERATION_KINDS)
@pytest.mark.parametrize("new_kind", GENERATION_KINDS)
def test_t13_rn50_generation_submitted_while_one_runs_is_refused(inline, running_kind, new_kind):
    """RN-50 / T13: a card generation, art generation or quick adjustment is refused with
    `generation_running` while another one runs, and no job is stored for it."""
    jobs = _jobs()
    Job = _job_model()
    seen = {}

    def fn(report):
        before = Job.objects.count()
        with pytest.raises(jobs.GenerationRunning) as refusal:
            jobs.submit(new_kind, _succeed())
        seen["code"] = refusal.value.code
        seen["message"] = refusal.value.message
        seen["created"] = Job.objects.count() - before

    first = jobs.submit(running_kind, fn)

    assert seen["code"] == "generation_running"
    assert isinstance(seen["message"], str) and "running" in seen["message"].lower()
    assert seen["created"] == 0
    assert jobs.get_job(first.id).status == "done"


@pytest.mark.django_db
@pytest.mark.parametrize("ending", ["done", "failed"])
def test_t13_rn50_next_generation_is_accepted_after_one_ends(inline, ending):
    """RN-50 / T13: once a generation ends, whatever the outcome, the next one runs."""
    jobs = _jobs()
    first = jobs.submit("generate", _succeed() if ending == "done" else _fail())
    assert jobs.get_job(first.id).status == ending

    second = jobs.submit("art", _succeed())

    assert jobs.get_job(second.id).status == "done"


@pytest.mark.django_db
def test_t13_rn50_build_is_not_a_generation_job(inline):
    """RN-50 / T13: a running build never refuses a generation with `generation_running`."""
    jobs = _jobs()
    outcome = {}

    def build(report):
        try:
            jobs.submit("generate", _succeed())
        except jobs.GenerationRunning:
            outcome["refused"] = True
        else:
            outcome["refused"] = False

    jobs.submit(BUILD_KIND, build)

    assert outcome == {"refused": False}


@pytest.mark.django_db
def test_t13_rn50_refusal_does_not_change_the_running_job(inline):
    """RN-50 / T13: refusing a second generation leaves the first one running to its end (no cancellation)."""
    jobs = _jobs()

    def fn(report):
        with pytest.raises(jobs.GenerationRunning):
            jobs.submit("adjust", _succeed())
        return FICTIONAL_CARD_ID

    job = jobs.get_job(jobs.submit("generate", fn).id)

    assert job.status == "done"
    assert str(job.result) == FICTIONAL_CARD_ID


# --- Usage queue (plan section 7, Concurrency) ---


@pytest.mark.django_db
def test_t13_rn03_usage_write_runs_at_once_with_no_build_running(inline):
    """RN-03 / T13: outside a build, a usage write is not delayed."""
    written = []

    _jobs().enqueue_usage(lambda: written.append("connection-test"))

    assert written == ["connection-test"]


@pytest.mark.django_db
@pytest.mark.parametrize("ending", ["done", "failed"])
def test_t13_rn03_usage_writes_wait_for_the_build_and_are_flushed_in_order(inline, ending):
    """RN-03 / T13: during a build, usage writes wait in memory and run in order when the build ends,
    whatever the outcome."""
    jobs = _jobs()
    written = []
    during = {}

    def build(report):
        jobs.enqueue_usage(lambda: written.append("first"))
        jobs.enqueue_usage(lambda: written.append("second"))
        during["written"] = list(written)
        if ending == "failed":
            raise FictionalFailure("build failed")

    job = jobs.submit(BUILD_KIND, build)

    assert during["written"] == []
    assert written == ["first", "second"]
    assert jobs.get_job(job.id).status == ending


@pytest.mark.django_db
def test_t13_rn03_usage_write_during_a_generation_runs_at_once(inline):
    """RN-03 / T13: only a build delays usage writes; a generation does not."""
    jobs = _jobs()
    written = []
    during = {}

    def generation(report):
        jobs.enqueue_usage(lambda: written.append("record"))
        during["written"] = list(written)

    jobs.submit("generate", generation)

    assert during["written"] == ["record"]


# --- Failures of the runner itself (database and executor) ---

ACTIVE = ("queued", "running")

UPDATE_FAILURES = [
    pytest.param({"running"}, id="update-to-running"),
    pytest.param({"done", "failed"}, id="final-state-update"),
    pytest.param({"running", "done", "failed"}, id="both-updates"),
]


# transaction=True: in production the job thread runs in autocommit. Inside the test's own
# transaction, a failed query would poison that transaction and hide the runner's behavior.
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("statuses", UPDATE_FAILURES)
def test_t13_rn10_rn50_ca70_locked_state_update_still_ends_the_job(inline, statuses):
    """RN-10 / RN-50 / CA-70 / T13: when a state UPDATE of the job raises OperationalError
    ("database is locked"), the job still ends: get_job reports it failed with the `internal`
    envelope (in memory is acceptable), the watchdog is released exactly once, and the
    generation slot is free for the next submission. A job never stays queued or running forever."""
    jobs = _jobs()

    with job_updates_failing(statuses) as refused:
        with watchdog_calls_counted() as calls:
            job = jobs.submit("generate", _succeed())
        assert refused, "The injected failure never triggered."
        assert calls == {"hold": 1, "release": 1}

        reported = jobs.get_job(job.id)
        assert reported.status == "failed"
        error = envelope_error(reported.error)
        assert error["code"] == "internal"
        assert "database is locked" not in repr(reported.error)

        try:
            second = jobs.submit("generate", _succeed())
        except jobs.GenerationRunning:
            pytest.fail("The generation slot stayed taken after a state update failed (RN-50).")

    assert jobs.get_job(second.id).status in ("done", "failed")
    assert jobs.get_job(job.id).status == "failed"


MAPPED_MESSAGE = "The disk that holds the data folder is full. Free some space and try again. ✦ fictional"


@pytest.mark.django_db
def test_t21_rn10_mapped_error_is_stored_with_its_code_and_message(inline):
    """RN-10 / RN-28 (plan section 6, Jobs): a job raising core.errors.MappedError stores its code and
    fixed message in the envelope instead of `internal`."""
    from core.errors import MappedError

    jobs = _jobs()

    def fn(report):
        raise MappedError("insufficient_space", MAPPED_MESSAGE)

    job = jobs.submit(BUILD_KIND, fn)

    error = envelope_error(jobs.get_job(job.id).error)
    assert error["code"] == "insufficient_space"
    assert error["message"] == MAPPED_MESSAGE
    assert envelope_error(_stored(job.id).error)["code"] == "insufficient_space"


@pytest.mark.django_db(transaction=True)
def test_t21_rn28_rn10_mapped_error_is_kept_in_memory_when_the_failed_state_cannot_be_stored(inline):
    """RN-28 / RN-10 (plan section 7, "database is locked"): when the FAILED update of a job that raised
    a MappedError fails, get_job still reports the job failed with that code and message, not `internal`."""
    from core.errors import MappedError

    jobs = _jobs()

    def fn(report):
        raise MappedError("insufficient_space", MAPPED_MESSAGE)

    with job_updates_failing({"failed"}) as refused:
        with watchdog_calls_counted() as calls:
            job = jobs.submit(BUILD_KIND, fn)
        assert refused, "The injected failure never triggered."
        assert calls == {"hold": 1, "release": 1}

        reported = jobs.get_job(job.id)
        assert reported.status == "failed"
        error = envelope_error(reported.error)
        assert error["code"] == "insufficient_space"
        assert error["message"] == MAPPED_MESSAGE

    error = envelope_error(jobs.get_job(job.id).error)
    assert error["code"] == "insufficient_space"
    assert error["message"] == MAPPED_MESSAGE


class ExecutorBroken(RuntimeError):
    """The executor refuses new work (for example after a shutdown)."""


class FailingOnceExecutor(InlineExecutor):
    """Raises on the first submit, then runs inline."""

    def __init__(self):
        self.calls = 0

    def submit(self, fn, /, *args, **kwargs):
        self.calls += 1
        if self.calls == 1:
            raise ExecutorBroken("cannot schedule new futures after shutdown")
        return super().submit(fn, *args, **kwargs)


@pytest.mark.django_db
@pytest.mark.parametrize("kind", ALL_KINDS)
def test_t13_rn10_ca70_executor_refusing_the_job_leaves_nothing_active(kind):
    """RN-10 / CA-70 / T13: when the executor's submit raises, the exception reaches the caller of
    `submit`, no job stays queued or running (it is deleted, or failed with `internal`), the
    watchdog hold is released, the generation slot is free and no build is counted as running."""
    jobs = _jobs()
    Job = _job_model()

    with runner_installed(FailingOnceExecutor()):
        with watchdog_calls_counted() as calls:
            with pytest.raises(ExecutorBroken):
                jobs.submit(kind, _succeed())
        # Every hold taken for the refused job is released (none at all is also balanced).
        assert calls["hold"] == calls["release"] <= 1

        assert not Job.objects.filter(status__in=ACTIVE).exists()
        for row in Job.objects.all():
            assert row.status == "failed"
            assert envelope_error(row.error)["code"] == "internal"
            assert jobs.get_job(row.pk).status == "failed"

        written = []
        jobs.enqueue_usage(lambda: written.append("record"))
        assert written == ["record"], "A refused build still delays usage writes."

        try:
            following = jobs.submit("generate", _succeed())
        except jobs.GenerationRunning:
            pytest.fail("The generation slot stayed taken after the executor refused the job (RN-50).")
        assert jobs.get_job(following.id).status == "done"


@pytest.mark.django_db
def test_t13_rn10_ca70_executor_refusal_releases_the_watchdog(installed_watchdog, clock, stop):
    """RN-10 / CA-70 / T13: after the executor refuses a job, the watchdog stops 180 s later as usual."""
    with runner_installed(FailingOnceExecutor()):
        with pytest.raises(ExecutorBroken):
            _jobs().submit("generate", _succeed())

    _assert_stops_exactly_180_seconds_from_now(installed_watchdog, clock, stop)


@pytest.mark.django_db
@pytest.mark.parametrize("ending", ["done", "failed"])
def test_t13_rn03_failing_usage_write_does_not_stop_the_others(inline, ending):
    """RN-03 / T13: a queued usage write that raises does not stop the following queued writes,
    nor the watchdog release at the end of the build."""
    jobs = _jobs()
    written = []

    def broken():
        raise FictionalFailure("usage table locked")

    def build(report):
        jobs.enqueue_usage(lambda: written.append("first"))
        jobs.enqueue_usage(broken)
        jobs.enqueue_usage(lambda: written.append("third"))
        if ending == "failed":
            raise FictionalFailure("build failed")

    with watchdog_calls_counted() as calls:
        job = jobs.submit(BUILD_KIND, build)

    assert written == ["first", "third"]
    assert calls == {"hold": 1, "release": 1}
    assert jobs.get_job(job.id).status == ending


# --- Real thread pool (transaction=True) ---


@pytest.fixture
def pool_executor():
    executor = ThreadPoolExecutor(max_workers=4)
    yield executor
    executor.shutdown(wait=True)


@pytest.fixture
def pool(pool_executor):
    with runner_installed(pool_executor) as runner:
        yield runner


def _blocking(started, release, result=FICTIONAL_CARD_ID):
    def fn(report):
        started.set()
        assert release.wait(WAIT_SECONDS), "The test never released the job."
        return result

    return fn


@pytest.mark.django_db(transaction=True)
def test_t13_rn10_pool_job_runs_to_done(pool):
    """RN-10 / T13: on the real thread pool, a job ends as done with its result."""
    jobs = _jobs()

    job = wait_for_end(jobs.submit("generate", _succeed()).id)

    assert job.status == "done"
    assert str(job.result) == FICTIONAL_CARD_ID


@pytest.mark.django_db(transaction=True)
def test_t13_rn10_pool_job_failure_stores_the_envelope(pool):
    """RN-10 / T13: on the real thread pool, an exception fails the job with the envelope and no exception text."""
    jobs = _jobs()
    text = "pool failure PELICAN-3307"

    job_id = jobs.submit("generate", _fail(text)).id
    job = wait_for_end(job_id)

    assert job.status == "failed"
    assert envelope_error(job.error)["code"] == "internal"
    assert text not in _stored_text(job_id)


@pytest.mark.django_db(transaction=True)
def test_t13_rn03_running_job_known_to_the_runner_is_not_an_orphan(pool):
    """RN-03 / T13: get_job reports a job this runner is running as running, never as failed."""
    jobs = _jobs()
    started, release = threading.Event(), threading.Event()
    try:
        job_id = jobs.submit(BUILD_KIND, _blocking(started, release)).id
        assert started.wait(WAIT_SECONDS)

        assert jobs.get_job(job_id).status == "running"
        assert _stored(job_id).status == "running"
    finally:
        release.set()

    assert wait_for_end(job_id).status == "done"


@pytest.mark.django_db(transaction=True)
def test_t13_rn03_progress_from_a_pool_thread_is_read_by_get_job(pool):
    """RN-03 / T13: progress reported in a job thread is read by get_job from another thread."""
    jobs = _jobs()
    reported, release = threading.Event(), threading.Event()

    def fn(report):
        report(0.25)
        reported.set()
        assert release.wait(WAIT_SECONDS)

    try:
        job_id = jobs.submit(BUILD_KIND, fn).id
        assert reported.wait(WAIT_SECONDS)
        assert jobs.get_job(job_id).progress == 0.25
    finally:
        release.set()
    wait_for_end(job_id)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("new_kind", GENERATION_KINDS)
def test_t13_rn50_pool_refuses_a_second_generation_while_one_runs(pool, new_kind):
    """RN-50 / T13: on the real thread pool, a generation submitted while one runs is refused with
    `generation_running`; after it ends, the next one is accepted."""
    jobs = _jobs()
    started, release = threading.Event(), threading.Event()
    try:
        first_id = jobs.submit("generate", _blocking(started, release)).id
        assert started.wait(WAIT_SECONDS)

        with pytest.raises(jobs.GenerationRunning) as refusal:
            jobs.submit(new_kind, _succeed())
        assert refusal.value.code == "generation_running"
        assert _job_model().objects.count() == 1
    finally:
        release.set()

    assert wait_for_end(first_id).status == "done"
    assert wait_for_end(jobs.submit(new_kind, _succeed()).id).status == "done"


@pytest.mark.django_db(transaction=True)
def test_t13_rn50_pool_refuses_a_generation_while_one_is_queued_or_running(pool):
    """RN-50 / T13: two generations submitted back to back: the second is refused, never queued behind."""
    jobs = _jobs()
    started, release = threading.Event(), threading.Event()
    try:
        first_id = jobs.submit("generate", _blocking(started, release)).id
        with pytest.raises(jobs.GenerationRunning):
            jobs.submit("generate", _succeed())
    finally:
        release.set()
    assert wait_for_end(first_id).status == "done"


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("ending", ["done", "failed"])
def test_t13_ca70_pool_job_holds_the_watchdog_until_it_ends(
    pool, pool_executor, installed_watchdog, clock, stop, ending
):
    """CA-70 / RN-41 / T13: on the real thread pool, the watchdog never stops while a job runs with no tab,
    and stops 180 s after it ends, whether it succeeded or failed."""
    jobs = _jobs()
    started, release = threading.Event(), threading.Event()

    def fn(report):
        started.set()
        assert release.wait(WAIT_SECONDS)
        if ending == "failed":
            raise FictionalFailure("fictional failure")

    try:
        job_id = jobs.submit("generate", fn).id
        assert started.wait(WAIT_SECONDS)
        run_checks(installed_watchdog, clock, 3600)
        assert stop.calls == 0
    finally:
        release.set()

    assert wait_for_end(job_id).status == ending
    # The worker may release its hold just after the end state is stored; let it finish first.
    pool_executor.shutdown(wait=True)
    assert stop.calls == 0
    _assert_stops_exactly_180_seconds_from_now(installed_watchdog, clock, stop)

