"""Local server entry point `core.startup.serve` (task T7, spec RN-29, RN-40, RN-47, CA-20).

Contract under test (plan section 9.5, launcher step 7):

- `core.startup.StartupError(problem, fix)` is an Exception that keeps both
  texts as the attributes `problem` and `fix`; the launcher shows them in a
  message box.
- `core.startup.serve(stop_event)` takes a `threading.Event`. It reads the port
  from `settings.RUNNING_PORT` when called and binds waitress to `127.0.0.1` on
  that port with exclusive address use (`SO_EXCLUSIVEADDRUSE` on Windows), in
  the calling thread, before serving. The host is always `127.0.0.1`; no
  setting or environment variable changes it.
- When the bind fails, serve raises `StartupError` from the calling thread,
  naming the port and `APP_PORT`, and leaves no thread or socket behind.
- Otherwise serve blocks while it serves the Django application, until
  `stop_event` is set. It then closes the listening socket and the waitress
  worker threads and returns None (within a few seconds of the event).

The tests run serve in a thread of their own, choose a free port at run time,
and connect only to 127.0.0.1 (tests.loopback lets that one address through
the network guard for these tests).
"""

import socket
import sys
import threading

import pytest

from tests.loopback import (
    LOOPBACK,
    ServeRunner,
    allow_loopback,
    bound_addresses,
    free_port,
    open_sockets,
    wait_for_threads,
    wait_until_accepting,
)

ON_WINDOWS = sys.platform == "win32"


@pytest.fixture
def loopback(monkeypatch):
    allow_loopback(monkeypatch)


@pytest.fixture
def port(settings):
    """A free port set as the running port, as the settings would read it from APP_PORT."""
    chosen = free_port()
    settings.RUNNING_PORT = chosen
    return chosen


@pytest.fixture
def threads_before():
    return set(threading.enumerate())


@pytest.fixture
def runners():
    """serve() runners started by a test; any still running at teardown is stopped."""
    started = []
    yield started
    for runner in started:
        runner.stop(timeout=10.0)


def _serve():
    from core.startup import serve

    return serve


def _start(runners, port):
    runner = ServeRunner(_serve()).start()
    runners.append(runner)
    accepting = wait_until_accepting(port, still_trying=runner.thread.is_alive)
    if runner.error is not None:
        raise runner.error
    assert accepting, f"serve() did not accept connections on 127.0.0.1:{port}"
    return runner


def _message(error):
    return f"{error.problem}\n{error.fix}"


# StartupError


def test_t7_rn40_startup_error_keeps_problem_and_fix():
    """RN-40 / T7: StartupError(problem, fix) is an Exception that carries the problem and the fix."""
    from core.startup import StartupError

    error = StartupError("The fictional thing is broken.", "Fix the fictional thing.")

    assert isinstance(error, Exception)
    assert error.problem == "The fictional thing is broken."
    assert error.fix == "Fix the fictional thing."


def test_t7_rn40_startup_error_can_be_raised_and_caught():
    """RN-40 / T7: the launcher catches StartupError as an exception and reads both texts."""
    from core.startup import StartupError

    with pytest.raises(StartupError) as raised:
        raise StartupError("Problem text ✓ ção", "Fix text — ünïcode")

    assert raised.value.problem == "Problem text ✓ ção"
    assert raised.value.fix == "Fix text — ünïcode"


# Bind to 127.0.0.1 on the running port


def test_t7_rn29_rn47_serve_listens_on_loopback_at_the_running_port(loopback, port, runners):
    """RN-29 / RN-47 / CA-20 / T7: serve() accepts connections on 127.0.0.1 at settings.RUNNING_PORT."""
    runner = _start(runners, port)

    assert runner.thread.is_alive()
    assert runner.error is None


def test_t7_rn29_ca20_no_listener_on_any_other_interface(loopback, port, runners):
    """RN-29 / CA-20 / T7: every socket on the running port is IPv4 127.0.0.1; none on 0.0.0.0, :: or ::1."""
    _start(runners, port)

    addresses = bound_addresses(port)

    assert addresses, "no socket of this process is bound to the running port"
    for family, address in addresses:
        assert family == socket.AF_INET, f"a socket on the port is not IPv4: {family!r} {address!r}"
        assert address == LOOPBACK, f"a socket on the port is bound to {address!r}"


@pytest.mark.parametrize("name", ["APP_HOST", "CARDFACTORY_HOST", "HOST", "BIND_ADDRESS"])
def test_t7_rn29_no_setting_changes_the_host(loopback, port, runners, monkeypatch, name):
    """RN-29 / CA-20 / T7: the host is always 127.0.0.1; a variable asking for 0.0.0.0 changes nothing."""
    monkeypatch.setenv(name, "0.0.0.0")

    _start(runners, port)

    addresses = bound_addresses(port)
    assert addresses
    assert all(address == LOOPBACK for _family, address in addresses)


def test_t7_rn29_serve_answers_http_with_the_django_application(loopback, port, runners):
    """RN-29 / T7: the server bound by serve() answers an HTTP request on 127.0.0.1 (the WSGI application runs)."""
    _start(runners, port)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.settimeout(10)
        client.connect((LOOPBACK, port))
        request = f"GET / HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nConnection: close\r\n\r\n"
        client.sendall(request.encode("ascii"))
        received = b""
        while len(received) < 16:
            chunk = client.recv(4096)
            if not chunk:
                break
            received += chunk

    assert received.startswith(b"HTTP/1.1 "), received[:80]


def _local_address(sock):
    # A socket of an earlier test may close between the scan and this call.
    try:
        return sock.getsockname()
    except OSError:
        return None


@pytest.mark.skipif(not ON_WINDOWS, reason="SO_EXCLUSIVEADDRUSE exists only on Windows")
def test_t7_rn47_listening_socket_uses_exclusive_address_use(loopback, port, runners):
    """RN-47 / T7 (plan 9.5): on Windows the listening socket has SO_EXCLUSIVEADDRUSE set."""
    _start(runners, port)

    listeners = [
        sock
        for sock in open_sockets()
        if sock.family == socket.AF_INET and _local_address(sock) == (LOOPBACK, port)
    ]
    assert listeners
    assert any(sock.getsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE) for sock in listeners)


def test_t7_rn47_another_program_cannot_share_the_running_port(loopback, port, runners):
    """RN-47 / T7 (plan 9.5): with the server running, another socket asking to reuse the address cannot bind the port."""
    _start(runners, port)

    intruder = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        intruder.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        with pytest.raises(OSError):
            intruder.bind((LOOPBACK, port))
    finally:
        intruder.close()


# Stop


def test_t7_stop_event_ends_serve_and_frees_the_port(loopback, port, runners, threads_before):
    """T7: setting stop_event makes serve() return; the port can be bound again and no thread is left."""
    runner = _start(runners, port)

    assert runner.stop(timeout=10.0), "serve() did not return after stop_event was set"
    assert runner.error is None
    assert runner.returned

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as again:
        again.bind((LOOPBACK, port))

    assert bound_addresses(port) == []
    assert wait_for_threads(threads_before) == []


def test_t7_serve_keeps_running_until_the_stop_event(loopback, port, runners):
    """T7: serve() does not return on its own while stop_event is clear."""
    runner = _start(runners, port)

    assert not runner.finish(timeout=0.5)
    assert wait_until_accepting(port)
    assert runner.stop(timeout=10.0)


# Bind failure


@pytest.fixture
def held_port(settings):
    """A port held by a listening local socket that is not Card Factory, set as the running port."""
    holders = []

    def _hold(reuse_address=False):
        holder = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        holders.append(holder)
        if reuse_address:
            holder.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        holder.bind((LOOPBACK, 0))
        holder.listen(1)
        chosen = holder.getsockname()[1]
        settings.RUNNING_PORT = chosen
        return chosen, holder

    yield _hold
    for holder in holders:
        holder.close()


def _serve_expecting_failure(runners):
    runner = ServeRunner(_serve()).start()
    runners.append(runner)
    finished = runner.finish(timeout=10.0)
    if not finished:
        runner.stop(timeout=10.0)
    assert finished, "serve() kept running on a port held by another socket"
    return runner


@pytest.mark.parametrize("reuse_address", [False, True], ids=["plain-holder", "holder-with-reuseaddr"])
def test_t7_rn40_rn47_port_held_by_a_local_socket_is_a_startup_error(loopback, held_port, runners, reuse_address):
    """RN-40 / RN-47 / T7: a port already held locally makes serve() raise StartupError naming the port and APP_PORT."""
    from core.startup import StartupError

    port, _holder = held_port(reuse_address)

    runner = _serve_expecting_failure(runners)

    assert isinstance(runner.error, StartupError), repr(runner.error)
    message = _message(runner.error)
    assert "APP_PORT" in message
    assert str(port) in message
    assert runner.error.problem.strip()
    assert runner.error.fix.strip()


def test_t7_rn40_bind_failure_leaves_no_thread_or_socket(loopback, held_port, runners, threads_before):
    """RN-40 / T7: after a bind failure, no waitress thread and no socket of the attempt stay open."""
    sockets_before = open_sockets()
    port, holder = held_port()

    runner = _serve_expecting_failure(runners)

    assert runner.error is not None
    runners.clear()
    assert wait_for_threads(threads_before) == []
    left_open = open_sockets() - sockets_before - {holder}
    assert left_open == set(), f"sockets left open: {left_open!r}"
    assert bound_addresses(port) == [(socket.AF_INET, LOOPBACK)]


def test_t7_rn40_bind_failure_does_not_take_over_the_held_port(loopback, held_port, runners):
    """RN-47 / T7: after the failure the other program still holds its port; Card Factory does not share it."""
    port, holder = held_port()

    _serve_expecting_failure(runners)

    assert bound_addresses(port) == [(socket.AF_INET, LOOPBACK)]
    assert holder.fileno() != -1


# Bind failure: the port held on all interfaces
#
# The common real case is another program bound to every interface (0.0.0.0 or
# [::]) on the same port. A bind to the specific address 127.0.0.1 can succeed
# over such a wildcard bind on Windows, which would let Card Factory sit on the
# port of another program (plan 9.5: "the bind stays the authority").
#
# The holders here are bound but do not listen: a socket listening on every
# interface may raise a Windows firewall prompt, and a bound socket already
# holds the port. Nothing is sent and nothing connects to them.


def _ipv6_dual_stack_available():
    if not socket.has_ipv6:
        return False
    try:
        with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            probe.bind(("::", 0))
    except OSError:
        return False
    return True


WILDCARD_HOLDERS = [
    pytest.param(socket.AF_INET, "0.0.0.0", False, id="ipv4-any-plain"),
    pytest.param(socket.AF_INET, "0.0.0.0", True, id="ipv4-any-with-reuseaddr"),
    pytest.param(
        socket.AF_INET6,
        "::",
        False,
        id="ipv6-any-dual-stack-plain",
        marks=pytest.mark.skipif(not _ipv6_dual_stack_available(), reason="no dual-stack IPv6 here"),
    ),
    pytest.param(
        socket.AF_INET6,
        "::",
        True,
        id="ipv6-any-dual-stack-with-reuseaddr",
        marks=pytest.mark.skipif(not _ipv6_dual_stack_available(), reason="no dual-stack IPv6 here"),
    ),
]


@pytest.fixture
def held_wildcard_port(settings):
    """A port held by a socket bound (not listening) on every interface, set as the running port."""
    holders = []

    def _hold(family, wildcard, reuse_address):
        holder = socket.socket(family, socket.SOCK_STREAM)
        holders.append(holder)
        if reuse_address:
            holder.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if family == socket.AF_INET6:
            # Dual-stack: the holder also takes the IPv4 side of the port.
            holder.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        holder.bind((wildcard, 0))
        chosen = holder.getsockname()[1]
        settings.RUNNING_PORT = chosen
        return chosen, holder

    yield _hold
    for holder in holders:
        holder.close()


@pytest.mark.parametrize(("family", "wildcard", "reuse_address"), WILDCARD_HOLDERS)
def test_t7_rn40_rn47_port_held_on_all_interfaces_is_a_startup_error(
    loopback, held_wildcard_port, runners, family, wildcard, reuse_address
):
    """RN-40 / RN-47 / T7: a port bound by another socket on 0.0.0.0 or [::] makes serve() raise StartupError naming APP_PORT."""
    from core.startup import StartupError

    port, _holder = held_wildcard_port(family, wildcard, reuse_address)

    runner = _serve_expecting_failure(runners)

    assert isinstance(runner.error, StartupError), (
        f"serve() did not fail over a holder on {wildcard}:{port}: {runner.error!r}"
    )
    message = _message(runner.error)
    assert "APP_PORT" in message
    assert str(port) in message


@pytest.mark.parametrize(("family", "wildcard", "reuse_address"), WILDCARD_HOLDERS)
def test_t7_rn40_rn47_port_held_on_all_interfaces_is_not_taken_over(
    loopback, held_wildcard_port, runners, threads_before, family, wildcard, reuse_address
):
    """RN-40 / RN-47 / T7: over a holder on 0.0.0.0 or [::], serve() leaves no thread or socket and does not take the port."""
    sockets_before = open_sockets()
    port, holder = held_wildcard_port(family, wildcard, reuse_address)

    runner = _serve_expecting_failure(runners)

    assert runner.error is not None
    runners.clear()
    assert wait_for_threads(threads_before) == []
    left_open = open_sockets() - sockets_before - {holder}
    assert left_open == set(), f"sockets left open: {left_open!r}"
    assert bound_addresses(port) == [(family, wildcard)]
    assert holder.fileno() != -1
