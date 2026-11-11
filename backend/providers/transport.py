"""Shared standard-library HTTP transport for the provider adapters.

Details: specs/plan.md, section 9.2. Error texts never include the key, the
request headers or the provider's response body (see spec RN-06).
"""

import http.client
import ssl
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlsplit

from core.errors import CODE_RATE_LIMITED
from providers.errors import (
    AuthError,
    ModelNotFound,
    ProviderError,
    ProviderUnavailable,
    QuotaError,
)

CONNECT_TIMEOUT = 10
TEXT_READ_TIMEOUT = 180
IMAGE_READ_TIMEOUT = 300

# Network failures worth one retry. The test network guard is not one of them,
# so a test that would go out fails instead of being retried.
_NETWORK_ERRORS = (OSError, http.client.HTTPException)


@dataclass(frozen=True)
class HttpResponse:
    """Status, headers (names in lowercase) and raw body of one HTTP answer."""

    status: int
    headers: dict[str, str]
    body: bytes

    def __post_init__(self) -> None:
        object.__setattr__(self, "headers", {name.lower(): value for name, value in self.headers.items()})


Sender = Callable[..., HttpResponse]


def request(
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    body: bytes | None,
    read_timeout: float,
    model_setting: str,
    is_quota_error: Callable[[HttpResponse], bool],
    send: Sender | None = None,
    classify_error: Callable[[HttpResponse], ProviderError | None] | None = None,
) -> HttpResponse:
    """Send one request, retrying once on 5xx or a network error, and return the 2xx answer.

    `is_quota_error` tells a quota 429 from a rate-limit 429; `model_setting`
    is the setting ModelNotFound names. `classify_error`, when given, maps a
    non-2xx answer first; returning None falls back to the default mapping.
    """
    if not all(_sendable(value) for value in headers.values()):
        raise AuthError("The API key contains characters that cannot be sent. Copy the key again.")
    sender = send or _send
    response: HttpResponse | None = None
    failure: str | None = None
    for _ in range(2):
        # Failures are only noted inside `except` and raised after it, so the
        # raised error keeps no reference to the original one, whose text can
        # hold the key or the request details.
        failure = None
        try:
            response = sender(
                method, url, headers, body, connect_timeout=CONNECT_TIMEOUT, read_timeout=read_timeout
            )
        except _NETWORK_ERRORS:
            failure = "network"
        except ValueError:
            failure = "unsendable"
        if failure == "unsendable":
            raise ProviderError("The request could not be built. Check the model name and the API key.")
        if failure == "network":
            continue
        if response.status >= 500:
            continue
        break
    if response is None or failure == "network":
        raise ProviderUnavailable("The provider could not be reached. Check the connection and try again.")
    if 200 <= response.status < 300:
        return response
    if classify_error is not None:
        error = classify_error(response)
        if error is not None:
            raise error
    raise _status_error(response, model_setting, is_quota_error)


def _sendable(value: str) -> bool:
    # http.client refuses CR and LF in a header value and encodes it as Latin-1;
    # its own error would quote the whole value, key included.
    if "\r" in value or "\n" in value:
        return False
    try:
        value.encode("latin-1")
    except UnicodeEncodeError:
        return False
    return True


def _status_error(
    response: HttpResponse, model_setting: str, is_quota_error: Callable[[HttpResponse], bool]
) -> ProviderError:
    status = response.status
    if status in (401, 403):
        return AuthError("The provider rejected the API key.")
    if status == 404:
        return ModelNotFound(f"The provider does not know the model set in {model_setting}.", setting=model_setting)
    if status == 429:
        if is_quota_error(response):
            return QuotaError("The provider account has no quota or credit left.")
        return ProviderUnavailable(
            "The provider is limiting requests. Wait a moment and try again.", code=CODE_RATE_LIMITED
        )
    if status >= 500:
        return ProviderUnavailable("The provider is not answering. Try again later.")
    return ProviderError(f"The provider refused the request (HTTP {status}).")


def _send(
    method: str,
    url: str,
    headers: dict[str, str],
    body: bytes | None,
    *,
    connect_timeout: float,
    read_timeout: float,
) -> HttpResponse:
    """Standard-library sender: connect with `connect_timeout`, then wait for the answer with `read_timeout`."""
    parts = urlsplit(url)
    if parts.scheme == "https":
        connection = http.client.HTTPSConnection(
            parts.hostname, parts.port, timeout=connect_timeout, context=ssl.create_default_context()
        )
    elif parts.scheme == "http":
        connection = http.client.HTTPConnection(parts.hostname, parts.port, timeout=connect_timeout)
    else:
        raise ValueError("Unsupported URL scheme for a provider request.")
    target = parts.path or "/"
    if parts.query:
        target = f"{target}?{parts.query}"
    try:
        connection.connect()
        connection.sock.settimeout(read_timeout)
        connection.request(method, target, body=body, headers=headers)
        answer = connection.getresponse()
        return HttpResponse(status=answer.status, headers=dict(answer.getheaders()), body=answer.read())
    finally:
        connection.close()
