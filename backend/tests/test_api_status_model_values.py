"""GET /api/status with model values that look like a key (task T128, spec RN-06, RN-08, CA-06, CA-78).

A model value equal to a configured key value, or starting with `sk-` or
`AIza`, names the model setting to fix (`config_invalid`), is returned as not
set (`null`, the representation of an unset model in the status, see
tests/test_api_status.py) and appears in no response. Each value under test is
given to the key-sweep helper as a secret, so every response is checked for
it (tests.configured_api).

Decided case: an image model that would otherwise be ignored with a notice (no
`IMAGE_PROVIDER` and Anthropic as the text provider) is still reported as the model setting to
fix when its value looks like a key (CA-78), once and never as `ignored`.

Values are fictional; keys only look like keys.
"""

import pytest

from tests.config_files import FAKE_AIZA_MODEL_VALUE, FAKE_IMAGE_KEY, FAKE_TEXT_KEY, full_text_settings
from tests.configured_api import configured_api  # noqa: F401 (fixture)

STATUS_URL = "/api/status"
SETTING_TO_FIX = "config_invalid"
IGNORED = "ignored"

UNPREFIXED_TEXT_KEY = "fake-text-key-1212-NOPREFIX-not-real-3434"
UNPREFIXED_IMAGE_KEY = "fake-image-key-5656-NOPREFIX-not-real-7878"

SK_VALUE = "sk-fake-model-6666-PASTEDKEY-not-real-7777"
AIZA_VALUE = FAKE_AIZA_MODEL_VALUE

PREFIXED_VALUES = [
    pytest.param(SK_VALUE, id="sk"),
    pytest.param("sk-ant-fake-api03-PASTED-not-real-0000", id="sk-ant"),
    pytest.param(AIZA_VALUE, id="AIza"),
    pytest.param("sk-fake-ção-日本語-\"quoted\"-\\back-not-real", id="sk-odd-characters"),
]

ORDINARY_MODELS = [
    pytest.param("fake-model-1", id="plain"),
    pytest.param("skeleton-model-1", id="starts-with-sk-letters"),
    pytest.param("ask-model-1", id="sk-dash-inside"),
    pytest.param("my-AIza-tuned-model", id="AIza-inside"),
    pytest.param("AIz-model-1", id="AIz-short"),
    pytest.param("módelo-✓-ギ-fake", id="non-ascii"),
]


def _status(api):
    response = api.get(STATUS_URL)
    assert response.status_code == 200, response.content[:500]
    return response.json()


def _named(body, code):
    return {entry["setting"] for entry in body["settings"] if entry["code"] == code}


def _assert_reported_once_to_fix(body, setting):
    entries = [entry for entry in body["settings"] if entry["setting"] == setting]
    assert len(entries) == 1, entries
    assert entries[0]["code"] == SETTING_TO_FIX
    assert entries[0]["message"].strip()


# --- Text model ---


@pytest.mark.parametrize("value", PREFIXED_VALUES)
def test_t128_ca78_status_text_model_with_key_prefix(configured_api, value):
    """CA-78 / RN-06 / RN-08 / T128: LLM_MODEL with a key prefix is named to fix, returned as null, never echoed."""
    configured_api.configure(full_text_settings(model=value), secrets=[value])

    body = _status(configured_api)

    assert body["text_model"] is None
    assert _named(body, SETTING_TO_FIX) == {"LLM_MODEL"}
    _assert_reported_once_to_fix(body, "LLM_MODEL")
    assert body["text_provider"] == "openai"
    assert body["text_key_configured"] is True


def test_t128_ca78_status_text_model_equal_to_text_key(configured_api):
    """CA-78 / RN-06 / T128: LLM_MODEL equal to LLM_API_KEY is named to fix, returned as null, never echoed."""
    configured_api.configure(
        full_text_settings(model=UNPREFIXED_TEXT_KEY, key=UNPREFIXED_TEXT_KEY), secrets=[UNPREFIXED_TEXT_KEY]
    )

    body = _status(configured_api)

    assert body["text_model"] is None
    assert _named(body, SETTING_TO_FIX) == {"LLM_MODEL"}
    _assert_reported_once_to_fix(body, "LLM_MODEL")
    assert body["text_key_configured"] is True


def test_t128_ca78_status_text_model_equal_to_image_key(configured_api):
    """CA-78 / RN-06 / T128: LLM_MODEL equal to IMAGE_API_KEY is named to fix, returned as null, never echoed."""
    configured_api.configure(
        full_text_settings(model=UNPREFIXED_IMAGE_KEY)
        | {"IMAGE_PROVIDER": "google", "IMAGE_API_KEY": UNPREFIXED_IMAGE_KEY, "IMAGE_MODEL": "fake-image-model-1"},
        secrets=[UNPREFIXED_IMAGE_KEY],
    )

    body = _status(configured_api)

    assert body["text_model"] is None
    assert body["image_model"] == "fake-image-model-1"
    assert _named(body, SETTING_TO_FIX) == {"LLM_MODEL"}


def test_t128_ca78_status_text_model_equal_to_ignored_image_key(configured_api):
    """CA-78 / RN-06 / T128: LLM_MODEL equal to an IMAGE_API_KEY ignored for lack of IMAGE_PROVIDER is never echoed."""
    configured_api.configure(
        full_text_settings(model=UNPREFIXED_IMAGE_KEY) | {"IMAGE_API_KEY": UNPREFIXED_IMAGE_KEY},
        secrets=[UNPREFIXED_IMAGE_KEY],
    )

    body = _status(configured_api)

    assert body["text_model"] is None
    assert _named(body, SETTING_TO_FIX) == {"LLM_MODEL"}
    assert _named(body, IGNORED) == {"IMAGE_API_KEY"}


# --- Image model ---


@pytest.mark.parametrize("value", PREFIXED_VALUES)
@pytest.mark.parametrize("image_provider", ["openai", "google"])
def test_t128_ca78_status_image_model_with_key_prefix(configured_api, value, image_provider):
    """CA-78 / RN-06 / RN-08 / T128: IMAGE_MODEL with a key prefix is named to fix, returned as null, never echoed."""
    configured_api.configure(
        full_text_settings()
        | {"IMAGE_PROVIDER": image_provider, "IMAGE_API_KEY": FAKE_IMAGE_KEY, "IMAGE_MODEL": value},
        secrets=[value],
    )

    body = _status(configured_api)

    assert body["image_model"] is None
    assert body["image_provider"] == image_provider
    assert _named(body, SETTING_TO_FIX) == {"IMAGE_MODEL"}
    _assert_reported_once_to_fix(body, "IMAGE_MODEL")
    assert body["text_model"] == "fake-text-model-1"


def test_t128_ca78_status_image_model_equal_to_image_key(configured_api):
    """CA-78 / RN-06 / T128: IMAGE_MODEL equal to IMAGE_API_KEY is named to fix, returned as null, never echoed."""
    configured_api.configure(
        full_text_settings()
        | {"IMAGE_PROVIDER": "google", "IMAGE_API_KEY": UNPREFIXED_IMAGE_KEY, "IMAGE_MODEL": UNPREFIXED_IMAGE_KEY},
        secrets=[UNPREFIXED_IMAGE_KEY],
    )

    body = _status(configured_api)

    assert body["image_model"] is None
    assert _named(body, SETTING_TO_FIX) == {"IMAGE_MODEL"}
    _assert_reported_once_to_fix(body, "IMAGE_MODEL")


def test_t128_ca78_status_image_model_equal_to_text_key(configured_api):
    """CA-78 / RN-06 / T128: IMAGE_MODEL equal to LLM_API_KEY (image key falling back to it) is never echoed."""
    configured_api.configure(
        full_text_settings(key=UNPREFIXED_TEXT_KEY) | {"IMAGE_PROVIDER": "openai", "IMAGE_MODEL": UNPREFIXED_TEXT_KEY},
        secrets=[UNPREFIXED_TEXT_KEY],
    )

    body = _status(configured_api)

    assert body["image_model"] is None
    assert body["text_model"] == "fake-text-model-1"
    assert _named(body, SETTING_TO_FIX) == {"IMAGE_MODEL"}


@pytest.mark.parametrize("text_provider", ["openai", "google"])
@pytest.mark.parametrize("value", [SK_VALUE, AIZA_VALUE, UNPREFIXED_TEXT_KEY])
def test_t128_ca78_status_image_model_on_text_provider_looking_like_a_key(configured_api, text_provider, value):
    """CA-78 / RN-06 / T128: with no IMAGE_PROVIDER and an image-capable text provider, a key-like IMAGE_MODEL is dropped."""
    configured_api.configure(
        full_text_settings(provider=text_provider, key=UNPREFIXED_TEXT_KEY) | {"IMAGE_MODEL": value},
        secrets=[value, UNPREFIXED_TEXT_KEY],
    )

    body = _status(configured_api)

    assert body["image_model"] is None
    assert _named(body, SETTING_TO_FIX) == {"IMAGE_MODEL"}
    _assert_reported_once_to_fix(body, "IMAGE_MODEL")


@pytest.mark.parametrize("value", [SK_VALUE, AIZA_VALUE, UNPREFIXED_TEXT_KEY])
def test_t128_ca78_status_ignored_image_model_looking_like_a_key(configured_api, value):
    """CA-78 / RN-06 / T128: with no IMAGE_PROVIDER and Anthropic text, a key-like IMAGE_MODEL is named to fix, not ignored.

    Decided case: the value is never returned, and the setting is reported
    once, as `config_invalid` (CA-78), instead of the `ignored` notice.
    """
    configured_api.configure(
        full_text_settings(provider="anthropic", key=UNPREFIXED_TEXT_KEY) | {"IMAGE_MODEL": value},
        secrets=[value, UNPREFIXED_TEXT_KEY],
    )

    body = _status(configured_api)

    assert body["image_model"] is None
    assert _named(body, SETTING_TO_FIX) == {"IMAGE_MODEL"}
    assert "IMAGE_MODEL" not in _named(body, IGNORED)
    _assert_reported_once_to_fix(body, "IMAGE_MODEL")


def test_t128_ca78_status_both_models_looking_like_keys(configured_api):
    """CA-78 / RN-08 / T128: a key-like value in both model settings names both, and neither value is returned."""
    configured_api.configure(
        full_text_settings(model=SK_VALUE)
        | {"IMAGE_PROVIDER": "google", "IMAGE_API_KEY": FAKE_IMAGE_KEY, "IMAGE_MODEL": AIZA_VALUE},
        secrets=[SK_VALUE, AIZA_VALUE],
    )

    body = _status(configured_api)

    assert body["text_model"] is None
    assert body["image_model"] is None
    assert _named(body, SETTING_TO_FIX) == {"LLM_MODEL", "IMAGE_MODEL"}


def test_t128_ca73_status_fixed_model_is_seen_on_the_next_call(configured_api):
    """CA-73 / CA-78 / T128: after the key-like model is replaced by a model name, the status shows it with nothing to fix."""
    configured_api.configure(full_text_settings(model=SK_VALUE), secrets=[SK_VALUE])
    assert _status(configured_api)["text_model"] is None

    configured_api.configure(full_text_settings(model="fake-text-model-2"))
    body = _status(configured_api)

    assert body["text_model"] == "fake-text-model-2"
    assert body["settings"] == []


# --- Ordinary model names ---


@pytest.mark.parametrize("model", ORDINARY_MODELS)
def test_t128_rn08_status_ordinary_models_returned_unchanged(configured_api, model):
    """RN-08 / CA-78 / T128: ordinary model names, even close to a key prefix, are returned as written."""
    configured_api.configure(
        full_text_settings(model=model)
        | {"IMAGE_PROVIDER": "openai", "IMAGE_API_KEY": FAKE_IMAGE_KEY, "IMAGE_MODEL": model}
    )

    body = _status(configured_api)

    assert body["text_model"] == model
    assert body["image_model"] == model
    assert body["settings"] == []
    assert body["text_key_configured"] is True


def test_t128_ca06_status_keys_still_never_returned_with_ordinary_models(configured_api):
    """CA-06 / RN-06 / T128: with ordinary models, the default fake keys still appear in no response."""
    configured_api.configure(
        full_text_settings() | {"IMAGE_PROVIDER": "google", "IMAGE_API_KEY": FAKE_IMAGE_KEY, "IMAGE_MODEL": "fake-image-model-1"}
    )

    body = _status(configured_api)

    assert {FAKE_TEXT_KEY, FAKE_IMAGE_KEY} <= configured_api.secrets
    assert body["image_model"] == "fake-image-model-1"
