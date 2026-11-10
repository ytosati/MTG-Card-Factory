"""In-process job runner: submit, progress, orphan detection and the usage queue.
Details: specs/plan.md, sections 6 (Jobs) and 7 (Concurrency).
"""

import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

from django.db import OperationalError, connection, connections

from core import watchdog
from core.errors import CODE_INTERNAL, INTERNAL_MESSAGE, MappedError, error_body
from core.models import Job

logger = logging.getLogger(__name__)

MAX_WORKERS = 4
# Card generation, art generation and quick adjustment share one slot (see spec RN-50).
GENERATION_KINDS = frozenset({Job.Kind.GENERATE, Job.Kind.ADJUST, Job.Kind.ART})
ACTIVE_STATUSES = (Job.Status.QUEUED, Job.Status.RUNNING)

CODE_GENERATION_RUNNING = "generation_running"
ORPHAN_MESSAGE = "This task stopped when Card Factory closed. Start it again."
GENERATION_RUNNING_MESSAGE = "A card or art generation is already running. Wait for it to finish, then try again."


class GenerationRunning(Exception):
    """A generation job was submitted while another one is queued or running (see spec RN-50)."""

    code = CODE_GENERATION_RUNNING
    message = GENERATION_RUNNING_MESSAGE

    def __init__(self):
        super().__init__(self.message)


class JobRunner:
    """Runs jobs on an executor and keeps their progress in memory.

    `executor` is a concurrent.futures.Executor; None means a thread pool.
    """

    def __init__(self, executor=None):
        self._executor = executor if executor is not None else ThreadPoolExecutor(max_workers=MAX_WORKERS)
        self._lock = threading.Lock()
        self._known = set()
        self._progress = {}
        # Ended jobs whose failed state could not be stored, with their error envelope; get_job reports them failed.
        self._failed = {}
        self._generation = None
        self._builds = 0
        self._usage_queue = []

    def submit(self, kind, fn):
        """Store a queued job and run `fn(report)` on the executor; raises GenerationRunning (RN-50).

        Call it outside `transaction.atomic()`: the job is dispatched at once, and its thread
        cannot see a row the caller has not committed yet.
        """
        job_id = uuid.uuid4()
        with self._lock:
            if kind in GENERATION_KINDS:
                if self._generation is not None:
                    raise GenerationRunning()
                self._generation = job_id
            elif kind == Job.Kind.BUILD:
                self._builds += 1
            # Known before the row exists, so a concurrent get_job never takes it for an orphan.
            self._known.add(job_id)
            self._progress[job_id] = 0.0
        watchdog.hold()
        try:
            job = Job.objects.create(id=job_id, kind=kind, status=Job.Status.QUEUED)
        except BaseException:
            try:
                self._finish(job_id, kind, stored=True)
            finally:
                watchdog.release()
            raise
        try:
            self._executor.submit(self._run, job_id, kind, fn)
        except BaseException:
            logger.exception("Job %s (%s) could not be started.", job_id, kind)
            try:
                self._end(job_id, kind, _failed_fields())
            finally:
                watchdog.release()
            raise
        return job

    def get_job(self, job_id):
        """The job with `job_id` (UUID or text), or None; an orphan is stored and returned as failed."""
        try:
            job_id = job_id if isinstance(job_id, uuid.UUID) else uuid.UUID(str(job_id))
        except ValueError:
            return None
        job = Job.objects.filter(pk=job_id).first()
        if job is None or job.status not in ACTIVE_STATUSES:
            return job
        with self._lock:
            known = job_id in self._known
            failed = self._failed.get(job_id)
            progress = self._progress.get(job_id)
        if failed is not None:
            return _failed_in_memory(job, failed)
        if not known:
            try:
                _fail_orphans(Job.objects.filter(pk=job_id))
                job.refresh_from_db()
            except OperationalError:
                logger.exception("Orphan job %s could not be stored as failed.", job_id)
                return _failed_in_memory(job, error_body(CODE_INTERNAL, ORPHAN_MESSAGE))
        elif progress is not None:
            job.progress = progress
        return job

    def enqueue_usage(self, write):
        """Run a usage write now, or after the running build ends (plan section 7)."""
        with self._lock:
            if self._builds:
                self._usage_queue.append(write)
                return
        write()

    def _run(self, job_id, kind, fn):
        fields = _failed_fields()
        try:
            Job.objects.filter(pk=job_id).update(status=Job.Status.RUNNING)
            result = fn(lambda progress: self._report(job_id, progress))
        except MappedError as error:
            logger.exception("Job %s (%s) failed.", job_id, kind)
            fields = _failed_fields(error_body(error.code, error.message, error.setting))
        except Exception:
            # The detail goes only to the redacted log; the job stores a fixed message (plan section 6).
            logger.exception("Job %s (%s) failed.", job_id, kind)
        except BaseException:
            logger.exception("Job %s (%s) stopped unexpectedly.", job_id, kind)
            raise
        else:
            fields = {"status": Job.Status.DONE, "result": result, "progress": 1.0}
        finally:
            try:
                self._end(job_id, kind, fields)
            finally:
                watchdog.release()
                _close_thread_connections()

    def _report(self, job_id, progress):
        with self._lock:
            if job_id in self._progress:
                self._progress[job_id] = float(progress)

    def _end(self, job_id, kind, fields):
        """Free the generation slot, store the end state, then forget the job and release its build."""
        # The slot is freed before the end state is stored, so a reader who sees it ended can submit again.
        with self._lock:
            if self._generation == job_id:
                self._generation = None
        stored = self._store_end(job_id, kind, fields)
        # A failure that cannot be stored keeps its own envelope in memory; any other end becomes internal.
        failed = fields["error"] if fields["status"] == Job.Status.FAILED else _failed_fields()["error"]
        self._finish(job_id, kind, stored, failed)

    def _store_end(self, job_id, kind, fields):
        """Store the end state, or the internal failure when that fails; False when neither is stored."""
        try:
            Job.objects.filter(pk=job_id).update(**fields)
            return True
        except Exception:
            logger.exception("Job %s (%s) could not store its end state.", job_id, kind)
        if fields["status"] == Job.Status.FAILED:
            return False
        try:
            Job.objects.filter(pk=job_id).update(**_failed_fields())
            return True
        except Exception:
            logger.exception("Job %s (%s) could not store its failure.", job_id, kind)
            return False

    def _finish(self, job_id, kind, stored, failed=None):
        with self._lock:
            if self._generation == job_id:
                self._generation = None
            self._progress.pop(job_id, None)
            if not stored:
                self._failed[job_id] = failed if failed is not None else _failed_fields()["error"]
            # Forgotten only after the end state is stored or kept in memory; earlier, get_job would see an orphan.
            self._known.discard(job_id)
        if kind == Job.Kind.BUILD:
            self._release_build()

    def _release_build(self):
        """Count one build less; the last one flushes the usage queue before it stops counting."""
        while True:
            with self._lock:
                if self._builds > 1 or not self._usage_queue:
                    self._builds -= 1
                    return
                pending, self._usage_queue = self._usage_queue, []
            # Writes enqueued during the flush still queue behind these, so the order is kept.
            self._flush(pending)

    def _flush(self, writes):
        for write in writes:
            try:
                write()
            except Exception:
                logger.exception("A queued usage record could not be written.")


def _failed_fields(error=None):
    """End state of a failed job; `error` is its envelope, the internal failure by default."""
    if error is None:
        error = error_body(CODE_INTERNAL, INTERNAL_MESSAGE)
    return {"status": Job.Status.FAILED, "result": None, "error": error}


def _failed_in_memory(job, error):
    """`job` reported as failed with the envelope `error`, without storing it."""
    job.status = Job.Status.FAILED
    job.result = None
    job.error = error
    return job


def _close_thread_connections():
    # A pool thread opened its own connections; one inside a test transaction is not its own.
    if not connection.in_atomic_block:
        connections.close_all()


def _fail_orphans(queryset):
    """Store every queued or running job of `queryset` as failed."""
    active = queryset.filter(status__in=ACTIVE_STATUSES)
    # Checked first so a startup with no orphans writes nothing to the database.
    if active.exists():
        active.update(status=Job.Status.FAILED, error=error_body(CODE_INTERNAL, ORPHAN_MESSAGE))


_runner = None
_runner_lock = threading.Lock()


def get_runner():
    """The runner of this process, created on first use with a thread pool."""
    global _runner
    with _runner_lock:
        if _runner is None:
            _runner = JobRunner()
        return _runner


def set_runner(runner):
    """Replace the runner of this process (tests install one with an inline executor)."""
    global _runner
    with _runner_lock:
        _runner = runner


def submit(kind, fn):
    """Submit a job to the runner of this process."""
    return get_runner().submit(kind, fn)


def get_job(job_id):
    """A job from the runner of this process, or None."""
    return get_runner().get_job(job_id)


def enqueue_usage(write):
    """Run a usage write now, or after the running build ends."""
    get_runner().enqueue_usage(write)


def fail_orphan_jobs():
    """Startup housekeeping: every job stored as queued or running becomes failed (see spec RN-03)."""
    _fail_orphans(Job.objects.all())
