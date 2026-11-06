"""Reading `.env` in core.config (task T4, spec RN-05, RN-06, RN-08).

Every test uses a temporary file and a cleared environment, never the
repository `.env`.
"""

import dataclasses

import pytest

from tests.config_files import (
    FAKE_IMAGE_KEY,
    FAKE_TEXT_KEY,
    clean_environment,  # noqa: F401 (fixture)
    env_text,
    full_text_settings,
    settings_named,
    write_env,
    write_settings,
)

pytestmark = pytest.mark.usefixtures("clean_environment")


def _load(path):
    from core.config import load_config

    return load_config(path)


# --- Parser ---


def test_t4_rn05_reads_plain_key_value_lines(tmp_path):
    """RN-05 / T4: `KEY=VALUE` lines give the text provider, key and model."""
    config = _load(write_settings(tmp_path, full_text_settings()))

    assert config.llm_provider == "openai"
    assert config.llm_model == "fake-text-model-1"
    assert config.llm_api_key.reveal() == FAKE_TEXT_KEY
    assert config.settings_to_fix == ()


def test_t4_rn05_ignores_comments_and_blank_lines(tmp_path):
    """RN-05 / T4: comment lines (also indented) and blank or whitespace-only lines are ignored."""
    content = (
        "# Card Factory configuration\n"
        "\n"
        "   # indented comment with LLM_MODEL=wrong-model\n"
        "#LLM_PROVIDER=google\n"
        "LLM_PROVIDER=openai\n"
        "   \n"
        "\t\n"
        f"LLM_API_KEY={FAKE_TEXT_KEY}\n"
        "\n\n"
        "LLM_MODEL=fake-text-model-1\n"
        "# trailing comment\n"
    )
    config = _load(write_env(tmp_path, content))

    assert config.llm_provider == "openai"
    assert config.llm_model == "fake-text-model-1"
    assert config.llm_api_key.reveal() == FAKE_TEXT_KEY
    assert config.settings_to_fix == ()


def test_t4_rn05_strips_spaces_around_key_and_value(tmp_path):
    """RN-05 / T4: spaces and tabs around the key, the equals sign and the value are removed."""
    content = (
        "  LLM_PROVIDER   =   openai   \n"
        f"\tLLM_API_KEY\t=\t{FAKE_TEXT_KEY}\t\n"
        "LLM_MODEL= fake-text-model-1 \n"
    )
    config = _load(write_env(tmp_path, content))

    assert config.llm_provider == "openai"
    assert config.llm_model == "fake-text-model-1"
    assert config.llm_api_key.reveal() == FAKE_TEXT_KEY


@pytest.mark.parametrize("quote", ['"', "'"])
def test_t4_rn05_strips_single_and_double_quotes(tmp_path, quote):
    """RN-05 / T4: a value wrapped in single or double quotes is read without the quotes."""
    content = (
        f"LLM_PROVIDER={quote}openai{quote}\n"
        f"LLM_API_KEY={quote}{FAKE_TEXT_KEY}{quote}\n"
        f"LLM_MODEL={quote}fake text model 1{quote}\n"
    )
    config = _load(write_env(tmp_path, content))

    assert config.llm_provider == "openai"
    assert config.llm_model == "fake text model 1"
    assert config.llm_api_key.reveal() == FAKE_TEXT_KEY


def test_t4_rn05_quotes_with_spaces_outside(tmp_path):
    """RN-05 / T4: spaces outside the quotes are removed before the quotes."""
    content = env_text(full_text_settings(model='  "fake-text-model-1"  '))
    config = _load(write_env(tmp_path, content))

    assert config.llm_model == "fake-text-model-1"


def test_t4_rn05_quoted_value_keeps_hash_sign(tmp_path):
    """RN-05 / T4: a `#` inside a quoted value is part of the value, not a comment."""
    key = "sk-fake#hash#0000"
    config = _load(write_settings(tmp_path, full_text_settings(key=f'"{key}"')))

    assert config.llm_api_key.reveal() == key


def test_t4_rn05_value_keeps_equals_signs(tmp_path):
    """RN-05 / T4: only the first `=` separates key and value; keys may end in `=` padding."""
    key = "c2stZmFrZS1rZXk=="
    config = _load(write_settings(tmp_path, full_text_settings(key=key)))

    assert config.llm_api_key.reveal() == key


def test_t4_rn05_skips_utf8_byte_order_mark(tmp_path):
    """RN-05 / T4: a UTF-8 byte-order mark (as Notepad may add) does not hide the first setting."""
    path = write_env(tmp_path, env_text(full_text_settings()), encoding="utf-8-sig")
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")

    config = _load(path)

    assert config.llm_provider == "openai"
    assert "LLM_PROVIDER" not in settings_named(config.settings_to_fix)
    assert config.settings_to_fix == ()


def test_t4_rn05_reads_utf8_values(tmp_path):
    """RN-05 / T4: values are decoded as UTF-8 regardless of the system code page."""
    model = "modèle-ção-日本語-Æther-—"
    config = _load(write_settings(tmp_path, full_text_settings(model=model)))

    assert config.llm_model == model


def test_t4_rn05_reads_windows_line_endings(tmp_path):
    """RN-05 / T4: CRLF line endings leave no carriage return in values."""
    path = write_env(tmp_path, env_text(full_text_settings()), newline="\r\n")
    assert b"\r\n" in path.read_bytes()

    config = _load(path)

    assert config.llm_model == "fake-text-model-1"
    assert config.llm_api_key.reveal() == FAKE_TEXT_KEY
    assert config.settings_to_fix == ()


def test_t4_rn05_last_line_without_newline(tmp_path):
    """RN-05 / T4: the last line is read even when the file does not end with a newline."""
    content = env_text(full_text_settings()).rstrip("\n")
    config = _load(write_env(tmp_path, content))

    assert config.llm_model == "fake-text-model-1"


def test_t4_rn05_free_text_model_names_are_kept_as_written(tmp_path):
    """RN-05 / T4: model names are free text, not checked against a list."""
    model = "my-own-fine-tune:v2.1@2026"
    config = _load(write_settings(tmp_path, full_text_settings(model=model)))

    assert config.llm_model == model
    assert config.settings_to_fix == ()


def test_t4_rn05_very_long_values_are_kept(tmp_path):
    """RN-05 / T4: a very long model name and key are read unchanged."""
    model = "m" * 20_000
    key = "sk-" + "k" * 20_000
    config = _load(write_settings(tmp_path, full_text_settings(model=model, key=key)))

    assert config.llm_model == model
    assert config.llm_api_key.reveal() == key


def test_t4_rn40_malformed_lines_do_not_stop_loading(tmp_path):
    """RN-40 / RN-08 / T4: a line that is not `KEY=VALUE` never raises; the other settings are read."""
    content = (
        "this line has no equals sign\n"
        "=value-without-key\n"
        + env_text(full_text_settings())
        + '"unterminated\n'
    )
    config = _load(write_env(tmp_path, content))

    assert config.llm_provider == "openai"
    assert config.llm_model == "fake-text-model-1"
    assert config.llm_api_key.reveal() == FAKE_TEXT_KEY


def test_t4_rn08_empty_file_reports_text_settings_and_never_raises(tmp_path):
    """RN-08 / CA-05 / T4: an empty file loads and names the text provider, key and model to fix."""
    config = _load(write_env(tmp_path, ""))

    assert {"LLM_PROVIDER", "LLM_API_KEY", "LLM_MODEL"} <= settings_named(config.settings_to_fix)


def test_t4_rn08_load_config_accepts_a_string_path(tmp_path):
    """RN-08 / T4: the loader takes the file path as a parameter, as a path or a string."""
    path = write_settings(tmp_path, full_text_settings())

    assert _load(str(path)).llm_model == "fake-text-model-1"


# --- Process environment override ---


def test_t4_rn05_process_variable_ignored_without_debug(tmp_path, monkeypatch):
    """RN-05 / T4: without CARDFACTORY_DEBUG=1 a global LLM_MODEL never changes the configuration."""
    monkeypatch.setenv("LLM_MODEL", "process-model")
    monkeypatch.setenv("LLM_API_KEY", "sk-fake-process-key-9999")
    config = _load(write_settings(tmp_path, full_text_settings()))

    assert config.llm_model == "fake-text-model-1"
    assert config.llm_api_key.reveal() == FAKE_TEXT_KEY


def test_t4_rn05_process_variable_does_not_fill_missing_setting_without_debug(tmp_path, monkeypatch):
    """RN-05 / RN-08 / T4: without debug, a process LLM_MODEL does not supply a model the file lacks."""
    monkeypatch.setenv("LLM_MODEL", "process-model")
    settings = full_text_settings()
    del settings["LLM_MODEL"]
    config = _load(write_settings(tmp_path, settings))

    assert config.llm_model != "process-model"
    assert "LLM_MODEL" in settings_named(config.settings_to_fix)


@pytest.mark.parametrize("value", ["0", "true", "yes", ""])
def test_t4_rn05_process_variable_ignored_when_debug_is_not_1(tmp_path, monkeypatch, value):
    """RN-05 / T4: only CARDFACTORY_DEBUG=1 enables the override."""
    monkeypatch.setenv("CARDFACTORY_DEBUG", value)
    monkeypatch.setenv("LLM_MODEL", "process-model")
    config = _load(write_settings(tmp_path, full_text_settings()))

    assert config.llm_model == "fake-text-model-1"


def test_t4_rn05_process_variables_override_with_debug(tmp_path, monkeypatch):
    """RN-05 / T4: with CARDFACTORY_DEBUG=1, process variables override `.env`."""
    monkeypatch.setenv("CARDFACTORY_DEBUG", "1")
    monkeypatch.setenv("LLM_MODEL", "process-model")
    monkeypatch.setenv("LLM_PROVIDER", "google")
    monkeypatch.setenv("LLM_API_KEY", "sk-fake-process-key-9999")
    config = _load(write_settings(tmp_path, full_text_settings()))

    assert config.llm_model == "process-model"
    assert config.llm_provider == "google"
    assert config.llm_api_key.reveal() == "sk-fake-process-key-9999"


def test_t4_rn05_process_variable_fills_missing_setting_with_debug(tmp_path, monkeypatch):
    """RN-05 / RN-08 / T4: with debug, a process variable supplies a setting the file lacks."""
    monkeypatch.setenv("CARDFACTORY_DEBUG", "1")
    monkeypatch.setenv("LLM_MODEL", "process-model")
    settings = full_text_settings()
    del settings["LLM_MODEL"]
    config = _load(write_settings(tmp_path, settings))

    assert config.llm_model == "process-model"
    assert config.settings_to_fix == ()


def test_t4_rn05_debug_flag_in_file_does_not_enable_override(tmp_path, monkeypatch):
    """RN-05 / T4: CARDFACTORY_DEBUG is a process variable; setting it in `.env` enables nothing."""
    monkeypatch.setenv("LLM_MODEL", "process-model")
    content = "CARDFACTORY_DEBUG=1\n" + env_text(full_text_settings())
    config = _load(write_env(tmp_path, content))

    assert config.llm_model == "fake-text-model-1"


# --- Frozen config and Secret ---


def test_t4_rn06_config_is_frozen(tmp_path):
    """RN-06 / T4: the config object cannot be changed after loading."""
    config = _load(write_settings(tmp_path, full_text_settings()))

    with pytest.raises((AttributeError, dataclasses.FrozenInstanceError, TypeError)):
        config.llm_model = "changed"
    with pytest.raises((AttributeError, dataclasses.FrozenInstanceError, TypeError)):
        config.llm_api_key = "changed"
    assert isinstance(config.settings_to_fix, tuple)
    assert isinstance(config.notices, tuple)


def test_t4_rn06_keys_are_secret_objects(tmp_path):
    """RN-06 / T4: the text and image keys are Secret values, not plain strings."""
    from core.config import Secret

    settings = full_text_settings() | {
        "IMAGE_PROVIDER": "google",
        "IMAGE_API_KEY": FAKE_IMAGE_KEY,
        "IMAGE_MODEL": "fake-image-model-1",
    }
    config = _load(write_settings(tmp_path, settings))

    assert isinstance(config.llm_api_key, Secret)
    assert isinstance(config.image_api_key, Secret)
    assert not isinstance(config.llm_api_key, str)
    assert not isinstance(config.image_api_key, str)
    assert config.image_api_key.reveal() == FAKE_IMAGE_KEY


def test_t4_rn06_secret_str_and_repr_never_reveal_the_value():
    """RN-06 / CA-06 / T4: str, repr and formatting of a Secret print `***`, never the value."""
    from core.config import Secret

    secret = Secret(FAKE_TEXT_KEY)

    assert str(secret) == "***"
    assert f"{secret}" == "***"
    assert "%s" % secret == "***"
    assert "{}".format(secret) == "***"
    assert FAKE_TEXT_KEY not in repr(secret)
    assert "***" in repr(secret)
    assert FAKE_TEXT_KEY not in f"{secret!r}"
    assert FAKE_TEXT_KEY not in str([secret]) and FAKE_TEXT_KEY not in str({"key": secret})


@pytest.mark.parametrize("value", ["k", "short", "ключ-🔑-キー", "x" * 10_000, "  spaced  "])
def test_t4_rn06_secret_hides_odd_values(value):
    """RN-06 / T4: short, non-ASCII and huge values are hidden the same way; reveal() returns them."""
    from core.config import Secret

    secret = Secret(value)

    assert str(secret) == "***"
    assert value not in repr(secret)
    assert secret.reveal() == value


def test_t4_rn08_secret_truth_value_tells_whether_a_key_is_set():
    """RN-08 / CA-05 / T4: bool(Secret("")) is False and bool(Secret("x")) is True; bool returns a plain bool."""
    from core.config import Secret

    assert bool(Secret("")) is False
    assert bool(Secret("x")) is True
    assert bool(Secret(FAKE_TEXT_KEY)) is True


def test_t4_rn06_config_text_never_contains_keys(tmp_path):
    """RN-06 / CA-06 / T4: str and repr of the config never contain the text or image key."""
    settings = full_text_settings() | {
        "IMAGE_PROVIDER": "google",
        "IMAGE_API_KEY": FAKE_IMAGE_KEY,
        "IMAGE_MODEL": "fake-image-model-1",
    }
    config = _load(write_settings(tmp_path, settings))

    for text in (str(config), repr(config)):
        assert FAKE_TEXT_KEY not in text
        assert FAKE_IMAGE_KEY not in text


# --- Parser decisions ---


def test_t4_rn05_no_inline_comment_on_unquoted_value(tmp_path):
    """RN-05 / T4: an unquoted value keeps ` # ...`; there are no inline comments."""
    config = _load(write_settings(tmp_path, full_text_settings(model="fake-model # note")))

    assert config.llm_model == "fake-model # note"


def test_t4_rn05_unquoted_key_with_hash_is_kept_whole(tmp_path):
    """RN-05 / RN-06 / T4: a key that contains `#` is read whole, without quotes."""
    key = "sk-fake#0000#hash"
    config = _load(write_settings(tmp_path, full_text_settings(key=key)))

    assert config.llm_api_key.reveal() == key


def test_t4_rn05_repeated_setting_last_line_wins(tmp_path):
    """RN-05 / T4: when a setting appears twice, the last line wins."""
    content = env_text(full_text_settings(model="first-model")) + "LLM_MODEL=last-model\n"
    config = _load(write_env(tmp_path, content))

    assert config.llm_model == "last-model"


def test_t4_rn05_setting_names_are_case_sensitive(tmp_path):
    """RN-05 / RN-08 / T4: `llm_model=` is not LLM_MODEL, so the model is still missing."""
    settings = full_text_settings()
    del settings["LLM_MODEL"]
    content = env_text(settings) + "llm_model=lower-case-model\nLlm_Model=mixed-case-model\n"
    config = _load(write_env(tmp_path, content))

    assert config.llm_model not in {"lower-case-model", "mixed-case-model"}
    assert settings_named(config.settings_to_fix) == {"LLM_MODEL"}


def test_t4_rn05_export_prefix_is_not_supported(tmp_path):
    """RN-05 / RN-08 / T4: `export LLM_MODEL=x` does not set LLM_MODEL."""
    settings = full_text_settings()
    del settings["LLM_MODEL"]
    content = env_text(settings) + "export LLM_MODEL=exported-model\n"
    config = _load(write_env(tmp_path, content))

    assert config.llm_model != "exported-model"
    assert "LLM_MODEL" in settings_named(config.settings_to_fix)


def test_t4_rn08_missing_file_does_not_raise(tmp_path):
    """RN-08 / RN-40 / CA-05 / T4: a missing configuration file loads; the text settings are named and the port is 47821."""
    config = _load(tmp_path / "missing-configuration-file")

    assert settings_named(config.settings_to_fix) == {"LLM_PROVIDER", "LLM_API_KEY", "LLM_MODEL"}
    assert config.app_port == 47821


@pytest.mark.parametrize("value", ["", "   ", "\t"])
def test_t4_rn05_empty_process_variable_does_not_erase_file_value_with_debug(tmp_path, monkeypatch, value):
    """RN-05 / T4: with CARDFACTORY_DEBUG=1, an empty or blank process variable is ignored."""
    monkeypatch.setenv("CARDFACTORY_DEBUG", "1")
    monkeypatch.setenv("LLM_MODEL", value)
    monkeypatch.setenv("LLM_API_KEY", value)
    config = _load(write_settings(tmp_path, full_text_settings()))

    assert config.llm_model == "fake-text-model-1"
    assert config.llm_api_key.reveal() == FAKE_TEXT_KEY
    assert config.settings_to_fix == ()
