"""Early pytest plugin: every outgoing socket connection fails during the test session.

Loaded with `-p tests.network_guard` (pytest.ini), so no test can reach the
network or a provider (see spec RN-29, CA-19).
"""

import socket
import sys
import threading


class NetworkAccessBlocked(RuntimeError):
    """Raised when a test tries to open a network connection or resolve a host name."""


# Not an OSError on purpose: code that recovers from network errors must not
# swallow the guard, so a test that goes out fails loudly instead of passing.
def _blocked(action, target):
    return NetworkAccessBlocked(
        f"Tests must not touch the network: blocked {action} to {target!r}. "
        "Use the fake provider and hand-written responses."
    )


_ORIGINALS = {}
_local = threading.local()


def _in_socketpair():
    return getattr(_local, "in_socketpair", False)


def _guarded_connect(self, address):
    if _in_socketpair():
        return _ORIGINALS["connect"](self, address)
    raise _blocked("socket connection", address)


def _guarded_connect_ex(self, address):
    raise _blocked("socket connection", address)


def _guarded_sendto(self, data, *args):
    address = args[-1] if args else None
    raise _blocked("datagram", address)


def _guarded_getaddrinfo(host, port, *args, **kwargs):
    raise _blocked("name resolution", (host, port))


def _guarded_gethostbyname(host):
    raise _blocked("name resolution", host)


def _guarded_gethostbyname_ex(host):
    raise _blocked("name resolution", host)


def _guarded_gethostbyaddr(address):
    raise _blocked("name resolution", address)


def _guarded_proactor_connect(self, conn, address):
    raise _blocked("socket connection", address)


def _guarded_proactor_sendto(self, conn, buf, flags=0, addr=None):
    raise _blocked("datagram", addr)


def _guarded_socketpair(*args, **kwargs):
    # On Windows socketpair() is built from a loopback connect inside the process;
    # asyncio needs it for every event loop, and it reaches no other machine.
    _local.in_socketpair = True
    try:
        return _ORIGINALS["socketpair"](*args, **kwargs)
    finally:
        _local.in_socketpair = False


_SOCKET_METHODS = {
    "connect": _guarded_connect,
    "connect_ex": _guarded_connect_ex,
    "sendto": _guarded_sendto,
}
_MODULE_FUNCTIONS = {
    "getaddrinfo": _guarded_getaddrinfo,
    "gethostbyname": _guarded_gethostbyname,
    "gethostbyname_ex": _guarded_gethostbyname_ex,
    "gethostbyaddr": _guarded_gethostbyaddr,
    "socketpair": _guarded_socketpair,
}


def _proactor_class():
    # The Windows asyncio loop connects through ConnectEx, which bypasses socket.connect.
    if sys.platform != "win32":
        return None
    from asyncio import windows_events

    return windows_events.IocpProactor


_PROACTOR_METHODS = {
    "connect": _guarded_proactor_connect,
    "sendto": _guarded_proactor_sendto,
}


def install():
    """Replace the socket entry points with guards; calling it twice is harmless."""
    if _ORIGINALS:
        return
    for name, guard in _SOCKET_METHODS.items():
        _ORIGINALS[name] = getattr(socket.socket, name)
        setattr(socket.socket, name, guard)
    for name, guard in _MODULE_FUNCTIONS.items():
        _ORIGINALS[name] = getattr(socket, name)
        setattr(socket, name, guard)
    proactor = _proactor_class()
    if proactor is not None:
        for name, guard in _PROACTOR_METHODS.items():
            _ORIGINALS[f"proactor.{name}"] = getattr(proactor, name)
            setattr(proactor, name, guard)


def uninstall():
    """Put the original socket entry points back."""
    for name in _SOCKET_METHODS:
        if name in _ORIGINALS:
            setattr(socket.socket, name, _ORIGINALS[name])
    for name in _MODULE_FUNCTIONS:
        if name in _ORIGINALS:
            setattr(socket, name, _ORIGINALS[name])
    proactor = _proactor_class()
    for name in _PROACTOR_METHODS:
        if proactor is not None and f"proactor.{name}" in _ORIGINALS:
            setattr(proactor, name, _ORIGINALS[f"proactor.{name}"])
    _ORIGINALS.clear()


def original(name):
    """The real socket function or method replaced by the guard, for tests of the guard itself."""
    return _ORIGINALS[name]


# Installed at import, before pytest-django loads the settings, so nothing runs unguarded.
install()


def pytest_unconfigure(config):
    """Restore the real socket functions once the session ends."""
    uninstall()
