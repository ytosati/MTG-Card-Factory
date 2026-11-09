"""Exceptions mapped to the error envelope, and a status that needs no account or database
(task T6, plan section 6, spec RN-06, RN-40, CA-06, CA-46).

No test here is marked `django_db`: pytest-django blocks database access, so a
status that touched the database would fail.
"""

import json

import pytest

from tests.config_files import FAKE_TEXT_KEY, full_text_settings
from tests.configured_api import (
    ENVELOPE_FIELDS,
    assert_error_envelope,
    configured_api,  # noqa: F401 (fixture)
)

STATUS_URL = "/api/status"
DRF_NOT_ACCEPTABLE_TEXT = "Could not satisfy"


def _envelope(response, status):
    """The `error` object of an envelope with `status`, whatever its code."""
    assert response.status_code == status, response.content[:500]
    assert response["Content-Type"].startswith("application/json")
    payload = json.loads(response.content.decode("utf-8"))
    assert set(payload) == {"error"}, payload
    assert set(payload["error"]) == ENVELOPE_FIELDS, payload
    return payload["error"]


def _internal_message(api):
    """The fixed message of an `internal` error, taken from an unmapped RuntimeError."""
    error = assert_error_envelope(api.get("/api/test-errors/runtime"), 500, "internal")
    return error["message"]


# --- M1: no account and no database for the status ---


@pytest.mark.parametrize(
    "authorization",
    [
        pytest.param("Basic Zm9vOmJhcg==", id="basic-valid-encoding"),
        pytest.param("Basic !!!", id="basic-malformed"),
        pytest.param("Basic", id="basic-without-credentials"),
        pytest.param(f"Bearer {FAKE_TEXT_KEY}", id="bearer-fake-key"),
        pytest.param("Token ✓ ção 🜲", id="odd-characters"),
        pytest.param("", id="empty"),
    ],
)
def test_t6_rn40_status_ignores_authorization_headers(configured_api, authorization):
    """RN-40 / CA-46 / RN-06 / T6: the product has no accounts; any Authorization header still gets
    the 200 status, without touching the database and without echoing the header."""
    configured_api.configure(full_text_settings())

    response = configured_api.get(STATUS_URL, HTTP_AUTHORIZATION=authorization)

    assert response.status_code == 200, response.content[:500]
    body = json.loads(response.content.decode("utf-8"))
    assert body["text_key_configured"] is True
    assert body["settings"] == []


def test_t6_rn40_status_with_a_missing_key_needs_no_database(configured_api):
    """RN-40 / CA-46 / T6: with a missing key the status answers without any database access."""
    configured_api.configure(full_text_settings(key=""))

    response = configured_api.get(STATUS_URL)

    assert response.status_code == 200, response.content[:500]
    body = json.loads(response.content.decode("utf-8"))
    assert "LLM_API_KEY" in {entry["setting"] for entry in body["settings"]}


# --- M2: unmapped exceptions never echo their text ---


@pytest.mark.urls("tests.error_views_urls")
@pytest.mark.parametrize("accept", ["text/html", "application/xml", "image/png"])
def test_t6_not_acceptable_answers_bad_request_with_a_fixed_message(configured_api, accept):
    """T6 / T85 / plan section 6: an Accept the API cannot satisfy answers 406 in the JSON envelope
    with code bad_request and a fixed message, never DRF's own text."""
    configured_api.configure(full_text_settings())

    response = configured_api.get(STATUS_URL, HTTP_ACCEPT=accept)

    error = assert_error_envelope(response, 406, "bad_request")
    assert DRF_NOT_ACCEPTABLE_TEXT not in error["message"]
    assert accept not in error["message"]
    assert error["setting"] is None
    assert error["fields"] is None


@pytest.mark.urls("tests.error_views_urls")
def test_t6_rn06_api_exception_detail_is_never_echoed(configured_api):
    """RN-06 / CA-06 / T6: an APIException whose detail holds a key answers internal with the fixed
    message; the detail never reaches the response."""
    configured_api.configure(full_text_settings())
    fixed = _internal_message(configured_api)

    response = configured_api.get("/api/test-errors/api-exception")

    error = assert_error_envelope(response, 500, "internal")
    assert error["message"] == fixed
    assert "detail" not in error["message"]


# --- M3: unexpected exceptions, Http404 and PermissionDenied ---


@pytest.mark.urls("tests.error_views_urls")
@pytest.mark.parametrize("debug", [False, True], ids=["debug-off", "debug-on"])
def test_t6_rn06_unexpected_exception_answers_500_internal_without_its_text(
    configured_api, settings, monkeypatch, debug
):
    """RN-06 / CA-06 / T6: a RuntimeError holding a key answers 500 internal with a fixed message
    and no key, with DEBUG off and on."""
    if debug:
        monkeypatch.setenv("CARDFACTORY_DEBUG", "1")
    settings.DEBUG = debug
    configured_api.configure(full_text_settings())

    response = configured_api.get("/api/test-errors/runtime")

    error = assert_error_envelope(response, 500, "internal")
    assert "boom" not in error["message"]
    assert error["setting"] is None
    assert error["fields"] is None


@pytest.mark.urls("tests.error_views_urls")
def test_t6_internal_message_is_the_same_for_different_exceptions(configured_api):
    """T6 / plan section 6: the internal message is fixed, not built from the exception."""
    configured_api.configure(full_text_settings())

    first = _internal_message(configured_api)
    second = assert_error_envelope(configured_api.get("/api/test-errors/api-exception"), 500, "internal")

    assert first == second["message"]
    assert first.strip()


@pytest.mark.urls("tests.error_views_urls")
def test_t6_http404_in_a_view_answers_not_found(configured_api):
    """T6 / plan section 6 / RN-06: Http404 raised by an API view answers 404 not_found, no key."""
    configured_api.configure(full_text_settings())

    response = configured_api.get("/api/test-errors/not-found")

    error = assert_error_envelope(response, 404, "not_found")
    assert "missing" not in error["message"]
    assert error["setting"] is None
    assert error["fields"] is None


@pytest.mark.urls("tests.error_views_urls")
def test_t6_permission_denied_answers_403_in_the_envelope(configured_api):
    """T6 / plan section 6 / RN-06: PermissionDenied raised by an API view answers 403 in the
    envelope (the plan names no code for it, so only the shape is fixed), with no key."""
    configured_api.configure(full_text_settings())

    response = configured_api.get("/api/test-errors/permission-denied")

    error = _envelope(response, 403)
    assert isinstance(error["code"], str) and error["code"]
    assert "denied" not in error["message"]
    assert error["setting"] is None
    assert error["fields"] is None
