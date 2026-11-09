"""Tests for the real launcher helpers: the single-instance lock and the free-port check (task T74).

Covers RN-41 and RN-47 on the local machine only: the port check binds and listens on
127.0.0.1 and never opens a connection.
"""

import socket
import sys

import pytest


def _launch():
    import launch

    return launch


windows_only = pytest.mark.skipif(sys.platform != "win32", reason="the lock uses msvcrt, a Windows module")


@windows_only
def test_rn41_second_lock_on_the_same_file_is_refused_while_the_first_is_held(tmp_path):
    """RN-41: while one handle holds launcher.lock, a second acquire_lock returns None."""
    path = tmp_path / "launcher.lock"
    first = _launch().acquire_lock(str(path))
    try:
        assert first is not None
        assert _launch().acquire_lock(str(path)) is None
    finally:
        first.close()


@windows_only
def test_rn41_lock_can_be_taken_again_after_the_first_handle_closes(tmp_path):
    """RN-41: once the first launcher closes its handle, a new start takes the lock."""
    path = tmp_path / "launcher.lock"
    _launch().acquire_lock(str(path)).close()

    again = _launch().acquire_lock(str(path))
    try:
        assert again is not None
    finally:
        again.close()


def test_rn47_port_is_free_is_false_while_a_socket_listens_and_true_after():
    """RN-47: a port with a listening socket on 127.0.0.1 is not free; after it closes, it is."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        assert _launch().port_is_free(port) is False
    finally:
        listener.close()

    assert _launch().port_is_free(port) is True


def test_rn47_ca53_port_held_on_every_interface_is_not_free():
    """RN-47 / CA-53: a port bound by another socket on 0.0.0.0 is not free (task T131).

    The holder only binds: a wildcard listener could raise a firewall prompt.
    """
    holder = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        holder.bind(("0.0.0.0", 0))
        port = holder.getsockname()[1]
        assert _launch().port_is_free(port) is False
    finally:
        holder.close()


def test_rn47_port_with_nothing_on_it_is_free():
    """RN-47: a port that no socket holds is free (task T131)."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()

    assert _launch().port_is_free(port) is True
