"""Startup errors and the local server entry point used by the launcher.
Details: specs/plan.md, section 9.5.
"""

import socket
import sys

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


def serve(stop_event):
    """Serve the application on `127.0.0.1` at the running port until `stop_event` is set."""
    # Imported here: the launcher imports this module before the settings load.
    from django.conf import settings
    from waitress.server import create_server

    from cardfactory.wsgi import application

    port = settings.RUNNING_PORT
    sock = _bind(port)
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
        _probe_wildcards(port)
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


def _probe_wildcards(port):
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
