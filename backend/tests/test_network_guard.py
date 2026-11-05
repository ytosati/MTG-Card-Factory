"""The test session blocks every outgoing connection (task T3, spec RN-29, CA-19).

Addresses and host names are fictional: TEST-NET ranges and the reserved .invalid domain.
"""

import asyncio
import http.client
import socket
import urllib.request

import pytest

from tests import network_guard
from tests.network_guard import NetworkAccessBlocked

FICTIONAL_ADDRESS = ("203.0.113.10", 443)
FICTIONAL_HOST = "provider.example.invalid"


@pytest.fixture
def tcp_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    yield sock
    sock.close()


def test_t3_connect_to_fictional_address_fails_with_clear_error(tcp_socket):
    """RN-29 / CA-19 / T3: socket.connect fails with the guard's error, naming the network rule and the address."""
    with pytest.raises(NetworkAccessBlocked) as raised:
        tcp_socket.connect(FICTIONAL_ADDRESS)

    message = str(raised.value)
    assert "Tests must not touch the network" in message
    assert "203.0.113.10" in message
    assert "443" in message


def test_t3_connect_ex_fails_instead_of_returning_an_error_code(tcp_socket):
    """RN-29 / CA-19 / T3: connect_ex raises the guard's error rather than returning an errno."""
    with pytest.raises(NetworkAccessBlocked, match="203.0.113.10"):
        tcp_socket.connect_ex(FICTIONAL_ADDRESS)


@pytest.mark.parametrize(
    "address",
    [("127.0.0.1", 47821), ("localhost", 47821), ("::1", 47821, 0, 0)],
    ids=["ipv4-loopback", "localhost-name", "ipv6-loopback"],
)
def test_t3_loopback_connections_are_blocked_too(address):
    """RN-29 / CA-19 / T3: loopback is not an exception; any socket connection fails."""
    family = socket.AF_INET6 if len(address) == 4 else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as sock:
        with pytest.raises(NetworkAccessBlocked):
            sock.connect(address)


def test_t3_udp_datagram_is_blocked():
    """RN-29 / CA-19 / T3: sending a datagram to an address is an outgoing connection and fails."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        with pytest.raises(NetworkAccessBlocked, match="203.0.113.10"):
            sock.sendto(b"fictional payload", FICTIONAL_ADDRESS)


@pytest.mark.parametrize(
    "resolve",
    [
        lambda: socket.getaddrinfo(FICTIONAL_HOST, 443),
        lambda: socket.gethostbyname(FICTIONAL_HOST),
        lambda: socket.gethostbyname_ex(FICTIONAL_HOST),
        lambda: socket.gethostbyaddr("203.0.113.10"),
    ],
    ids=["getaddrinfo", "gethostbyname", "gethostbyname_ex", "gethostbyaddr"],
)
def test_t3_name_resolution_is_blocked(resolve):
    """RN-29 / CA-19 / T3: resolving a host name could send a DNS query, so it fails with the guard's error."""
    with pytest.raises(NetworkAccessBlocked, match="name resolution"):
        resolve()


def test_t3_create_connection_fails_with_the_guard_error():
    """RN-29 / CA-19 / T3: socket.create_connection, used by HTTP clients, fails with the guard's error."""
    with pytest.raises(NetworkAccessBlocked, match="provider.example.invalid"):
        socket.create_connection((FICTIONAL_HOST, 443), timeout=1)


def test_t3_create_connection_to_a_literal_ip_fails_with_the_guard_error():
    """RN-29 / CA-19 / T3: a numeric address skips DNS but still fails before any packet leaves."""
    with pytest.raises(NetworkAccessBlocked):
        socket.create_connection(FICTIONAL_ADDRESS, timeout=1)


def test_t3_urlopen_fails_with_the_guard_error_not_a_network_error():
    """RN-29 / CA-19 / T3: an HTTP request through urllib raises the guard's error, never a URLError from a real attempt."""
    with pytest.raises(NetworkAccessBlocked, match="Tests must not touch the network"):
        urllib.request.urlopen(f"https://{FICTIONAL_HOST}/v1/generate", timeout=1)


def test_t3_http_client_fails_with_the_guard_error():
    """RN-29 / CA-19 / T3: http.client, the base of most provider SDK transports, is blocked as well."""
    connection = http.client.HTTPSConnection(FICTIONAL_HOST, timeout=1)
    try:
        with pytest.raises(NetworkAccessBlocked):
            connection.request("POST", "/v1/messages", body=b"{}")
    finally:
        connection.close()


def test_t3_guard_error_is_not_an_os_error():
    """RN-29 / CA-19 / T3: code that recovers from OSError cannot swallow the guard and hide a network call."""
    assert not issubclass(NetworkAccessBlocked, OSError)


def test_t3_guard_is_active_without_opt_in():
    """RN-29 / CA-19 / T3: the guard is installed for the whole session; no fixture or marker is needed."""
    assert socket.socket.connect is network_guard._guarded_connect
    assert socket.socket.connect_ex is network_guard._guarded_connect_ex
    assert socket.getaddrinfo is network_guard._guarded_getaddrinfo


def test_t3_in_process_socketpair_still_works():
    """RN-29 / CA-19 / T3: socketpair reaches no other machine and asyncio needs it, so it keeps working."""
    left, right = socket.socketpair()
    try:
        left.sendall(b"ping")
        assert right.recv(4) == b"ping"
    finally:
        left.close()
        right.close()


def test_t3_socketpair_does_not_open_a_hole_for_later_connections(tcp_socket):
    """RN-29 / CA-19 / T3: after a socketpair, ordinary connections are still blocked."""
    left, right = socket.socketpair()
    left.close()
    right.close()

    with pytest.raises(NetworkAccessBlocked):
        tcp_socket.connect(FICTIONAL_ADDRESS)


def test_t3_asyncio_event_loop_runs_under_the_guard():
    """RN-29 / CA-19 / T3: an asyncio loop starts (its self-pipe is a socketpair) and still cannot connect out."""

    async def try_to_connect():
        await asyncio.open_connection(*FICTIONAL_ADDRESS)

    with pytest.raises(NetworkAccessBlocked):
        asyncio.run(try_to_connect())


@pytest.mark.django_db
def test_t3_django_test_database_works_under_the_guard():
    """RN-29 / CA-19 / T3: the SQLite test database opens no socket, so database tests run normally."""
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        assert cursor.fetchone() == (1,)


def test_t3_uninstall_restores_the_originals_and_install_reapplies_the_guard():
    """RN-29 / CA-19 / T3: the guard puts the real socket functions back at the end of the session."""
    real_connect = network_guard.original("connect")
    real_getaddrinfo = network_guard.original("getaddrinfo")
    real_socketpair = network_guard.original("socketpair")

    network_guard.uninstall()
    try:
        assert socket.socket.connect is real_connect
        assert socket.getaddrinfo is real_getaddrinfo
        assert socket.socketpair is real_socketpair
    finally:
        network_guard.install()

    assert socket.socket.connect is network_guard._guarded_connect
    assert socket.getaddrinfo is network_guard._guarded_getaddrinfo


def test_t3_install_twice_keeps_the_real_originals():
    """RN-29 / CA-19 / T3: a second install does not record the guards as originals, so restore stays correct."""
    real_connect = network_guard.original("connect")

    network_guard.install()

    assert network_guard.original("connect") is real_connect


def test_t3_asyncio_loop_sock_connect_is_blocked():
    """RN-29 / CA-19 / T3: loop.sock_connect, which on Windows uses ConnectEx instead of socket.connect, is blocked."""

    async def try_to_connect():
        loop = asyncio.get_running_loop()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setblocking(False)
            await loop.sock_connect(sock, FICTIONAL_ADDRESS)

    with pytest.raises(NetworkAccessBlocked, match="203.0.113.10"):
        asyncio.run(try_to_connect())


def test_t3_asyncio_datagram_endpoint_is_blocked():
    """RN-29 / CA-19 / T3: an asyncio UDP endpoint toward a fictional address cannot send."""

    async def try_to_send():
        loop = asyncio.get_running_loop()
        transport, _ = await loop.create_datagram_endpoint(
            asyncio.DatagramProtocol, remote_addr=FICTIONAL_ADDRESS
        )
        transport.close()

    with pytest.raises(NetworkAccessBlocked):
        asyncio.run(try_to_send())
