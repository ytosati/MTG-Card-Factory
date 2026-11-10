"""Milestone 2 end-to-end flow: the reference database is built from the Setup screen (task T116).

Spec: RN-01, RN-03, RN-28, CA-07, CA-08, CA-18. Details: specs/plan.md,
sections 6 (setup, jobs, readiness gate), 7 (concurrency, catalog version,
all-or-nothing build) and 14 (end-to-end suite).

The demo path runs through the API in the order of the demo: Status and Setup
before the build, the build started and followed to its end, an interrupted
build rerun without duplicates, a rerun on a ready database, and the Status
screen listing every source of the registry. Builds run on the real thread
pool, so the database is a file shared by the request thread and the job
thread (`transaction=True`).

Until a later milestone adds an endpoint that needs the reference database,
the readiness gate is seen through the probe view of
`tests.readiness_gate_urls`, which keeps the default permissions.
"""

import sqlite3
import time

import pytest
from django.utils import timezone

from tests.catalog_build_helpers import CARD_IDS, fts_rows
from tests.e2e.helpers import (
    NOT_READY_STATUS,
    READ_WHILE_IMPORTING_SECONDS,
    ImportPause,
    QueuedUsageWrite,
    fail_after_last_import,
    listed_size,
    listed_url,
    listing_entries,
    parse_time,
)
from tests.readiness_gate_urls import PROBE_ROUTE
from tests.setup_api_helpers import EXPECTED_SPACE_FACTOR, PLENTY_OF_SPACE, download_files, is_not_ready_answer

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.urls("tests.readiness_gate_urls")]

PROBE_URL = "/" + PROBE_ROUTE
INTERNAL = "internal"
USAGE_WAIT_SECONDS = 30.0


# ---------------------------------------------------------------- what the demo looks at


def _registry():
    from catalog import sources

    return sources.SOURCES


def _expected_download_size(app):
    """The sum over the source registry of the sizes the data source lists (see spec RN-28)."""
    entries = listing_entries(app.source)
    return sum(listed_size(entries[source.listing_type]) for source in _registry())


def _assert_gate_closed(app):
    response = app.api.get(PROBE_URL)
    assert response.status_code == NOT_READY_STATUS, response.content[:500]
    assert is_not_ready_answer(response), response.content[:500]


def _assert_gate_open(app):
    response = app.api.get(PROBE_URL)
    assert response.status_code == 200, response.content[:500]


def _assert_catalog_built_once():
    """Every fictional card exactly once, one source record per source and one completed build (RN-03)."""
    from catalog.models import BuildRun, OracleCard, SourceRecord

    stored = list(OracleCard.objects.values_list("oracle_id", flat=True))
    assert len(stored) == len(set(stored))
    assert {str(card) for card in stored} == CARD_IDS
    full_text = [str(oracle_id) for oracle_id, _ in fts_rows()]
    assert sorted(full_text) == sorted(CARD_IDS)
    records = list(SourceRecord.objects.values_list("source", flat=True))
    assert sorted(records) == sorted(source.name for source in _registry())
    assert BuildRun.objects.count() == 1


def _assert_catalog_empty():
    from catalog.models import BuildRun, OracleCard, SourceRecord

    assert OracleCard.objects.count() == 0
    assert fts_rows() == []
    assert SourceRecord.objects.count() == 0
    assert BuildRun.objects.count() == 0


def _assert_sources_listed(app, status, downloaded_after, downloaded_before):
    """Every source of the registry, once, with its origin, publication date and download date (RN-01, CA-08)."""
    entries = listing_entries(app.source)
    listed = {item["source"]: item for item in status["sources"]}
    assert len(listed) == len(status["sources"]), status["sources"]
    assert set(listed) == {source.name for source in _registry()}, status["sources"]
    for source in _registry():
        item = listed[source.name]
        entry = entries[source.listing_type]
        assert item["url"] == listed_url(entry)
        assert parse_time(item["published_at"]) == parse_time(entry["updated_at"])
        downloaded_at = parse_time(item["downloaded_at"])
        assert downloaded_after <= downloaded_at <= downloaded_before, (downloaded_at, downloaded_after)


def _assert_progress_shown(seen):
    """The job reports progress between 0 and 1 that never goes back, and ends at 1 (RN-28, CA-18)."""
    values = [body["progress"] for body in seen]
    assert all(0.0 <= value <= 1.0 for value in values), values
    assert values == sorted(values), values
    assert values[-1] == 1.0


def _assert_first_start(app):
    """CA-18: before any build, Status opens, Setup states the size and space, and nothing is downloaded."""
    status = app.status()
    assert status["database_ready"] is False
    assert status["sources"] == []

    setup = app.setup()
    size = _expected_download_size(app)
    assert setup["database_ready"] is False
    assert setup["job"] is None
    assert setup["listing_error"] is None
    assert setup["download_size"] == size > 0
    assert setup["space_needed"] == size * EXPECTED_SPACE_FACTOR
    assert setup["free_space"] == PLENTY_OF_SPACE

    _assert_gate_closed(app)
    assert app.bulk_requests() == 0, "A data file was downloaded before the person started the build."
    assert download_files(app.api.home) == []


# ---------------------------------------------------------------- the demo path


def test_m2_rn28_ca18_first_start_builds_the_database_and_opens_the_normal_screens(app):
    """RN-28, CA-18, RN-01: Status and Setup answer before the build with the download size and the
    space needed and nothing downloaded; the started build shows progress until done; then the gate
    opens and Status lists every source of the registry with its dates."""
    _assert_first_start(app)

    before = timezone.now()
    job = app.start_build()
    assert job["status"] in ("queued", "running", "done")
    ended, seen = app.follow_job(job["id"])
    after = timezone.now()

    assert ended["status"] == "done", ended
    assert ended["error"] is None
    _assert_progress_shown(seen)
    assert app.bulk_requests() == 1

    _assert_gate_open(app)
    status = app.status()
    assert status["database_ready"] is True
    _assert_sources_listed(app, status, before, after)
    setup = app.setup()
    assert setup["database_ready"] is True
    assert setup["job"] is None
    _assert_catalog_built_once()
    # The source files of a finished build are deleted (plan section 7, data layout).
    assert download_files(app.api.home) == []


def test_m2_rn03_ca07_ca08_interrupted_build_reruns_without_duplicates_and_a_ready_rerun_downloads_nothing(
    app, monkeypatch
):
    """The demo in order: first start (CA-18); a build interrupted inside the import leaves the database
    not ready with nothing stored and the cause on Setup (RN-03, CA-07); the next build is ready with no
    duplicated record (CA-07); a rerun on the ready database downloads nothing and Status keeps showing
    each source's origin, publication date and download date (RN-01, CA-08)."""
    _assert_first_start(app)

    # The injected failure runs once: the next build imports normally.
    failures = fail_after_last_import(monkeypatch)
    flow_started = timezone.now()
    interrupted = app.start_build()
    ended, _ = app.follow_job(interrupted["id"])
    assert failures, "The injected failure never ran inside the import."
    assert ended["status"] == "failed", ended
    assert ended["result"] is None
    error = ended["error"]["error"]
    assert error["code"] == INTERNAL
    assert "injected" not in error["message"].lower(), "A job stored the text of an exception (plan section 6)."

    _assert_catalog_empty()
    _assert_gate_closed(app)
    status = app.status()
    assert status["database_ready"] is False
    assert status["sources"] == []
    setup = app.setup()
    assert setup["database_ready"] is False
    assert setup["job"]["id"] == interrupted["id"]
    assert setup["job"]["status"] == "failed"
    assert setup["job"]["error"] == ended["error"]

    rebuilt = app.start_build()
    assert rebuilt["id"] != interrupted["id"]
    ended, seen = app.follow_job(rebuilt["id"])
    after = timezone.now()
    assert ended["status"] == "done", ended
    _assert_progress_shown(seen)
    _assert_catalog_built_once()
    _assert_gate_open(app)
    first_status = app.status()
    assert first_status["database_ready"] is True
    # A download kept from the interrupted build may be reused, so its date may precede the rerun.
    _assert_sources_listed(app, first_status, flow_started, after)

    requests_before = app.requests()
    rerun = app.start_build()
    ended, _ = app.follow_job(rerun["id"])
    assert ended["status"] == "done", ended
    assert app.requests() == requests_before, "A rerun on a ready database contacted the data source."
    assert app.setup()["database_ready"] is True
    assert app.requests() == requests_before, "Setup on a ready database contacted the data source."
    _assert_catalog_built_once()
    assert app.status()["sources"] == first_status["sources"]
    _assert_gate_open(app)


# ---------------------------------------------------------------- concurrency during the import


def test_m2_rn03_rn28_reads_answer_and_a_usage_record_waits_while_the_import_holds_the_write_lock(app, monkeypatch):
    """Plan section 7 (WAL, IMMEDIATE, usage queue), RN-03, RN-28: while the build is paused inside its
    import transaction on the real pool, GET /api/setup, GET /api/status and GET /api/jobs/{id} answer at
    once and see the database as not ready; the import holds the write lock; a usage record handed to the
    queue is not written until the build ends, then it is written once, after the build is stored done."""
    from django.db import connection

    from core.jobs import enqueue_usage
    from core.models import Job

    pause = ImportPause().install(monkeypatch)
    app.setup()
    job = app.start_build()
    write = None
    try:
        pause.wait_inside()

        started = time.monotonic()
        setup = app.setup()
        status = app.status()
        running = app.job(job["id"])
        _assert_gate_closed(app)
        elapsed = time.monotonic() - started
        assert elapsed < READ_WHILE_IMPORTING_SECONDS, f"Reads waited {elapsed:.1f} s for the import."

        assert setup["database_ready"] is False
        assert setup["job"]["id"] == job["id"]
        assert setup["job"]["status"] == "running"
        assert status["database_ready"] is False
        assert status["sources"] == []
        assert running["status"] == "running"
        assert 0.0 < running["progress"] < 1.0

        write = QueuedUsageWrite(job["id"])
        enqueue_usage(write)
        assert write.calls == [], "A usage record was written while the build ran."

        _assert_write_lock_held_by_the_import(connection.settings_dict["NAME"])
    finally:
        pause.release.set()

    ended, _ = app.follow_job(job["id"])
    assert not pause.timed_out
    assert ended["status"] == "done", ended
    assert write.done.wait(USAGE_WAIT_SECONDS), "The queued usage record was never written."
    assert len(write.calls) == 1
    assert write.calls[0]["build_status"] == Job.Status.DONE
    assert Job.objects.filter(pk=write.row_id).exists()
    _assert_catalog_built_once()
    _assert_gate_open(app)
    assert app.setup()["job"] is None


def _assert_write_lock_held_by_the_import(database_path):
    """The database is in WAL mode, a reader sees none of the uncommitted rows, and no other
    connection can take the write lock while the import transaction is open (plan section 7)."""
    other = sqlite3.connect(database_path, timeout=0, isolation_level=None)
    try:
        assert other.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        assert other.execute("SELECT COUNT(*) FROM catalog_oraclecard").fetchone()[0] == 0
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            other.execute("BEGIN IMMEDIATE")
    finally:
        other.close()
