"""Shared HTTP transport for the provider adapters (task T39, spec RN-06, RN-10, RN-29).

Details: specs/plan.md, section 9.2 (direct HTTP with the standard library,
named timeouts, one retry on 5xx and network errors, the error set, 429 split
into quota and rate limit, no key and no response body in error texts).

API under test:

    providers.transport
        CONNECT_TIMEOUT = 10        seconds to open the connection
        TEXT_READ_TIMEOUT = 180     seconds to wait for a text answer
        IMAGE_READ_TIMEOUT = 300    seconds to wait for an image answer

        HttpResponse(status: int, headers: dict[str, str], body: bytes)

        request(method, url, *, headers, body, read_timeout, model_setting,
                is_quota_error, send=None) -> HttpResponse
            Sends one request and returns the 2xx response untouched (the
            adapter parses it). `send` is the seam: a callable
                send(method, url, headers, body, *, connect_timeout, read_timeout)
                    -> HttpResponse
            that raises OSError or http.client.HTTPException on a network
            failure. When `send` is None the standard-library sender is used.
            `is_quota_error(response) -> bool` tells, for a 429, a quota or
            billing error (True) from a rate limit (False); each provider words
            it differently, so the adapter supplies it.
            `model_setting` is "LLM_MODEL" or "IMAGE_MODEL", named by
            ModelNotFound.

    Mapping: 401 and 403 -> AuthError; 404 -> ModelNotFound(setting=model_setting);
    429 -> QuotaError or ProviderUnavailable with `.code == "rate_limited"`;
    5xx and network errors -> retried once, then ProviderUnavailable; any other
    non-2xx status -> a ProviderError, not retried.

Every request here goes through a fake sender or a patched socket; nothing
reaches the network (the network guard would fail the test).
"""

import ast
import http.client
import io
import socket
import ssl
import sys
import traceback
from pathlib import Path

import pytest

# Fictional values that only look like keys.
FAKE_KEY = "sk-fake-transport-Qm9ja0tleVZhbHVlT25seQ7Zx"
MASKED_ECHO = "sk-fake-****************************7Zx"
BODY_SENTINEL = "provider-body-sentinel-text"
URL = "https://api.provider.invalid/v1/fictional/endpoint"
REQUEST_BODY = b'{"prompt": "a fictional goblin who collects bells"}'
SECRET_HEADERS = {
    "Authorization": f"Bearer {FAKE_KEY}",
    "x-api-key": FAKE_KEY,
    "x-goog-api-key": FAKE_KEY,
    "Content-Type": "application/json",
}

SERVER_ERROR_STATUSES = (500, 502, 503, 504, 529, 599)
OTHER_CLIENT_STATUSES = (400, 405, 409, 413, 422)
NETWORK_ERRORS = (
    TimeoutError,
    socket.timeout,
    ConnectionResetError,
    ConnectionRefusedError,
    ConnectionAbortedError,
    socket.gaierror,
    OSError,
    http.client.RemoteDisconnected,
    http.client.BadStatusLine,
)


def _transport():
    import providers.transport

    return providers.transport


def _errors():
    import providers.errors

    return providers.errors


def _response(status, body=b"", headers=None):
    return _transport().HttpResponse(status=status, headers=headers or {}, body=body)


def _echo_body(status_text="error"):
    """A provider error body that echoes a masked key and the full key, as a rejected-key body can."""
    return (
        '{"error": {"message": "%s: Incorrect API key provided: %s. %s. key=%s", '
        '"type": "invalid_request_error"}}' % (status_text, MASKED_ECHO, BODY_SENTINEL, FAKE_KEY)
    ).encode("utf-8")


class FakeSend:
    """Scripted stand-in for the standard-library sender; records every call."""

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def __call__(self, method, url, headers, body, *, connect_timeout, read_timeout):
        self.calls.append(
            {
                "method": method,
                "url": url,
                "headers": dict(headers),
                "body": body,
                "connect_timeout": connect_timeout,
                "read_timeout": read_timeout,
            }
        )
        if not self.outcomes:
            raise AssertionError("the transport sent more requests than scripted")
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def _request(send, *, read_timeout=None, model_setting="LLM_MODEL", is_quota_error=None, headers=None):
    transport = _transport()
    return transport.request(
        "POST",
        URL,
        headers=SECRET_HEADERS if headers is None else headers,
        body=REQUEST_BODY,
        read_timeout=transport.TEXT_READ_TIMEOUT if read_timeout is None else read_timeout,
        model_setting=model_setting,
        is_quota_error=is_quota_error or (lambda response: False),
        send=send,
    )


def _assert_error_text_is_clean(error):
    """RN-06: neither the key, the masked echo nor the response body reaches any error text."""
    texts = [str(error), repr(error), *(str(arg) for arg in error.args)]
    texts.append("".join(traceback.format_exception(error)))
    for text in texts:
        assert FAKE_KEY not in text
        assert MASKED_ECHO not in text
        assert BODY_SENTINEL not in text
        assert "Bearer" not in text
    assert str(error).strip(), "RN-10: the error carries a clear, non-empty message"


# --- Named timeouts --------------------------------------------------------


def test_rn10_timeouts_are_named_constants():
    """RN-10 (plan 9.2): connect 10 s, text read 180 s, image read 300 s."""
    transport = _transport()
    assert transport.CONNECT_TIMEOUT == 10
    assert transport.TEXT_READ_TIMEOUT == 180
    assert transport.IMAGE_READ_TIMEOUT == 300


@pytest.mark.parametrize("name", ["TEXT_READ_TIMEOUT", "IMAGE_READ_TIMEOUT"])
def test_rn10_every_attempt_uses_the_connect_and_the_chosen_read_timeout(name):
    """RN-10: the sender gets the connect timeout and the read timeout the caller chose,
    on the first attempt and on the retry."""
    transport = _transport()
    read_timeout = getattr(transport, name)
    send = FakeSend(_response(503), _response(200, b"{}"))
    _request(send, read_timeout=read_timeout)
    assert len(send.calls) == 2
    for call in send.calls:
        assert call["connect_timeout"] == transport.CONNECT_TIMEOUT
        assert call["read_timeout"] == read_timeout


def test_rn10_a_timeout_is_retried_once_then_becomes_provider_unavailable():
    """RN-10: a provider that does not answer in time is a clear outage, after one retry."""
    errors = _errors()
    send = FakeSend(TimeoutError("timed out"), TimeoutError("timed out"))
    with pytest.raises(errors.ProviderUnavailable) as caught:
        _request(send)
    assert len(send.calls) == 2
    _assert_error_text_is_clean(caught.value)


# --- Success path -----------------------------------------------------------


def test_rn10_a_success_response_is_returned_untouched_after_one_call():
    """RN-10: a 2xx answer is handed to the adapter as is, with no retry."""
    body = '{"name": "Bellkeeper Goblin", "cost": "{1}{R/P}", "note": "ção — \U0001f514"}'.encode()
    send = FakeSend(_response(200, body, {"Content-Type": "application/json"}))
    response = _request(send)
    assert response.status == 200
    assert response.body == body
    assert len(send.calls) == 1


@pytest.mark.parametrize("body", [b"", b"not json at all", b"\xff\xfe\x00garbage", b"{" * 10000])
def test_rn10_a_malformed_success_body_is_left_to_the_adapter(body):
    """RN-10: the transport does not judge a 2xx body; the adapter maps it to InvalidResponse
    with its usage, so the transport neither raises nor retries."""
    send = FakeSend(_response(200, body))
    response = _request(send)
    assert response.body == body
    assert len(send.calls) == 1


def test_rn06_the_request_goes_out_as_given_with_the_key_only_in_headers():
    """RN-06 (plan 9.2): the method, URL, headers and body reach the sender unchanged;
    the transport never moves the key into the URL."""
    send = FakeSend(_response(200, b"{}"))
    _request(send)
    call = send.calls[0]
    assert call["method"] == "POST"
    assert call["url"] == URL
    assert FAKE_KEY not in call["url"]
    assert call["headers"] == SECRET_HEADERS
    assert call["body"] == REQUEST_BODY


# --- Retry -----------------------------------------------------------------


@pytest.mark.parametrize("status", SERVER_ERROR_STATUSES)
def test_rn10_a_server_error_is_retried_once_and_the_retry_can_succeed(status):
    """RN-10 (plan 9.2): one retry on 5xx; a success on the retry is returned."""
    send = FakeSend(_response(status, _echo_body()), _response(200, b'{"ok": true}'))
    response = _request(send)
    assert response.status == 200
    assert len(send.calls) == 2
    assert send.calls[0] == send.calls[1], "the retry resends the same request"


@pytest.mark.parametrize("status", SERVER_ERROR_STATUSES)
def test_rn10_two_server_errors_become_provider_unavailable(status):
    """RN-10: a provider failing twice is an outage, with a clean message and no third call."""
    errors = _errors()
    send = FakeSend(_response(status, _echo_body()), _response(status, _echo_body()))
    with pytest.raises(errors.ProviderUnavailable) as caught:
        _request(send)
    assert len(send.calls) == 2
    assert getattr(caught.value, "code", None) != "rate_limited"
    _assert_error_text_is_clean(caught.value)


@pytest.mark.parametrize("error_class", NETWORK_ERRORS)
def test_rn10_a_network_error_is_retried_once_and_the_retry_can_succeed(error_class):
    """RN-10 (plan 9.2): one retry on network errors."""
    send = FakeSend(_network_error(error_class), _response(200, b"{}"))
    response = _request(send)
    assert response.status == 200
    assert len(send.calls) == 2


@pytest.mark.parametrize("error_class", NETWORK_ERRORS)
def test_rn10_two_network_errors_become_provider_unavailable(error_class):
    """RN-10: a provider that cannot be reached is an outage, after one retry.
    RN-06: the text of the low-level error, here echoing the key, is not reused."""
    errors = _errors()
    send = FakeSend(_network_error(error_class), _network_error(error_class))
    with pytest.raises(errors.ProviderUnavailable) as caught:
        _request(send)
    assert len(send.calls) == 2
    assert getattr(caught.value, "code", None) != "rate_limited"
    error = caught.value
    for text in (str(error), repr(error), *(str(arg) for arg in error.args)):
        assert FAKE_KEY not in text
        assert MASKED_ECHO not in text
        assert BODY_SENTINEL not in text
    assert str(error).strip()


def _network_error(error_class):
    return error_class(f"connection failed near {MASKED_ECHO} {BODY_SENTINEL} {FAKE_KEY}")


@pytest.mark.parametrize(
    "first, second, expected",
    [
        (TimeoutError("timed out"), (503, b""), "ProviderUnavailable"),
        ((502, b""), ConnectionResetError("reset"), "ProviderUnavailable"),
        ((500, b""), (401, b""), "AuthError"),
        (ConnectionResetError("reset"), (404, b""), "ModelNotFound"),
    ],
)
def test_rn10_the_retry_answer_is_mapped_like_a_first_answer(first, second, expected):
    """RN-10: after the one retry, its own outcome decides the error; there is no third call."""
    errors = _errors()
    outcomes = [o if isinstance(o, BaseException) else _response(*o) for o in (first, second)]
    send = FakeSend(*outcomes)
    with pytest.raises(getattr(errors, expected)):
        _request(send)
    assert len(send.calls) == 2


@pytest.mark.parametrize("status", (401, 403, 404, 429, *OTHER_CLIENT_STATUSES))
def test_rn10_a_client_error_is_not_retried(status):
    """RN-10 (plan 9.2): only 5xx and network errors are retried; a 4xx answer,
    including both kinds of 429, is final."""
    errors = _errors()
    for is_quota in (True, False):
        send = FakeSend(_response(status, _echo_body()))
        with pytest.raises(errors.ProviderError):
            _request(send, is_quota_error=lambda response, value=is_quota: value)
        assert len(send.calls) == 1


def test_rn29_a_blocked_connection_is_not_swallowed_as_a_network_error():
    """RN-29: the test network guard (not an OSError) propagates instead of becoming
    a retry or ProviderUnavailable, so a test that would go out fails loudly."""
    from tests.network_guard import NetworkAccessBlocked

    send = FakeSend(NetworkAccessBlocked("blocked"))
    with pytest.raises(NetworkAccessBlocked):
        _request(send)
    assert len(send.calls) == 1


# --- Status mapping -----------------------------------------------------------


@pytest.mark.parametrize("status", [401, 403])
def test_ca25_a_rejected_key_becomes_auth_error(status):
    """CA-25, RN-08 via RN-10: a rejected key is reported as such, with no key or body in the text."""
    errors = _errors()
    send = FakeSend(_response(status, _echo_body("Unauthorized")))
    with pytest.raises(errors.AuthError) as caught:
        _request(send)
    _assert_error_text_is_clean(caught.value)


@pytest.mark.parametrize("setting", ["LLM_MODEL", "IMAGE_MODEL"])
def test_ca76_an_unknown_model_becomes_model_not_found_naming_the_setting(setting):
    """CA-76: an unknown model names the model setting given by the caller."""
    errors = _errors()
    send = FakeSend(_response(404, _echo_body("The model does not exist")))
    with pytest.raises(errors.ModelNotFound) as caught:
        _request(send, model_setting=setting)
    assert caught.value.setting == setting
    _assert_error_text_is_clean(caught.value)


def test_ca25_a_429_for_quota_becomes_quota_error():
    """CA-25 (plan 9.2): a 429 that the adapter recognizes as quota or billing is QuotaError."""
    errors = _errors()
    seen = []

    def is_quota_error(response):
        seen.append(response)
        return True

    body = _echo_body("insufficient_quota")
    send = FakeSend(_response(429, body, {"Retry-After": "20"}))
    with pytest.raises(errors.QuotaError) as caught:
        _request(send, is_quota_error=is_quota_error)
    assert len(seen) == 1
    assert seen[0].status == 429
    assert seen[0].body == body, "the adapter decides from the provider's own body"
    _assert_error_text_is_clean(caught.value)


def test_rn10_a_429_for_rate_limit_becomes_provider_unavailable_rate_limited():
    """RN-10, RN-08 (plan 9.2): a rate-limit 429 is ProviderUnavailable with code `rate_limited`,
    so the cause shown is the right one."""
    errors = _errors()
    send = FakeSend(_response(429, _echo_body("rate_limit_exceeded")))
    with pytest.raises(errors.ProviderUnavailable) as caught:
        _request(send, is_quota_error=lambda response: False)
    assert caught.value.code == "rate_limited"
    assert not isinstance(caught.value, errors.QuotaError)
    _assert_error_text_is_clean(caught.value)


@pytest.mark.parametrize("body", [b"", b"<html>Too Many Requests</html>", b"\xff\xfe\x00", b"{\"error\": null}"])
def test_rn10_a_429_with_a_malformed_body_still_maps_by_the_adapter_decision(body):
    """RN-10: an empty or malformed 429 body is still classified by the adapter's decision."""
    errors = _errors()
    with pytest.raises(errors.QuotaError):
        _request(FakeSend(_response(429, body)), is_quota_error=lambda response: True)
    with pytest.raises(errors.ProviderUnavailable) as caught:
        _request(FakeSend(_response(429, body)), is_quota_error=lambda response: False)
    assert caught.value.code == "rate_limited"


@pytest.mark.parametrize("status", OTHER_CLIENT_STATUSES)
def test_rn10_another_client_error_is_a_provider_error_with_a_clean_message(status):
    """RN-10: any other refused request still becomes one of the error set, never a raw HTTP error."""
    errors = _errors()
    send = FakeSend(_response(status, _echo_body("Bad request")))
    with pytest.raises(errors.ProviderError) as caught:
        _request(send)
    _assert_error_text_is_clean(caught.value)


# --- No key or body in any error text -----------------------------------------


ALL_FAILURES = [
    [(401, None)],
    [(403, None)],
    [(404, None)],
    [(429, True)],
    [(429, False)],
    [(400, None)],
    [(422, None)],
    [(500, None), (500, None)],
    [(503, None), (529, None)],
]


@pytest.mark.parametrize("script", ALL_FAILURES, ids=lambda script: "-".join(str(s) for s, _ in script))
@pytest.mark.parametrize(
    "body",
    [
        _echo_body(),
        ("x" * 200_000 + MASKED_ECHO + BODY_SENTINEL).encode(),
        f"ção — \U0001f525 {MASKED_ECHO} {BODY_SENTINEL} {FAKE_KEY}".encode("utf-8"),
        f"{MASKED_ECHO} {BODY_SENTINEL}".encode("utf-16"),
    ],
    ids=["json-echo", "huge", "odd-characters", "utf16"],
)
def test_rn06_no_error_text_contains_the_key_or_the_response_body(script, body):
    """RN-06 (plan 9.2): whatever the status, the error text holds neither the key,
    the authorization header, a masked echo of the key nor the provider's body."""
    errors = _errors()
    is_quota = script[0][1]
    send = FakeSend(*(_response(status, body, {"X-Echo": MASKED_ECHO}) for status, _ in script))
    with pytest.raises(errors.ProviderError) as caught:
        _request(send, is_quota_error=lambda response: bool(is_quota))
    _assert_error_text_is_clean(caught.value)


# --- Standard-library sender ------------------------------------------------


class _FakeSocket:
    """A socket that never touches the network: it records what is sent and
    answers with a canned HTTP response."""

    def __init__(self, raw_response):
        self.raw_response = raw_response
        self.sent = b""
        self.timeouts = []
        self.timeout_when_read = None

    def settimeout(self, value):
        self.timeouts.append(value)

    def gettimeout(self):
        return self.timeouts[-1] if self.timeouts else None

    def setsockopt(self, *args):
        pass

    def sendall(self, data):
        self.sent += bytes(data)

    def send(self, data):
        self.sent += bytes(data)
        return len(data)

    def makefile(self, mode="rb", *args, **kwargs):
        self.timeout_when_read = self.gettimeout()
        return io.BytesIO(self.raw_response)

    def close(self):
        pass

    def shutdown(self, *args):
        pass

    def fileno(self):
        return -1


@pytest.fixture
def patched_socket(monkeypatch):
    """Replaces the connection and TLS steps with a fake socket; records the connect timeout."""
    for name in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"):
        monkeypatch.delenv(name, raising=False)
    state = {"connect_timeouts": [], "sockets": [], "responses": []}

    def fake_create_connection(address, timeout=None, *args, **kwargs):
        state["connect_timeouts"].append(timeout)
        raw = state["responses"].pop(0)
        if isinstance(raw, BaseException):
            raise raw
        fake = _FakeSocket(raw)
        if timeout is not None:
            fake.settimeout(timeout)
        state["sockets"].append(fake)
        return fake

    monkeypatch.setattr(socket, "create_connection", fake_create_connection)
    monkeypatch.setattr(ssl.SSLContext, "wrap_socket", lambda self, sock, *args, **kwargs: sock)
    return state


def _raw(status, reason, body):
    return (
        f"HTTP/1.1 {status} {reason}\r\nContent-Type: application/json\r\n"
        f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n"
    ).encode("ascii") + body


def _request_default(read_timeout):
    transport = _transport()
    return transport.request(
        "POST",
        URL,
        headers=SECRET_HEADERS,
        body=REQUEST_BODY,
        read_timeout=read_timeout,
        model_setting="LLM_MODEL",
        is_quota_error=lambda response: False,
    )


@pytest.mark.parametrize("name", ["TEXT_READ_TIMEOUT", "IMAGE_READ_TIMEOUT"])
def test_rn10_the_standard_sender_applies_the_connect_then_the_read_timeout(patched_socket, name):
    """RN-10 (plan 9.2): without an injected sender, the standard-library sender opens the
    connection with the 10 s connect timeout and waits for the answer with the read timeout."""
    transport = _transport()
    read_timeout = getattr(transport, name)
    body = b'{"name": "Bellkeeper Goblin"}'
    patched_socket["responses"].append(_raw(200, "OK", body))
    response = _request_default(read_timeout)
    assert response.status == 200
    assert response.body == body
    assert patched_socket["connect_timeouts"] == [transport.CONNECT_TIMEOUT]
    fake = patched_socket["sockets"][0]
    assert fake.timeout_when_read == read_timeout
    assert b"POST /v1/fictional/endpoint" in fake.sent
    assert REQUEST_BODY in fake.sent
    assert f"x-api-key: {FAKE_KEY}".encode().lower() in fake.sent.lower()


def test_rn10_the_standard_sender_retries_a_refused_connection_once(patched_socket):
    """RN-10: a refused connection through the real sender is retried once, then ProviderUnavailable."""
    errors = _errors()
    patched_socket["responses"].extend([ConnectionRefusedError("refused"), ConnectionRefusedError("refused")])
    with pytest.raises(errors.ProviderUnavailable) as caught:
        _request_default(_transport().TEXT_READ_TIMEOUT)
    assert len(patched_socket["connect_timeouts"]) == 2
    assert FAKE_KEY not in str(caught.value)


def test_rn06_the_standard_sender_maps_a_rejected_key_without_the_body(patched_socket):
    """RN-06, CA-25: a real 401 answer read by the standard sender maps to AuthError
    with no key, masked echo or body in any error text."""
    errors = _errors()
    patched_socket["responses"].append(_raw(401, "Unauthorized", _echo_body("Unauthorized")))
    with pytest.raises(errors.AuthError) as caught:
        _request_default(_transport().TEXT_READ_TIMEOUT)
    assert len(patched_socket["connect_timeouts"]) == 1
    _assert_error_text_is_clean(caught.value)


def test_rn29_the_transport_uses_only_the_standard_library():
    """RN-29, plan 9.2 and 13: the transport is direct HTTP with the standard library
    and the project's own modules; no HTTP client package is added."""
    source = Path(_transport().__file__).read_text(encoding="utf-8")
    allowed = set(sys.stdlib_module_names) | {"providers", "core", "__future__"}
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                continue
            names = [node.module or ""]
        else:
            continue
        for name in names:
            assert name.split(".")[0] in allowed, f"non-standard import {name!r}"
