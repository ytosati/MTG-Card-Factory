"""Helpers of the end-to-end suite: the application seen through its API, and seams inside the build.

Details: specs/plan.md, sections 6 (endpoints, jobs, readiness gate), 7 (concurrency,
all-or-nothing build) and 14 (end-to-end suite). Every value is fictional.
"""

import json
import threading
import time
from datetime import datetime

from tests.catalog_build_helpers import InjectedFailure
from tests.setup_api_helpers import BUILD_URL, JOBS_URL, SETUP_URL, STATUS_URL, own_origin

ACCEPTED = 202
NOT_READY_STATUS = 503
END_STATUSES = ("done", "failed")
ACTIVE_STATUSES = ("queued", "running")

# Limits for work done on the real thread pool; generous so a slow machine does not fail the suite.
JOB_SECONDS = 30.0
PAUSE_SECONDS = 30.0
POLL_SECONDS = 0.01
# Well below the SQLite busy timeout: a read that waited for the import's write lock would exceed it.
READ_WHILE_IMPORTING_SECONDS = 5.0


class E2EApp:
    """The running application as the browser sees it: the API test client on a temporary home,
    a fictional data source behind the fake transport and the real job runner."""

    def __init__(self, api, environment, runner, port):
        self.api = api
        self.environment = environment
        self.runner = runner
        self.origin = own_origin(port)

    @property
    def source(self):
        return self.environment.source

    def json(self, path, status=200):
        response = self.api.get(path)
        assert response.status_code == status, (path, response.status_code, response.content[:500])
        assert response["Content-Type"].startswith("application/json")
        return response.json()

    def status(self):
        return self.json(STATUS_URL)

    def setup(self):
        return self.json(SETUP_URL)

    def job(self, job_id):
        return self.json(f"{JOBS_URL}/{job_id}")

    def start_build(self):
        response = self.api.request("POST", BUILD_URL, data={}, **self.origin)
        assert response.status_code == ACCEPTED, response.content[:500]
        body = response.json()
        assert body["kind"] == "build", body
        return body

    def follow_job(self, job_id, timeout=JOB_SECONDS):
        """Poll GET /api/jobs/{id} until the job ends; returns (last body, every body seen)."""
        seen = []
        deadline = time.monotonic() + timeout
        while True:
            body = self.job(job_id)
            seen.append(body)
            if body["status"] in END_STATUSES:
                return body, seen
            assert body["status"] in ACTIVE_STATUSES, body
            if time.monotonic() > deadline:
                raise AssertionError(f"The job did not end within {timeout} s (last: {body}).")
            time.sleep(POLL_SECONDS)

    def bulk_requests(self):
        return self.environment.bulk_requests()

    def requests(self):
        return len(self.source.requests)


def listing_entries(source):
    """{listing type: entry} of the listing served by a FakeDataSource."""
    return {entry["type"]: entry for entry in json.loads(source.listing().decode("utf-8"))["data"]}


def parse_time(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def build_importers():
    """The per-source importers the build runs inside its import transaction (catalog.build)."""
    from catalog import build, sources

    importers = getattr(build, "_IMPORTERS", None)
    assert isinstance(importers, dict), "catalog.build keeps no importer per source (plan section 7)."
    missing = [source.name for source in sources.SOURCES if source.name not in importers]
    assert not missing, f"Sources of the registry with no importer: {missing}"
    return importers


def fail_after_last_import(monkeypatch):
    """Make the import of the last source of the registry write its rows, then raise InjectedFailure.

    The failure comes from inside the import transaction, on the job's own thread,
    like a process ended in the middle of the import. Returns a list that records each failure.
    """
    from catalog import sources

    importers = build_importers()
    name = sources.SOURCES[-1].name
    original = importers[name]
    failures = []

    def failing(*args, **kwargs):
        original(*args, **kwargs)
        if not failures:
            failures.append(name)
            raise InjectedFailure("injected failure inside the import transaction")

    monkeypatch.setitem(importers, name, failing)
    return failures


class ImportPause:
    """Pauses the build inside its import transaction, after the first source's rows are written."""

    def __init__(self):
        self.inside = threading.Event()
        self.release = threading.Event()
        self.timed_out = False

    def install(self, monkeypatch):
        from catalog import sources

        importers = build_importers()
        name = sources.SOURCES[0].name
        original = importers[name]

        def paused(*args, **kwargs):
            original(*args, **kwargs)
            self.inside.set()
            if not self.release.wait(PAUSE_SECONDS):
                self.timed_out = True
                raise InjectedFailure("the test never released the paused import")

        monkeypatch.setitem(importers, name, paused)
        return self

    def wait_inside(self):
        assert self.inside.wait(PAUSE_SECONDS), "The build never reached its import transaction."


class QueuedUsageWrite:
    """A stand-in for the usage record of a connection test (spec RN-09; the usage model comes in
    Milestone 3): a write outside the catalog tables, handed to `core.jobs.enqueue_usage`."""

    def __init__(self, build_job_id):
        self.build_job_id = build_job_id
        self.done = threading.Event()
        self.calls = []
        self.row_id = None

    def __call__(self):
        from core.models import Job

        build_status = Job.objects.get(pk=self.build_job_id).status
        # A finished row of a non-build kind: the Setup screen and the build ignore it.
        row = Job.objects.create(kind=Job.Kind.GENERATE, status=Job.Status.DONE, progress=1.0)
        self.row_id = row.pk
        self.calls.append({"thread": threading.get_ident(), "build_status": build_status})
        self.done.set()
