"""A locked database answers `database_busy` in the API (task T133).

Spec: RN-10 (failures become clear messages), RN-28 (the build and its causes).
Details: specs/plan.md, sections 6 (error envelope and codes) and 7 ("Concurrency":
`database is locked` maps to the error code `database_busy`).

Assumed API (the plan names the code and the rule, not the function):

    core.errors.CODE_DATABASE_BUSY = "database_busy"
    core.errors.DATABASE_BUSY_MESSAGE     a fixed message that is safe to show
    core.errors.database_busy_error(error) -> MappedError | None
        The MappedError(CODE_DATABASE_BUSY, DATABASE_BUSY_MESSAGE) of an
        OperationalError for a locked database (SQLite primary result code
        SQLITE_BUSY, extended codes included, or, with no SQLite code, the
        text "database is locked"); None for any other error.
        The single mapping: the API exception handler and the catalog build
        both go through it.

    Any view: an OperationalError for a locked database raised in a request
    answers HTTP 503 with the envelope code `database_busy` and the fixed
    message; the exception text never reaches the response. Any other
    OperationalError stays `internal` (500, fixed message).

Locks are simulated at the SQL level on this thread's connection; no real lock
is taken. Every card, model and value is fictional.
"""

import json
import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlencode

import pytest

from tests.catalog_build_helpers import (
    FakeDataSource,
    FakeSleep,
    database_locked_operational_error,
    failing_write,
)
from tests.cards_helpers import new_card
from tests.config_files import DEFAULT_PORT, full_text_settings
from tests.configured_api import assert_error_envelope, configured_api  # noqa: F401 (fixture)
from tests.job_helpers import envelope_error, inline_runner
from tests.setup_api_helpers import (
    BUILD_URL,
    SetupEnvironment,
    clear_listing_cache,
    mark_ready,
    own_origin,
)

BUSY_STATUS = 503
INTERNAL_STATUS = 500
CODE_DATABASE_BUSY = "database_busy"
CODE_INTERNAL = "internal"
USAGE_URL = "/api/usage"
JOB_TABLE = "core_job"
CARD_TABLE = "cards_card"
BACKEND = Path(__file__).resolve().parents[1]
PRODUCTION_PACKAGES = ("api", "cards", "catalog", "core", "generation", "providers", "validators", "cardfactory")

# Text that must never reach a response: the exception text, its class and the SQL.
DETAIL_SENTINEL = "fictional-lock-detail-7731"
LEAK_MARKERS = (
    "database is locked",
    DETAIL_SENTINEL,
    "OperationalError",
    "Traceback",
    "SELECT",
    "INSERT",
    CARD_TABLE,
    JOB_TABLE,
    "sqlite",
)


# ---------------------------------------------------------------- simulated errors


def _sqlite_error(message, code=None, name=None):
    """The OperationalError Django raises for a SQLite failure, with its sqlite3 cause."""
    from django.db import OperationalError

    cause = sqlite3.OperationalError(message)
    if code is not None:
        cause.sqlite_errorcode = code
        cause.sqlite_errorname = name
    error = OperationalError(message)
    error.__cause__ = cause
    return error


def _plain_error(message):
    """An OperationalError with no SQLite cause, as some wrappers raise it."""
    from django.db import OperationalError

    return OperationalError(message)


# Extended result codes share the primary code in their low byte (SQLite documentation).
SQLITE_BUSY_RECOVERY = sqlite3.SQLITE_BUSY | (1 << 8)
SQLITE_BUSY_SNAPSHOT = sqlite3.SQLITE_BUSY | (2 << 8)
SQLITE_BUSY_TIMEOUT = sqlite3.SQLITE_BUSY | (3 << 8)


def _locked_errors():
    return {
        "sqlite-busy": database_locked_operational_error(),
        "busy-recovery": _sqlite_error("database is locked", SQLITE_BUSY_RECOVERY, "SQLITE_BUSY_RECOVERY"),
        "busy-snapshot": _sqlite_error("database is locked", SQLITE_BUSY_SNAPSHOT, "SQLITE_BUSY_SNAPSHOT"),
        "busy-timeout": _sqlite_error("database is locked", SQLITE_BUSY_TIMEOUT, "SQLITE_BUSY_TIMEOUT"),
        "text-only": _plain_error("database is locked"),
        "text-only-upper-case": _plain_error("Database Is Locked"),
        "text-with-detail": _plain_error(f"database is locked ✦ {DETAIL_SENTINEL} ção 🜲"),
    }


LOCKED_IDS = list(_locked_errors())


def _other_errors():
    return {
        "no-such-table": _sqlite_error(f"no such table: {CARD_TABLE}", sqlite3.SQLITE_ERROR, "SQLITE_ERROR"),
        "disk-io": _sqlite_error("disk I/O error", sqlite3.SQLITE_IOERR, "SQLITE_IOERR"),
        "readonly": _sqlite_error(
            "attempt to write a readonly database", sqlite3.SQLITE_READONLY, "SQLITE_READONLY"
        ),
        "cannot-open": _sqlite_error("unable to open database file", sqlite3.SQLITE_CANTOPEN, "SQLITE_CANTOPEN"),
        "text-only-other": _plain_error(f"no such column: {DETAIL_SENTINEL}"),
        "empty-text": _plain_error(""),
        "odd-characters": _plain_error("✦ ção 🜲 \x00 <script>"),
        "huge-text": _plain_error("near SELECT: syntax error " + "x" * 100_000),
    }


OTHER_IDS = list(_other_errors())


@contextmanager
def statements_failing(table, error, kind="SELECT"):
    """Make every `kind` statement that names `table` raise `error` on this thread's connection.

    Works at the SQL level, so it does not depend on which selector or service issues it.
    Yields the list of refused statements.
    """
    from django.db import connection

    refused = []

    def wrapper(execute, sql, params, many, context):
        text = str(sql)
        if text.lstrip().upper().startswith(kind) and table in text.lower():
            refused.append(text)
            raise error
        return execute(sql, params, many, context)

    with connection.execute_wrapper(wrapper):
        yield refused


def _assert_no_leak(response):
    text = response.content.decode("utf-8")
    for marker in LEAK_MARKERS:
        assert marker.lower() not in text.lower(), f"The response quotes {marker!r}: {text[:500]}"


def _core_errors():
    from core import errors

    return errors


# ---------------------------------------------------------------- fixtures


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


@pytest.fixture
def ready_api(configured_api):
    """A configured API with a ready catalog, so the gated read endpoints answer."""
    configured_api.configure(full_text_settings())
    mark_ready()
    with inline_runner():
        yield configured_api


def _post_build(env):
    return env.api.request("POST", BUILD_URL, data={}, **own_origin(DEFAULT_PORT))


def _get_usage(api, card):
    return api.get(f"{USAGE_URL}?{urlencode({'card': card.pk})}")


# ---------------------------------------------------------------- the core mapping


def test_t133_rn10_core_names_the_code_and_a_fixed_message():
    """RN-10 / T133 (plan section 6): `core.errors` holds the code `database_busy` and a fixed,
    non-empty message that quotes no exception text."""
    errors = _core_errors()

    assert errors.CODE_DATABASE_BUSY == CODE_DATABASE_BUSY
    assert isinstance(errors.DATABASE_BUSY_MESSAGE, str) and errors.DATABASE_BUSY_MESSAGE.strip()
    assert "database is locked" not in errors.DATABASE_BUSY_MESSAGE.lower()
    assert "operationalerror" not in errors.DATABASE_BUSY_MESSAGE.lower()


@pytest.mark.parametrize("name", LOCKED_IDS)
def test_t133_rn10_core_maps_a_locked_database_to_database_busy(name):
    """RN-10 / T133 (plan section 7): an OperationalError for a locked database, by SQLite code
    (extended codes included) or by its text alone, maps to `database_busy` with the fixed message."""
    errors = _core_errors()

    mapped = errors.database_busy_error(_locked_errors()[name])

    assert isinstance(mapped, errors.MappedError)
    assert mapped.code == CODE_DATABASE_BUSY
    assert mapped.message == errors.DATABASE_BUSY_MESSAGE
    assert mapped.setting is None
    assert DETAIL_SENTINEL not in mapped.message


@pytest.mark.parametrize("name", OTHER_IDS)
def test_t133_rn10_core_does_not_map_other_operational_errors(name):
    """RN-10 / T133: any other OperationalError is not a busy database: the mapping returns None."""
    assert _core_errors().database_busy_error(_other_errors()[name]) is None


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(RuntimeError("database is locked"), id="runtime-error-with-the-text"),
        pytest.param(ValueError(""), id="value-error-empty"),
        pytest.param(OSError(5, "fictional input/output error"), id="os-error"),
    ],
)
def test_t133_rn10_core_maps_only_operational_errors(error):
    """RN-10 / T133: an exception that is not a database OperationalError is never `database_busy`,
    even when its text says the database is locked."""
    assert _core_errors().database_busy_error(error) is None


# ---------------------------------------------------------------- POST /api/setup/build


@pytest.mark.django_db
@pytest.mark.parametrize("name", LOCKED_IDS)
def test_t133_rn28_locked_database_on_setup_build_answers_database_busy(env, name):
    """RN-28 / RN-10 / T133: when storing the build job meets a locked database, POST /api/setup/build
    answers 503 `database_busy` in the envelope with the fixed message and no exception text."""
    with failing_write(JOB_TABLE, error=_locked_errors()[name]) as refused:
        response = _post_build(env)
    assert refused, "The request never stored a job."

    error = assert_error_envelope(response, BUSY_STATUS, CODE_DATABASE_BUSY)
    assert error["message"] == _core_errors().DATABASE_BUSY_MESSAGE
    assert error["setting"] is None
    assert error["fields"] is None
    _assert_no_leak(response)


@pytest.mark.django_db
@pytest.mark.parametrize("name", OTHER_IDS)
def test_t133_rn10_other_operational_error_on_setup_build_stays_internal(env, name):
    """RN-10 / T133: any other OperationalError on POST /api/setup/build answers 500 `internal` with
    the fixed message, never `database_busy`, and quotes nothing of the exception."""
    with failing_write(JOB_TABLE, error=_other_errors()[name]) as refused:
        response = _post_build(env)
    assert refused, "The request never stored a job."

    error = assert_error_envelope(response, INTERNAL_STATUS, CODE_INTERNAL)
    assert error["message"] == _core_errors().INTERNAL_MESSAGE
    _assert_no_leak(response)


# ---------------------------------------------------------------- a read endpoint: GET /api/usage


@pytest.mark.django_db
@pytest.mark.parametrize("name", LOCKED_IDS)
def test_t133_rn10_locked_database_on_a_read_answers_database_busy(ready_api, name):
    """RN-10 / T133: when a read meets a locked database, GET /api/usage answers 503 `database_busy`
    in the envelope with the fixed message and no exception text."""
    card = new_card()

    with statements_failing(CARD_TABLE, _locked_errors()[name]) as refused:
        response = _get_usage(ready_api, card)
    assert refused, "The request never read the card."

    error = assert_error_envelope(response, BUSY_STATUS, CODE_DATABASE_BUSY)
    assert error["message"] == _core_errors().DATABASE_BUSY_MESSAGE
    assert error["setting"] is None
    assert error["fields"] is None
    _assert_no_leak(response)


@pytest.mark.django_db
@pytest.mark.parametrize("name", OTHER_IDS)
def test_t133_rn10_other_operational_error_on_a_read_stays_internal(ready_api, name):
    """RN-10 / T133: any other OperationalError on GET /api/usage answers 500 `internal` with the
    fixed message, never `database_busy`, and quotes nothing of the exception."""
    card = new_card()

    with statements_failing(CARD_TABLE, _other_errors()[name]) as refused:
        response = _get_usage(ready_api, card)
    assert refused, "The request never read the card."

    error = assert_error_envelope(response, INTERNAL_STATUS, CODE_INTERNAL)
    assert error["message"] == _core_errors().INTERNAL_MESSAGE
    _assert_no_leak(response)


@pytest.mark.django_db
def test_t133_rn10_read_answers_again_once_the_lock_is_gone(ready_api):
    """RN-10 / T133: a busy answer leaves nothing behind: the same read answers 200 once the lock ends."""
    card = new_card()

    with statements_failing(CARD_TABLE, database_locked_operational_error()):
        assert_error_envelope(_get_usage(ready_api, card), BUSY_STATUS, CODE_DATABASE_BUSY)

    response = _get_usage(ready_api, card)
    assert response.status_code == 200, response.content[:500]
    assert json.loads(response.content.decode("utf-8"))["card"] == str(card.pk)


# ---------------------------------------------------------------- one mapping, shared with the build


@contextmanager
def busy_mapping_spied(monkeypatch):
    """Replace `core.errors.database_busy_error` everywhere it is bound, recording each call.

    Covers both `from core import errors` and `from core.errors import database_busy_error`.
    """
    errors = _core_errors()
    original = errors.database_busy_error
    calls = []

    def spy(error):
        calls.append(error)
        return original(error)

    for module in list(sys.modules.values()):
        name = getattr(module, "__name__", "") or ""
        if name.split(".")[0] not in PRODUCTION_PACKAGES:
            continue
        for attribute, value in list(vars(module).items()):
            if value is original:
                monkeypatch.setattr(module, attribute, spy)
    yield calls


@pytest.mark.django_db(transaction=True)
def test_t133_rn28_build_maps_a_locked_database_through_the_core_mapping(monkeypatch, tmp_path):
    """RN-28 / RN-03 / T133 (plan section 7): the build maps "database is locked" during the import
    through `core.errors.database_busy_error`, and the job stores its code and fixed message."""
    from catalog import build

    home = tmp_path / "home"
    (home / "data").mkdir(parents=True)
    monkeypatch.setenv("CARDFACTORY_HOME", str(home))
    locked = database_locked_operational_error()

    with busy_mapping_spied(monkeypatch) as calls, inline_runner():
        with failing_write("catalog_oraclecard", error=locked) as refused:
            job = build.start_build(transport=FakeDataSource(), sleep=FakeSleep())
        from core.jobs import get_job

        stored = get_job(job.id)
    assert refused, "The build never wrote a card."

    assert locked in calls, "The build did not map the locked database through the core mapping."
    assert stored.status == "failed"
    error = envelope_error(stored.error)
    assert error["code"] == CODE_DATABASE_BUSY
    assert error["message"] == _core_errors().DATABASE_BUSY_MESSAGE


@pytest.mark.django_db
def test_t133_rn10_api_maps_a_locked_database_through_the_core_mapping(ready_api, monkeypatch):
    """RN-10 / T133: the API answer for a locked database comes from the same core mapping."""
    card = new_card()
    locked = database_locked_operational_error()

    with busy_mapping_spied(monkeypatch) as calls:
        with statements_failing(CARD_TABLE, locked):
            response = _get_usage(ready_api, card)

    assert locked in calls, "The API did not map the locked database through the core mapping."
    assert_error_envelope(response, BUSY_STATUS, CODE_DATABASE_BUSY)


def _production_sources():
    for package in PRODUCTION_PACKAGES:
        folder = BACKEND / package
        if folder.is_dir():
            yield from (path for path in folder.rglob("*.py") if "migrations" not in path.parts)


def test_t133_rn10_the_locked_database_rule_lives_only_in_core():
    """RN-10 / T133 (plan section 7): the "database is locked" rule and the `database_busy` code are
    written once, in core; no other production module keeps its own copy."""
    owners = {}
    for path in _production_sources():
        text = path.read_text(encoding="utf-8")
        for literal in ('"database is locked"', "'database is locked'", '"database_busy"', "'database_busy'"):
            if literal in text:
                owners.setdefault(literal.strip("'\""), set()).add(path.relative_to(BACKEND).as_posix())

    assert owners.get("database is locked"), "No production module holds the locked-database rule."
    assert owners.get("database_busy"), "No production module holds the database_busy code."
    for literal, paths in owners.items():
        assert all(path.startswith("core/") for path in paths), (literal, sorted(paths))
        assert len(paths) == 1, (literal, sorted(paths))
