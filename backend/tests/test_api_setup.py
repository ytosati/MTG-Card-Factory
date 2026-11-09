"""Setup endpoints and the status additions (task T22).

Spec: RN-01, RN-28, CA-08, CA-18, CA-60. Details: specs/plan.md, sections 6
(endpoints, error envelope and codes, jobs) and 7 (catalog version, build).

Expected API (field names proposed by this suite where the plan names none):

    GET /api/setup -> 200
        database_ready  bool          a ready build of the current CATALOG_VERSION exists
        job             JobResponse | null
                                      the running build job, or the latest build job when it
                                      failed (so the screen shows the cause); else null
        download_size   int | null    sum over the source registry of the sizes in the
                                      data source listing, in bytes; null when the listing
                                      cannot be read
        space_needed    int | null    download_size * BUILD_SPACE_FACTOR (3), in bytes
        free_space      int | null    free bytes on the drive that holds the data folder;
                                      null when the drive cannot be read (POST then
                                      starts the build instead of refusing)
        listing_error   ErrorEnvelope | null
                                      the cause when the listing cannot be read
                                      (code `source_unreachable`)
        settings        [{setting, code, message}]
                                      the same settings list as GET /api/status
        The listing is read, never a data file, and it is cached for the session
        (a failure is not cached, so a retry reads it again).

    POST /api/setup/build -> 202 with the build job (JobResponse)
        507 `insufficient_space` when the free space is less than space_needed;
        502 `source_unreachable` when the listing cannot be read (nothing started);
        while a build runs, 202 with that build's job instead of another one;
        on a ready database, 202 with a build job that ends done with no download.

    Gate: `database_not_ready` answers 503 (tests/test_api_readiness_gate.py).

    GET /api/status gains:
        database_ready  bool
        sources         [{source, url, published_at, downloaded_at}], one per
                        SourceRecord of the ready build (origin, publication date,
                        download date)

Seams: tests/setup_api_helpers.py. Builds run on an inline runner, so a build
started by POST runs to its end inside the request; requests made from inside
the fake transport observe the build while it runs.
"""

import json
import uuid
from datetime import datetime

import pytest

from tests.catalog_build_helpers import (
    LISTING_URL,
    ORACLE_SOURCE,
    ORACLE_URI,
    PUBLISHED_AT,
    FakeDataSource,
    bulk_bytes,
)
from tests.config_files import DEFAULT_PORT, full_text_settings
from tests.configured_api import assert_error_envelope, configured_api  # noqa: F401 (fixture)
from tests.job_helpers import JOB_FIELDS, envelope_error, inline_runner
from tests.setup_api_helpers import (
    BUILD_URL,
    CODE_INSUFFICIENT_SPACE,
    CODE_SOURCE_UNREACHABLE,
    DEFAULT_CARDS_HOSTS,
    DEFAULT_CARDS_LISTING_TYPE,
    DEFAULT_CARDS_SIZE,
    EXPECTED_SPACE_FACTOR,
    JOBS_URL,
    PLENTY_OF_SPACE,
    SETUP_URL,
    STATUS_URL,
    DuringDownload,
    SetupEnvironment,
    clear_listing_cache,
    constant_values,
    download_files,
    listing_body,
    mark_ready,
    own_origin,
)

pytestmark = pytest.mark.django_db

SETUP_FIELDS = {"database_ready", "job", "download_size", "space_needed", "free_space", "listing_error", "settings"}
SOURCE_FIELDS = {"source", "url", "published_at", "downloaded_at"}
ACCEPTED = 202
INSUFFICIENT_SPACE_STATUS = 507
SOURCE_UNREACHABLE_STATUS = 502
BULK_SIZE = len(bulk_bytes())
OWN_ORIGIN = own_origin(DEFAULT_PORT)
FOREIGN_ORIGIN = {"HTTP_ORIGIN": "http://evil.example"}


# ---------------------------------------------------------------- fixtures and helpers


@pytest.fixture
def env(configured_api, monkeypatch):
    """A configured API on a temporary home, with the fictional data source and plenty of free space."""
    configured_api.configure(full_text_settings())
    configured_api.set_running_port(DEFAULT_PORT)
    with inline_runner():
        environment = SetupEnvironment(monkeypatch)
        environment.api = configured_api
        yield environment
    clear_listing_cache()


def _json(response, status=200):
    assert response.status_code == status, response.content[:500]
    assert response["Content-Type"].startswith("application/json")
    return response.json()


def _setup(env):
    body = _json(env.api.get(SETUP_URL))
    assert SETUP_FIELDS <= set(body), body
    return body


def _status(env):
    return _json(env.api.get(STATUS_URL))


def _post_build(env, **headers):
    return env.api.request("POST", BUILD_URL, data={}, **(headers or OWN_ORIGIN))


def _start_build(env):
    body = _json(_post_build(env), ACCEPTED)
    assert set(body) == JOB_FIELDS, body
    assert body["kind"] == "build"
    return body


def _build_jobs():
    from core.models import Job

    return list(Job.objects.filter(kind="build"))


def _parse(value):
    assert isinstance(value, str) and value, value
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _assert_no_build_started(env):
    assert env.bulk_requests() == 0, "The bulk file was requested although no build was started."
    assert _build_jobs() == []
    assert download_files(env.api.home) == []


# ---------------------------------------------------------------- GET /api/setup before any build


def test_t22_rn28_ca18_setup_states_size_and_space_before_any_build(env):
    """RN-28 / CA-18 / T22: before any build the setup answers not ready, no job, the download size from the
    listing, the space needed (size x 3) and the free space on the data folder's drive, with no listing error."""
    body = _setup(env)

    assert body["database_ready"] is False
    assert body["job"] is None
    assert body["download_size"] == BULK_SIZE
    assert body["space_needed"] == BULK_SIZE * EXPECTED_SPACE_FACTOR
    assert body["free_space"] == PLENTY_OF_SPACE
    assert body["listing_error"] is None


def test_t22_rn28_space_factor_is_the_named_constant_three():
    """RN-28 / T22: the factor of the space needed is the named constant BUILD_SPACE_FACTOR, equal to 3."""
    values = constant_values("BUILD_SPACE_FACTOR")

    assert values, "BUILD_SPACE_FACTOR is not defined in a catalog, core or api module."
    assert set(values.values()) == {EXPECTED_SPACE_FACTOR}, values


def test_t22_rn28_download_size_is_the_sum_over_the_source_registry(env, monkeypatch):
    """RN-28 / T22 / plan section 7: the download size sums every registry source, and only those
    (the listing also names files the registry does not use)."""
    from catalog import sources

    second = sources.Source(
        name="scryfall_default", listing_type=DEFAULT_CARDS_LISTING_TYPE, allowed_hosts=DEFAULT_CARDS_HOSTS
    )
    monkeypatch.setattr(sources, "SOURCES", (*sources.SOURCES, second))

    body = _setup(env)

    assert body["download_size"] == BULK_SIZE + DEFAULT_CARDS_SIZE
    assert body["space_needed"] == (BULK_SIZE + DEFAULT_CARDS_SIZE) * EXPECTED_SPACE_FACTOR


def test_t22_rn28_listing_entries_outside_the_registry_are_not_counted(env):
    """RN-28 / T22: with only Oracle Cards in the registry, the listed Default Cards file is not counted."""
    body = _setup(env)

    assert body["download_size"] == BULK_SIZE
    assert body["download_size"] != BULK_SIZE + DEFAULT_CARDS_SIZE


@pytest.mark.parametrize(
    "size",
    [
        pytest.param(0, id="zero"),
        pytest.param(1, id="one-byte"),
        pytest.param(2**31 + 7, id="over-32-bits"),
        pytest.param(5 * 10**12, id="five-terabytes"),
    ],
)
def test_t22_rn28_sizes_are_exact_integers_in_bytes(env, size):
    """RN-28 / T22: the download size and the space needed are exact byte counts, including zero and sizes
    beyond 32 bits."""
    env.use_source(FakeDataSource(listing_body=listing_body(size=size)))

    body = _setup(env)

    assert body["download_size"] == size
    assert body["space_needed"] == size * EXPECTED_SPACE_FACTOR
    assert isinstance(body["download_size"], int) and isinstance(body["space_needed"], int)


def test_t22_rn28_space_needed_follows_the_named_constant(env, monkeypatch):
    """RN-28 / T22: the space needed is computed from BUILD_SPACE_FACTOR, not from a literal 3."""
    for module_name in constant_values("BUILD_SPACE_FACTOR"):
        monkeypatch.setattr(f"{module_name}.BUILD_SPACE_FACTOR", 5)

    body = _setup(env)

    assert body["space_needed"] == BULK_SIZE * 5


@pytest.mark.parametrize("free", [0, 1, 123_456_789, PLENTY_OF_SPACE])
def test_t22_rn28_free_space_is_reported_as_read(env, free):
    """RN-28 / T22: the free space is the value read from the disk, zero included."""
    env.set_free_space(free)

    assert _setup(env)["free_space"] == free


def test_t22_rn28_free_space_is_read_on_the_drive_of_the_data_folder(env):
    """RN-28 / T22: the free space is read for the data folder (the folder itself, a folder inside it
    or one that holds it), never for another place."""
    from core.paths import data_dir

    _setup(env)

    assert env.disk.calls, "The free space was not read from the disk."
    data_folder = data_dir().resolve()
    for asked in env.disk.calls:
        path = type(data_folder)(asked).resolve()
        assert data_folder.is_relative_to(path) or path.is_relative_to(data_folder), asked


# ---------------------------------------------------------------- CA-18: nothing downloaded before POST


def test_t22_ca18_repeated_setup_reads_only_the_listing_and_starts_nothing(env):
    """CA-18 / RN-28 / T22: polling GET /api/setup reads only the listing, never the bulk file, starts no
    build job, writes no download and leaves the database not ready."""
    from catalog.selectors import is_ready

    for _ in range(4):
        assert _setup(env)["database_ready"] is False

    assert set(env.source.urls()) <= {LISTING_URL}
    assert env.source.unexpected == []
    _assert_no_build_started(env)
    assert is_ready() is False


def test_t22_rn28_listing_is_cached_while_the_screen_polls(env):
    """RN-28 / T22: the listing is read once for the session, whatever the number of polls."""
    for _ in range(5):
        _setup(env)

    assert env.listing_requests() == 1


def test_t22_ca18_status_contacts_no_data_source(env):
    """CA-18 / T22: the Status screen opens before the build without contacting the data source."""
    _status(env)

    assert env.source.requests == []
    _assert_no_build_started(env)


# ---------------------------------------------------------------- unreachable listing (RN-28)


def _assert_unreachable(body):
    assert body["database_ready"] is False
    assert body["download_size"] is None
    assert body["space_needed"] is None
    assert isinstance(body["free_space"], int)
    error = envelope_error(body["listing_error"])
    assert error["code"] == CODE_SOURCE_UNREACHABLE
    return error


class _NoNetwork:
    """A transport whose every request fails as a dropped connection."""

    def __init__(self):
        self.requests = []
        self.unexpected = []

    def urls(self):
        return list(self.requests)

    def __call__(self, url, headers):
        self.requests.append(url)
        raise ConnectionResetError(10054, "fictional connection reset")


def test_t22_rn28_listing_without_network_returns_the_cause(env):
    """RN-28 / T22: with no network the setup still answers, with the no-network cause of the downloader and
    no sizes."""
    from catalog import download

    env.use_source(_NoNetwork())

    error = _assert_unreachable(_setup(env))

    assert error["message"] == download.NO_NETWORK_MESSAGE
    assert ORACLE_URI not in env.source.urls()


@pytest.mark.parametrize("status", [404, 429, 500, 503])
def test_t22_rn28_listing_error_status_returns_the_cause(env, status):
    """RN-28 / T22: a listing answered with an HTTP error returns `source_unreachable` naming the status."""
    env.use_source(FakeDataSource(listing_status=status))

    error = _assert_unreachable(_setup(env))

    assert str(status) in error["message"]
    _assert_no_build_started(env)


MARKER = "MARKER-ECHO-7781"


@pytest.mark.parametrize(
    "body",
    [
        pytest.param(b"", id="empty"),
        pytest.param(b"not json \x00\xff " + MARKER.encode(), id="not-json"),
        pytest.param(b"{" * 200_000, id="huge-garbage"),
        pytest.param(b"{}", id="no-data"),
        pytest.param(json.dumps({"data": []}).encode(), id="no-oracle-entry"),
        pytest.param(json.dumps({"data": "oracle_cards " + MARKER}).encode(), id="data-not-a-list"),
        pytest.param(listing_body(size=-1), id="negative-size"),
        pytest.param(listing_body(size="123"), id="size-as-text"),
        pytest.param(listing_body(size=True), id="size-as-bool"),
        pytest.param(listing_body(size=None), id="size-null"),
        pytest.param(listing_body(size=12, download_uri=f"https://evil.example/{MARKER}.json"), id="foreign-host"),
        pytest.param(listing_body(size=12, download_uri=f"http://data.scryfall.io/{MARKER}.json"), id="plain-http"),
        pytest.param(listing_body(size=12, updated_at=f"yesterday {MARKER}"), id="bad-date"),
        pytest.param(listing_body(size=12, updated_at="2026-11-08T22:04:23"), id="date-without-zone"),
        pytest.param(
            listing_body(size=12, download_uri="https://data.scryfall.io/ünï 🜲 {W/U}{2/B}  .json", updated_at="—"),
            id="odd-characters",
        ),
    ],
)
def test_t22_rn28_malformed_listing_returns_the_cause_without_echoing_it(env, body):
    """RN-28 / T22: a malformed listing answers `source_unreachable` with a fixed message that quotes none of
    the listing, no sizes, and no build."""
    env.use_source(FakeDataSource(listing_body=body))

    error = _assert_unreachable(_setup(env))

    assert MARKER not in error["message"]
    assert "evil.example" not in error["message"]
    _assert_no_build_started(env)


def test_t22_rn28_unreachable_listing_is_not_cached_so_a_retry_reads_it_again(env):
    """RN-28 / T22: after an unreachable listing, the next GET (the retry) reads the listing again and states
    the sizes once the source answers."""
    failing = env.use_source(FakeDataSource(listing_status=503))
    _assert_unreachable(_setup(env))
    assert failing.urls(), "The failing listing was never asked for."

    working = env.use_source(FakeDataSource())
    body = _setup(env)

    assert working.urls() == [LISTING_URL]
    assert body["listing_error"] is None
    assert body["download_size"] == BULK_SIZE


# ---------------------------------------------------------------- POST /api/setup/build


def test_t22_rn28_post_starts_the_build_as_a_job(env):
    """RN-28 / RN-01 / T22: POST answers 202 with a build job; the build reaches ready, the job ends done with
    its progress at 1, and the setup reports no job (only a running or failed build is shown)."""
    job = _start_build(env)

    body = _setup(env)

    assert body["database_ready"] is True
    assert body["job"] is None
    assert env.bulk_requests() == 1
    jobs = _json(env.api.get(f"{JOBS_URL}/{job['id']}"))
    assert (jobs["status"], jobs["progress"]) == ("done", 1.0)


def test_t22_ca18_progress_is_reported_while_the_build_runs(env):
    """CA-18 / RN-28 / T22: during the download the setup reports the running build job with a progress
    between 0 and 1 and the database not ready; GET /api/jobs/{id} reports the same progress."""

    def observe():
        setup = _setup(env)
        job = _json(env.api.get(f"{JOBS_URL}/{setup['job']['id']}"))
        return setup, job

    watcher = DuringDownload(observe)
    env.source.on_request = watcher

    started = _start_build(env)

    assert watcher.results, "The bulk file was never requested."
    during, job = watcher.results[0]
    assert during["database_ready"] is False
    assert during["job"]["id"] == started["id"]
    assert during["job"]["status"] == "running"
    assert 0 < during["job"]["progress"] < 1
    assert during["job"]["error"] is None
    assert (job["status"], job["progress"]) == ("running", during["job"]["progress"])
    assert _setup(env)["database_ready"] is True


def test_t22_rn28_repeated_post_while_a_build_runs_returns_the_running_job(env):
    """RN-28 / T22: a second POST while the build runs answers the running build's job and starts no
    other build: one build job, one bulk download."""
    watcher = DuringDownload(lambda: _post_build(env))
    env.source.on_request = watcher

    first = _start_build(env)

    assert watcher.results, "The bulk file was never requested."
    second = watcher.results[0]
    assert second.status_code == ACCEPTED, second.content[:500]
    body = second.json()
    assert set(body) == JOB_FIELDS
    assert body["id"] == first["id"]
    assert body["kind"] == "build"
    assert body["status"] in ("queued", "running")
    assert [str(job.id) for job in _build_jobs()] == [first["id"]]
    assert env.bulk_requests() == 1


def test_t22_rn28_failed_build_shows_its_cause_in_setup(env):
    """RN-28 / T22: a build whose download keeps failing ends failed; the setup reports the job with its
    cause (`source_unreachable`) and the database not ready."""
    env.use_source(FakeDataSource(cut_bulk=True))

    job = _start_build(env)
    body = _setup(env)

    assert body["database_ready"] is False
    assert body["job"]["id"] == job["id"]
    assert body["job"]["status"] == "failed"
    assert envelope_error(body["job"]["error"])["code"] == CODE_SOURCE_UNREACHABLE


def test_t22_rn28_post_after_a_failed_build_starts_a_new_one(env):
    """RN-28 / T22: once a build failed, POST starts a new build (the retry) that can reach ready."""
    env.use_source(FakeDataSource(cut_bulk=True))
    failed = _start_build(env)

    env.use_source(FakeDataSource())
    retry = _start_build(env)

    assert retry["id"] != failed["id"]
    jobs = _json(env.api.get(f"{JOBS_URL}/{retry['id']}"))
    assert jobs["status"] == "done"
    assert _setup(env)["database_ready"] is True


# ---------------------------------------------------------------- CA-60: not enough free space


@pytest.mark.parametrize(
    "free",
    [
        pytest.param(0, id="zero"),
        pytest.param(1, id="one-byte"),
        pytest.param(BULK_SIZE, id="download-size-only"),
        pytest.param(BULK_SIZE * EXPECTED_SPACE_FACTOR - 1, id="one-byte-short"),
    ],
)
def test_t22_ca60_build_is_refused_with_too_little_free_space(env, free):
    """CA-60 / RN-28 / T22: with less free space than the build needs, POST answers `insufficient_space`,
    starts no build and downloads nothing; the setup still names the space needed."""
    env.set_free_space(free)

    response = _post_build(env)

    error = assert_error_envelope(response, INSUFFICIENT_SPACE_STATUS, CODE_INSUFFICIENT_SPACE)
    assert error["fields"] is None
    _assert_no_build_started(env)
    body = _setup(env)
    assert body["job"] is None
    assert body["database_ready"] is False
    assert body["space_needed"] == BULK_SIZE * EXPECTED_SPACE_FACTOR
    assert body["free_space"] == free


def test_t22_ca60_exactly_the_space_needed_is_enough(env):
    """CA-60 / T22: the build is refused only when the free space is less than needed; equal is enough."""
    env.set_free_space(BULK_SIZE * EXPECTED_SPACE_FACTOR)

    _start_build(env)

    assert _setup(env)["database_ready"] is True


def test_t22_ca60_refusal_follows_the_listing_of_the_registry(env):
    """CA-60 / T22: a huge listed size (5 TB) is refused on a disk with 1 TB free."""
    env.use_source(FakeDataSource(listing_body=listing_body(size=5 * 10**12)))
    env.set_free_space(10**12)

    response = _post_build(env)

    assert_error_envelope(response, INSUFFICIENT_SPACE_STATUS, CODE_INSUFFICIENT_SPACE)
    _assert_no_build_started(env)


@pytest.mark.parametrize(
    "source",
    [
        pytest.param(lambda: FakeDataSource(listing_status=503), id="listing-503"),
        pytest.param(lambda: FakeDataSource(listing_body=b"not json"), id="malformed-listing"),
        pytest.param(lambda: _NoNetwork(), id="no-network"),
    ],
)
def test_t22_rn28_post_with_an_unreachable_listing_starts_nothing(env, source):
    """RN-28 / T22: when the listing cannot be read, POST answers 502 `source_unreachable` and starts no
    build (the space needed is unknown)."""
    env.use_source(source())

    response = _post_build(env)

    assert_error_envelope(response, SOURCE_UNREACHABLE_STATUS, CODE_SOURCE_UNREACHABLE)
    assert ORACLE_URI not in env.source.urls()
    assert _build_jobs() == []
    assert download_files(env.api.home) == []


def test_t22_ca08_post_on_a_ready_database_downloads_nothing(env):
    """CA-08 / RN-03 / T22: on a ready database POST answers 202 with a build job that ends done without
    downloading anything; the database stays ready."""
    mark_ready()

    job = _start_build(env)

    assert env.bulk_requests() == 0
    assert download_files(env.api.home) == []
    stored = _json(env.api.get(f"{JOBS_URL}/{job['id']}"))
    assert (stored["status"], stored["error"]) == ("done", None)
    assert _setup(env)["database_ready"] is True


# ---------------------------------------------------------------- origin check (RN-29, plan section 8)


@pytest.mark.parametrize("origin", ["http://evil.example", "http://127.0.0.1:1", "null"])
def test_t22_rn29_post_from_another_origin_starts_no_build(env, origin):
    """RN-29 / T22: POST /api/setup/build from another origin answers `origin_refused` and starts nothing."""
    response = _post_build(env, HTTP_ORIGIN=origin)

    assert_error_envelope(response, 403, "origin_refused")
    assert env.source.requests == []
    _assert_no_build_started(env)


def test_t22_rn29_post_from_the_own_page_is_accepted(env):
    """RN-29 / T22: POST from the application's own page starts the build."""
    _start_build(env)

    assert len(_build_jobs()) == 1


# ---------------------------------------------------------------- settings to fix (RN-28, RN-08)


def test_t22_rn28_setup_lists_no_setting_with_a_valid_configuration(env):
    """RN-28 / RN-08 / T22: with a valid configuration the setup's settings list is empty, as in status."""
    body = _setup(env)

    assert body["settings"] == []
    assert body["settings"] == _status(env)["settings"]


def test_t22_rn28_setup_names_a_missing_setting_like_status(env):
    """RN-28 / RN-08 / CA-46 / T22: with a missing key the setup lists the `config_invalid` item for
    LLM_API_KEY, the same list as GET /api/status, each item {setting, code, message}."""
    env.api.configure(full_text_settings(key=""))

    body = _setup(env)

    assert ("LLM_API_KEY", "config_invalid") in {(item["setting"], item["code"]) for item in body["settings"]}
    for item in body["settings"]:
        assert set(item) == {"setting", "code", "message"}
        assert item["message"].strip()
    assert body["settings"] == _status(env)["settings"]


# ---------------------------------------------------------------- status: readiness and sources (RN-01, CA-08)


def test_t22_rn01_status_before_the_build_is_not_ready_with_no_sources(env):
    """RN-01 / CA-18 / T22: before any build the status reports the database not ready and no source."""
    body = _status(env)

    assert body["database_ready"] is False
    assert body["sources"] == []


def test_t22_ca08_status_lists_each_source_with_origin_and_both_dates(env):
    """CA-08 / RN-01 / T22: after a ready build the status reports ready and, for every registry source, its
    origin, the publication date from the listing and the download date."""
    from django.utils import timezone

    from catalog import sources

    before = timezone.now()
    _start_build(env)
    after = timezone.now()

    body = _status(env)

    assert body["database_ready"] is True
    assert {entry["source"] for entry in body["sources"]} == {source.name for source in sources.SOURCES}
    entry = next(entry for entry in body["sources"] if entry["source"] == ORACLE_SOURCE)
    assert SOURCE_FIELDS <= set(entry)
    assert entry["url"] == ORACLE_URI
    assert _parse(entry["published_at"]) == datetime.fromisoformat(PUBLISHED_AT)
    downloaded = _parse(entry["downloaded_at"])
    assert downloaded.tzinfo is not None
    assert before <= downloaded <= after


def test_t22_ca08_status_reads_the_stored_source_records(env):
    """CA-08 / RN-01 / T22: the status shows the stored source record as written (a fictional record)."""
    from catalog.models import SourceRecord

    mark_ready()
    SourceRecord.objects.create(
        source=ORACLE_SOURCE,
        url="https://data.scryfall.io/oracle-cards/fictional-oracle-cards-20250101000000.json",
        published_at=datetime.fromisoformat("2025-01-01T00:00:00+00:00"),
        downloaded_at=datetime.fromisoformat("2025-01-02T03:04:05+00:00"),
        sha256="0" * 64,
        size=12345,
    )

    body = _status(env)

    assert body["database_ready"] is True
    assert len(body["sources"]) == 1
    entry = body["sources"][0]
    assert entry["source"] == ORACLE_SOURCE
    assert entry["url"] == "https://data.scryfall.io/oracle-cards/fictional-oracle-cards-20250101000000.json"
    assert _parse(entry["published_at"]) == datetime.fromisoformat("2025-01-01T00:00:00+00:00")
    assert _parse(entry["downloaded_at"]) == datetime.fromisoformat("2025-01-02T03:04:05+00:00")


def test_t22_rn28_readiness_follows_the_catalog_version(env, monkeypatch):
    """RN-28 / RN-03 / T22: a build of an older catalog version is not ready, in setup and in status."""
    from catalog import sources

    mark_ready()
    monkeypatch.setattr(sources, "CATALOG_VERSION", sources.CATALOG_VERSION + 1)

    assert _setup(env)["database_ready"] is False
    assert _status(env)["database_ready"] is False


def test_t22_rn28_setup_and_status_agree_on_readiness(env):
    """RN-28 / T22: setup and status report the same readiness, before and after a ready build."""
    assert _setup(env)["database_ready"] is _status(env)["database_ready"] is False

    mark_ready()

    assert _setup(env)["database_ready"] is _status(env)["database_ready"] is True


def test_t22_rn06_setup_and_status_carry_no_key(env):
    """RN-06 / T22: the setup, build and status answers hold no key value (checked by configured_api)."""
    _setup(env)
    _start_build(env)
    _setup(env)
    body = _status(env)

    assert isinstance(body["text_key_configured"], bool)


def test_t22_unknown_job_id_in_setup_never_breaks_the_answer(env):
    """T22: a stored build job the runner does not know (left by a closed process) is reported failed,
    not running, so the screen offers a retry."""
    from core.models import Job

    Job.objects.create(id=uuid.uuid4(), kind="build", status="running")

    body = _setup(env)

    assert body["job"] is not None
    assert body["job"]["status"] == "failed"
    assert body["database_ready"] is False


# ---------------------------------------------------------------- review additions: attempts, sharing, failures


def test_t22_rn28_setup_without_network_tries_the_listing_once_without_pausing(env):
    """RN-28 / T22: a poll of GET /api/setup with no network makes exactly one listing request and no pause;
    the next poll tries once again (a failure is not cached)."""
    env.use_source(_NoNetwork())

    _assert_unreachable(_setup(env))
    assert env.source.urls() == [LISTING_URL]
    assert env.sleep.calls == []

    _assert_unreachable(_setup(env))
    assert env.source.urls() == [LISTING_URL, LISTING_URL]
    assert env.sleep.calls == []


def test_t22_rn28_post_without_network_keeps_the_download_attempts(env):
    """RN-28 / T22: POST /api/setup/build keeps the downloader's attempts (DOWNLOAD_ATTEMPTS, with a pause
    between them) before it answers 502 `source_unreachable`."""
    from catalog import download

    env.use_source(_NoNetwork())

    response = _post_build(env)

    assert_error_envelope(response, SOURCE_UNREACHABLE_STATUS, CODE_SOURCE_UNREACHABLE)
    assert env.source.urls() == [LISTING_URL] * download.DOWNLOAD_ATTEMPTS
    assert len(env.sleep.calls) == download.DOWNLOAD_ATTEMPTS - 1
    assert _build_jobs() == []


def test_t22_rn28_setup_answers_when_readiness_cannot_be_read(env):
    """RN-28 / RN-40 / T22: when reading readiness raises OperationalError, GET /api/setup still answers 200:
    not ready, no job, and the settings list."""
    from tests.setup_api_helpers import readiness_failing

    env.api.configure(full_text_settings(key=""))

    with readiness_failing() as refused:
        body = _setup(env)

    assert refused, "Readiness was not read from the catalog tables."
    assert body["database_ready"] is False
    assert body["job"] is None
    assert ("LLM_API_KEY", "config_invalid") in {(item["setting"], item["code"]) for item in body["settings"]}


def test_t22_rn40_status_answers_when_readiness_cannot_be_read(env):
    """RN-40 / RN-01 / T22: when reading readiness raises OperationalError, GET /api/status still answers 200:
    not ready, no sources, and the settings list."""
    from tests.setup_api_helpers import readiness_failing

    env.api.configure(full_text_settings(key=""))

    with readiness_failing() as refused:
        body = _status(env)

    assert refused, "Readiness was not read from the catalog tables."
    assert body["database_ready"] is False
    assert body["sources"] == []
    assert ("LLM_API_KEY", "config_invalid") in {(item["setting"], item["code"]) for item in body["settings"]}


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(PermissionError(13, "fictional access denied"), id="permission"),
        pytest.param(FileNotFoundError(2, "fictional missing drive"), id="missing-drive"),
        pytest.param(OSError(5, "fictional input/output error"), id="io-error"),
    ],
)
def test_t22_rn28_unreadable_free_space_is_null_and_does_not_block_the_build(env, error):
    """RN-28 / T22: when the free space cannot be read, GET /api/setup answers 200 with free_space null, the
    sizes and the settings list, and POST /api/setup/build starts the build (202) instead of refusing."""
    env.disk.error = error

    body = _setup(env)

    assert body["free_space"] is None
    assert body["download_size"] == BULK_SIZE
    assert body["settings"] == []
    _start_build(env)
    assert _setup(env)["database_ready"] is True
