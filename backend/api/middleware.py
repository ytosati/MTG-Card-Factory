"""Origin check: the API refuses state-changing requests from another origin (spec RN-29).
Details: specs/plan.md, section 6.
"""

from urllib.parse import urlsplit

from django.conf import settings
from django.http import JsonResponse

from api.exceptions import error_body

CODE_ORIGIN_REFUSED = "origin_refused"
ORIGIN_REFUSED_MESSAGE = "This request did not come from the Card Factory page and was refused."
ORIGIN_REFUSED_STATUS = 403

SAFE_METHODS = ("GET", "HEAD", "OPTIONS")
OWN_HOSTS = ("127.0.0.1", "localhost")


def _own_origins():
    return {f"http://{host}:{settings.RUNNING_PORT}" for host in OWN_HOSTS}


def _origin_of(url):
    """`scheme://host:port` of a URL, or None when it cannot be read."""
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return None
    if not parts.scheme or not parts.hostname or port is None:
        return None
    return f"{parts.scheme}://{parts.hostname}:{port}"


def is_own_origin(request):
    """True when `Origin` (or, without it, `Referer`) names this application, or neither is sent.

    Browsers always send `Origin` on a cross-site POST; only local non-browser
    clients omit both headers.
    """
    origin = request.META.get("HTTP_ORIGIN")
    if origin is not None:
        return origin in _own_origins()
    referer = request.META.get("HTTP_REFERER")
    if referer is not None:
        return _origin_of(referer) in _own_origins()
    return True


class OriginCheckMiddleware:
    """Answers `origin_refused` before any view runs, so a refused heartbeat never reaches the watchdog."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.path.startswith("/api/")
            and request.method not in SAFE_METHODS
            and not is_own_origin(request)
        ):
            return JsonResponse(
                error_body(CODE_ORIGIN_REFUSED, ORIGIN_REFUSED_MESSAGE), status=ORIGIN_REFUSED_STATUS
            )
        return self.get_response(request)
