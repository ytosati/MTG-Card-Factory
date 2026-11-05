"""Tests that the launcher tests run under the network guard (see spec RN-29, CA-19)."""

import socket

import pytest

from cardfactory_network_guard import NetworkAccessBlocked

# TEST-NET-2 (RFC 5737): documentation only, never routed.
FICTIONAL_HOST = ("198.51.100.20", 47821)


def test_rn29_ca19_launcher_tests_cannot_open_a_connection():
    """RN-29 / CA-19: a connection attempt from a launcher test fails with the guard's error."""
    with pytest.raises(NetworkAccessBlocked):
        socket.create_connection(FICTIONAL_HOST, timeout=1)


def test_rn29_ca19_launcher_tests_cannot_send_a_datagram():
    """RN-29 / CA-19: a datagram from a launcher test fails with the guard's error."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        with pytest.raises(NetworkAccessBlocked):
            sock.sendto(b"fictional", FICTIONAL_HOST)
