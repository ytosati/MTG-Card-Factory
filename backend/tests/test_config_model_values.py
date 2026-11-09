"""Model values that look like a key, in core.config (task T128, spec RN-06, RN-08, CA-06, CA-78).

A model value (`LLM_MODEL`, `IMAGE_MODEL`) equal to a configured key value, or
starting with a known key prefix (`sk-`, `AIza`), is not kept in the
configuration, like an unrecognized provider value, and is reported as the
model setting to fix (`config_invalid`). An unset model is the empty string in
the config object (plan section 8).

Decided case: an image model that would otherwise be ignored with a notice (no
`IMAGE_PROVIDER` and a text provider that cannot make images) is still a model
value that looks like a key. CA-78 names the model setting to fix for a text
or an image model, and plan section 8 makes such a value a setting to fix with
no exception, so it is reported once, as `config_invalid`, and never kept.

Every test uses a temporary file and a cleared environment, never the
repository `.env`. Values are fictional; keys only look like keys.
"""

import pytest

from tests.config_files import (
    FAKE_AIZA_MODEL_VALUE,
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

SETTING_TO_FIX = "config_invalid"

# Keys with no known prefix, so only the equality rule can catch them.
UNPREFIXED_TEXT_KEY = "fake-text-key-1212-NOPREFIX-not-real-3434"
UNPREFIXED_IMAGE_KEY = "fake-image-key-5656-NOPREFIX-not-real-7878"

# Model values that start the way a provider key starts (spec CA-78).
PREFIXED_VALUES = [
    pytest.param("sk-fake-model-6666-PASTEDKEY-not-real-7777", id="sk-long"),
    pytest.param("sk-proj-fake-0000-PASTED-not-real", id="sk-proj"),
    pytest.param("sk-ant-fake-api03-PASTED-not-real-0000", id="sk-ant"),
    pytest.param(FAKE_AIZA_MODEL_VALUE, id="AIza-mixed"),
    pytest.param("AIzaSy-fake_0000-PASTED-not-real", id="AIza-dash-underscore"),
    pytest.param("sk-", id="sk-prefix-only"),
    pytest.param("AIza", id="AIza-prefix-only"),
    pytest.param("sk-" + "x" * 20_000, id="sk-huge"),
    pytest.param("sk-fake-ção-日本語-\"quoted\"-#hash-not-real", id="sk-odd-characters"),
]

# Ordinary model names, including near misses of the prefixes; kept unchanged.
ORDINARY_MODELS = [
    pytest.param("fake-text-model-1", id="plain"),
    pytest.param("gpt-fake-4o-mini", id="gpt-like"),
    pytest.param("claude-fake-sonnet-4-5", id="claude-like"),
    pytest.param("gemini-fake-2.5-pro", id="gemini-like"),
    pytest.param("imagen-fake-4.0-generate-001", id="imagen-like"),
    pytest.param("skeleton-model-1", id="starts-with-sk-letters"),
    pytest.param("sk_model-1", id="sk-underscore"),
    pytest.param("ask-model-1", id="sk-dash-inside"),
    pytest.param("model-sk-edition", id="sk-dash-later"),
    pytest.param("AIz-model-1", id="AIz-short"),
    pytest.param("my-AIza-tuned-model", id="AIza-inside"),
    pytest.param("módelo-✓-ギ-fake", id="non-ascii"),
    pytest.param("my-own-fine-tune:v2.1@2026", id="punctuation"),
]


def _load(directory, settings):
    from core.config import load_config

    return load_config(write_settings(directory, settings))


def _entries_for(config, setting):
    return [entry for entry in (*config.settings_to_fix, *config.notices) if entry.setting == setting]


def _assert_model_reported_once_to_fix(config, setting):
    """The model setting is named exactly once, as a setting to fix (plan section 6)."""
    entries = _entries_for(config, setting)
    assert len(entries) == 1, [(entry.setting, entry.code) for entry in entries]
    assert entries[0].code == SETTING_TO_FIX
    assert entries[0].message.strip()


def _assert_value_nowhere(config, value):
    """The value is not in the config's text forms, its model fields or any message."""
    texts = [
        str(config),
        repr(config),
        config.llm_provider,
        config.llm_model,
        config.image_provider,
        config.image_model,
        *(entry.message for entry in (*config.settings_to_fix, *config.notices)),
    ]
    for text in texts:
        assert value not in text


def _text_settings_with_model(model, key=FAKE_TEXT_KEY):
    return full_text_settings(provider="openai", model=model, key=key)


def _image_settings_with_model(model, image_key=FAKE_IMAGE_KEY):
    return full_text_settings(provider="openai") | {
        "IMAGE_PROVIDER": "google",
        "IMAGE_API_KEY": image_key,
        "IMAGE_MODEL": model,
    }


# --- Text model with a key prefix ---


@pytest.mark.parametrize("value", PREFIXED_VALUES)
def test_t128_ca78_text_model_with_key_prefix_is_a_setting_to_fix(tmp_path, value):
    """CA-78 / RN-08 / T128: LLM_MODEL starting with a key prefix names LLM_MODEL as the setting to fix."""
    config = _load(tmp_path, _text_settings_with_model(value))

    assert settings_named(config.settings_to_fix) == {"LLM_MODEL"}
    _assert_model_reported_once_to_fix(config, "LLM_MODEL")


@pytest.mark.parametrize("value", PREFIXED_VALUES)
def test_t128_rn06_text_model_with_key_prefix_is_not_kept(tmp_path, value):
    """RN-06 / CA-78 / T128: LLM_MODEL starting with a key prefix is not kept; the model reads as not set."""
    config = _load(tmp_path, _text_settings_with_model(value))

    assert config.llm_model == ""
    _assert_value_nowhere(config, value)


@pytest.mark.parametrize("provider", ["openai", "anthropic", "google"])
def test_t128_ca78_text_model_with_key_prefix_is_dropped_for_every_text_provider(tmp_path, provider):
    """CA-78 / RN-07 / T128: the check does not depend on the text provider."""
    for value in ("sk-fake-model-6666-PASTEDKEY-not-real-7777", FAKE_AIZA_MODEL_VALUE):
        config = _load(tmp_path, full_text_settings(provider=provider, model=value))

        assert config.llm_model == ""
        assert settings_named(config.settings_to_fix) == {"LLM_MODEL"}


# --- Image model with a key prefix ---


@pytest.mark.parametrize("value", PREFIXED_VALUES)
@pytest.mark.parametrize("image_provider", ["openai", "google"])
def test_t128_ca78_image_model_with_key_prefix_is_a_setting_to_fix(tmp_path, value, image_provider):
    """CA-78 / RN-08 / T128: IMAGE_MODEL starting with a key prefix names IMAGE_MODEL and is not kept."""
    settings = _image_settings_with_model(value) | {"IMAGE_PROVIDER": image_provider}
    config = _load(tmp_path, settings)

    assert config.image_model == ""
    assert settings_named(config.settings_to_fix) == {"IMAGE_MODEL"}
    _assert_model_reported_once_to_fix(config, "IMAGE_MODEL")
    _assert_value_nowhere(config, value)


@pytest.mark.parametrize("text_provider", ["openai", "google"])
@pytest.mark.parametrize(
    "value", ["sk-fake-model-6666-PASTEDKEY-not-real-7777", FAKE_AIZA_MODEL_VALUE]
)
def test_t128_ca78_image_model_with_key_prefix_and_image_capable_text_is_a_setting_to_fix(
    tmp_path, text_provider, value
):
    """CA-78 / RN-06 / T128: with no IMAGE_PROVIDER, art uses the text provider; a key-like IMAGE_MODEL is still dropped."""
    settings = full_text_settings(provider=text_provider) | {"IMAGE_MODEL": value}
    config = _load(tmp_path, settings)

    assert config.image_model == ""
    assert settings_named(config.settings_to_fix) == {"IMAGE_MODEL"}
    _assert_model_reported_once_to_fix(config, "IMAGE_MODEL")
    _assert_value_nowhere(config, value)


@pytest.mark.parametrize(
    "value", ["sk-fake-model-6666-PASTEDKEY-not-real-7777", FAKE_AIZA_MODEL_VALUE]
)
def test_t128_ca78_ignored_image_model_with_key_prefix_is_a_setting_to_fix(tmp_path, value):
    """CA-78 / RN-06 / T128: with no IMAGE_PROVIDER and Anthropic text, a key-like IMAGE_MODEL is reported once, to fix.

    Decided case: CA-78 names the model setting to fix for any image model
    value that looks like a key, so the `ignored` notice is not used for it.
    """
    settings = full_text_settings(provider="anthropic") | {"IMAGE_MODEL": value}
    config = _load(tmp_path, settings)

    assert config.image_model == ""
    assert settings_named(config.settings_to_fix) == {"IMAGE_MODEL"}
    assert "IMAGE_MODEL" not in settings_named(config.notices)
    _assert_model_reported_once_to_fix(config, "IMAGE_MODEL")
    _assert_value_nowhere(config, value)


def test_t128_ca78_ignored_image_model_with_key_prefix_keeps_the_ignored_key_notice(tmp_path):
    """CA-74 / CA-78 / T128: an ignored IMAGE_API_KEY keeps its notice next to the key-like IMAGE_MODEL."""
    value = "sk-fake-model-6666-PASTEDKEY-not-real-7777"
    settings = full_text_settings(provider="anthropic") | {"IMAGE_API_KEY": FAKE_IMAGE_KEY, "IMAGE_MODEL": value}
    config = _load(tmp_path, settings)

    assert settings_named(config.notices) == {"IMAGE_API_KEY"}
    assert settings_named(config.settings_to_fix) == {"IMAGE_MODEL"}
    _assert_value_nowhere(config, value)


@pytest.mark.parametrize(
    "value", ["sk-fake-model-6666-PASTEDKEY-not-real-7777", FAKE_AIZA_MODEL_VALUE]
)
def test_t128_ca78_anthropic_image_provider_with_key_like_model_names_both_settings(tmp_path, value):
    """CA-78 / CA-74 / RN-08 / T128: IMAGE_PROVIDER=anthropic and a key-like IMAGE_MODEL name both settings once
    each, as settings to fix, and the model value is dropped."""
    settings = full_text_settings(provider="openai") | {
        "IMAGE_PROVIDER": "anthropic",
        "IMAGE_API_KEY": FAKE_IMAGE_KEY,
        "IMAGE_MODEL": value,
    }
    config = _load(tmp_path, settings)

    assert config.image_model == ""
    assert settings_named(config.settings_to_fix) == {"IMAGE_PROVIDER", "IMAGE_MODEL"}
    assert settings_named(config.notices) == set()
    _assert_model_reported_once_to_fix(config, "IMAGE_MODEL")
    provider_entries = _entries_for(config, "IMAGE_PROVIDER")
    assert len(provider_entries) == 1 and provider_entries[0].code == SETTING_TO_FIX
    _assert_value_nowhere(config, value)


# --- Model equal to a configured key value ---


def test_t128_ca78_text_model_equal_to_text_key_is_a_setting_to_fix(tmp_path):
    """CA-78 / RN-06 / T128: LLM_MODEL equal to LLM_API_KEY (no known prefix) is dropped and named."""
    config = _load(tmp_path, _text_settings_with_model(UNPREFIXED_TEXT_KEY, key=UNPREFIXED_TEXT_KEY))

    assert config.llm_model == ""
    assert settings_named(config.settings_to_fix) == {"LLM_MODEL"}
    _assert_model_reported_once_to_fix(config, "LLM_MODEL")
    _assert_value_nowhere(config, UNPREFIXED_TEXT_KEY)
    assert config.llm_api_key.reveal() == UNPREFIXED_TEXT_KEY


def test_t128_ca78_text_model_equal_to_image_key_is_a_setting_to_fix(tmp_path):
    """CA-78 / RN-06 / T128: LLM_MODEL equal to IMAGE_API_KEY is dropped and named."""
    settings = _image_settings_with_model("fake-image-model-1", image_key=UNPREFIXED_IMAGE_KEY) | {
        "LLM_MODEL": UNPREFIXED_IMAGE_KEY
    }
    config = _load(tmp_path, settings)

    assert config.llm_model == ""
    assert config.image_model == "fake-image-model-1"
    assert settings_named(config.settings_to_fix) == {"LLM_MODEL"}
    _assert_value_nowhere(config, UNPREFIXED_IMAGE_KEY)


def test_t128_ca78_image_model_equal_to_image_key_is_a_setting_to_fix(tmp_path):
    """CA-78 / RN-06 / T128: IMAGE_MODEL equal to IMAGE_API_KEY is dropped and named."""
    settings = _image_settings_with_model(UNPREFIXED_IMAGE_KEY, image_key=UNPREFIXED_IMAGE_KEY)
    config = _load(tmp_path, settings)

    assert config.image_model == ""
    assert settings_named(config.settings_to_fix) == {"IMAGE_MODEL"}
    _assert_model_reported_once_to_fix(config, "IMAGE_MODEL")
    _assert_value_nowhere(config, UNPREFIXED_IMAGE_KEY)


def test_t128_ca78_image_model_equal_to_text_key_is_a_setting_to_fix(tmp_path):
    """CA-78 / RN-06 / T128: IMAGE_MODEL equal to LLM_API_KEY is dropped and named."""
    settings = full_text_settings(provider="openai", key=UNPREFIXED_TEXT_KEY) | {
        "IMAGE_PROVIDER": "openai",
        "IMAGE_MODEL": UNPREFIXED_TEXT_KEY,
    }
    config = _load(tmp_path, settings)

    assert config.image_model == ""
    assert config.llm_model == "fake-text-model-1"
    assert settings_named(config.settings_to_fix) == {"IMAGE_MODEL"}
    _assert_value_nowhere(config, UNPREFIXED_TEXT_KEY)


def test_t128_ca78_image_model_equal_to_text_key_without_image_provider_is_a_setting_to_fix(tmp_path):
    """CA-78 / RN-06 / T128: with art on the text provider, IMAGE_MODEL equal to the text key is dropped and named."""
    settings = full_text_settings(provider="google", key=UNPREFIXED_TEXT_KEY) | {"IMAGE_MODEL": UNPREFIXED_TEXT_KEY}
    config = _load(tmp_path, settings)

    assert config.image_model == ""
    assert settings_named(config.settings_to_fix) == {"IMAGE_MODEL"}
    _assert_value_nowhere(config, UNPREFIXED_TEXT_KEY)


def test_t128_ca78_model_equal_to_ignored_image_key_is_a_setting_to_fix(tmp_path):
    """CA-78 / RN-06 / T128: an IMAGE_API_KEY ignored for lack of IMAGE_PROVIDER is still a configured key value."""
    settings = full_text_settings(provider="openai", model=UNPREFIXED_IMAGE_KEY) | {
        "IMAGE_API_KEY": UNPREFIXED_IMAGE_KEY
    }
    config = _load(tmp_path, settings)

    assert config.llm_model == ""
    assert settings_named(config.settings_to_fix) == {"LLM_MODEL"}
    assert settings_named(config.notices) == {"IMAGE_API_KEY"}
    _assert_value_nowhere(config, UNPREFIXED_IMAGE_KEY)


def test_t128_ca78_model_equal_to_key_of_invalid_image_provider_is_a_setting_to_fix(tmp_path):
    """CA-78 / RN-06 / T128: the image key kept with an invalid IMAGE_PROVIDER is still a configured key value."""
    settings = full_text_settings(provider="openai", model=UNPREFIXED_IMAGE_KEY) | {
        "IMAGE_PROVIDER": "anthropic",
        "IMAGE_API_KEY": UNPREFIXED_IMAGE_KEY,
    }
    config = _load(tmp_path, settings)

    assert config.llm_model == ""
    assert settings_named(config.settings_to_fix) == {"LLM_MODEL", "IMAGE_PROVIDER"}
    _assert_value_nowhere(config, UNPREFIXED_IMAGE_KEY)


def test_t128_ca78_both_models_equal_to_keys_name_both_settings(tmp_path):
    """CA-78 / RN-08 / T128: a key in each model setting names both model settings."""
    settings = full_text_settings(provider="openai", model=UNPREFIXED_TEXT_KEY, key=UNPREFIXED_TEXT_KEY) | {
        "IMAGE_PROVIDER": "google",
        "IMAGE_API_KEY": UNPREFIXED_IMAGE_KEY,
        "IMAGE_MODEL": UNPREFIXED_IMAGE_KEY,
    }
    config = _load(tmp_path, settings)

    assert config.llm_model == ""
    assert config.image_model == ""
    assert settings_named(config.settings_to_fix) == {"LLM_MODEL", "IMAGE_MODEL"}
    _assert_model_reported_once_to_fix(config, "LLM_MODEL")
    _assert_model_reported_once_to_fix(config, "IMAGE_MODEL")


def test_t128_ca78_quoted_and_padded_model_equal_to_key_is_dropped(tmp_path):
    """CA-78 / RN-06 / T128: equality is checked on the values as read (quotes and spaces stripped)."""
    content = (
        f"LLM_PROVIDER=openai\n"
        f"LLM_API_KEY=  {UNPREFIXED_TEXT_KEY}  \n"
        f'LLM_MODEL="  {UNPREFIXED_TEXT_KEY}  "\n'
    )
    from core.config import load_config

    config = load_config(write_env(tmp_path, content))

    assert config.llm_model == ""
    assert settings_named(config.settings_to_fix) == {"LLM_MODEL"}
    _assert_value_nowhere(config, UNPREFIXED_TEXT_KEY)


def test_t128_ca78_quoted_model_with_key_prefix_is_dropped(tmp_path):
    """CA-78 / RN-06 / T128: a quoted, padded value with a key prefix is checked after quotes and spaces are stripped."""
    value = FAKE_AIZA_MODEL_VALUE
    content = env_text(full_text_settings()).replace("LLM_MODEL=fake-text-model-1", f"LLM_MODEL= ' {value} ' ")
    from core.config import load_config

    config = load_config(write_env(tmp_path, content))

    assert config.llm_model == ""
    assert settings_named(config.settings_to_fix) == {"LLM_MODEL"}
    _assert_value_nowhere(config, value)


def test_t128_ca78_debug_override_with_key_like_model_is_dropped(tmp_path, monkeypatch):
    """CA-78 / RN-06 / T128: a key-like LLM_MODEL from the process environment (debug override) is also dropped."""
    value = "sk-fake-model-6666-PASTEDKEY-not-real-7777"
    monkeypatch.setenv("CARDFACTORY_DEBUG", "1")
    monkeypatch.setenv("LLM_MODEL", value)

    config = _load(tmp_path, full_text_settings())

    assert config.llm_model == ""
    assert settings_named(config.settings_to_fix) == {"LLM_MODEL"}
    _assert_value_nowhere(config, value)


def test_t128_ca78_key_like_model_leaves_the_keys_in_place(tmp_path):
    """RN-08 / T128: dropping a key-like model never drops the keys or names a key setting."""
    settings = _image_settings_with_model(FAKE_AIZA_MODEL_VALUE) | {
        "LLM_MODEL": "sk-fake-model-6666-PASTEDKEY-not-real-7777"
    }
    config = _load(tmp_path, settings)

    assert config.llm_api_key.reveal() == FAKE_TEXT_KEY
    assert config.image_api_key.reveal() == FAKE_IMAGE_KEY
    assert config.llm_provider == "openai"
    assert config.image_provider == "google"
    assert settings_named(config.settings_to_fix) == {"LLM_MODEL", "IMAGE_MODEL"}


# --- Ordinary model names (unchanged) ---


@pytest.mark.parametrize("model", ORDINARY_MODELS)
def test_t128_rn05_ordinary_text_model_is_kept_unchanged(tmp_path, model):
    """RN-05 / CA-78 / T128: an ordinary LLM_MODEL, even one close to a key prefix, is kept as written."""
    config = _load(tmp_path, _text_settings_with_model(model))

    assert config.llm_model == model
    assert config.settings_to_fix == ()


@pytest.mark.parametrize("model", ORDINARY_MODELS)
def test_t128_rn05_ordinary_image_model_is_kept_unchanged(tmp_path, model):
    """RN-05 / CA-78 / T128: an ordinary IMAGE_MODEL, even one close to a key prefix, is kept as written."""
    config = _load(tmp_path, _image_settings_with_model(model))

    assert config.image_model == model
    assert config.settings_to_fix == ()


def test_t128_rn05_model_containing_part_of_a_key_is_kept(tmp_path):
    """RN-05 / T128: only a model equal to a key is dropped; a model sharing a few characters with it is kept."""
    model = UNPREFIXED_TEXT_KEY[:12]
    config = _load(tmp_path, _text_settings_with_model(model, key=UNPREFIXED_TEXT_KEY))

    assert config.llm_model == model
    assert config.settings_to_fix == ()
