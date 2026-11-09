"""Encodings and an unreadable `.env` in core.config (task T129, spec RN-08, RN-40, CA-06, CA-73, CA-77).

Plan sections 6 and 8: the parser reads UTF-8, with or without a byte-order
mark, and UTF-16 with a byte-order mark; an invalid UTF-8 byte is replaced, so
a stray character in a comment keeps the other settings. A file that exists
but cannot be opened, or that holds NUL bytes after decoding (UTF-16 with no
byte-order mark), reads as empty and is reported as the single item
`{setting: ".env", code: "config_invalid", message}`, with a message for its
cause (check its permissions, or save it as UTF-8) that holds no part of the
file. No other setting to fix and no notice are reported while it cannot be
read. A read that fails is never cached. A missing file is not this case: it
reads as empty and names the text settings (the launcher handles it at
startup, RN-40).

A permission error is simulated by tests.config_files.deny_opening, since
Windows permissions cannot be toggled portably in a test. Every test uses a
temporary file and a cleared environment, never the repository `.env`. Values
are fictional; keys only look like keys.
"""

import codecs
import os

import pytest

from tests.config_files import (
    DEFAULT_PORT,
    FAKE_IMAGE_KEY,
    FAKE_TEXT_KEY,
    clean_environment,  # noqa: F401 (fixture)
    deny_opening,
    env_text,
    full_text_settings,
    settings_named,
    write_env_bytes,
    write_settings,
)

pytestmark = pytest.mark.usefixtures("clean_environment")

SETTING_TO_FIX = "config_invalid"
ENV_SETTING = ".env"
TEXT_SETTINGS = {"LLM_PROVIDER", "LLM_API_KEY", "LLM_MODEL"}

# Distinctive values: none of them may appear in a message about the file.
DISTINCT_MODEL = "fake-distinct-model-UNREADABLE-4242"
DISTINCT_COMMENT = "fictional comment ZORBLAX-quill-7171"
OTHER_PORT = 47900


def _settings():
    """A full configuration with an image part and a changed port, so any leak or port change shows."""
    return full_text_settings(model=DISTINCT_MODEL) | {
        "IMAGE_PROVIDER": "google",
        "IMAGE_API_KEY": FAKE_IMAGE_KEY,
        "IMAGE_MODEL": "fake-image-model-1",
        "APP_PORT": str(OTHER_PORT),
    }


def _text():
    return f"# {DISTINCT_COMMENT}\n" + env_text(_settings())


def _file_parts():
    """Pieces of the file content that must never appear in the `.env` item."""
    return [FAKE_TEXT_KEY, FAKE_IMAGE_KEY, DISTINCT_MODEL, DISTINCT_COMMENT, "ZORBLAX", "fake-image-model-1"]


def _load(path):
    from core.config import load_config

    return load_config(path)


def _get(path):
    from core.config import get_config

    return get_config(path)


def _assert_reads_settings(config):
    """The file was read like plain UTF-8: every value present and nothing to fix."""
    assert config.llm_provider == "openai"
    assert config.llm_api_key.reveal() == FAKE_TEXT_KEY
    assert config.llm_model == DISTINCT_MODEL
    assert config.image_provider == "google"
    assert config.image_api_key.reveal() == FAKE_IMAGE_KEY
    assert config.image_model == "fake-image-model-1"
    assert config.app_port == OTHER_PORT
    assert config.settings_to_fix == ()
    assert config.notices == ()


def _env_item(config):
    """Check the single `.env` item and return its message (plan section 6, CA-77)."""
    entries = [(entry.setting, entry.code) for entry in (*config.settings_to_fix, *config.notices)]
    assert entries == [(ENV_SETTING, SETTING_TO_FIX)], entries
    message = config.settings_to_fix[0].message
    assert isinstance(message, str) and message.strip()
    return message


def _assert_reads_as_empty(config):
    """The unreadable file reads as empty: no value kept, the default port, no key."""
    assert config.llm_provider == ""
    assert config.llm_model == ""
    assert config.image_provider == ""
    assert config.image_model == ""
    assert not config.llm_api_key
    assert not config.image_api_key
    assert config.app_port == DEFAULT_PORT


def _assert_no_part_of_the_file(config, extra=()):
    texts = [str(config), repr(config), *(entry.message for entry in (*config.settings_to_fix, *config.notices))]
    for part in (*_file_parts(), *extra):
        for text in texts:
            assert part not in text


def _permission_message(message):
    return "permission" in message.lower()


def _utf8_message(message):
    return "utf-8" in message.lower()


# --- Encodings read like UTF-8 (RN-40) ---


@pytest.mark.parametrize(
    "encode",
    [
        pytest.param(lambda text: text.encode("utf-16"), id="utf-16-native-bom"),
        pytest.param(lambda text: codecs.BOM_UTF16_LE + text.encode("utf-16-le"), id="utf-16-le-bom"),
        pytest.param(lambda text: codecs.BOM_UTF16_BE + text.encode("utf-16-be"), id="utf-16-be-bom"),
        pytest.param(lambda text: codecs.BOM_UTF16_LE + text.replace("\n", "\r\n").encode("utf-16-le"), id="utf-16-le-bom-crlf"),
    ],
)
def test_t129_rn40_utf16_with_bom_reads_like_utf8(tmp_path, encode):
    """RN-40 / CA-77 / T129: a file saved as UTF-16 with a byte-order mark (Notepad "Unicode") is read like UTF-8."""
    config = _load(write_env_bytes(tmp_path, encode(_text())))

    _assert_reads_settings(config)


def test_t129_rn40_utf16_with_bom_keeps_non_ascii_values(tmp_path):
    """RN-40 / T129: non-ASCII and hybrid-symbol text in a UTF-16 file is decoded as written."""
    model = "módelo-✓-ギ-{W/U}-🜲-fake"
    content = codecs.BOM_UTF16_LE + env_text(full_text_settings(model=model)).encode("utf-16-le")

    config = _load(write_env_bytes(tmp_path, content))

    assert config.llm_model == model
    assert config.settings_to_fix == ()


def test_t129_rn40_utf16_bom_only_file_reads_as_an_empty_file(tmp_path):
    """RN-40 / RN-08 / T129: a UTF-16 file with only the byte-order mark is an empty file, not an unreadable one."""
    config = _load(write_env_bytes(tmp_path, codecs.BOM_UTF16_LE))

    assert settings_named(config.settings_to_fix) == TEXT_SETTINGS
    assert ENV_SETTING not in settings_named(config.settings_to_fix)


@pytest.mark.parametrize(
    "prefix",
    [pytest.param(b"", id="no-bom"), pytest.param(codecs.BOM_UTF8, id="utf-8-bom")],
)
@pytest.mark.parametrize(
    "stray",
    [
        pytest.param(b"\xe9", id="latin-1-e-acute"),
        pytest.param(b"\xff\xfe\xfd", id="invalid-run"),
        pytest.param(b"\x80", id="lone-continuation"),
        pytest.param(b"\xc3", id="truncated-sequence"),
        pytest.param(b"\xed\xa0\x80", id="encoded-surrogate"),
    ],
)
def test_t129_rn40_stray_invalid_byte_in_a_comment_keeps_the_other_settings(tmp_path, prefix, stray):
    """RN-40 / T129: one byte that is not valid UTF-8 in a comment does not discard the file."""
    content = prefix + b"# caf" + stray + b" comment\n" + env_text(_settings()).encode("utf-8")

    config = _load(write_env_bytes(tmp_path, content))

    _assert_reads_settings(config)


def test_t129_rn40_stray_invalid_byte_on_the_last_line_keeps_the_other_settings(tmp_path):
    """RN-40 / T129: a stray byte at the very end of the file (no newline) keeps every setting above it."""
    content = env_text(_settings()).encode("utf-8") + b"# trailing \xa9"

    config = _load(write_env_bytes(tmp_path, content))

    _assert_reads_settings(config)


def test_t129_rn40_stray_invalid_byte_in_one_value_keeps_the_other_settings(tmp_path):
    """RN-40 / T129: a stray byte inside one value never empties the other settings nor names the file."""
    settings = _settings()
    content = env_text(settings).replace("IMAGE_MODEL=fake-image-model-1", "IMAGE_MODEL=fake-image-\x00SPLIT")
    raw = content.encode("utf-8").replace(b"\x00", b"\xe9")

    config = _load(write_env_bytes(tmp_path, raw))

    assert config.llm_provider == "openai"
    assert config.llm_api_key.reveal() == FAKE_TEXT_KEY
    assert config.llm_model == DISTINCT_MODEL
    assert config.app_port == OTHER_PORT
    assert ENV_SETTING not in settings_named(config.settings_to_fix)


# --- A file that cannot be opened (RN-40, CA-77) ---


def test_t129_ca77_permission_error_is_the_single_env_item(tmp_path, monkeypatch):
    """CA-77 / RN-40 / T129: a file that cannot be opened is the single `.env` item, with the permissions fix."""
    path = write_settings(tmp_path, _settings())
    denial = deny_opening(monkeypatch, path)

    config = _load(path)

    assert denial.attempts >= 1, "the loader must try to open the file"
    message = _env_item(config)
    assert _permission_message(message), message
    _assert_reads_as_empty(config)
    _assert_no_part_of_the_file(config)


def test_t129_ca77_folder_at_the_path_is_the_single_env_item(tmp_path):
    """CA-77 / RN-40 / T129: a folder named `.env` cannot be opened: the single `.env` item, with the permissions fix."""
    path = tmp_path / ".env"
    path.mkdir()
    (path / "inside.txt").write_text(_text(), encoding="utf-8")

    config = _load(path)

    message = _env_item(config)
    assert _permission_message(message), message
    _assert_reads_as_empty(config)
    _assert_no_part_of_the_file(config)


def test_t129_ca77_unreadable_file_never_raises_and_names_no_other_setting(tmp_path, monkeypatch):
    """CA-77 / RN-08 / T129: an unreadable file that would otherwise lack every text setting still names only `.env`."""
    path = write_settings(tmp_path, {"LLM_PROVIDER": "banana", "APP_PORT": "not-a-port", "IMAGE_API_KEY": FAKE_IMAGE_KEY})
    deny_opening(monkeypatch, path)

    config = _load(path)

    _env_item(config)
    assert settings_named(config.settings_to_fix) == {ENV_SETTING}
    assert config.notices == ()


def test_t129_ca77_permission_error_through_get_config(tmp_path, monkeypatch):
    """CA-77 / RN-08 / T129: get_config() reports the same single `.env` item as load_config()."""
    path = write_settings(tmp_path, _settings())
    deny_opening(monkeypatch, path)

    config = _get(path)

    assert _permission_message(_env_item(config))
    _assert_no_part_of_the_file(config)


# --- Text that is not UTF-8: NUL bytes after decoding (RN-40, CA-77) ---


@pytest.mark.parametrize(
    "encoding",
    [pytest.param("utf-16-le", id="utf-16-le-no-bom"), pytest.param("utf-16-be", id="utf-16-be-no-bom")],
)
def test_t129_ca77_utf16_without_bom_is_the_single_env_item(tmp_path, encoding):
    """CA-77 / RN-40 / T129: UTF-16 with no byte-order mark is the single `.env` item, with the save-as-UTF-8 fix."""
    content = _text().encode(encoding)

    config = _load(write_env_bytes(tmp_path, content))

    message = _env_item(config)
    assert _utf8_message(message), message
    _assert_reads_as_empty(config)
    garbled = content.decode("utf-8", errors="replace")
    _assert_no_part_of_the_file(config, extra=[line for line in garbled.split("\n") if len(line) >= 8])


def test_t129_ca77_nul_byte_in_a_utf8_file_is_the_single_env_item(tmp_path):
    """CA-77 / RN-40 / T129: one NUL byte after decoding is the single `.env` item: the file is not read as text."""
    content = env_text(_settings()).replace("LLM_PROVIDER=openai", "LLM_PROVIDER=open\x00ai").encode("utf-8")

    config = _load(write_env_bytes(tmp_path, content))

    assert _utf8_message(_env_item(config))
    _assert_reads_as_empty(config)
    _assert_no_part_of_the_file(config)


def test_t129_ca77_messages_differ_by_cause(tmp_path, monkeypatch):
    """CA-77 / T129: the fix for a file that cannot be opened differs from the fix for text that is not UTF-8."""
    denied_dir = tmp_path / "denied"
    utf16_dir = tmp_path / "utf16"
    denied_dir.mkdir()
    utf16_dir.mkdir()
    denied = write_settings(denied_dir, _settings())
    deny_opening(monkeypatch, denied)
    utf16 = write_env_bytes(utf16_dir, _text().encode("utf-16-le"))

    permission_message = _env_item(_load(denied))
    text_message = _env_item(_load(utf16))

    assert permission_message != text_message
    assert _permission_message(permission_message) and not _utf8_message(permission_message)
    assert _utf8_message(text_message)


@pytest.mark.parametrize(
    "content",
    [
        pytest.param(b"", id="empty"),
        pytest.param(b"\n\n# only comments\n", id="comments-only"),
        pytest.param(codecs.BOM_UTF8, id="utf-8-bom-only"),
        pytest.param(b"\xfd\xfc\x80\n", id="only-invalid-bytes"),
    ],
)
def test_t129_rn40_readable_files_are_never_the_env_item(tmp_path, content):
    """RN-40 / RN-08 / T129: an empty or comment-only file, or one with only invalid UTF-8, names the text settings, not `.env`."""
    config = _load(write_env_bytes(tmp_path, content))

    assert settings_named(config.settings_to_fix) == TEXT_SETTINGS


# --- A missing file keeps its behavior (RN-40, the launcher's case) ---


def test_t129_rn40_missing_file_names_the_text_settings_not_env(tmp_path):
    """RN-40 / RN-08 / T129: a missing file reads as empty and names the text settings; it is not the `.env` item."""
    path = tmp_path / ".env"

    for config in (_load(path), _get(path)):
        assert settings_named(config.settings_to_fix) == TEXT_SETTINGS
        assert config.app_port == DEFAULT_PORT


# --- A read that fails is never cached (CA-73, CA-77) ---


def test_t129_ca73_file_readable_again_with_same_mtime_and_size_is_read(tmp_path, monkeypatch):
    """CA-73 / CA-77 / T129: after a permission fix that leaves the file untouched, the next get_config() reads it."""
    path = write_settings(tmp_path, _settings())
    stamp = (os.stat(path).st_mtime_ns, os.stat(path).st_size)
    denial = deny_opening(monkeypatch, path)
    assert settings_named(_get(path).settings_to_fix) == {ENV_SETTING}

    denial.allow()
    assert (os.stat(path).st_mtime_ns, os.stat(path).st_size) == stamp
    config = _get(path)

    _assert_reads_settings(config)


def test_t129_ca73_failed_read_is_tried_again_on_every_call(tmp_path, monkeypatch):
    """CA-73 / T129: while the file cannot be opened, each get_config() call tries it again."""
    path = write_settings(tmp_path, _settings())
    denial = deny_opening(monkeypatch, path)

    _get(path)
    attempts = denial.attempts
    config = _get(path)

    assert denial.attempts > attempts
    assert settings_named(config.settings_to_fix) == {ENV_SETTING}


def test_t129_ca77_folder_replaced_by_a_file_is_read(tmp_path):
    """CA-77 / CA-73 / T129: after the folder at the path is replaced by a valid file, the next call reads it."""
    path = tmp_path / ".env"
    path.mkdir()
    assert settings_named(_get(path).settings_to_fix) == {ENV_SETTING}

    path.rmdir()
    write_settings(tmp_path, _settings())

    _assert_reads_settings(_get(path))


def test_t129_ca73_utf16_resaved_as_utf8_is_read(tmp_path):
    """CA-77 / CA-73 / T129: a UTF-16 file without a byte-order mark saved again as UTF-8 is read on the next call."""
    path = write_env_bytes(tmp_path, _text().encode("utf-16-le"))
    assert settings_named(_get(path).settings_to_fix) == {ENV_SETTING}

    write_env_bytes(tmp_path, _text().encode("utf-8"))

    _assert_reads_settings(_get(path))
