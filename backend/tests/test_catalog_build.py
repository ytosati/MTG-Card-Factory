"""All-or-nothing catalog build and the `build_catalog` command (task T21).

Spec: RN-01, RN-03, RN-28, RN-41, CA-07, CA-08. Details: specs/plan.md, sections
5 (catalog services), 6 (error codes, jobs), 7 (data layout, concurrency, catalog
version, all-or-nothing build) and 10 (data sources).

API under test:

    catalog.build.run_build(*, transport=None, sleep=None, report=None)
        Runs the build over the source registry (`catalog.sources.SOURCES`).
        When the database is ready for the current `CATALOG_VERSION` it returns
        at once and contacts no data source. Otherwise:
        phase 1, outside any transaction: reads the download listing, downloads
        each source to `data/downloads/` and extracts the needed fields to a
        compact JSON-lines file;
        phase 2, in one short transaction that writes only catalog tables:
        deletes the previous catalog rows, imports the cards (roles tagged),
        rebuilds the card full-text table `oracle_fts`, writes one
        `SourceRecord` per source (origin URL, publication date from the
        listing, download date, sha256, size) and the ready `BuildRun` with
        `CATALOG_VERSION`. The source files are deleted after the import.
        `transport` and `sleep` are the seams of `catalog.download`; None uses
        the defaults of that module (so `catalog.download.urllib_transport` is
        resolved when the build runs). `report(progress)` receives floats from
        0 to 1. A failure raises; a download failure keeps its error code.
        `CATALOG_VERSION` is read from `catalog.sources` when the build runs.

    catalog.build.start_build(*, transport=None, sleep=None) -> core.models.Job
        Submits `run_build` as a job of kind `build` through `core.jobs.submit`,
        so the job holds the watchdog while it runs and the usage queue is
        flushed when it ends. A failure is stored in the job's error envelope
        with its error code: `insufficient_space` for a full disk (during the
        downloads or the import), `source_unreachable` for an unreachable data
        source (plan section 6).

    manage.py build_catalog
        Runs the build and prints a clear result that says the database is
        ready; a failure raises CommandError with its cause. Tests replace
        `catalog.download.urllib_transport` with a fake transport.

Out of scope here (later tasks): the setup endpoints, the free space check
before the start and a second build while one runs (T22).

No test touches the network: a fictional data source is served by a fake
transport (tests/catalog_build_helpers.py).
"""

import errno
import io
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import pytest
from django.utils import timezone

from tests.catalog_build_helpers import (
    CARD_IDS,
    CATALOG_TABLE_PREFIXES,
    LISTING_URL,
    NEWER_CARD_IDS,
    NEWER_PUBLISHED_AT,
    NEWER_RECORDS,
    ODD_TEXT,
    ORACLE_SOURCE,
    ORACLE_URI,
    PUBLISHED_AT,
    SENTRY,
    FakeDataSource,
    FakeSleep,
    InjectedFailure,
    NoTransport,
    bulk_bytes,
    database_locked_operational_error,
    disk_full_operational_error,
    failing_write,
    files_with_bytes,
    fts_match,
    fts_rows,
    sha256,
    writes_recorded,
)
from tests.job_helpers import (
    BUILD_KIND,
    FakeClock,
    StopRecorder,
    envelope_error,
    inline_runner,
    run_checks,
    runner_installed,
    wait_for_end,
    watchdog_calls_counted,
)

CODE_INSUFFICIENT_SPACE = "insufficient_space"
CODE_SOURCE_UNREACHABLE = "source_unreachable"
CODE_DATABASE_BUSY = "database_busy"
PHASE_TWO_TABLES = ("catalog_oraclecard", "oracle_fts", "catalog_sourcerecord", "catalog_buildrun")


# ---------------------------------------------------------------- fixtures and helpers


@pytest.fixture
def home(monkeypatch, tmp_path):
    """A temporary application home with an empty data folder."""
    folder = tmp_path / "home"
    (folder / "data").mkdir(parents=True)
    monkeypatch.setenv("CARDFACTORY_HOME", str(folder))
    return folder


@pytest.fixture
def build():
    from catalog import build as module

    return module


@pytest.fixture
def inline():
    with inline_runner() as runner:
        yield runner


@pytest.fixture
def pool():
    executor = ThreadPoolExecutor(max_workers=4)
    try:
        with runner_installed(executor) as runner:
            yield runner
    finally:
        executor.shutdown(wait=True)


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


def _is_ready():
    from catalog.selectors import is_ready

    return is_ready()


def _catalog_version():
    from catalog import sources

    return sources.CATALOG_VERSION


def _raise_catalog_version(monkeypatch, build):
    """Raise the constant where it is defined and wherever a module keeps its own name for it."""
    from catalog import selectors, sources

    value = sources.CATALOG_VERSION + 1
    for module in (sources, selectors, build):
        if hasattr(module, "CATALOG_VERSION"):
            monkeypatch.setattr(module, "CATALOG_VERSION", value)
    return value


def _card_ids():
    from catalog.models import OracleCard

    return [uuid.UUID(str(value)) for value in OracleCard.objects.values_list("oracle_id", flat=True)]


def _uuids(ids):
    return {uuid.UUID(value) for value in ids}


def _assert_nothing_stored():
    """RN-03: an interrupted build leaves no catalog rows and no ready mark."""
    from catalog.models import BuildRun, OracleCard, SourceRecord

    assert not _is_ready()
    assert OracleCard.objects.count() == 0
    assert fts_rows() == []
    assert SourceRecord.objects.count() == 0
    assert BuildRun.objects.count() == 0


def _assert_built_once(expected_ids):
    """RN-03 / CA-07: ready, every card stored once, one full-text row and one source record each."""
    from catalog.models import BuildRun, SourceRecord
    from catalog.sources import SOURCES

    assert _is_ready()
    ids = _card_ids()
    assert len(ids) == len(set(ids)), "A card was stored twice."
    assert set(ids) == _uuids(expected_ids)
    fts_ids = [oracle_id for oracle_id, _ in fts_rows()]
    assert len(fts_ids) == len(set(fts_ids)), "A card has two full-text rows."
    assert set(fts_ids) == _uuids(expected_ids)
    for source in SOURCES:
        assert SourceRecord.objects.filter(source=source.name).count() == 1
    assert BuildRun.objects.filter(catalog_version=_catalog_version()).count() == 1


def _job_error(job):
    from core.jobs import get_job

    stored = get_job(job.id)
    assert stored.status == "failed"
    return envelope_error(stored.error)


def _user_rows():
    """Jobs of a person's earlier work: rows of a table the build must never touch."""
    from core.models import Job

    Job.objects.create(kind="generate", status="done", progress=1.0, result=uuid.uuid4())
    Job.objects.create(
        kind="art",
        status="failed",
        progress=0.4,
        error={"error": {"code": "quota", "message": "Fictional quota message.", "setting": None, "fields": None}},
    )
    return _snapshot_user_rows()


def _snapshot_user_rows():
    from core.models import Job

    return sorted(
        (str(row["id"]), row["kind"], row["status"], row["progress"], str(row["result"]), repr(row["error"]))
        for row in Job.objects.values()
    )


# ---------------------------------------------------------------- a complete build


@pytest.mark.django_db
def test_t21_rn01_build_stores_every_card_once_and_marks_the_database_ready(home, build):
    """RN-01 / RN-03: a build from the fictional source stores each card once and is ready."""
    assert not _is_ready()

    build.run_build(transport=FakeDataSource(), sleep=FakeSleep())

    _assert_built_once(CARD_IDS)


@pytest.mark.django_db
def test_t21_rn01_ca08_source_record_states_origin_publication_and_download_dates(home, build):
    """RN-01 / CA-08: each source records its origin, publication date, download date, sha256 and size."""
    from catalog.models import SourceRecord

    source = FakeDataSource()
    before = timezone.now()
    build.run_build(transport=source, sleep=FakeSleep())
    after = timezone.now()

    record = SourceRecord.objects.get(source=ORACLE_SOURCE)
    assert record.url == ORACLE_URI
    assert record.published_at == datetime.fromisoformat(PUBLISHED_AT)
    assert before <= record.downloaded_at <= after
    assert record.sha256 == sha256(source.bulk)
    assert record.size == len(source.bulk)


@pytest.mark.django_db
def test_t21_rn03_ready_build_run_carries_the_current_catalog_version(home, build):
    """RN-03 (plan section 7): the ready BuildRun holds CATALOG_VERSION, started before it finished."""
    from catalog.models import BuildRun

    build.run_build(transport=FakeDataSource(), sleep=FakeSleep())

    run = BuildRun.objects.get()
    assert run.catalog_version == _catalog_version()
    assert run.started_at <= run.finished_at


@pytest.mark.django_db
def test_t21_rn01_full_text_rows_match_the_stored_cards(home, build):
    """RN-01 (plan section 7): the card full-text table is rebuilt with one row per stored card."""
    from catalog.models import OracleCard

    build.run_build(transport=FakeDataSource(), sleep=FakeSleep())

    names = {uuid.UUID(str(card.oracle_id)): card.name for card in OracleCard.objects.all()}
    rows = fts_rows()
    assert len(rows) == len(names)
    assert dict(rows) == names
    assert fts_match('"lorekeeper"') == {uuid.UUID(SENTRY["oracle_id"])}
    # Text with quotes and FTS operators is stored as text and found as a phrase.
    assert fts_match('"unquoted"') == {uuid.UUID(ODD_TEXT["oracle_id"])}


@pytest.mark.django_db
def test_t21_rn12_roles_are_stored_with_each_card(home, build):
    """RN-12 / RN-01 (plan sections 7 and 9.6): the build stores the roles `tag_roles` finds for each card."""
    from catalog.ingest import tag_roles
    from catalog.models import OracleCard

    build.run_build(transport=FakeDataSource(), sleep=FakeSleep())

    cards = list(OracleCard.objects.all())
    for card in cards:
        assert card.roles == tag_roles(card.type_line, card.oracle_text, card.name), card.name
    sentry = OracleCard.objects.get(oracle_id=SENTRY["oracle_id"])
    assert "card_draw" in sentry.roles


@pytest.mark.django_db
def test_t21_rn28_progress_is_reported_from_zero_to_one(home, build):
    """RN-28: the build reports its progress as non-decreasing values between 0 and 1."""
    reported = []

    build.run_build(transport=FakeDataSource(), sleep=FakeSleep(), report=reported.append)

    assert reported, "The build reported no progress."
    values = [float(value) for value in reported]
    assert all(0.0 <= value <= 1.0 for value in values), values
    assert values == sorted(values), values


@pytest.mark.django_db
def test_t21_rn03_source_files_are_removed_after_the_import(home, build):
    """RN-03 (plan sections 7 and 10): the downloaded source files are deleted after the import."""
    build.run_build(transport=FakeDataSource(), sleep=FakeSleep())

    downloads = home / "data" / "downloads"
    left = [path for path in downloads.rglob("*") if path.is_file()] if downloads.exists() else []
    assert left == []


@pytest.mark.django_db(transaction=True)
def test_t21_rn03_downloads_run_outside_any_transaction(home, build):
    """RN-03 (plan section 7): phase 1 (listing and downloads) runs outside any database transaction."""
    from django.db import connection

    seen = []
    source = FakeDataSource(on_request=lambda url: seen.append((url, connection.in_atomic_block)))

    build.run_build(transport=source, sleep=FakeSleep())

    assert {url for url, _ in seen} >= {LISTING_URL, ORACLE_URI}
    assert [url for url, atomic in seen if atomic] == []


@pytest.mark.django_db(transaction=True)
def test_t21_rn03_build_writes_only_catalog_tables(home, build, monkeypatch):
    """RN-03 (plan section 7): the build, a rebuild included, never writes a user table."""
    before = _user_rows()
    build.run_build(transport=FakeDataSource(), sleep=FakeSleep())
    _raise_catalog_version(monkeypatch, build)

    with writes_recorded() as tables:
        build.run_build(transport=FakeDataSource(bulk=bulk_bytes(NEWER_RECORDS)), sleep=FakeSleep())

    assert tables, "No write was recorded; the rebuild did nothing."
    outside = sorted({table for table in tables if not table.startswith(CATALOG_TABLE_PREFIXES)})
    assert outside == []
    assert _snapshot_user_rows() == before


# ---------------------------------------------------------------- interruptions (all or nothing)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("table", PHASE_TWO_TABLES)
def test_t21_rn03_ca07_import_interrupted_mid_transaction_leaves_nothing_and_rerun_is_ready(home, build, table):
    """RN-03 / CA-07: an import interrupted at any write is rolled back whole: not ready, no partial rows;
    a new run rebuilds it with no duplicated records."""
    with failing_write(table) as refused:
        with pytest.raises(Exception):
            build.run_build(transport=FakeDataSource(), sleep=FakeSleep())
    assert refused, f"The build never wrote {table}."

    _assert_nothing_stored()

    build.run_build(transport=FakeDataSource(), sleep=FakeSleep())

    _assert_built_once(CARD_IDS)


@pytest.mark.django_db(transaction=True)
def test_t21_ca07_interrupted_download_is_not_ready_and_a_rerun_is_ready_without_duplicates(home, build):
    """CA-07 / RN-03 / RN-28: a download dropped on every attempt fails the build, nothing is ready;
    a new run builds the database with no duplicated records."""
    with pytest.raises(Exception):
        build.run_build(transport=FakeDataSource(cut_bulk=True), sleep=FakeSleep())

    _assert_nothing_stored()

    build.run_build(transport=FakeDataSource(), sleep=FakeSleep())
    build_again_source = NoTransport()
    build.run_build(transport=build_again_source, sleep=FakeSleep())

    _assert_built_once(CARD_IDS)
    assert build_again_source.requests == []


@pytest.mark.django_db(transaction=True)
def test_t21_rn03_interrupted_rebuild_keeps_the_previous_rows_and_is_not_ready(home, build, monkeypatch):
    """RN-03: a rebuild interrupted in its transaction leaves the previous catalog rows as they were,
    never a mix of old and new, and the database is not ready for the new version."""
    build.run_build(transport=FakeDataSource(), sleep=FakeSleep())
    _raise_catalog_version(monkeypatch, build)
    newer = FakeDataSource(bulk=bulk_bytes(NEWER_RECORDS), published_at=NEWER_PUBLISHED_AT)

    with failing_write("catalog_buildrun"):
        with pytest.raises(Exception):
            build.run_build(transport=newer, sleep=FakeSleep())

    assert not _is_ready()
    assert set(_card_ids()) == _uuids(CARD_IDS)
    assert {oracle_id for oracle_id, _ in fts_rows()} == _uuids(CARD_IDS)

    build.run_build(transport=FakeDataSource(bulk=bulk_bytes(NEWER_RECORDS)), sleep=FakeSleep())

    _assert_built_once(NEWER_CARD_IDS)


@pytest.mark.django_db(transaction=True)
def test_t21_rn03_ca07_rerun_after_a_failed_import_does_not_download_the_source_again(home, build):
    """RN-03 / CA-07: after an import that failed for a cause other than a full disk, the downloaded
    source is kept, so the rerun does not download the bulk file again and becomes ready."""
    with failing_write("catalog_buildrun"):
        with pytest.raises(Exception):
            build.run_build(transport=FakeDataSource(), sleep=FakeSleep())
    _assert_nothing_stored()

    rerun = FakeDataSource()
    build.run_build(transport=rerun, sleep=FakeSleep())

    assert ORACLE_URI not in rerun.urls(), "The rerun downloaded the bulk file again."
    assert set(rerun.urls()) <= {LISTING_URL}
    _assert_built_once(CARD_IDS)


@pytest.mark.django_db(transaction=True)
def test_t21_rn03_database_becoming_ready_during_the_downloads_is_left_as_it_is(home, build):
    """RN-03: when the database becomes ready for the current version between phase 1 and phase 2,
    the build does not delete or reimport anything and leaves exactly one BuildRun of that version."""
    from catalog.models import BuildRun, OracleCard, SourceRecord

    sentinel = OracleCard.objects.create(
        oracle_id=uuid.UUID("b2000000-0000-4000-8000-0000000000ff"),
        name="Sentinel of the Finished Build",
        mana_cost="{1}",
        cmc=1.0,
        type_line="Artifact",
        oracle_text="",
        layout="normal",
        commander_legality="legal",
    )

    def on_request(url):
        if url == ORACLE_URI and not BuildRun.objects.exists():
            now = timezone.now()
            BuildRun.objects.create(catalog_version=_catalog_version(), started_at=now, finished_at=now)

    build.run_build(transport=FakeDataSource(on_request=on_request), sleep=FakeSleep())

    assert _is_ready()
    assert BuildRun.objects.filter(catalog_version=_catalog_version()).count() == 1
    assert BuildRun.objects.count() == 1
    assert _card_ids() == [sentinel.oracle_id]
    assert SourceRecord.objects.count() == 0
    assert fts_rows() == []


# ---------------------------------------------------------------- a ready database


@pytest.mark.django_db
def test_t21_ca08_rerun_on_a_ready_database_downloads_nothing(home, build):
    """CA-08 / RN-01: with the database ready, a new run contacts no data source and changes nothing."""
    from catalog.models import SourceRecord

    build.run_build(transport=FakeDataSource(), sleep=FakeSleep())
    record = SourceRecord.objects.values().get()
    transport = NoTransport()

    build.run_build(transport=transport, sleep=FakeSleep())

    assert transport.requests == []
    _assert_built_once(CARD_IDS)
    assert SourceRecord.objects.values().get() == record


@pytest.mark.django_db
def test_t21_ca08_build_job_on_a_ready_database_downloads_nothing(home, build, inline):
    """CA-08: a build job started on a ready database ends done without contacting the data source."""
    from core.jobs import get_job

    build.run_build(transport=FakeDataSource(), sleep=FakeSleep())
    transport = NoTransport()

    job = build.start_build(transport=transport, sleep=FakeSleep())

    assert get_job(job.id).status == "done"
    assert transport.requests == []


@pytest.mark.django_db(transaction=True)
def test_t21_rn03_raised_catalog_version_is_not_ready_and_a_rerun_rebuilds_leaving_user_rows(
    home, build, monkeypatch
):
    """RN-03 (plan section 7, catalog version): a raised CATALOG_VERSION makes the database not ready;
    the next run downloads and rebuilds every source, with user tables untouched."""
    from catalog.models import BuildRun, SourceRecord

    build.run_build(transport=FakeDataSource(), sleep=FakeSleep())
    user_rows = _user_rows()
    assert _is_ready()

    new_version = _raise_catalog_version(monkeypatch, build)
    assert not _is_ready()

    newer = FakeDataSource(bulk=bulk_bytes(NEWER_RECORDS), published_at=NEWER_PUBLISHED_AT)
    build.run_build(transport=newer, sleep=FakeSleep())

    assert ORACLE_URI in newer.urls()
    _assert_built_once(NEWER_CARD_IDS)
    assert BuildRun.objects.filter(catalog_version=new_version).count() == 1
    record = SourceRecord.objects.get(source=ORACLE_SOURCE)
    assert record.published_at == datetime.fromisoformat(NEWER_PUBLISHED_AT)
    assert record.sha256 == sha256(newer.bulk)
    # The card removed from the source is gone from the full-text table too.
    assert fts_match('"ilvar"') == set()
    assert _snapshot_user_rows() == user_rows


# ---------------------------------------------------------------- failures and their causes


@pytest.mark.django_db
def test_t21_rn28_disk_full_during_the_downloads_reports_insufficient_space(home, build, inline, monkeypatch):
    """RN-28 / RN-03: the disk fills up while the source is saved: the build job fails with
    `insufficient_space` and a message that states the cause; nothing is ready."""
    real_replace = os.replace

    def replace(src, dst, *args, **kwargs):
        if "downloads" in (Path(src).parent.name, Path(dst).parent.name):
            raise OSError(errno.ENOSPC, "No space left on device")
        return real_replace(src, dst, *args, **kwargs)

    monkeypatch.setattr(os, "replace", replace)

    job = build.start_build(transport=FakeDataSource(), sleep=FakeSleep())

    error = _job_error(job)
    assert error["code"] == CODE_INSUFFICIENT_SPACE
    assert "disk" in error["message"].lower() or "space" in error["message"].lower()
    _assert_nothing_stored()


@pytest.mark.django_db(transaction=True)
def test_t21_rn28_disk_full_during_the_import_reports_insufficient_space(home, build, inline):
    """RN-28 / RN-03: SQLite reports a full disk during the import: the transaction is rolled back,
    the job fails with `insufficient_space`, and nothing is ready."""
    with failing_write("catalog_oraclecard", error=disk_full_operational_error()) as refused:
        job = build.start_build(transport=FakeDataSource(), sleep=FakeSleep())
    assert refused, "The build never wrote a card."

    error = _job_error(job)
    assert error["code"] == CODE_INSUFFICIENT_SPACE
    _assert_nothing_stored()


@pytest.mark.django_db
def test_t21_rn28_unreachable_data_source_reports_its_cause(home, build, inline):
    """RN-28: a data source that keeps answering with an error fails the job with `source_unreachable`
    after the retries, and nothing is ready."""
    sleep = FakeSleep()

    job = build.start_build(transport=FakeDataSource(listing_status=503), sleep=sleep)

    error = _job_error(job)
    assert error["code"] == CODE_SOURCE_UNREACHABLE
    assert "503" in error["message"]
    assert len(sleep.calls) == 2, "The listing was not tried three times in all."
    _assert_nothing_stored()


@pytest.mark.django_db(transaction=True)
def test_t21_rn28_disk_full_during_the_import_leaves_no_full_source_file(home, build, inline):
    """RN-28 / RN-03 (plan section 7, data layout): after a full disk in the import, the downloads folder
    keeps no full copy of the source file, so the space is given back."""
    source = FakeDataSource()
    with failing_write("catalog_oraclecard", error=disk_full_operational_error()):
        job = build.start_build(transport=source, sleep=FakeSleep())

    assert _job_error(job)["code"] == CODE_INSUFFICIENT_SPACE
    assert files_with_bytes(home / "data" / "downloads", source.bulk) == []


@pytest.mark.django_db(transaction=True)
def test_t21_rn03_locked_database_during_the_import_reports_database_busy(home, build, inline):
    """RN-03 (plan sections 6 and 7): "database is locked" during the import fails the job with
    `database_busy`; the transaction is rolled back and nothing is ready."""
    with failing_write("catalog_oraclecard", error=database_locked_operational_error()) as refused:
        job = build.start_build(transport=FakeDataSource(), sleep=FakeSleep())
    assert refused, "The build never wrote a card."

    error = _job_error(job)
    assert error["code"] == CODE_DATABASE_BUSY
    assert "database is locked" not in error["message"]
    _assert_nothing_stored()


MALFORMED_BULK_FILES = {
    "truncated": bulk_bytes()[: len(bulk_bytes()) // 2],
    "not_an_array": b'{"object": "list", "data": []}',
    "invalid_oracle_id": bulk_bytes([SENTRY, dict(SENTRY, oracle_id="not-a-uuid", name="Brokenid Wisp")]),
    "empty_file": b"",
    "not_json": "Ünïcödé noise ✦ <html>".encode("utf-8"),
}


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("name", sorted(MALFORMED_BULK_FILES))
def test_t21_rn03_malformed_bulk_file_fails_the_build_with_no_partial_rows(home, build, inline, name):
    """RN-03: a source file that cannot be read fails the build job with an error envelope and
    leaves no partial rows; the database is not ready."""
    job = build.start_build(transport=FakeDataSource(bulk=MALFORMED_BULK_FILES[name]), sleep=FakeSleep())

    _job_error(job)
    _assert_nothing_stored()


@pytest.mark.django_db
def test_t21_rn28_malformed_listing_fails_with_source_unreachable(home, build, inline):
    """RN-28: a download listing that cannot be read fails the job with `source_unreachable`."""
    job = build.start_build(transport=FakeDataSource(listing_body=b"<html>not json</html>"), sleep=FakeSleep())

    assert _job_error(job)["code"] == CODE_SOURCE_UNREACHABLE
    _assert_nothing_stored()


# ---------------------------------------------------------------- the build as a job


@pytest.mark.django_db
def test_t21_rn03_build_runs_as_a_job_of_kind_build_and_ends_done(home, build, inline):
    """RN-03 / RN-28 (plan section 7): the build is a job of kind `build`; it ends done, ready, with no result."""
    from core.jobs import get_job

    job = build.start_build(transport=FakeDataSource(), sleep=FakeSleep())

    stored = get_job(job.id)
    assert stored.kind == BUILD_KIND
    assert stored.status == "done"
    assert stored.result is None
    assert stored.error is None
    _assert_built_once(CARD_IDS)


@pytest.mark.django_db(transaction=True)
def test_t21_rn03_build_job_on_the_thread_pool_ends_ready(home, build, pool):
    """RN-03: on the real thread pool, the build job ends done and the database is ready."""
    job = build.start_build(transport=FakeDataSource(), sleep=FakeSleep())

    ended = wait_for_end(job.id)

    assert ended.status == "done", ended.error
    _assert_built_once(CARD_IDS)


@pytest.mark.django_db(transaction=True)
def test_t21_rn03_build_progress_is_read_from_the_running_job(home, build, pool):
    """RN-28 / RN-03 (plan section 7): progress reported during the build is read through `get_job`."""
    import threading

    from core.jobs import get_job
    from core.models import Job

    downloading = threading.Event()
    resume = threading.Event()

    def on_request(url):
        if url == ORACLE_URI:
            downloading.set()
            assert resume.wait(10), "The test never resumed the build."

    job = build.start_build(transport=FakeDataSource(on_request=on_request), sleep=FakeSleep())
    try:
        assert downloading.wait(10), "The build never downloaded the source."
        running = get_job(job.id)
        assert running.status == Job.Status.RUNNING
        assert 0.0 <= running.progress < 1.0
    finally:
        resume.set()
    assert wait_for_end(job.id).progress == 1.0


@pytest.mark.django_db(transaction=True)
def test_t21_rn03_build_killed_mid_way_is_reported_failed_and_the_next_start_retries(home, build, inline):
    """RN-03 / CA-07 (plan section 7, orphans): a process killed mid-build leaves a running build job and
    no ready mark; it is reported as failed, never running, and the next build makes the database ready."""
    from core.jobs import fail_orphan_jobs, get_job
    from core.models import Job

    killed = Job.objects.create(kind=BUILD_KIND, status=Job.Status.RUNNING, progress=0.6)
    leftover = home / "data" / "downloads"
    leftover.mkdir(parents=True)
    (leftover / "fictional-leftover.part").write_bytes(b'[{"oracle_id": "b2000000-')

    assert get_job(killed.id).status == Job.Status.FAILED
    assert not _is_ready()

    stale = Job.objects.create(kind=BUILD_KIND, status=Job.Status.RUNNING, progress=0.2)
    fail_orphan_jobs()
    assert Job.objects.get(pk=stale.pk).status == Job.Status.FAILED

    retried = build.start_build(transport=FakeDataSource(), sleep=FakeSleep())

    assert get_job(retried.id).status == Job.Status.DONE
    assert Job.objects.filter(status__in=(Job.Status.QUEUED, Job.Status.RUNNING)).count() == 0
    _assert_built_once(CARD_IDS)


@pytest.mark.django_db
@pytest.mark.parametrize("outcome", ["done", "failed"])
def test_t21_rn41_watchdog_is_held_during_the_build_and_released_after(
    home, build, inline, installed_watchdog, clock, stop, outcome
):
    """RN-41 / CA-70: while the build runs the application does not stop with no tab open;
    after it ends, done or failed, it stops IDLE_SECONDS later."""
    from core.watchdog import IDLE_SECONDS

    held = []

    def on_request(url):
        # Long after the last heartbeat, in the middle of the build.
        run_checks(installed_watchdog, clock, 3600, step=60)
        held.append(stop.calls)

    source = FakeDataSource(on_request=on_request, listing_status=200 if outcome == "done" else 503)
    with watchdog_calls_counted() as calls:
        job = build.start_build(transport=source, sleep=FakeSleep())

    from core.jobs import get_job

    assert get_job(job.id).status == outcome
    assert held and set(held) == {0}, "The application stopped during the build."
    assert calls == {"hold": 1, "release": 1}
    run_checks(installed_watchdog, clock, IDLE_SECONDS, step=1)
    assert stop.calls == 1, "The watchdog was not released after the build."


@pytest.mark.django_db
@pytest.mark.parametrize("outcome", ["done", "failed"])
def test_t21_rn03_usage_records_wait_for_the_build_and_are_flushed_when_it_ends(home, build, inline, outcome):
    """RN-03 (plan section 7, usage queue): a usage write made while the build runs waits and is written
    when the build ends, whatever the outcome."""
    from core.jobs import enqueue_usage

    written = []
    seen_during = []

    def on_request(url):
        if url == LISTING_URL and not seen_during:
            enqueue_usage(lambda: written.append("connection test"))
            seen_during.append(list(written))

    source = FakeDataSource(on_request=on_request, listing_status=200 if outcome == "done" else 503)
    build.start_build(transport=source, sleep=FakeSleep())

    assert seen_during == [[]], "The usage record was written while the build ran."
    assert written == ["connection test"]


# ---------------------------------------------------------------- management command


@pytest.fixture
def served(monkeypatch):
    """The default transport of catalog.download replaced by a fictional data source."""
    from catalog import download

    def install(transport):
        monkeypatch.setattr(download, "urllib_transport", transport)
        monkeypatch.setattr(download.time, "sleep", FakeSleep())
        return transport

    return install


def _call_build_catalog():
    from django.core.management import call_command

    out, err = io.StringIO(), io.StringIO()
    call_command("build_catalog", stdout=out, stderr=err)
    return out.getvalue(), err.getvalue()


@pytest.mark.django_db(transaction=True)
def test_t21_rn01_build_catalog_command_builds_the_database_and_says_it_is_ready(home, served):
    """RN-01 / RN-03: `manage.py build_catalog` runs the build and prints a clear result."""
    source = served(FakeDataSource())

    out, _ = _call_build_catalog()

    assert ORACLE_URI in source.urls()
    _assert_built_once(CARD_IDS)
    assert "ready" in out.lower(), out


@pytest.mark.django_db(transaction=True)
def test_t21_ca08_build_catalog_command_on_a_ready_database_downloads_nothing(home, served, build):
    """CA-08: the command run on a ready database contacts no data source and says it is ready."""
    build.run_build(transport=FakeDataSource(), sleep=FakeSleep())
    transport = served(NoTransport())

    out, _ = _call_build_catalog()

    assert transport.requests == []
    assert "ready" in out.lower(), out
    _assert_built_once(CARD_IDS)


@pytest.mark.django_db(transaction=True)
def test_t21_rn28_build_catalog_command_failure_states_the_cause(home, served):
    """RN-28 / RN-03: when the data source fails, the command fails with its cause and nothing is ready."""
    from django.core.management.base import CommandError

    from core.errors import INTERNAL_MESSAGE

    served(FakeDataSource(listing_status=503))

    with pytest.raises(CommandError) as raised:
        _call_build_catalog()

    message = str(raised.value)
    assert "503" in message
    assert INTERNAL_MESSAGE not in message
    _assert_nothing_stored()


@pytest.mark.django_db(transaction=True)
def test_t21_rn28_build_catalog_command_prints_its_progress(home, served):
    """RN-28: the command shows the build's progress as at least one percentage."""
    import re

    served(FakeDataSource())

    out, err = _call_build_catalog()

    assert re.search(r"\b\d{1,3}(?:[.,]\d+)?\s?%", out + err), out + err
