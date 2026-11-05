"""Smoke tests for the backend project skeleton (task T1, spec RN-29).

Each check evaluates the settings in a fresh interpreter (see settings_probe),
with CARDFACTORY_HOME pointing at a temporary folder so the repository data/
folder and .env are never used.
"""

from pathlib import Path

import pytest

from tests.settings_probe import BACKEND_DIR, REPOSITORY_ROOT, run_probe

EXPECTED_APPS = ("core", "catalog", "providers", "validators", "generation", "cards", "api")

SETTINGS_PROBE = """
import json
import django
from django.conf import settings
django.setup()
print(json.dumps({
    "debug": settings.DEBUG,
    "allowed_hosts": list(settings.ALLOWED_HOSTS),
    "database_engine": settings.DATABASES["default"]["ENGINE"],
    "database_name": str(settings.DATABASES["default"]["NAME"]),
}))
"""

SQLITE_PROBE = """
import json
import django
django.setup()
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("PRAGMA journal_mode")
    journal_mode = cursor.fetchone()[0]
    cursor.execute("PRAGMA busy_timeout")
    busy_timeout = cursor.fetchone()[0]
print(json.dumps({"journal_mode": journal_mode, "busy_timeout": busy_timeout}))
"""

TRANSACTION_PROBE = """
import json
import sqlite3
import django
django.setup()
from django.conf import settings
from django.db import connection, transaction

database_name = settings.DATABASES["default"]["NAME"]
connection.ensure_connection()


def other_writer_blocked():
    other = sqlite3.connect(database_name, timeout=0, isolation_level=None)
    try:
        other.execute("BEGIN IMMEDIATE")
    except sqlite3.OperationalError:
        return True
    else:
        other.execute("ROLLBACK")
        return False
    finally:
        other.close()


outside = other_writer_blocked()
with transaction.atomic():
    inside = other_writer_blocked()
print(json.dumps({
    "transaction_mode": settings.DATABASES["default"].get("OPTIONS", {}).get("transaction_mode"),
    "blocked_outside_atomic": outside,
    "blocked_inside_atomic": inside,
}))
"""

APPS_PROBE = """
import json
import django
django.setup()
from django.apps import apps
print(json.dumps({name: apps.is_installed(name) for name in %r}))
""" % (EXPECTED_APPS,)

PATHS_PROBE = """
import json
from core import paths
print(json.dumps({
    "app_home": str(paths.app_home()),
    "data_dir": str(paths.data_dir()),
}))
"""


def _same_path(left, right):
    return Path(left).resolve() == Path(right).resolve()


@pytest.fixture
def app_home(tmp_path):
    """A temporary application home with its data folder, outside the repository."""
    home = tmp_path / "home"
    (home / "data").mkdir(parents=True)
    return home


@pytest.fixture
def workdir(tmp_path):
    """A neutral working directory for probes, outside the repository."""
    path = tmp_path / "cwd"
    path.mkdir()
    return path


@pytest.fixture
def probe(workdir):
    """Run a probe from a neutral working directory, so nothing depends on the cwd."""

    def _run(code, **env):
        overrides = {
            "PYTHONPATH": str(BACKEND_DIR),
            "DJANGO_SETTINGS_MODULE": "cardfactory.settings",
        }
        overrides.update(env)
        return run_probe(code, overrides, cwd=workdir)

    return _run


# Allowed hosts


@pytest.mark.parametrize("debug_value", [None, "1"])
def test_rn29_allowed_hosts_limited_to_local_machine(probe, app_home, debug_value):
    """RN-29 / T1: ALLOWED_HOSTS is exactly 127.0.0.1 and localhost, with or without debug."""
    result = probe(
        SETTINGS_PROBE,
        CARDFACTORY_HOME=str(app_home),
        CARDFACTORY_DEBUG=debug_value,
    )

    assert sorted(result["allowed_hosts"]) == ["127.0.0.1", "localhost"]


# DEBUG


def test_rn29_debug_off_when_cardfactory_debug_not_set(probe, app_home):
    """RN-29 / T1: DEBUG is off when CARDFACTORY_DEBUG is absent."""
    result = probe(SETTINGS_PROBE, CARDFACTORY_HOME=str(app_home), CARDFACTORY_DEBUG=None)

    assert result["debug"] is False


def test_rn29_debug_on_when_cardfactory_debug_is_1(probe, app_home):
    """RN-29 / T1: DEBUG is on only when CARDFACTORY_DEBUG=1."""
    result = probe(SETTINGS_PROBE, CARDFACTORY_HOME=str(app_home), CARDFACTORY_DEBUG="1")

    assert result["debug"] is True


@pytest.mark.parametrize("value", [" 1", "1 ", "  1  ", "\t1\n"])
def test_t1_debug_on_when_value_is_1_after_stripping_whitespace(probe, app_home, value):
    """RN-29 / T1: CARDFACTORY_DEBUG is compared after stripping surrounding whitespace."""
    result = probe(SETTINGS_PROBE, CARDFACTORY_HOME=str(app_home), CARDFACTORY_DEBUG=value)

    assert result["debug"] is True


@pytest.mark.parametrize("value", ["   ", " 0 ", " true ", "1 1", "01", "1.0", "\t\n"])
def test_t1_debug_off_when_stripped_value_is_not_1(probe, app_home, value):
    """RN-29 / T1: after stripping whitespace, any value other than "1" leaves DEBUG off."""
    result = probe(SETTINGS_PROBE, CARDFACTORY_HOME=str(app_home), CARDFACTORY_DEBUG=value)

    assert result["debug"] is False


@pytest.mark.parametrize("value", ["", "0", "true", "True", "yes", "on", "2", "debug"])
def test_rn29_debug_off_for_any_value_other_than_1(probe, app_home, value):
    """RN-29 / T1: any CARDFACTORY_DEBUG value other than "1" leaves DEBUG off."""
    result = probe(SETTINGS_PROBE, CARDFACTORY_HOME=str(app_home), CARDFACTORY_DEBUG=value)

    assert result["debug"] is False


# Application home and database path


def test_t1_paths_use_cardfactory_home(probe, app_home):
    """RN-29 / T1 (plan section 7): core.paths resolves the home from CARDFACTORY_HOME."""
    result = probe(PATHS_PROBE, CARDFACTORY_HOME=str(app_home))

    assert _same_path(result["app_home"], app_home)
    assert _same_path(result["data_dir"], app_home / "data")


def test_t1_paths_default_to_repository_root(probe):
    """RN-29 / T1 (plan section 7): without CARDFACTORY_HOME the home is the repository root, not the cwd."""
    result = probe(PATHS_PROBE, CARDFACTORY_HOME=None)

    assert _same_path(result["app_home"], REPOSITORY_ROOT)
    assert _same_path(result["data_dir"], REPOSITORY_ROOT / "data")


@pytest.mark.parametrize("value", ["", "   ", "\t", " \t\n "])
def test_t1_empty_or_blank_home_is_treated_as_unset(probe, value):
    """RN-29 / T1: an empty or whitespace-only CARDFACTORY_HOME falls back to the repository root."""
    result = probe(PATHS_PROBE, CARDFACTORY_HOME=value)

    assert _same_path(result["app_home"], REPOSITORY_ROOT)
    assert _same_path(result["data_dir"], REPOSITORY_ROOT / "data")


@pytest.mark.parametrize("relative", ["relhome", "./relhome", "nested/home"])
def test_t1_relative_home_resolves_against_cwd(probe, workdir, relative):
    """RN-29 / T1: a relative CARDFACTORY_HOME becomes an absolute path under the current directory."""
    result = probe(PATHS_PROBE, CARDFACTORY_HOME=relative)

    assert Path(result["app_home"]).is_absolute()
    assert Path(result["data_dir"]).is_absolute()
    assert _same_path(result["app_home"], workdir / relative)
    assert _same_path(result["data_dir"], workdir / relative / "data")


@pytest.mark.parametrize("padding", [("  ", "  "), ("\t", "\n"), (" ", "")])
def test_t1_absolute_home_is_stripped_of_surrounding_whitespace(probe, app_home, padding):
    """RN-29 / T1: a non-blank CARDFACTORY_HOME is used without its surrounding whitespace."""
    before, after = padding

    result = probe(PATHS_PROBE, CARDFACTORY_HOME=f"{before}{app_home}{after}")

    assert result["app_home"] == result["app_home"].strip()
    assert _same_path(result["app_home"], app_home)
    assert _same_path(result["data_dir"], app_home / "data")


@pytest.mark.parametrize("value", [" relhome ", "\trelhome\n", "  ./relhome"])
def test_t1_relative_home_is_stripped_before_resolving(probe, workdir, value):
    """RN-29 / T1: surrounding whitespace is removed before a relative home is resolved."""
    result = probe(PATHS_PROBE, CARDFACTORY_HOME=value)

    assert result["app_home"] == result["app_home"].strip()
    assert Path(result["app_home"]).is_absolute()
    assert _same_path(result["app_home"], workdir / "relhome")


def test_t1_padded_home_gives_database_path_without_whitespace(probe, app_home):
    """RN-29 / T1: the database NAME uses the stripped CARDFACTORY_HOME."""
    result = probe(SETTINGS_PROBE, CARDFACTORY_HOME=f"  {app_home}  ")

    assert _same_path(result["database_name"], app_home / "data" / "cardfactory.sqlite3")


def test_t1_relative_home_resolves_against_cwd_at_call_time(probe, workdir):
    """RN-29 / T1: a relative CARDFACTORY_HOME follows the working directory at the time of each call."""
    other = workdir / "other"
    other.mkdir()
    code = """
import json, os
from core import paths
first = str(paths.app_home())
os.chdir(%r)
second = str(paths.app_home())
print(json.dumps({"first": first, "second": second}))
""" % (str(other),)

    result = probe(code, CARDFACTORY_HOME="relhome")

    assert _same_path(result["first"], workdir / "relhome")
    assert Path(result["second"]).is_absolute()
    assert _same_path(result["second"], other / "relhome")


def test_t1_relative_home_gives_absolute_database_path(probe, workdir):
    """RN-29 / T1: with a relative CARDFACTORY_HOME the database NAME is absolute, under the cwd."""
    (workdir / "relhome" / "data").mkdir(parents=True)

    result = probe(SETTINGS_PROBE, CARDFACTORY_HOME="relhome")

    assert Path(result["database_name"]).is_absolute()
    assert _same_path(result["database_name"], workdir / "relhome" / "data" / "cardfactory.sqlite3")


def test_t1_database_is_sqlite_file_under_home(probe, app_home):
    """RN-29 / T1 (plan section 7): the database is <home>/data/cardfactory.sqlite3."""
    result = probe(SETTINGS_PROBE, CARDFACTORY_HOME=str(app_home))

    assert result["database_engine"] == "django.db.backends.sqlite3"
    assert _same_path(result["database_name"], app_home / "data" / "cardfactory.sqlite3")


def test_t1_database_path_handles_spaces_and_non_ascii_home(probe, tmp_path):
    """RN-29 / T1 (plan section 7): a home with spaces and accented characters is used as given."""
    home = tmp_path / "Área de Trabalho" / "Card Factory ção"
    (home / "data").mkdir(parents=True)

    result = probe(SETTINGS_PROBE, CARDFACTORY_HOME=str(home))

    assert _same_path(result["database_name"], home / "data" / "cardfactory.sqlite3")


# SQLite concurrency settings


def test_t1_sqlite_connection_uses_wal_mode(probe, app_home):
    """RN-29 / T1 (plan section 7): the SQLite connection runs in WAL mode."""
    result = probe(SQLITE_PROBE, CARDFACTORY_HOME=str(app_home))

    assert str(result["journal_mode"]).lower() == "wal"
    assert (app_home / "data" / "cardfactory.sqlite3").is_file()


def test_t1_sqlite_connection_has_busy_timeout(probe, app_home):
    """RN-29 / T1 (plan section 7): the SQLite connection has a positive busy timeout."""
    result = probe(SQLITE_PROBE, CARDFACTORY_HOME=str(app_home))

    assert int(result["busy_timeout"]) > 0


def test_t1_sqlite_wal_mode_with_non_ascii_home(probe, tmp_path):
    """RN-29 / T1 (plan section 7): WAL mode also holds when the home path has accented characters."""
    home = tmp_path / "Usuário Ñandú"
    (home / "data").mkdir(parents=True)

    result = probe(SQLITE_PROBE, CARDFACTORY_HOME=str(home))

    assert str(result["journal_mode"]).lower() == "wal"
    assert (home / "data" / "cardfactory.sqlite3").is_file()


def test_t1_sqlite_transaction_mode_is_immediate(probe, app_home):
    """RN-29 / T1 (plan section 7): the database OPTIONS set transaction_mode IMMEDIATE."""
    result = probe(TRANSACTION_PROBE, CARDFACTORY_HOME=str(app_home))

    assert result["transaction_mode"] == "IMMEDIATE"


def test_t1_atomic_block_takes_the_write_lock_on_entry(probe, app_home):
    """RN-29 / T1 (plan section 7): transaction.atomic() begins IMMEDIATE, holding the write lock at once."""
    result = probe(TRANSACTION_PROBE, CARDFACTORY_HOME=str(app_home))

    assert result["blocked_outside_atomic"] is False
    assert result["blocked_inside_atomic"] is True


# Installed apps


def test_t1_project_apps_are_installed(probe, app_home):
    """RN-29 / T1 (plan section 3): the seven project apps are installed."""
    result = probe(APPS_PROBE, CARDFACTORY_HOME=str(app_home))

    missing = [name for name, installed in result.items() if not installed]
    assert missing == []
