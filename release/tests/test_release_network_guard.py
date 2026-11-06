"""Tests that the release tests run under the network guard (see spec RN-29, CA-19)."""

import socket

import pytest

from cardfactory_network_guard import NetworkAccessBlocked

# TEST-NET-1 (RFC 5737): documentation only, never routed.
FICTIONAL_HOST = ("192.0.2.10", 443)


def test_rn29_ca19_release_tests_cannot_open_a_connection():
    """RN-29 / CA-19: a connection attempt from a release test fails with the guard's error."""
    with pytest.raises(NetworkAccessBlocked):
        socket.create_connection(FICTIONAL_HOST, timeout=1)


def test_rn29_ca19_release_tests_cannot_connect_a_raw_socket():
    """RN-29 / CA-19: socket.connect with a numeric address is blocked, not only name resolution."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        with pytest.raises(NetworkAccessBlocked):
            sock.connect(FICTIONAL_HOST)


def test_rn29_ca19_release_tests_cannot_resolve_a_host_name():
    """RN-29 / CA-19: name resolution from a release test fails with the guard's error."""
    with pytest.raises(NetworkAccessBlocked):
        socket.getaddrinfo("downloads.example.invalid", 443)
