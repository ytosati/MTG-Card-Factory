"""Database upgrade service `core.startup.upgrade_database` (task T72, spec RN-42, CA-48).

Contract under test (plan sections 7 and 9.5, launcher step 6):

- `core.startup.upgrade_database()` takes no arguments and returns None. It
  works on the configured `default` database (`settings.DATABASES`, the file
  `data/cardfactory.sqlite3` under the application home).
- When migrations are pending, it first copies the database to
  `data/backups/cardfactory.sqlite3` with the SQLite backup API of the standard
  library, replacing any previous backup, and then applies them.
- When nothing is pending, it makes no backup and leaves the file unchanged.
- When the database file does not exist, it makes no backup and runs the
  migrations, which create it.
- When the database records a migration the application does not have (a
  database from a newer version), it raises `StartupError` and changes nothing.
- When the backup cannot be written, it raises `StartupError` before
  migrating, so the database stays as it was.
- When a migration fails, it closes the connections, restores the database
  from the backup and raises `StartupError`, so the launcher shows the problem
  and the fix in a message box.
- It never writes to stdout or stderr, and it works when `sys.stdout` and
  `sys.stderr` are None (`pythonw.exe` has neither).

The fixture database of an older version is a real SQLite file in a temporary
home: every migration applied, then `auth` rolled back by one migration, with a
fictional group stored in a table that both states share. The application
models hold no data yet; the CA-48 check with cards, versions and images is
repeated in T84.
"""

import sqlite3
import sys

import pytest
from django.core.management import call_command
from django.db import connections

DATABASE_FILE = "cardfactory.sqlite3"
# The fixture is one `auth` migration behind the application.
OLD_AUTH_TARGET = "0011_update_proxy_permissions"
PENDING_AUTH_MIGRATION = "0012_alter_user_first_name_max_length"
FICTIONAL_GROUP = "Guild of the Ninth Lantern"
# A migration no version of the application has: the database comes from a newer one.
FUTURE_MIGRATION = "9999_fictional_future_change"


class UpgradeHome:
    """Paths of the temporary home used by one test."""

    def __init__(self, home):
        self.home = home
        self.data = home / "data"
        self.database = self.data / DATABASE_FILE
        self.backups = self.data / "backups"
        self.backup = self.backups / DATABASE_FILE


@pytest.fixture
def upgrade_home(tmp_path, monkeypatch, django_db_blocker):
    """A temporary home whose `data/cardfactory.sqlite3` is the configured default database."""
    home = tmp_path / "home"
    (home / "data").mkdir(parents=True)
    paths = UpgradeHome(home)
    monkeypatch.setenv("CARDFACTORY_HOME", str(home))

    # A new connection object: Django ignores close() on pytest-django's in-memory
    # test database, so renaming the open connection would keep using that database.
    original = connections["default"]
    wrapper = original.__class__({**original.settings_dict, "NAME": str(paths.database)}, alias="default")
    connections["default"] = wrapper
    try:
        with django_db_blocker.unblock():
            yield paths
    finally:
        wrapper.close()
        connections["default"] = original


def _upgrade_database():
    from core.startup import upgrade_database

    return upgrade_database


def _startup_error():
    from core.startup import StartupError

    return StartupError


def _query(path, sql, params=()):
    """Rows read with a plain sqlite3 connection, outside Django."""
    connection = sqlite3.connect(path)
    try:
        return connection.execute(sql, params).fetchall()
    finally:
        connection.close()


def _execute(path, sql, params=()):
    connection = sqlite3.connect(path)
    try:
        with connection:
            connection.execute(sql, params)
    finally:
        connection.close()


def _group_names(path):
    return [row[0] for row in _query(path, "SELECT name FROM auth_group ORDER BY name")]


def _applied(path, app, name):
    rows = _query(path, "SELECT 1 FROM django_migrations WHERE app = ? AND name = ?", (app, name))
    return bool(rows)


def _migrate_quietly(*args):
    call_command("migrate", *args, verbosity=0, interactive=False)


def _build_old_database(paths):
    """An older version's database: one migration behind, holding a fictional group."""
    _migrate_quietly()
    _migrate_quietly("auth", OLD_AUTH_TARGET)
    connections.close_all()
    _execute(paths.database, "INSERT INTO auth_group (name) VALUES (?)", (FICTIONAL_GROUP,))
    assert not _applied(paths.database, "auth", PENDING_AUTH_MIGRATION)
    assert _group_names(paths.database) == [FICTIONAL_GROUP]


def _build_current_database(paths):
    _migrate_quietly()
    connections.close_all()
    _execute(paths.database, "INSERT INTO auth_group (name) VALUES (?)", (FICTIONAL_GROUP,))


def _build_newer_database(paths):
    """A newer version's database: it records a migration this code does not have."""
    _build_current_database(paths)
    _execute(
        paths.database,
        "INSERT INTO django_migrations (app, name, applied) VALUES (?, ?, ?)",
        ("auth", FUTURE_MIGRATION, "2031-01-01 00:00:00"),
    )


def _database_bytes(paths):
    connections.close_all()
    return paths.database.read_bytes()


# Upgrade from an older version


def test_upgrade_applies_pending_migrations_and_keeps_records_rn42_ca48(upgrade_home):
    """RN-42, CA-48: an older database is upgraded and keeps every stored record."""
    _build_old_database(upgrade_home)

    result = _upgrade_database()()

    connections.close_all()
    assert result is None
    assert _applied(upgrade_home.database, "auth", PENDING_AUTH_MIGRATION)
    assert _group_names(upgrade_home.database) == [FICTIONAL_GROUP]


def test_upgrade_writes_a_backup_of_the_database_before_migrating_rn42(upgrade_home):
    """RN-42: the backup is a readable SQLite copy of the database as it was before the upgrade."""
    _build_old_database(upgrade_home)

    _upgrade_database()()

    connections.close_all()
    assert upgrade_home.backup.is_file()
    assert _group_names(upgrade_home.backup) == [FICTIONAL_GROUP]
    assert not _applied(upgrade_home.backup, "auth", PENDING_AUTH_MIGRATION)


def test_upgrade_replaces_the_previous_backup_rn42(upgrade_home):
    """RN-42: only the last backup is kept; an older one is replaced."""
    _build_old_database(upgrade_home)
    upgrade_home.backups.mkdir()
    upgrade_home.backup.write_bytes(b"not a database: a stale backup \x00\xff")

    _upgrade_database()()

    connections.close_all()
    assert _group_names(upgrade_home.backup) == [FICTIONAL_GROUP]
    assert sorted(path.name for path in upgrade_home.backups.iterdir()) == [DATABASE_FILE]


def test_no_backup_when_nothing_is_pending_rn42(upgrade_home):
    """RN-42: the backup is taken only when migrations are pending; the file stays unchanged."""
    _build_current_database(upgrade_home)
    before = _database_bytes(upgrade_home)

    _upgrade_database()()

    assert not upgrade_home.backup.exists()
    assert _database_bytes(upgrade_home) == before


def test_missing_database_is_created_without_a_backup_rn42(upgrade_home):
    """RN-42: with no database file there is nothing to back up; the migrations create it."""
    assert not upgrade_home.database.exists()

    _upgrade_database()()

    connections.close_all()
    assert upgrade_home.database.is_file()
    assert _applied(upgrade_home.database, "auth", PENDING_AUTH_MIGRATION)
    assert not upgrade_home.backup.exists()


# Database from a newer version


def test_newer_database_is_refused_with_its_data_unchanged_rn42_ca48(upgrade_home):
    """RN-42, CA-48: a database with a migration the application lacks is refused, unchanged."""
    _build_newer_database(upgrade_home)
    before = _database_bytes(upgrade_home)

    with pytest.raises(_startup_error()) as raised:
        _upgrade_database()()

    assert raised.value.problem.strip()
    assert raised.value.fix.strip()
    assert _database_bytes(upgrade_home) == before
    assert _group_names(upgrade_home.database) == [FICTIONAL_GROUP]


def test_newer_database_is_refused_even_when_migrations_are_also_pending_rn42(upgrade_home):
    """RN-42: an unknown migration wins over pending ones; nothing is migrated."""
    _build_old_database(upgrade_home)
    _execute(
        upgrade_home.database,
        "INSERT INTO django_migrations (app, name, applied) VALUES (?, ?, ?)",
        ("auth", FUTURE_MIGRATION, "2031-01-01 00:00:00"),
    )
    before = _database_bytes(upgrade_home)

    with pytest.raises(_startup_error()):
        _upgrade_database()()

    assert _database_bytes(upgrade_home) == before
    assert not _applied(upgrade_home.database, "auth", PENDING_AUTH_MIGRATION)


# Failures


def test_failed_migration_restores_the_database_from_the_backup_rn42(upgrade_home, monkeypatch):
    """RN-42: a migration that fails after changing the database leaves the data as it was."""
    from django.db.migrations.executor import MigrationExecutor

    _build_old_database(upgrade_home)
    original_migrate = MigrationExecutor.migrate

    def migrate_then_fail(self, *args, **kwargs):
        original_migrate(self, *args, **kwargs)
        with self.connection.cursor() as cursor:
            cursor.execute("DELETE FROM auth_group")
        raise RuntimeError("fictional migration failure")

    monkeypatch.setattr(MigrationExecutor, "migrate", migrate_then_fail)

    with pytest.raises(_startup_error()) as raised:
        _upgrade_database()()

    connections.close_all()
    assert raised.value.problem.strip()
    assert raised.value.fix.strip()
    assert "fictional migration failure" not in f"{raised.value.problem}\n{raised.value.fix}"
    assert _group_names(upgrade_home.database) == [FICTIONAL_GROUP]
    assert not _applied(upgrade_home.database, "auth", PENDING_AUTH_MIGRATION)


def test_unwritable_backup_stops_before_migrating_rn42(upgrade_home):
    """RN-42: when the backup cannot be written, nothing is migrated."""
    _build_old_database(upgrade_home)
    # A file where the backups folder should be: the backup cannot be created on any system.
    upgrade_home.backups.write_bytes(b"in the way")
    before = _database_bytes(upgrade_home)

    with pytest.raises(_startup_error()) as raised:
        _upgrade_database()()

    assert raised.value.problem.strip()
    assert raised.value.fix.strip()
    assert _database_bytes(upgrade_home) == before
    assert not _applied(upgrade_home.database, "auth", PENDING_AUTH_MIGRATION)


# Standard streams


def test_upgrade_works_without_standard_streams_rn42(upgrade_home):
    """RN-42, plan section 9.5: under pythonw.exe sys.stdout and sys.stderr are None."""
    _build_old_database(upgrade_home)
    upgrade_database = _upgrade_database()
    saved = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = None
    try:
        upgrade_database()
    finally:
        sys.stdout, sys.stderr = saved

    connections.close_all()
    assert _applied(upgrade_home.database, "auth", PENDING_AUTH_MIGRATION)
    assert _group_names(upgrade_home.database) == [FICTIONAL_GROUP]


def test_upgrade_writes_nothing_to_stdout_or_stderr_rn42(upgrade_home, capfd):
    """RN-42, plan section 9.5: the upgrade never writes to the standard streams."""
    _build_old_database(upgrade_home)
    capfd.readouterr()

    _upgrade_database()()

    captured = capfd.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_refusal_writes_nothing_to_stdout_or_stderr_rn42(upgrade_home, capfd):
    """RN-42: the refusal of a newer database is only the StartupError, never console output."""
    _build_newer_database(upgrade_home)
    capfd.readouterr()

    with pytest.raises(_startup_error()):
        _upgrade_database()()

    captured = capfd.readouterr()
    assert captured.out == ""
    assert captured.err == ""


# Orphan jobs (task T13, spec RN-03, RN-10; plan section 7): the startup step
# also fails every job stored as queued or running, after migrating.


def _store_jobs():
    """One job in each state, stored through the ORM on the upgrade database."""
    from core.models import Job

    jobs = {status: Job.objects.create(kind="build", status=status).pk for status in ("queued", "running", "done")}
    connections.close_all()
    return jobs


def _job_states(ids):
    from core.models import Job

    rows = {row.pk: row for row in Job.objects.filter(pk__in=ids.values())}
    connections.close_all()
    return {status: (rows[pk].status, rows[pk].error) for status, pk in ids.items()}


def _assert_orphans_failed(states):
    for status in ("queued", "running"):
        state, error = states[status]
        assert state == "failed", status
        assert isinstance(error, dict) and set(error) == {"error"}, error
        assert set(error["error"]) == {"code", "message", "setting", "fields"}
        assert error["error"]["message"].strip()
    assert states["done"] == ("done", None)


def test_t13_rn03_startup_fails_orphan_jobs_when_nothing_is_pending(upgrade_home):
    """RN-03 / RN-10 / T13: on a current database, the startup step fails queued and running jobs
    left by an earlier process and leaves ended ones alone."""
    _build_current_database(upgrade_home)
    ids = _store_jobs()

    _upgrade_database()()

    _assert_orphans_failed(_job_states(ids))


def test_t13_rn03_startup_fails_orphan_jobs_after_migrating(upgrade_home):
    """RN-03 / RN-10 / T13: on an older database, the orphans are failed once the migrations ran."""
    _build_old_database(upgrade_home)
    ids = _store_jobs()

    _upgrade_database()()

    assert _applied(upgrade_home.database, "auth", PENDING_AUTH_MIGRATION)
    _assert_orphans_failed(_job_states(ids))


def test_t13_rn42_refused_newer_database_keeps_its_jobs_unchanged(upgrade_home):
    """RN-42 / T13: a newer database is refused with its data unchanged, jobs included."""
    _build_current_database(upgrade_home)
    ids = _store_jobs()
    _execute(
        upgrade_home.database,
        "INSERT INTO django_migrations (app, name, applied) VALUES (?, ?, ?)",
        ("auth", FUTURE_MIGRATION, "2031-01-01 00:00:00"),
    )
    before = _database_bytes(upgrade_home)

    with pytest.raises(_startup_error()):
        _upgrade_database()()

    assert _database_bytes(upgrade_home) == before
    states = _job_states(ids)
    assert states["running"][0] == "running"
    assert states["queued"][0] == "queued"
