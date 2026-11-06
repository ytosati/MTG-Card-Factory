"""The key check of tests.configured_api catches a key anywhere in a response (spec RN-06, CA-06, task T6).

These tests build responses by hand, so they need no endpoint.
"""

import json

import pytest
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse

from tests.config_files import FAKE_IMAGE_KEY, FAKE_TEXT_KEY, full_text_settings
from tests.configured_api import (
    assert_error_envelope,
    assert_no_key_in_response,
    configured_api,  # noqa: F401 (fixture)
)

ODD_KEY = 'sk-fake-"quoted"\\ção✓-not-real-8888'


def test_t6_rn06_clean_response_passes():
    """RN-06 / T6: a response with no key passes the check."""
    response = JsonResponse({"text_key_configured": True})

    assert_no_key_in_response(response, [FAKE_TEXT_KEY, FAKE_IMAGE_KEY])


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(lambda key: HttpResponse(f"prefix {key} suffix"), id="plain-body"),
        pytest.param(lambda key: JsonResponse({"nested": [{"value": key}]}), id="json-body"),
        pytest.param(lambda key: JsonResponse({key: 1}), id="json-name"),
        pytest.param(
            lambda key: HttpResponse(json.dumps({"v": key}, ensure_ascii=True), content_type="application/json"),
            id="json-ascii-escaped",
        ),
        pytest.param(lambda key: StreamingHttpResponse(iter([b"part ", key.encode("utf-8")])), id="streaming"),
    ],
)
@pytest.mark.parametrize("key", [FAKE_TEXT_KEY, ODD_KEY])
def test_t6_rn06_key_in_body_fails(build, key):
    """RN-06 / CA-06 / T6: a key in the body, raw or JSON-escaped, fails the check."""
    response = build(key)

    with pytest.raises(AssertionError) as caught:
        assert_no_key_in_response(response, [key])

    assert key not in str(caught.value), "the failure message must not print the key"


def test_t6_rn06_key_in_header_fails():
    """RN-06 / CA-06 / T6: a key in a response header fails the check."""
    response = JsonResponse({})
    response["X-Debug"] = f"key={FAKE_IMAGE_KEY}"

    with pytest.raises(AssertionError):
        assert_no_key_in_response(response, [FAKE_IMAGE_KEY])


def test_t6_rn06_key_in_cookie_fails():
    """RN-06 / CA-06 / T6: a key in a cookie fails the check."""
    response = JsonResponse({})
    response.set_cookie("leak", FAKE_TEXT_KEY)

    with pytest.raises(AssertionError):
        assert_no_key_in_response(response, [FAKE_TEXT_KEY])


def test_t6_rn06_streaming_body_is_still_readable_after_the_check():
    """T6: the check reads a streaming body and gives it back to the caller."""
    response = StreamingHttpResponse(iter([b"one ", b"two"]))

    assert_no_key_in_response(response, [FAKE_TEXT_KEY])

    assert b"".join(response.streaming_content) == b"one two"


def test_t6_rn06_short_values_are_skipped():
    """T6: values under 8 characters are not searched, like the log filter (plan section 8)."""
    response = HttpResponse("a short word: abc")

    assert_no_key_in_response(response, ["abc", "", None])


def test_t6_configure_records_written_keys_as_secrets(configured_api):
    """RN-06 / T6: every key written to the file is checked, plus extra values the test names."""
    extra = "sk-fake-extra-9999-EXTRAKEY-not-real-0000"
    custom = "sk-fake-custom-1212-CUSTOM-not-real-3434"
    configured_api.configure(full_text_settings(key=custom) | {"IMAGE_API_KEY": ODD_KEY}, secrets=[extra])

    assert {custom, ODD_KEY, extra, FAKE_TEXT_KEY, FAKE_IMAGE_KEY} <= configured_api.secrets


def test_t6_configure_writes_into_a_temporary_home(configured_api):
    """T6 / T4: the fake configuration lives in a temporary home, never the repository."""
    from core.paths import REPOSITORY_ROOT, app_home

    path = configured_api.configure(full_text_settings())

    assert app_home() == configured_api.home
    assert path == configured_api.home / ".env"
    assert REPOSITORY_ROOT not in path.parents


def test_t6_configure_change_is_seen_by_get_config(configured_api):
    """CA-73 / T6: each write moves the modification time, so get_config() reads the new file."""
    from core.config import get_config

    configured_api.configure(full_text_settings(model="fake-text-model-1"))
    assert get_config().llm_model == "fake-text-model-1"

    configured_api.configure(full_text_settings(model="fake-text-model-2"))
    assert get_config().llm_model == "fake-text-model-2"


def test_t6_envelope_check_rejects_extra_fields():
    """T6 / plan section 6: the envelope has exactly code, message, setting and fields."""
    response = JsonResponse(
        {"error": {"code": "not_found", "message": "Not found.", "setting": None, "fields": None, "detail": "x"}},
        status=404,
    )

    with pytest.raises(AssertionError):
        assert_error_envelope(response, 404, "not_found")


def test_t6_envelope_check_accepts_the_plan_shape():
    """T6 / plan section 6: a well-formed envelope passes and its error object is returned."""
    response = JsonResponse(
        {"error": {"code": "not_found", "message": "Not found.", "setting": None, "fields": None}},
        status=404,
    )

    error = assert_error_envelope(response, 404, "not_found")

    assert error["code"] == "not_found"
