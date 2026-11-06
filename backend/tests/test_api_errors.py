"""Error envelope of the API (task T6, plan section 6, spec RN-06).

Every API error answers `{"error": {"code", "message", "setting", "fields"}}`.
An unknown `/api/` path answers 404 with code `not_found`, never an HTML page.
"""

import pytest

from tests.config_files import full_text_settings
from tests.configured_api import assert_error_envelope, configured_api  # noqa: F401 (fixture)

UNKNOWN_API_PATHS = [
    "/api/",
    "/api/does-not-exist",
    "/api/does-not-exist/",
    "/api/status/extra",
    "/api/unknown/deep/path?q=1",
    "/api/%E2%9C%93-%F0%9F%9C%B2",
    "/api/" + "a" * 2_000,
    "/api/0",
    "/api/-1",
]


@pytest.mark.parametrize("path", UNKNOWN_API_PATHS)
def test_t6_unknown_api_path_answers_404_in_the_envelope(configured_api, path):
    """T6 / plan section 6: an unknown /api/ path answers 404 with code not_found in the envelope."""
    configured_api.configure(full_text_settings())

    response = configured_api.get(path)

    error = assert_error_envelope(response, 404, "not_found")
    assert error["setting"] is None
    assert error["fields"] is None


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_t6_unknown_api_path_answers_404_for_every_method(configured_api, method):
    """T6 / plan section 6: the envelope applies to an unknown /api/ path whatever the method."""
    configured_api.configure(full_text_settings())

    response = configured_api.request(method, "/api/does-not-exist", data={"idea": "fictional"})

    assert_error_envelope(response, 404, "not_found")


def test_t6_unknown_api_path_is_never_html(configured_api):
    """T6 / plan section 6: an unknown /api/ path never answers with an HTML page."""
    configured_api.configure(full_text_settings())

    response = configured_api.get("/api/no-such-endpoint")

    assert b"<html" not in response.content.lower()
    assert b"<!doctype" not in response.content.lower()


def test_t6_rn06_not_found_holds_no_key_with_debug_on(configured_api, monkeypatch, settings):
    """RN-06 / CA-06 / T6: even with DEBUG on, the 404 envelope repeats no key from the configuration."""
    monkeypatch.setenv("CARDFACTORY_DEBUG", "1")
    settings.DEBUG = True
    configured_api.configure(full_text_settings())

    response = configured_api.get("/api/does-not-exist")

    assert_error_envelope(response, 404, "not_found")


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_t6_unsupported_method_on_status_answers_405_in_the_envelope(configured_api, method):
    """T6 / plan section 6 / RN-06: a method /api/status does not accept answers 405 with code
    method_not_allowed in the envelope, never HTML, and with no key in the response."""
    configured_api.configure(full_text_settings())

    response = configured_api.request(method, "/api/status", data={"idea": "fictional"})

    error = assert_error_envelope(response, 405, "method_not_allowed")
    assert error["setting"] is None
    assert error["fields"] is None
    assert b"<html" not in response.content.lower()
    assert b"<!doctype" not in response.content.lower()
