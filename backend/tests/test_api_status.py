"""GET /api/status, configuration part (task T6, spec RN-06, RN-08, RN-40, RN-47).

Response fields under test (plan section 6; later tasks add fields, never rename these):

    text_provider        str | null   "openai", "anthropic" or "google"; null when not set or unknown
    text_model           str | null   LLM_MODEL as written; null when not set
    text_key_configured  bool         whether LLM_API_KEY is set; never the key
    image_provider       str | null   IMAGE_PROVIDER when set and valid; null otherwise
    image_model          str | null   IMAGE_MODEL when set and not ignored; null otherwise
    settings             list         {setting, code, message}; code "config_invalid" for a
                                      setting to fix, "ignored" for a notice (RN-08)
    next_start_port      int | null   the port the next start will use, when it differs from
                                      the running port (Django setting RUNNING_PORT); else null

Every request goes through tests.configured_api, which writes a temporary
`.env` and fails when a key value appears in a response. No test reads the
repository `.env` or touches the network.
"""

import pytest

from tests.config_files import DEFAULT_PORT, FAKE_IMAGE_KEY, FAKE_TEXT_KEY, full_text_settings
from tests.configured_api import configured_api  # noqa: F401 (fixture)
from tests.settings_probe import BACKEND_DIR, run_probe

STATUS_URL = "/api/status"
SETTING_TO_FIX = "config_invalid"
IGNORED = "ignored"
STATUS_FIELDS = {
    "text_provider",
    "text_model",
    "text_key_configured",
    "image_provider",
    "image_model",
    "settings",
    "next_start_port",
}
OTHER_PORT = 47900
KEY_PASTED_AS_PROVIDER = "sk-fake-pasted-4444-PASTEDKEY-not-real-5555"


def _status(api):
    response = api.get(STATUS_URL)
    assert response.status_code == 200, response.content[:500]
    assert response["Content-Type"].startswith("application/json")
    return response.json()


def _entries(body, code=None):
    return [entry for entry in body["settings"] if code is None or entry["code"] == code]


def _named(body, code):
    return {entry["setting"] for entry in _entries(body, code)}


def _full_configuration():
    return full_text_settings() | {
        "IMAGE_PROVIDER": "google",
        "IMAGE_API_KEY": FAKE_IMAGE_KEY,
        "IMAGE_MODEL": "fake-image-model-1",
        "APP_PORT": str(DEFAULT_PORT),
    }


# --- Shape ---


def test_t6_rn08_status_has_the_configuration_fields(configured_api):
    """RN-08 / T6: the status answers 200 with the configuration fields of plan section 6."""
    configured_api.configure(_full_configuration())

    body = _status(configured_api)

    assert STATUS_FIELDS <= set(body)
    assert isinstance(body["settings"], list)


def test_t6_rn08_each_settings_entry_is_setting_code_message(configured_api):
    """RN-08 / T6: every settings entry is exactly {setting, code, message} with a stable code."""
    configured_api.configure(
        {
            "LLM_PROVIDER": "openia",
            "LLM_API_KEY": "",
            "LLM_MODEL": "",
            "IMAGE_API_KEY": FAKE_IMAGE_KEY,
            "APP_PORT": "not-a-port",
        }
    )

    body = _status(configured_api)

    assert body["settings"], "expected settings to fix and notices"
    for entry in body["settings"]:
        assert set(entry) == {"setting", "code", "message"}
        assert isinstance(entry["setting"], str) and entry["setting"]
        assert entry["code"] in {SETTING_TO_FIX, IGNORED}
        assert isinstance(entry["message"], str) and entry["message"].strip()


# --- Full configuration: booleans only for keys (RN-06, CA-06) ---


def test_t6_ca06_full_configuration_reports_values_and_a_key_boolean(configured_api):
    """CA-06 / RN-06 / T6: a full configuration lists providers and models, a key boolean and nothing to fix."""
    configured_api.configure(_full_configuration())

    body = _status(configured_api)

    assert body["text_provider"] == "openai"
    assert body["text_model"] == "fake-text-model-1"
    assert body["text_key_configured"] is True
    assert body["image_provider"] == "google"
    assert body["image_model"] == "fake-image-model-1"
    assert body["settings"] == []
    assert body["next_start_port"] is None


def _fields_named_like_keys(value, path=""):
    if isinstance(value, dict):
        for name, item in value.items():
            if "key" in name.lower():
                yield f"{path}.{name}", item
            yield from _fields_named_like_keys(item, f"{path}.{name}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _fields_named_like_keys(item, f"{path}[{index}]")


@pytest.mark.parametrize(
    "settings",
    [
        pytest.param(_full_configuration(), id="full"),
        pytest.param(full_text_settings() | {"LLM_API_KEY": ""}, id="missing-key"),
        pytest.param(full_text_settings(provider="anthropic") | {"IMAGE_API_KEY": FAKE_IMAGE_KEY}, id="ignored-image-key"),
        pytest.param(full_text_settings() | {"IMAGE_PROVIDER": "anthropic", "IMAGE_API_KEY": FAKE_IMAGE_KEY}, id="invalid-image-provider"),
    ],
)
def test_t6_rn06_every_key_field_is_a_boolean(configured_api, settings):
    """RN-06 / CA-06 / T6: every field whose name mentions a key holds a boolean, never a value."""
    configured_api.configure(settings)

    body = _status(configured_api)

    found = list(_fields_named_like_keys(body))
    assert found, "expected at least text_key_configured"
    for path, value in found:
        assert isinstance(value, bool), f"{path} must be a boolean"


def test_t6_ca06_response_never_contains_the_keys_or_their_text_form(configured_api):
    """CA-06 / RN-06 / T6: neither key appears, nor the masked text form of a Secret object."""
    configured_api.configure(_full_configuration())

    response = configured_api.get(STATUS_URL)

    text = response.content.decode("utf-8")
    assert FAKE_TEXT_KEY not in text
    assert FAKE_IMAGE_KEY not in text
    assert "***" not in text
    assert "Secret(" not in text


def test_t6_ca06_key_with_odd_characters_never_appears(configured_api):
    """CA-06 / RN-06 / T6: a key with quotes, backslashes, # and non-ASCII characters is not echoed in any form."""
    odd_key = 'sk-fake-"odd"\\key#ção-✓-not-real-0000'
    configured_api.configure(full_text_settings(key=odd_key))

    body = _status(configured_api)

    assert body["text_key_configured"] is True


def test_t6_rn06_key_pasted_into_text_provider_is_not_echoed(configured_api):
    """RN-06 / RN-08 / T6: a key pasted into LLM_PROVIDER names the setting and is never shown back."""
    configured_api.configure(
        full_text_settings() | {"LLM_PROVIDER": KEY_PASTED_AS_PROVIDER},
        secrets=[KEY_PASTED_AS_PROVIDER],
    )

    body = _status(configured_api)

    assert "LLM_PROVIDER" in _named(body, SETTING_TO_FIX)
    assert body["text_provider"] is None


def test_t6_rn06_key_pasted_into_image_provider_is_not_echoed(configured_api):
    """RN-06 / RN-08 / T6: a key pasted into IMAGE_PROVIDER names the setting and is never shown back."""
    configured_api.configure(
        full_text_settings() | {"IMAGE_PROVIDER": KEY_PASTED_AS_PROVIDER, "IMAGE_MODEL": "fake-image-model-1"},
        secrets=[KEY_PASTED_AS_PROVIDER],
    )

    body = _status(configured_api)

    assert "IMAGE_PROVIDER" in _named(body, SETTING_TO_FIX)
    assert body["image_provider"] is None


def test_t6_rn08_model_name_with_odd_characters_is_shown_as_written(configured_api):
    """RN-06 / T6: a model name is free text and shown as written; the key boolean stays separate."""
    configured_api.configure(full_text_settings(model="módelo-✓-ギ-fake"))

    body = _status(configured_api)

    assert body["text_model"] == "módelo-✓-ギ-fake"
    assert body["text_key_configured"] is True


# --- Missing key (CA-46, RN-08, RN-40) ---


@pytest.mark.parametrize(
    "key_line",
    [
        pytest.param(None, id="absent"),
        pytest.param("", id="empty"),
        pytest.param("   ", id="spaces"),
        pytest.param('""', id="empty-quotes"),
    ],
)
def test_t6_ca46_missing_key_names_the_setting(configured_api, key_line):
    """CA-46 / RN-08 / RN-40 / T6: with no text key the status answers and names LLM_API_KEY to fix."""
    settings = {"LLM_PROVIDER": "openai", "LLM_MODEL": "fake-text-model-1"}
    if key_line is not None:
        settings["LLM_API_KEY"] = key_line
    configured_api.configure(settings)

    body = _status(configured_api)

    assert body["text_key_configured"] is False
    assert _named(body, SETTING_TO_FIX) == {"LLM_API_KEY"}
    assert body["text_provider"] == "openai"
    assert body["text_model"] == "fake-text-model-1"


def test_t6_ca46_missing_key_response_holds_no_image_key(configured_api):
    """CA-46 / RN-06 / T6: with the text key missing, an image key in the file still never appears."""
    configured_api.configure(
        {
            "LLM_PROVIDER": "openai",
            "LLM_MODEL": "fake-text-model-1",
            "IMAGE_PROVIDER": "google",
            "IMAGE_API_KEY": FAKE_IMAGE_KEY,
            "IMAGE_MODEL": "fake-image-model-1",
        }
    )

    body = _status(configured_api)

    assert "LLM_API_KEY" in _named(body, SETTING_TO_FIX)
    assert body["text_key_configured"] is False


def test_t6_rn40_missing_file_answers_with_every_text_setting_to_fix(configured_api):
    """RN-40 / RN-08 / T6: without a `.env` the status still answers and names the three text settings."""
    configured_api.remove_configuration()

    body = _status(configured_api)

    assert _named(body, SETTING_TO_FIX) == {"LLM_PROVIDER", "LLM_API_KEY", "LLM_MODEL"}
    assert body["text_provider"] is None
    assert body["text_model"] is None
    assert body["text_key_configured"] is False
    assert body["next_start_port"] is None


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("", id="empty-file"),
        pytest.param("\n\n# only comments\n   \n", id="comments-only"),
        pytest.param("﻿LLM_PROVIDER=banana\nLLM_MODEL\n=orphan\nAPP_PORT=-1\n", id="malformed-lines"),
        pytest.param("LLM_PROVIDER=" + "x" * 100_000 + "\nAPP_PORT=" + "9" * 5_000 + "\n", id="huge-values"),
        pytest.param("LLM_PROVIDER=\x00\x01\x7f\nLLM_MODEL=☠\nIMAGE_PROVIDER=🜲\n", id="control-and-symbols"),
    ],
)
def test_t6_rn40_invalid_configuration_never_blocks_the_status(configured_api, text):
    """RN-40 / RN-08 / T6: invalid or garbled values still give a 200 status that names settings to fix."""
    configured_api.configure(text=text)

    body = _status(configured_api)

    assert STATUS_FIELDS <= set(body)
    assert "LLM_PROVIDER" in _named(body, SETTING_TO_FIX)


# --- A fix in the file is seen on the next call (CA-73) ---


def test_t6_ca73_added_key_is_seen_on_the_next_call(configured_api):
    """CA-73 / RN-08 / T6: after the missing key is added to the file, the next status has nothing to fix."""
    configured_api.configure(full_text_settings(key=""))
    before = _status(configured_api)
    assert "LLM_API_KEY" in _named(before, SETTING_TO_FIX)

    configured_api.configure(full_text_settings())
    after = _status(configured_api)

    assert after["settings"] == []
    assert after["text_key_configured"] is True


def test_t6_ca73_changed_provider_and_model_are_seen_on_the_next_call(configured_api):
    """CA-73 / RN-08 / T6: a changed provider and model show on the next call, without a restart."""
    configured_api.configure(full_text_settings(provider="openai", model="fake-text-model-1"))
    assert _status(configured_api)["text_provider"] == "openai"

    configured_api.configure(full_text_settings(provider="Anthropic", model="fake-text-model-2"))
    body = _status(configured_api)

    assert body["text_provider"] == "anthropic"
    assert body["text_model"] == "fake-text-model-2"


def test_t6_ca73_removed_key_is_seen_on_the_next_call(configured_api):
    """CA-73 / RN-08 / T6: a key removed from the file is reported on the next call."""
    configured_api.configure(full_text_settings())
    assert _status(configured_api)["text_key_configured"] is True

    configured_api.configure(full_text_settings(key=""))
    body = _status(configured_api)

    assert body["text_key_configured"] is False
    assert "LLM_API_KEY" in _named(body, SETTING_TO_FIX)


def test_t6_ca73_file_created_while_running_is_seen(configured_api):
    """CA-73 / RN-08 / T6: a `.env` created after the first status call is read on the next one."""
    configured_api.remove_configuration()
    assert "LLM_API_KEY" in _named(_status(configured_api), SETTING_TO_FIX)

    configured_api.configure(full_text_settings())

    assert _status(configured_api)["settings"] == []


# --- Image settings (CA-74) ---


@pytest.mark.parametrize("text_provider", ["openai", "anthropic", "google"])
def test_t6_ca74_no_image_settings_is_not_a_setting_to_fix(configured_api, text_provider):
    """CA-74 / RN-08 / T6: with no image settings nothing is reported, whatever the text provider."""
    configured_api.configure(full_text_settings(provider=text_provider))

    body = _status(configured_api)

    assert body["settings"] == []
    assert body["image_provider"] is None
    assert body["image_model"] is None


def test_t6_ca74_empty_image_settings_are_not_settings_to_fix(configured_api):
    """CA-74 / RN-08 / T6: image settings written empty only make art unavailable; nothing to fix."""
    configured_api.configure(
        full_text_settings(provider="anthropic") | {"IMAGE_PROVIDER": "", "IMAGE_API_KEY": "", "IMAGE_MODEL": "  "}
    )

    body = _status(configured_api)

    assert body["settings"] == []


@pytest.mark.parametrize("value", ["anthropic", "Anthropic", " ANTHROPIC ", '"anthropic"'])
def test_t6_ca74_anthropic_image_provider_is_a_setting_to_fix(configured_api, value):
    """CA-74 / RN-08 / T6: IMAGE_PROVIDER set to Anthropic is named as a setting to fix."""
    configured_api.configure(
        full_text_settings() | {"IMAGE_PROVIDER": value, "IMAGE_MODEL": "fake-image-model-1"}
    )

    body = _status(configured_api)

    assert _named(body, SETTING_TO_FIX) == {"IMAGE_PROVIDER"}


@pytest.mark.parametrize("value", ["dall-e", "midjourney", "0", "-1", "open ai", "✓"])
def test_t6_rn08_unknown_image_provider_is_a_setting_to_fix(configured_api, value):
    """RN-08 / CA-74 / T6: an unknown IMAGE_PROVIDER is a setting to fix; text settings are unaffected."""
    configured_api.configure(full_text_settings() | {"IMAGE_PROVIDER": value})

    body = _status(configured_api)

    assert "IMAGE_PROVIDER" in _named(body, SETTING_TO_FIX)
    assert not {"LLM_PROVIDER", "LLM_API_KEY", "LLM_MODEL"} & _named(body, SETTING_TO_FIX)
    assert body["text_key_configured"] is True
    assert body["text_provider"] == "openai"


def test_t6_ca74_image_key_without_image_provider_is_ignored(configured_api):
    """CA-74 / RN-08 / RN-06 / T6: IMAGE_API_KEY with no IMAGE_PROVIDER is reported as ignored, not to fix."""
    configured_api.configure(full_text_settings(provider="anthropic") | {"IMAGE_API_KEY": FAKE_IMAGE_KEY})

    body = _status(configured_api)

    assert _named(body, IGNORED) == {"IMAGE_API_KEY"}
    assert _named(body, SETTING_TO_FIX) == set()


def test_t6_ca74_image_key_without_image_provider_is_ignored_with_image_capable_text(configured_api):
    """CA-74 / RN-08 / T6: the image key is ignored even when the text provider can make images."""
    configured_api.configure(full_text_settings(provider="openai") | {"IMAGE_API_KEY": FAKE_IMAGE_KEY})

    body = _status(configured_api)

    assert "IMAGE_API_KEY" in _named(body, IGNORED)
    assert _named(body, SETTING_TO_FIX) == set()


def test_t6_ca74_image_model_without_provider_and_anthropic_text_is_ignored(configured_api):
    """CA-74 / RN-08 / T6: an image model with no image provider and Anthropic text is ignored with a notice."""
    configured_api.configure(full_text_settings(provider="anthropic") | {"IMAGE_MODEL": "fake-image-model-1"})

    body = _status(configured_api)

    assert _named(body, IGNORED) == {"IMAGE_MODEL"}
    assert _named(body, SETTING_TO_FIX) == set()
    assert body["image_model"] is None


@pytest.mark.parametrize("text_provider", ["openai", "google"])
def test_t6_rn08_image_model_without_provider_is_used_with_image_capable_text(configured_api, text_provider):
    """RN-08 / RN-07 / T6: with an image-capable text provider the image model is neither ignored nor to fix."""
    configured_api.configure(full_text_settings(provider=text_provider) | {"IMAGE_MODEL": "fake-image-model-1"})

    body = _status(configured_api)

    assert body["settings"] == []
    assert body["image_model"] == "fake-image-model-1"


def test_t6_ca74_image_problem_leaves_text_settings_working(configured_api):
    """CA-74 / RN-08 / T6: a problem in the image settings never names a text setting."""
    configured_api.configure(
        full_text_settings() | {"IMAGE_PROVIDER": "anthropic", "IMAGE_API_KEY": FAKE_IMAGE_KEY}
    )

    body = _status(configured_api)

    assert not {"LLM_PROVIDER", "LLM_API_KEY", "LLM_MODEL"} & _named(body, SETTING_TO_FIX)
    assert body["text_key_configured"] is True


# --- Port (CA-75, RN-47 and the decided case of T6) ---


@pytest.mark.parametrize(
    "value",
    ["0", "65536", "-1", "abc", "47 821", "1e3", "4782.1", "٤٧٨٢١", "４７８２１", "9" * 5_000, "+47821"],
)
def test_t6_ca75_invalid_port_names_the_port_setting(configured_api, value):
    """CA-75 / RN-47 / T6: a port that is not a number from 1 to 65535 names APP_PORT to fix."""
    configured_api.set_running_port(DEFAULT_PORT)
    configured_api.configure(full_text_settings() | {"APP_PORT": value})

    body = _status(configured_api)

    assert _named(body, SETTING_TO_FIX) == {"APP_PORT"}
    # The next start falls back to the default port, which is already the running one.
    assert body["next_start_port"] is None


@pytest.mark.parametrize("value", [None, "", "   ", '""'])
def test_t6_ca75_missing_or_empty_port_is_not_a_setting_to_fix(configured_api, value):
    """CA-75 / RN-47 / T6: a missing or empty port means the default port and nothing to fix."""
    configured_api.set_running_port(DEFAULT_PORT)
    settings = full_text_settings()
    if value is not None:
        settings["APP_PORT"] = value
    configured_api.configure(settings)

    body = _status(configured_api)

    assert body["settings"] == []
    assert body["next_start_port"] is None


@pytest.mark.parametrize("value", [str(DEFAULT_PORT), f"0{DEFAULT_PORT}", f' "{DEFAULT_PORT}" '])
def test_t6_rn47_same_port_as_running_reports_no_change(configured_api, value):
    """RN-47 / T6: a port equal to the running one (leading zeros, quotes, spaces) reports no change."""
    configured_api.set_running_port(DEFAULT_PORT)
    configured_api.configure(full_text_settings() | {"APP_PORT": value})

    body = _status(configured_api)

    assert body["settings"] == []
    assert body["next_start_port"] is None


@pytest.mark.parametrize("value, expected", [("47900", 47900), ("1", 1), ("65535", 65535), ("00080", 80)])
def test_t6_rn47_changed_valid_port_is_reported_for_the_next_start(configured_api, value, expected):
    """RN-47 / RN-08 / T6: a valid port different from the running one is reported for the next start."""
    configured_api.set_running_port(DEFAULT_PORT)
    configured_api.configure(full_text_settings() | {"APP_PORT": value})

    body = _status(configured_api)

    assert body["next_start_port"] == expected
    assert body["settings"] == []


def test_t6_rn47_port_changed_while_running_is_reported_then_cleared(configured_api):
    """RN-47 / RN-08 / T6: the port is read once at startup; a change in the file shows for the next start."""
    configured_api.set_running_port(DEFAULT_PORT)
    configured_api.configure(full_text_settings() | {"APP_PORT": str(DEFAULT_PORT)})
    assert _status(configured_api)["next_start_port"] is None

    configured_api.configure(full_text_settings() | {"APP_PORT": str(OTHER_PORT)})
    assert _status(configured_api)["next_start_port"] == OTHER_PORT

    configured_api.configure(full_text_settings() | {"APP_PORT": str(DEFAULT_PORT)})
    assert _status(configured_api)["next_start_port"] is None


def test_t6_rn47_port_becoming_invalid_reports_setting_and_next_start(configured_api):
    """RN-47 / RN-08 / CA-75 / T6 (decided): running on another port, an invalid value names APP_PORT
    and reports the default port for the next start."""
    configured_api.set_running_port(OTHER_PORT)
    configured_api.configure(full_text_settings() | {"APP_PORT": "not-a-port"})

    body = _status(configured_api)

    assert _named(body, SETTING_TO_FIX) == {"APP_PORT"}
    assert body["next_start_port"] == DEFAULT_PORT


@pytest.mark.parametrize("value", [None, "", "  "])
def test_t6_rn47_port_becoming_empty_reports_next_start_only(configured_api, value):
    """RN-47 / RN-08 / T6 (decided): running on another port, an empty or missing value reports the
    default port for the next start and is not a setting to fix."""
    configured_api.set_running_port(OTHER_PORT)
    settings = full_text_settings()
    if value is not None:
        settings["APP_PORT"] = value
    configured_api.configure(settings)

    body = _status(configured_api)

    assert body["settings"] == []
    assert body["next_start_port"] == DEFAULT_PORT


def test_t6_rn47_running_port_stays_when_the_file_changes(configured_api):
    """RN-47 / T6: started on one port, the same value in the file reports no change, later edits do."""
    configured_api.set_running_port(OTHER_PORT)
    configured_api.configure(full_text_settings() | {"APP_PORT": str(OTHER_PORT)})
    assert _status(configured_api)["next_start_port"] is None

    configured_api.configure(full_text_settings() | {"APP_PORT": "abc"})
    body = _status(configured_api)
    assert body["next_start_port"] == DEFAULT_PORT
    assert _named(body, SETTING_TO_FIX) == {"APP_PORT"}

    configured_api.configure(full_text_settings() | {"APP_PORT": str(OTHER_PORT)})
    body = _status(configured_api)
    assert body["next_start_port"] is None
    assert body["settings"] == []


# --- Startup with invalid values (RN-40, RN-47, CA-75), in a fresh process ---

STARTUP_PROBE = """
import json
import django
from django.conf import settings
django.setup()
from django.test import Client
response = Client(HTTP_HOST="127.0.0.1").get("/api/status")
body = response.json() if response.status_code == 200 else None
print(json.dumps({
    "running_port": getattr(settings, "RUNNING_PORT", None),
    "status_code": response.status_code,
    "settings": sorted(entry["setting"] for entry in body["settings"]) if body else None,
}))
"""


def _write_home_env(home, text):
    (home / ".env").write_text(text, encoding="utf-8")


def _run_startup_probe(tmp_path, home):
    workdir = tmp_path / "cwd"
    workdir.mkdir()
    overrides = {
        "PYTHONPATH": str(BACKEND_DIR),
        "DJANGO_SETTINGS_MODULE": "cardfactory.settings",
        "CARDFACTORY_HOME": str(home),
    }
    return run_probe(STARTUP_PROBE, overrides, cwd=workdir)


@pytest.mark.parametrize(
    "port_line, running_port, named",
    [
        pytest.param(f"APP_PORT={OTHER_PORT}\n", OTHER_PORT, [], id="valid"),
        pytest.param("APP_PORT=abc\n", DEFAULT_PORT, ["APP_PORT"], id="invalid"),
        pytest.param("APP_PORT=\n", DEFAULT_PORT, [], id="empty"),
        pytest.param("", DEFAULT_PORT, [], id="missing"),
    ],
)
def test_t6_ca75_startup_reads_the_port_once_and_never_blocks(tmp_path, port_line, running_port, named):
    """CA-75 / RN-47 / RN-40 / T6: settings load the port once at startup (default when invalid or
    empty), and the status answers in the started application."""
    home = tmp_path / "probe-home"
    home.mkdir()
    _write_home_env(
        home,
        f"LLM_PROVIDER=openai\nLLM_API_KEY={FAKE_TEXT_KEY}\nLLM_MODEL=fake-text-model-1\n{port_line}",
    )

    result = _run_startup_probe(tmp_path, home)

    assert result["running_port"] == running_port
    assert result["status_code"] == 200
    assert result["settings"] == named


def test_t6_rn40_startup_with_every_value_invalid_still_serves_the_status(tmp_path):
    """RN-40 / RN-08 / T6: a file where every value is invalid never blocks startup."""
    home = tmp_path / "probe-home"
    home.mkdir()
    _write_home_env(
        home,
        "LLM_PROVIDER=banana\nLLM_API_KEY=\nLLM_MODEL=\nIMAGE_PROVIDER=anthropic\nAPP_PORT=99999\n",
    )

    result = _run_startup_probe(tmp_path, home)

    assert result["status_code"] == 200
    assert result["running_port"] == DEFAULT_PORT
    assert set(result["settings"]) == {"LLM_PROVIDER", "LLM_API_KEY", "LLM_MODEL", "IMAGE_PROVIDER", "APP_PORT"}
