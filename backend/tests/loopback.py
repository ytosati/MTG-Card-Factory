"""Test helper: IPv4 loopback for tests of the local server (task T7, spec RN-29).

The network guard blocks every connection for the whole session. The local
server tests need the IPv4 loopback address `127.0.0.1` and nothing else:
waitress builds its wake-up trigger from a loopback connection on Windows, and
the tests connect to the server they started. `allow_loopback` lets exactly
that address through for one test; every other address and every host name
still meets the guard. Lookups of a numeric address (or of no host) are
answered locally with `AI_NUMERICHOST`, so no name ever reaches a resolver;
waitress makes such a lookup for its default listen value.
"""

import gc
import ipaddress
import socket
import threading
import time

from tests import network_guard

LOOPBACK = "127.0.0.1"


def _is_loopback(address):
    return isinstance(address, tuple) and len(address) == 2 and address[0] == LOOPBACK


def _is_numeric_host(host):
    if host is None:
        return True
    if isinstance(host, bytes):
        host = host.decode("ascii", "replace")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


def allow_loopback(monkeypatch):
    """Let connections to 127.0.0.1 and numeric lookups through the guard until the test ends."""
    real_connect = network_guard.original("connect")
    real_getaddrinfo = network_guard.original("getaddrinfo")
    guarded_connect = socket.socket.connect
    guarded_getaddrinfo = socket.getaddrinfo

    def connect(self, address):
        if _is_loopback(address):
            return real_connect(self, address)
        return guarded_connect(self, address)

    def getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        if _is_numeric_host(host):
            # Numeric only: nothing is sent to a name resolver.
            return real_getaddrinfo(host, port, family, type, proto, flags | socket.AI_NUMERICHOST)
        return guarded_getaddrinfo(host, port, family, type, proto, flags)

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)


def free_port():
    """A TCP port on 127.0.0.1 that was free a moment ago, chosen by the system."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((LOOPBACK, 0))
        return probe.getsockname()[1]


def open_sockets():
    """Every socket object of this process that is still open."""
    gc.collect()
    # type(), not isinstance(): isinstance would evaluate Django's lazy objects.
    return {
        sock
        for sock in gc.get_objects()
        if issubclass(type(sock), socket.socket) and sock.fileno() != -1
    }


def bound_addresses(port):
    """(family, address) of every open socket of this process whose local port is `port`."""
    found = []
    for sock in open_sockets():
        try:
            name = sock.getsockname()
        except OSError:
            continue
        if isinstance(name, tuple) and len(name) >= 2 and name[1] == port:
            found.append((sock.family, name[0]))
    return found


def wait_until_accepting(port, timeout=10.0, still_trying=lambda: True):
    """Wait until a TCP connection to 127.0.0.1:port succeeds; the probe connection is closed at once.

    Gives up early when `still_trying()` turns false (the server thread ended).
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and still_trying():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            # A short timeout: Windows retries a refused loopback connection for seconds.
            probe.settimeout(0.25)
            try:
                probe.connect((LOOPBACK, port))
                return True
            except OSError:
                pass
        time.sleep(0.05)
    return False


def wait_for_threads(before, timeout=10.0):
    """Wait until no thread started after `before` is alive; returns the ones still alive."""
    deadline = time.monotonic() + timeout
    while True:
        extra = [thread for thread in threading.enumerate() if thread not in before and thread.is_alive()]
        if not extra or time.monotonic() >= deadline:
            return extra
        time.sleep(0.05)


class ServeRunner:
    """Runs `core.startup.serve(stop_event)` in a thread and keeps what it returned or raised."""

    def __init__(self, serve):
        self.serve = serve
        self.stop_event = threading.Event()
        self.error = None
        self.returned = False
        self.thread = threading.Thread(target=self._run, name="test-serve", daemon=True)

    def _run(self):
        try:
            self.serve(self.stop_event)
            self.returned = True
        except BaseException as error:  # noqa: BLE001 (handed to the test thread)
            self.error = error

    def start(self):
        self.thread.start()
        return self

    def stop(self, timeout=10.0):
        """Set the stop event and wait for serve() to finish; True when it finished in time."""
        self.stop_event.set()
        self.thread.join(timeout)
        return not self.thread.is_alive()

    def finish(self, timeout=10.0):
        """Wait for serve() to finish on its own; True when it finished in time."""
        self.thread.join(timeout)
        return not self.thread.is_alive()
