"""GET /api/status with an unreadable `.env` (task T129, spec RN-06, RN-08, RN-40, CA-06, CA-73, CA-77).

A configuration file that exists but cannot be opened, or that holds NUL
bytes after decoding (UTF-16 with no byte-order mark), is the single settings
item `{setting: ".env", code: "config_invalid", message}`, with the fix for its
cause (check its permissions, or save it as UTF-8). No other setting to fix,
no notice and no port change are reported while it cannot be read, and no
response holds any part of the file: every distinctive piece of the file is
given to tests.configured_api as a secret, so each response is checked for it.
After the file is fixed, the next status shows its settings without a restart.

Values are fictional; keys only look like keys.
"""

import codecs

import pytest

from tests.config_files import DEFAULT_PORT, FAKE_IMAGE_KEY, FAKE_TEXT_KEY, deny_opening, env_text, full_text_settings
from tests.configured_api import configured_api  # noqa: F401 (fixture)

STATUS_URL = "/api/status"
SETTING_TO_FIX = "config_invalid"
ENV_SETTING = ".env"
OTHER_PORT = 47900

DISTINCT_MODEL = "fake-distinct-model-UNREADABLE-4242"
DISTINCT_IMAGE_MODEL = "fake-distinct-image-UNREADABLE-5353"
DISTINCT_COMMENT = "fictional comment ZORBLAX-quill-7171"
FILE_PARTS = (DISTINCT_MODEL, DISTINCT_IMAGE_MODEL, DISTINCT_COMMENT, "ZORBLAX-quill")
# Parts that never appear, even once the file is fixed (the models do appear then).
NEVER_SHOWN_PARTS = (DISTINCT_COMMENT, "ZORBLAX-quill")
MODEL_VALUES = (DISTINCT_MODEL, DISTINCT_IMAGE_MODEL)


def _assert_no_model_value(response):
    """While the file is unreadable, no model value from the file appears in the response."""
    text = response.content.decode("utf-8")
    for value in MODEL_VALUES:
        assert value not in text, "A model value from the unreadable file appears in the response."


def _settings(port=DEFAULT_PORT):
    return full_text_settings(model=DISTINCT_MODEL) | {
        "IMAGE_PROVIDER": "google",
        "IMAGE_API_KEY": FAKE_IMAGE_KEY,
        "IMAGE_MODEL": DISTINCT_IMAGE_MODEL,
        "APP_PORT": str(port),
    }


def _text(port=DEFAULT_PORT):
    return f"# {DISTINCT_COMMENT}\n" + env_text(_settings(port))


def _garbled_lines(content):
    """The lines of `content` as a UTF-8 reader would see them, NULs included."""
    garbled = content.decode("utf-8", errors="replace")
    return [line for line in garbled.split("\n") if len(line) >= 8]


def _status(api):
    response = api.get(STATUS_URL)
    assert response.status_code == 200, response.content[:500]
    assert response["Content-Type"].startswith("application/json")
    return response.json()


def _env_message(body):
    """Check the single `.env` item and the empty configuration around it; return the message."""
    assert [(entry["setting"], entry["code"]) for entry in body["settings"]] == [(ENV_SETTING, SETTING_TO_FIX)]
    entry = body["settings"][0]
    assert set(entry) == {"setting", "code", "message"}
    assert isinstance(entry["message"], str) and entry["message"].strip()
    assert body["text_provider"] is None
    assert body["text_model"] is None
    assert body["text_key_configured"] is False
    assert body["image_provider"] is None
    assert body["image_model"] is None
    assert body["next_start_port"] is None
    return entry["message"]


def _assert_shows_the_settings(body, port_change=None):
    assert body["settings"] == []
    assert body["text_provider"] == "openai"
    assert body["text_model"] == DISTINCT_MODEL
    assert body["text_key_configured"] is True
    assert body["image_provider"] == "google"
    assert body["image_model"] == DISTINCT_IMAGE_MODEL
    assert body["next_start_port"] == port_change


# --- A file that cannot be opened ---


@pytest.mark.parametrize("running_port", [DEFAULT_PORT, OTHER_PORT])
def test_t129_ca77_permission_error_is_the_single_env_item(configured_api, monkeypatch, running_port):
    """CA-77 / RN-40 / CA-06 / T129: a file that cannot be opened is the single `.env` item with the permissions fix,
    no port change (even when the running port is not the default) and no part of the file."""
    configured_api.set_running_port(running_port)
    path = configured_api.configure(_settings(OTHER_PORT), secrets=FILE_PARTS)
    deny_opening(monkeypatch, path)

    message = _env_message(_status(configured_api))

    assert "permission" in message.lower(), message


def test_t129_ca77_folder_at_the_path_is_the_single_env_item(configured_api):
    """CA-77 / RN-40 / T129: a folder named `.env` in the home is the single `.env` item with the permissions fix."""
    configured_api.set_running_port(OTHER_PORT)
    configured_api.env_path.mkdir()

    message = _env_message(_status(configured_api))

    assert "permission" in message.lower(), message


# --- Text that is not UTF-8 ---


@pytest.mark.parametrize("encoding", ["utf-16-le", "utf-16-be"])
@pytest.mark.parametrize("running_port", [DEFAULT_PORT, OTHER_PORT])
def test_t129_ca77_utf16_without_bom_is_the_single_env_item(configured_api, encoding, running_port):
    """CA-77 / RN-40 / CA-06 / T129: UTF-16 with no byte-order mark is the single `.env` item with the save-as-UTF-8 fix,
    no port change and no part of the file, garbled or not."""
    configured_api.set_running_port(running_port)
    content = _text(OTHER_PORT).encode(encoding)
    configured_api.configure_bytes(content, secrets=(*FILE_PARTS, *_garbled_lines(content)))

    message = _env_message(_status(configured_api))

    assert "utf-8" in message.lower(), message


def test_t129_rn40_utf16_with_bom_is_read_like_utf8(configured_api):
    """RN-40 / CA-77 / T129: a UTF-16 file with a byte-order mark (Notepad "Unicode") shows its settings."""
    configured_api.set_running_port(DEFAULT_PORT)
    configured_api.configure_bytes(codecs.BOM_UTF16_LE + _text().encode("utf-16-le"), secrets=(FAKE_TEXT_KEY,))

    _assert_shows_the_settings(_status(configured_api))


def test_t129_rn40_stray_byte_in_a_comment_keeps_the_settings(configured_api):
    """RN-40 / T129: a stray byte that is not valid UTF-8 in a comment does not discard the file."""
    configured_api.set_running_port(DEFAULT_PORT)
    configured_api.configure_bytes(b"# caf\xe9 \xff note\n" + env_text(_settings()).encode("utf-8"))

    _assert_shows_the_settings(_status(configured_api))


# --- After the fix, without a restart (CA-73, CA-77) ---


def _unreadable_status(api):
    """The status while the file cannot be read: the single item, and no model value from the file."""
    response = api.get(STATUS_URL)
    assert response.status_code == 200, response.content[:500]
    _assert_no_model_value(response)
    return response.json()


def test_t129_ca77_permission_fixed_with_same_file_is_seen_on_the_next_call(configured_api, monkeypatch):
    """CA-77 / CA-73 / T129: after the permission is fixed (file untouched), reopening the status shows its settings."""
    configured_api.set_running_port(DEFAULT_PORT)
    path = configured_api.configure(_settings(), secrets=NEVER_SHOWN_PARTS)
    denial = deny_opening(monkeypatch, path)
    _env_message(_unreadable_status(configured_api))

    denial.allow()

    _assert_shows_the_settings(_status(configured_api))


def test_t129_ca77_utf16_saved_again_as_utf8_is_seen_on_the_next_call(configured_api):
    """CA-77 / CA-73 / T129: after the file is saved again as UTF-8, reopening the status shows its settings."""
    configured_api.set_running_port(DEFAULT_PORT)
    content = _text().encode("utf-16-le")
    configured_api.configure_bytes(content, secrets=(*NEVER_SHOWN_PARTS, *_garbled_lines(content)))
    _env_message(_unreadable_status(configured_api))

    configured_api.configure(text=_text())

    _assert_shows_the_settings(_status(configured_api))


def test_t129_ca77_fixed_file_with_a_new_port_reports_the_port_change(configured_api, monkeypatch):
    """CA-77 / RN-47 / T129: the port change hidden while the file was unreadable shows once it can be read."""
    configured_api.set_running_port(DEFAULT_PORT)
    path = configured_api.configure(_settings(OTHER_PORT), secrets=NEVER_SHOWN_PARTS)
    denial = deny_opening(monkeypatch, path)
    assert _env_message(_unreadable_status(configured_api))

    denial.allow()

    _assert_shows_the_settings(_status(configured_api), port_change=OTHER_PORT)


# --- A missing file is not the `.env` item ---


def test_t129_rn40_missing_file_is_not_the_env_item(configured_api):
    """RN-40 / RN-08 / T129: without a `.env` the status names the text settings, as before; `.env` is not named."""
    configured_api.remove_configuration()

    body = _status(configured_api)

    named = {entry["setting"] for entry in body["settings"]}
    assert named == {"LLM_PROVIDER", "LLM_API_KEY", "LLM_MODEL"}
    assert ENV_SETTING not in named
