"""Startup errors, the database upgrade and the local server entry point used by the launcher.
Details: specs/plan.md, sections 7 and 9.5.
"""

import io
import socket
import sqlite3
import sys
from pathlib import Path

# Re-exported for the launcher, which imports only core.config and core.startup.
from core.watchdog import Watchdog, install  # noqa: F401

# The server listens only on the local machine; no setting changes it (see spec RN-29).
HOST = "127.0.0.1"
# How often the serving loop checks the stop event, in seconds.
STOP_CHECK_INTERVAL = 0.5


class StartupError(Exception):
    """A startup failure the person can fix: what went wrong and what to do (see spec RN-40)."""

    def __init__(self, problem, fix):
        super().__init__(problem, fix)
        self.problem = problem
        self.fix = fix


def upgrade_database():
    """Back up and migrate the default database when migrations are pending (see spec RN-42).

    Refuses a database from a newer version, and restores the backup when a migration fails.
    Then fails the jobs an earlier process left queued or running (see spec RN-03).
    """
    # Imported here: the launcher imports this module before the settings load.
    from django.core.management import call_command
    from django.db import connections
    from django.db.migrations.executor import MigrationExecutor

    from core.paths import data_dir

    database = Path(connections["default"].settings_dict["NAME"])
    existed = database.is_file()
    try:
        executor = MigrationExecutor(connections["default"])
        if existed and _unknown_migrations(executor.loader):
            raise _newer_database_error()
        if not executor.migration_plan(executor.loader.graph.leaf_nodes()):
            _fail_orphan_jobs()
            return
    finally:
        connections.close_all()

    backup = data_dir() / "backups" / database.name
    if existed:
        _write_backup(database, backup)
    try:
        # Quiet buffers, not the standard streams: under pythonw.exe they are None.
        call_command(
            "migrate", verbosity=0, interactive=False, stdout=io.StringIO(), stderr=io.StringIO()
        )
    except Exception as error:
        connections.close_all()
        _undo_failed_migration(database, backup, existed)
        raise _failed_migration_error() from error
    finally:
        connections.close_all()
    try:
        _fail_orphan_jobs()
    finally:
        connections.close_all()


def _fail_orphan_jobs():
    # Imported here: the models load only once Django is set up.
    from core.jobs import fail_orphan_jobs

    fail_orphan_jobs()


def _unknown_migrations(loader):
    """Migrations recorded in the database that this version of the code does not have."""
    known = set(loader.disk_migrations)
    for migration in loader.disk_migrations.values():
        known.update(migration.replaces)
    return set(loader.applied_migrations) - known


def _write_backup(database, backup):
    """Copy `database` to `backup` with the SQLite backup API, replacing any previous backup."""
    try:
        backup.parent.mkdir(exist_ok=True)
        # Removed first: an old backup that is not a valid database would make the copy fail.
        backup.unlink(missing_ok=True)
        _sqlite_copy(database, backup)
    except (OSError, sqlite3.Error) as error:
        raise StartupError(
            "Card Factory could not save a backup of its data before upgrading it, "
            "so the data was not changed.",
            "Make sure the data\\backups folder can be written (free some disk space, or "
            "remove a file named backups from the data folder), then start Card Factory again.",
        ) from error


def _undo_failed_migration(database, backup, existed):
    """Put the database back as it was before the failed migration."""
    try:
        if existed:
            _sqlite_copy(backup, database)
        else:
            # There was no data: the partly created file goes, so the next start begins anew.
            for suffix in ("", "-wal", "-shm", "-journal"):
                Path(f"{database}{suffix}").unlink(missing_ok=True)
    except (OSError, sqlite3.Error) as error:
        if existed:
            fix = (
                "Copy data\\backups\\cardfactory.sqlite3 over data\\cardfactory.sqlite3, "
                "then start Card Factory again."
            )
        else:
            fix = "Delete data\\cardfactory.sqlite3, then start Card Factory again."
        raise StartupError(
            "Card Factory could not upgrade its data, and could not put the data back as it was.",
            fix,
        ) from error


def _sqlite_copy(source, target):
    """Copy one SQLite database into another with the backup API, write-ahead log included."""
    source_connection = sqlite3.connect(source)
    try:
        target_connection = sqlite3.connect(target)
        try:
            source_connection.backup(target_connection)
        finally:
            target_connection.close()
    finally:
        source_connection.close()


def _newer_database_error():
    return StartupError(
        "The data folder comes from a newer version of Card Factory, "
        "so this version cannot use it. The data was not changed.",
        "Start the newer version of Card Factory with this data folder, "
        "or install the latest version.",
    )


def _failed_migration_error():
    return StartupError(
        "Card Factory could not upgrade its data to this version. The data was left as it was.",
        "Start the previous version of Card Factory, then report the problem "
        "on the project's GitHub page.",
    )


def bind():
    """A socket listening on `127.0.0.1` at the running port, or StartupError naming APP_PORT."""
    # Imported here: the launcher imports this module before the settings load.
    from django.conf import settings

    return _bind(settings.RUNNING_PORT)


def serve(stop_event, sock=None):
    """Serve the application on `127.0.0.1` at the running port until `stop_event` is set.

    `sock` is a socket from `bind()`; without one, serve() binds it first.
    """
    from waitress.server import create_server

    from cardfactory.wsgi import application

    if sock is None:
        sock = bind()
    try:
        # Waitress would set SO_REUSEADDR on a socket it binds itself, so it gets this one bound.
        server = create_server(application, sockets=[sock])
    except BaseException:
        sock.close()
        raise
    try:
        while not stop_event.is_set():
            server.asyncore.loop(timeout=STOP_CHECK_INTERVAL, map=server._map, count=1)
    finally:
        _close(server)


def _bind(port):
    """An IPv4 socket bound to `127.0.0.1:port` and listening, or StartupError naming APP_PORT."""
    try:
        probe_wildcards(port)
    except OSError as error:
        raise _port_error(port) from error
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if _exclusive_address_use():
            # Without it, Windows lets a socket with SO_REUSEADDR share the port (see spec RN-47).
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        sock.bind((HOST, port))
        sock.listen()
    except OSError as error:
        sock.close()
        raise _port_error(port) from error
    return sock


def probe_wildcards(port):
    """Raise OSError when another socket holds `port` on every interface (0.0.0.0 or [::]).

    Windows lets a bind to 127.0.0.1 succeed over another program's wildcard
    bind, even with SO_EXCLUSIVEADDRUSE, so Card Factory would serve over it
    (see spec RN-47). An exclusive bind on each wildcard address fails in that
    case. The probes never listen (no firewall prompt, see CA-20) and are
    closed at once. Other systems already refuse the 127.0.0.1 bind itself.
    """
    if not _exclusive_address_use():
        return
    probes = [(socket.AF_INET, "0.0.0.0")]
    if socket.has_ipv6:
        probes.append((socket.AF_INET6, "::"))
    for family, wildcard in probes:
        try:
            probe = socket.socket(family, socket.SOCK_STREAM)
        except OSError:
            # No IPv6 stack on this machine: nothing can hold the port there.
            continue
        with probe:
            try:
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                if family == socket.AF_INET6:
                    # Dual-stack, so a holder on either side of [::] is found.
                    probe.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            except OSError:
                # This probe cannot be set up here; only a failed bind means the port is held.
                continue
            probe.bind((wildcard, port))


def _exclusive_address_use():
    return sys.platform == "win32" and hasattr(socket, "SO_EXCLUSIVEADDRUSE")


def _port_error(port):
    return StartupError(
        f"Card Factory cannot use port {port}: another program may be using it.",
        f"Close the program that uses port {port}, or set APP_PORT in .env to another port, "
        "then start Card Factory again.",
    )


def _close(server):
    """Close the listening socket, open connections, the wake-up trigger and the worker threads."""
    server.close()
    for channel in list(server._map.values()):
        channel.close()
    server.task_dispatcher.shutdown()
