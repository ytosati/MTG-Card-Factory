"""Launcher startup sequence after the bootstrap: checks, lock, probe, upgrade, server, browser, watchdog.
Details: specs/plan.md, section 9.5 (launcher steps 2 to 8).
"""

import http.client
import json
import logging
import os
import socket
import sys
import threading
import time
import types
import webbrowser

from core.startup import StartupError, probe_wildcards

HOST = "127.0.0.1"
PROBE_PATH = "/api/instance"
PROBE_TIMEOUT_SECONDS = 2
# Longer than any real instance answer; a larger body is not the instance JSON.
PROBE_MAX_BYTES = 64 * 1024
INSTANCE_WAIT_SECONDS = 30
INSTANCE_POLL_SECONDS = 0.5
SERVER_JOIN_SECONDS = 1
# The serving loop checks its stop event every half second; this bounds a stuck shutdown.
SERVER_STOP_SECONDS = 10
APP_NAME = "card-factory"

UNEXPECTED_PROBLEM = "Card Factory could not start because of an unexpected problem."
UNEXPECTED_FIX = (
    "The details are in data\\logs\\app.log in the Card Factory folder. Start Card Factory "
    "again; if the problem continues, report it on the project's GitHub page."
)

_FREE = "free"
_SAME_HOME = "same-home"
_OTHER_HOME = "other-home"
_OTHER = "other"

logger = logging.getLogger("cardfactory.launcher")


def default_deps():
    """The real collaborators of `main`."""
    import core.startup
    import startup_checks

    return types.SimpleNamespace(
        run_checks=startup_checks.run_checks,
        show_message=startup_checks.message_box,
        acquire_lock=acquire_lock,
        load_settings=load_settings,
        port_is_free=port_is_free,
        http_connection=http.client.HTTPConnection,
        upgrade_database=core.startup.upgrade_database,
        start_server=start_server,
        open_browser=webbrowser.open,
        make_watchdog=core.startup.Watchdog,
        install_watchdog=core.startup.install,
        sleep=time.sleep,
        clock=time.monotonic,
    )


def port_is_free(port):
    """True when no other socket holds the port on `127.0.0.1` or on every interface.

    Exclusive binds that never listen; on Windows a bind to 127.0.0.1 succeeds over a
    wildcard holder, so the wildcard addresses are checked too (see spec RN-47).
    """
    try:
        probe_wildcards(port)
    except OSError:
        return False
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            if sys.platform == "win32":
                # Without it, Windows lets a bind share a port held with SO_REUSEADDR.
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            sock.bind((HOST, port))
        except OSError:
            return False
    return True


def acquire_lock(path):
    """Lock `path` for the life of the process; the open file is the handle, or None when held."""
    import msvcrt

    handle = open(path, "a+b")
    try:
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        handle.close()
        return None
    return handle


def load_settings():
    """Load the Django settings; StartupError from them (such as the secret key) reaches the caller."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cardfactory.settings")
    import django

    django.setup()
    from django.conf import settings

    return settings


def start_server(stop_event):
    """Bind the port now (StartupError on failure), then serve in a thread until `stop_event` is set."""
    import core.startup

    sock = core.startup.bind()
    thread = ServerThread(core.startup.serve, stop_event, sock)
    thread.start()
    return thread


class ServerThread(threading.Thread):
    """Runs `serve(stop_event, sock=sock)`; `error` keeps what it raised, for the launcher to show."""

    def __init__(self, serve, stop_event, sock):
        super().__init__(name="card-factory-server")
        self._serve = serve
        self._stop_event = stop_event
        self._sock = sock
        self.error = None

    def run(self):
        try:
            self._serve(self._stop_event, sock=self._sock)
        except Exception as error:
            self.error = error


def main(home, *, deps):
    """Run the startup sequence for the Card Factory in `home`; the exit code."""
    home = os.fspath(home)
    data = os.path.join(home, "data")
    instance_file = os.path.join(data, "instance.json")
    lock = None
    try:
        if not deps.run_checks(home, deps.show_message):
            return 1
        lock = deps.acquire_lock(os.path.join(data, "launcher.lock"))
        if lock is None:
            return _open_running_instance(home, instance_file, deps)
        # Left by the previous run; a second launcher waits for the one this run writes.
        _remove(instance_file)

        port = deps.load_settings().RUNNING_PORT
        # A free port skips the probe, which waits about two seconds on a free port on Windows.
        answer = _FREE if deps.port_is_free(port) else _probe(deps, port, home)
        if answer == _SAME_HOME:
            deps.open_browser(_url(port))
            return 0
        if answer != _FREE:
            lock = _release(lock)
            deps.show_message(*_port_message(port, answer))
            return 1

        deps.upgrade_database()
        _run_server(deps, port, instance_file)
        return 0
    except StartupError as error:
        # Released before the window, so a second start meanwhile runs on its own (see spec RN-41).
        lock = _release(lock)
        deps.show_message(error.problem, error.fix)
        return 1
    except Exception:
        # Never the exception text in the window: it could hold a key (plan section 9.5).
        logger.exception("Card Factory could not start.")
        lock = _release(lock)
        deps.show_message(UNEXPECTED_PROBLEM, UNEXPECTED_FIX)
        return 1
    finally:
        _release(lock)


def _release(lock):
    """Release the single-instance lock, if still held; None, the lock's new value."""
    if lock is not None and hasattr(lock, "close"):
        lock.close()
    return None


def _run_server(deps, port, instance_file):
    """Start the server, announce it, open the browser and wait until it stops; raise what failed."""
    stop_event = threading.Event()
    server = deps.start_server(stop_event)
    try:
        _write_instance(instance_file, port)
        watchdog = deps.make_watchdog(stop_event.set)
        # Installed before the browser opens, so the first heartbeat is never lost.
        deps.install_watchdog(watchdog)
        deps.open_browser(_url(port))
        watchdog.arm()
        watchdog.start()
        while server.is_alive():
            server.join(SERVER_JOIN_SECONDS)
    except BaseException:
        # Stopped before the lock is released, so no server outlives its launcher.
        stop_event.set()
        server.join(SERVER_STOP_SECONDS)
        raise
    error = getattr(server, "error", None)
    if error is not None:
        raise error


def _open_running_instance(home, instance_file, deps):
    """With the lock held by another launcher of this folder: open a tab of its port (see spec RN-41).

    Waits until its `data/instance.json` names a port where this Card Factory answers,
    so a file left by the previous run is never trusted.
    """
    deadline = deps.clock() + INSTANCE_WAIT_SECONDS
    while True:
        port = _read_instance_port(instance_file)
        if port is not None and _probe(deps, port, home) == _SAME_HOME:
            deps.open_browser(_url(port))
            return 0
        if deps.clock() >= deadline:
            deps.show_message(
                "Card Factory is already starting from this folder, but it is not ready yet.",
                "Wait a minute, then start Card Factory again.",
            )
            return 1
        deps.sleep(INSTANCE_POLL_SECONDS)


def _read_instance_port(instance_file):
    try:
        with open(instance_file, encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return None
    port = payload.get("port") if isinstance(payload, dict) else None
    if isinstance(port, int) and not isinstance(port, bool) and 1 <= port <= 65535:
        return port
    return None


def _write_instance(instance_file, port):
    # Written to a temporary file and renamed, so a second launcher never reads half of it.
    temporary = f"{instance_file}.tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump({"port": port, "pid": os.getpid()}, handle)
    os.replace(temporary, instance_file)


def _remove(path):
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def _probe(deps, port, home):
    """What answers on the port: nothing, this Card Factory, another one, or anything else (see spec RN-47)."""
    connection = deps.http_connection(HOST, port, timeout=PROBE_TIMEOUT_SECONDS)
    try:
        try:
            # request() connects first; the send itself never waits on the loopback.
            connection.request("GET", PROBE_PATH)
        except (ConnectionRefusedError, TimeoutError):
            # Windows retries a refused loopback connection for about two seconds, so a free
            # port often ends in this timeout; the bind stays the authority (plan section 9.5).
            return _FREE
        except (OSError, http.client.HTTPException):
            return _OTHER
        try:
            response = connection.getresponse()
            if response.status != 200:
                return _OTHER
            body = response.read(PROBE_MAX_BYTES + 1)
        except (OSError, http.client.HTTPException):
            return _OTHER
        if len(body) > PROBE_MAX_BYTES:
            return _OTHER
        try:
            payload = json.loads(body)
        except ValueError:
            return _OTHER
        if not isinstance(payload, dict) or payload.get("app") != APP_NAME:
            return _OTHER
        running_home = payload.get("home")
        if not isinstance(running_home, str) or not running_home:
            return _OTHER
        return _SAME_HOME if _same_folder(running_home, home) else _OTHER_HOME
    finally:
        connection.close()


def _same_folder(first, second):
    def normalize(path):
        return os.path.normcase(os.path.realpath(path))

    return normalize(first) == normalize(second)


def _port_message(port, answer):
    if answer == _OTHER_HOME:
        return (
            f"Card Factory cannot use port {port}: another Card Factory, started from another "
            "folder, is using it.",
            "Close the other Card Factory, or set APP_PORT in .env to another port, "
            "then start Card Factory again.",
        )
    return (
        f"Card Factory cannot use port {port}: another program is using it.",
        f"Close the program that uses port {port}, or set APP_PORT in .env to another port, "
        "then start Card Factory again.",
    )


def _url(port):
    return f"http://{HOST}:{port}/"
