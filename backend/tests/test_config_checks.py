"""Settings to fix and notices reported by core.config (task T4, spec RN-05, RN-07, RN-08, RN-47).

Every test uses a temporary file and a cleared environment, never the
repository `.env`.
"""

import pytest

from tests.config_files import (
    DEFAULT_PORT,
    FAKE_IMAGE_KEY,
    FAKE_TEXT_KEY,
    clean_environment,  # noqa: F401 (fixture)
    full_text_settings,
    settings_named,
    write_settings,
)

pytestmark = pytest.mark.usefixtures("clean_environment")


def _load(directory, settings):
    from core.config import load_config

    return load_config(write_settings(directory, settings))


def _all_messages(config):
    return [entry.message for entry in (*config.settings_to_fix, *config.notices)]


# --- Entry shape ---


def test_t4_rn08_entries_have_setting_code_and_message(tmp_path):
    """RN-08 / T4: each setting to fix and notice has a setting name, a code and a message."""
    settings = {
        "LLM_PROVIDER": "openia",
        "LLM_API_KEY": "",
        "LLM_MODEL": "",
        "IMAGE_API_KEY": FAKE_IMAGE_KEY,
        "APP_PORT": "not-a-port",
    }
    config = _load(tmp_path, settings)

    entries = (*config.settings_to_fix, *config.notices)
    assert config.settings_to_fix and config.notices
    for entry in entries:
        assert isinstance(entry.setting, str) and entry.setting
        assert isinstance(entry.code, str) and entry.code
        assert isinstance(entry.message, str) and entry.message.strip()


# --- Text settings (CA-05) ---


@pytest.mark.parametrize("provider", ["openai", "anthropic", "google"])
def test_t4_ca05_full_text_configuration_needs_no_fix(tmp_path, provider):
    """CA-05 / RN-05 / T4: each known text provider with a key and a model has no setting to fix."""
    config = _load(tmp_path, full_text_settings(provider=provider))

    assert config.llm_provider == provider
    assert config.settings_to_fix == ()
    assert config.notices == ()


@pytest.mark.parametrize(
    ("written", "expected"),
    [
        ("OpenAI", "openai"),
        ("  OPENAI  ", "openai"),
        ("Anthropic", "anthropic"),
        ("GoOgLe", "google"),
        ('" Google "', "google"),
    ],
)
def test_t4_rn05_text_provider_trimmed_and_case_insensitive(tmp_path, written, expected):
    """RN-05 / RN-08 / T4: provider values are trimmed and compared case-insensitively."""
    config = _load(tmp_path, full_text_settings(provider=written))

    assert config.llm_provider == expected
    assert config.settings_to_fix == ()


@pytest.mark.parametrize(
    "provider",
    ["openia", "gpt", "claude", "gemini", "fake", "open ai", "openai​", "ｏｐｅｎａｉ", "open-ai", "openai,google"],
)
def test_t4_ca05_unknown_text_provider_is_a_setting_to_fix(tmp_path, provider):
    """CA-05 / RN-08 / T4: an unknown text provider names LLM_PROVIDER, and only it."""
    config = _load(tmp_path, full_text_settings(provider=provider))

    assert settings_named(config.settings_to_fix) == {"LLM_PROVIDER"}


def test_t4_ca05_empty_text_provider_is_a_setting_to_fix(tmp_path):
    """CA-05 / RN-05 / T4: the text provider is required; an empty value names LLM_PROVIDER."""
    config = _load(tmp_path, full_text_settings(provider=""))

    assert settings_named(config.settings_to_fix) == {"LLM_PROVIDER"}


@pytest.mark.parametrize("key", ["", "   ", '""', "''"])
def test_t4_ca05_missing_text_key_is_a_setting_to_fix(tmp_path, key):
    """CA-05 / RN-08 / T4: an empty text key names LLM_API_KEY, and only it."""
    config = _load(tmp_path, full_text_settings(key=key))

    assert settings_named(config.settings_to_fix) == {"LLM_API_KEY"}


def test_t4_ca05_absent_text_key_line_is_a_setting_to_fix(tmp_path):
    """CA-05 / RN-08 / T4: a file without the LLM_API_KEY line names LLM_API_KEY."""
    settings = full_text_settings()
    del settings["LLM_API_KEY"]
    config = _load(tmp_path, settings)

    assert settings_named(config.settings_to_fix) == {"LLM_API_KEY"}


@pytest.mark.parametrize("model", ["", "   ", '""'])
def test_t4_ca05_missing_text_model_is_a_setting_to_fix(tmp_path, model):
    """CA-05 / RN-05 / RN-08 / T4: an empty model names LLM_MODEL, and only it."""
    config = _load(tmp_path, full_text_settings(model=model))

    assert settings_named(config.settings_to_fix) == {"LLM_MODEL"}


def test_t4_ca05_several_problems_are_all_named(tmp_path):
    """CA-05 / RN-08 / T4: unknown provider, missing key and missing model are reported together."""
    config = _load(tmp_path, {"LLM_PROVIDER": "nonsense", "LLM_API_KEY": "", "LLM_MODEL": ""})

    assert settings_named(config.settings_to_fix) == {"LLM_PROVIDER", "LLM_API_KEY", "LLM_MODEL"}


def test_t4_rn06_messages_never_contain_keys(tmp_path):
    """RN-06 / CA-06 / T4: no setting to fix or notice message contains a key value."""
    settings = {
        "LLM_PROVIDER": "nonsense",
        "LLM_API_KEY": FAKE_TEXT_KEY,
        "LLM_MODEL": "",
        "IMAGE_API_KEY": FAKE_IMAGE_KEY,
        "APP_PORT": "0",
    }
    config = _load(tmp_path, settings)

    messages = _all_messages(config)
    assert messages
    for message in messages:
        assert FAKE_TEXT_KEY not in message
        assert FAKE_IMAGE_KEY not in message


# --- Image settings (RN-07, RN-08, CA-67, CA-68, CA-74) ---


@pytest.mark.parametrize("text_provider", ["openai", "anthropic", "google"])
def test_t4_ca74_empty_image_settings_are_not_settings_to_fix(tmp_path, text_provider):
    """CA-74 / RN-08 / T4: empty image settings report no setting to fix and no notice."""
    settings = full_text_settings(provider=text_provider) | {
        "IMAGE_PROVIDER": "",
        "IMAGE_API_KEY": "",
        "IMAGE_MODEL": "",
    }
    config = _load(tmp_path, settings)

    assert config.settings_to_fix == ()
    assert config.notices == ()


def test_t4_ca74_absent_image_lines_are_not_settings_to_fix(tmp_path):
    """CA-74 / RN-08 / T4: a file with no image lines at all reports no setting to fix."""
    config = _load(tmp_path, full_text_settings(provider="anthropic"))

    assert config.settings_to_fix == ()
    assert config.notices == ()


@pytest.mark.parametrize("image_provider", ["anthropic", "Anthropic", " ANTHROPIC "])
def test_t4_ca74_anthropic_image_provider_is_a_setting_to_fix(tmp_path, image_provider):
    """CA-74 / RN-08 / T4: Anthropic is not image-capable, so IMAGE_PROVIDER is named; text needs no fix."""
    settings = full_text_settings(provider="openai") | {
        "IMAGE_PROVIDER": image_provider,
        "IMAGE_API_KEY": FAKE_IMAGE_KEY,
        "IMAGE_MODEL": "fake-image-model-1",
    }
    config = _load(tmp_path, settings)

    assert settings_named(config.settings_to_fix) == {"IMAGE_PROVIDER"}


@pytest.mark.parametrize("image_provider", ["midjourney", "dalle", "imagen", "fake", "open ai", "google​"])
def test_t4_rn08_unknown_image_provider_is_a_setting_to_fix(tmp_path, image_provider):
    """RN-08 / T4: an unknown image provider names IMAGE_PROVIDER; the text settings stay valid."""
    settings = full_text_settings(provider="openai") | {
        "IMAGE_PROVIDER": image_provider,
        "IMAGE_API_KEY": FAKE_IMAGE_KEY,
        "IMAGE_MODEL": "fake-image-model-1",
    }
    config = _load(tmp_path, settings)

    assert settings_named(config.settings_to_fix) == {"IMAGE_PROVIDER"}


@pytest.mark.parametrize(
    ("written", "expected"),
    [("OpenAI", "openai"), ("  Google ", "google"), ("GOOGLE", "google"), ("'openai'", "openai")],
)
def test_t4_rn05_image_provider_trimmed_and_case_insensitive(tmp_path, written, expected):
    """RN-05 / RN-08 / T4: the image provider is trimmed and compared case-insensitively."""
    settings = full_text_settings(provider="anthropic") | {
        "IMAGE_PROVIDER": written,
        "IMAGE_API_KEY": FAKE_IMAGE_KEY,
        "IMAGE_MODEL": "fake-image-model-1",
    }
    config = _load(tmp_path, settings)

    assert config.image_provider == expected
    assert config.settings_to_fix == ()


@pytest.mark.parametrize("image_provider", ["openai", "google"])
def test_t4_ca68_image_provider_without_image_model_names_the_image_model(tmp_path, image_provider):
    """CA-68 / RN-07 / T4: an image provider set with no image model names IMAGE_MODEL, and only it."""
    settings = full_text_settings(provider="anthropic") | {
        "IMAGE_PROVIDER": image_provider,
        "IMAGE_API_KEY": FAKE_IMAGE_KEY,
        "IMAGE_MODEL": "",
    }
    config = _load(tmp_path, settings)

    assert settings_named(config.settings_to_fix) == {"IMAGE_MODEL"}


def test_t4_rn05_different_image_provider_with_empty_image_key_names_the_image_key(tmp_path):
    """RN-05 / RN-08 / T4: when the image provider differs from the text provider, an empty image key names IMAGE_API_KEY."""
    settings = full_text_settings(provider="anthropic") | {
        "IMAGE_PROVIDER": "openai",
        "IMAGE_API_KEY": "",
        "IMAGE_MODEL": "fake-image-model-1",
    }
    config = _load(tmp_path, settings)

    assert settings_named(config.settings_to_fix) == {"IMAGE_API_KEY"}


def test_t4_rn05_different_image_provider_uses_its_own_key(tmp_path):
    """RN-05 / T4: with a different image provider and its own key, the image key is that key."""
    settings = full_text_settings(provider="anthropic") | {
        "IMAGE_PROVIDER": "google",
        "IMAGE_API_KEY": FAKE_IMAGE_KEY,
        "IMAGE_MODEL": "fake-image-model-1",
    }
    config = _load(tmp_path, settings)

    assert config.image_api_key.reveal() == FAKE_IMAGE_KEY
    assert config.image_model == "fake-image-model-1"
    assert config.settings_to_fix == ()
    assert config.notices == ()


@pytest.mark.parametrize("image_provider", ["openai", "OpenAI", " openai "])
def test_t4_ca67_same_image_provider_with_empty_image_key_uses_text_key(tmp_path, image_provider):
    """CA-67 / RN-05 / T4: with the image provider equal to the text provider and no image key, the text key is used."""
    settings = full_text_settings(provider="openai") | {
        "IMAGE_PROVIDER": image_provider,
        "IMAGE_API_KEY": "",
        "IMAGE_MODEL": "fake-image-model-1",
    }
    config = _load(tmp_path, settings)

    assert config.image_api_key.reveal() == FAKE_TEXT_KEY
    assert config.settings_to_fix == ()
    assert config.notices == ()


def test_t4_ca67_same_image_provider_with_own_image_key_uses_it(tmp_path):
    """CA-67 / RN-05 / T4: an image key set for the same provider is used instead of the text key."""
    settings = full_text_settings(provider="google") | {
        "IMAGE_PROVIDER": "google",
        "IMAGE_API_KEY": FAKE_IMAGE_KEY,
        "IMAGE_MODEL": "fake-image-model-1",
    }
    config = _load(tmp_path, settings)

    assert config.image_api_key.reveal() == FAKE_IMAGE_KEY
    assert config.settings_to_fix == ()


@pytest.mark.parametrize("text_provider", ["openai", "google"])
def test_t4_rn05_no_image_provider_falls_back_to_text_key(tmp_path, text_provider):
    """RN-05 / RN-07 / T4: with no image provider and an image-capable text provider, art uses the text key and image model."""
    settings = full_text_settings(provider=text_provider) | {
        "IMAGE_PROVIDER": "",
        "IMAGE_API_KEY": "",
        "IMAGE_MODEL": "fake-image-model-1",
    }
    config = _load(tmp_path, settings)

    assert config.image_api_key.reveal() == FAKE_TEXT_KEY
    assert config.image_model == "fake-image-model-1"
    assert config.settings_to_fix == ()
    assert config.notices == ()


@pytest.mark.parametrize("text_provider", ["openai", "anthropic", "google"])
def test_t4_ca74_image_key_without_image_provider_is_ignored_with_notice(tmp_path, text_provider):
    """CA-74 / RN-08 / T4: an image key with no image provider is ignored with a notice, not a setting to fix."""
    settings = full_text_settings(provider=text_provider) | {
        "IMAGE_PROVIDER": "",
        "IMAGE_API_KEY": FAKE_IMAGE_KEY,
    }
    config = _load(tmp_path, settings)

    assert settings_named(config.notices) == {"IMAGE_API_KEY"}
    assert config.settings_to_fix == ()
    assert config.image_api_key.reveal() != FAKE_IMAGE_KEY


@pytest.mark.parametrize("text_provider", ["openai", "google"])
def test_t4_ca74_ignored_image_key_is_replaced_by_text_key(tmp_path, text_provider):
    """CA-74 / RN-05 / T4: the ignored image key is never used; art on the text provider uses the text key."""
    settings = full_text_settings(provider=text_provider) | {
        "IMAGE_PROVIDER": "",
        "IMAGE_API_KEY": FAKE_IMAGE_KEY,
        "IMAGE_MODEL": "fake-image-model-1",
    }
    config = _load(tmp_path, settings)

    assert config.image_api_key.reveal() == FAKE_TEXT_KEY
    assert settings_named(config.notices) == {"IMAGE_API_KEY"}


def test_t4_ca74_image_model_without_image_provider_and_anthropic_text_is_ignored_with_notice(tmp_path):
    """CA-74 / RN-08 / T4: an image model with no image provider and Anthropic as text provider is ignored with a notice."""
    settings = full_text_settings(provider="anthropic") | {
        "IMAGE_PROVIDER": "",
        "IMAGE_API_KEY": "",
        "IMAGE_MODEL": "fake-image-model-1",
    }
    config = _load(tmp_path, settings)

    assert settings_named(config.notices) == {"IMAGE_MODEL"}
    assert config.settings_to_fix == ()


def test_t4_ca74_image_key_and_model_ignored_together_with_anthropic_text(tmp_path):
    """CA-74 / RN-08 / T4: with Anthropic text and no image provider, both an image key and an image model get a notice."""
    settings = full_text_settings(provider="anthropic") | {
        "IMAGE_PROVIDER": "",
        "IMAGE_API_KEY": FAKE_IMAGE_KEY,
        "IMAGE_MODEL": "fake-image-model-1",
    }
    config = _load(tmp_path, settings)

    assert settings_named(config.notices) == {"IMAGE_API_KEY", "IMAGE_MODEL"}
    assert config.settings_to_fix == ()


def test_t4_rn08_image_problems_leave_text_settings_valid(tmp_path):
    """RN-08 / T4: image settings are checked separately; an image problem names only image settings."""
    settings = full_text_settings(provider="google") | {
        "IMAGE_PROVIDER": "anthropic",
        "IMAGE_API_KEY": "",
        "IMAGE_MODEL": "",
    }
    config = _load(tmp_path, settings)

    named = settings_named(config.settings_to_fix)
    assert "IMAGE_PROVIDER" in named
    assert named <= {"IMAGE_PROVIDER", "IMAGE_API_KEY", "IMAGE_MODEL"}
    assert config.llm_provider == "google"
    assert config.llm_model == "fake-text-model-1"


def test_t4_rn08_text_problems_do_not_hide_image_problems(tmp_path):
    """RN-08 / T4: a text problem and an image problem are both reported."""
    settings = full_text_settings(provider="openai", key="") | {
        "IMAGE_PROVIDER": "google",
        "IMAGE_API_KEY": FAKE_IMAGE_KEY,
        "IMAGE_MODEL": "",
    }
    config = _load(tmp_path, settings)

    assert settings_named(config.settings_to_fix) == {"LLM_API_KEY", "IMAGE_MODEL"}


# --- Port (RN-47, CA-75) ---


def test_t4_rn47_port_defaults_to_47821_when_absent(tmp_path):
    """RN-47 / T4: with no APP_PORT line, the port is 47821 and nothing is reported."""
    config = _load(tmp_path, full_text_settings())

    assert config.app_port == DEFAULT_PORT
    assert config.settings_to_fix == ()


@pytest.mark.parametrize(("written", "expected"), [("1", 1), ("8080", 8080), ("65535", 65535), (" 50000 ", 50000), ('"47900"', 47900)])
def test_t4_rn47_valid_port_is_used(tmp_path, written, expected):
    """RN-47 / CA-75 / T4: a number from 1 to 65535 is used as the port."""
    config = _load(tmp_path, full_text_settings() | {"APP_PORT": written})

    assert config.app_port == expected
    assert isinstance(config.app_port, int)
    assert config.settings_to_fix == ()


@pytest.mark.parametrize(
    "written",
    ["abc", "0", "65536", "-1", "-47821", "80.5", "1e3", "0x1F90", "99999999999999999999999999", "80 80", "8080abc", "port"],
)
def test_t4_ca75_invalid_port_falls_back_to_default_as_setting_to_fix(tmp_path, written):
    """CA-75 / RN-47 / T4: a port that is not a number from 1 to 65535 becomes 47821 and names APP_PORT."""
    config = _load(tmp_path, full_text_settings() | {"APP_PORT": written})

    assert config.app_port == DEFAULT_PORT
    assert settings_named(config.settings_to_fix) == {"APP_PORT"}


def _assert_value_nowhere(config, value):
    texts = [str(config), repr(config), config.llm_provider, config.image_provider, *_all_messages(config)]
    # Case-insensitive: a provider value may be kept lowercased.
    for text in texts:
        assert value.lower() not in text.lower()


def test_t4_rn06_key_pasted_as_text_provider_is_not_kept(tmp_path):
    """RN-06 / CA-06 / T4: an unrecognized LLM_PROVIDER (a pasted key) is dropped; the setting is still named."""
    pasted = "sk-fake-pasted-4444-PROVIDERKEY-not-real"
    config = _load(tmp_path, full_text_settings(provider=pasted))

    assert config.llm_provider == ""
    assert settings_named(config.settings_to_fix) == {"LLM_PROVIDER"}
    _assert_value_nowhere(config, pasted)


def test_t4_rn06_key_pasted_as_image_provider_is_not_kept(tmp_path):
    """RN-06 / CA-06 / T4: an unrecognized IMAGE_PROVIDER (a pasted key) is dropped; the setting is still named."""
    pasted = "sk-fake-pasted-5555-IMAGEPROVIDER-not-real"
    settings = full_text_settings(provider="openai") | {
        "IMAGE_PROVIDER": pasted,
        "IMAGE_API_KEY": FAKE_IMAGE_KEY,
        "IMAGE_MODEL": "fake-image-model-1",
    }
    config = _load(tmp_path, settings)

    assert config.image_provider == ""
    assert settings_named(config.settings_to_fix) == {"IMAGE_PROVIDER"}
    _assert_value_nowhere(config, pasted)


def test_t4_ca05_missing_text_key_is_falsy(tmp_path):
    """CA-05 / RN-08 / T4: with no text key, bool(config.llm_api_key) is False; with one, True."""
    assert bool(_load(tmp_path, full_text_settings(key="")).llm_api_key) is False

    other = tmp_path / "other"
    other.mkdir()
    assert bool(_load(other, full_text_settings()).llm_api_key) is True


@pytest.mark.parametrize("written", ["", "   ", "\t"])
def test_t4_rn47_empty_port_is_default_without_fix(tmp_path, written):
    """RN-47 / T4: an empty or blank APP_PORT is the default 47821, not a setting to fix."""
    config = _load(tmp_path, full_text_settings() | {"APP_PORT": written})

    assert config.app_port == DEFAULT_PORT
    assert config.settings_to_fix == ()


@pytest.mark.parametrize(("written", "expected"), [("08080", 8080), ("00001", 1), ("065535", 65535)])
def test_t4_rn47_leading_zeros_are_valid(tmp_path, written, expected):
    """RN-47 / CA-75 / T4: ASCII digits with leading zeros are a valid port."""
    config = _load(tmp_path, full_text_settings() | {"APP_PORT": written})

    assert config.app_port == expected
    assert config.settings_to_fix == ()


@pytest.mark.parametrize("written", ["+8080", "８０８０", "٨٠٨٠", "8080​", "00000", "065536"])
def test_t4_ca75_non_ascii_or_signed_port_is_invalid(tmp_path, written):
    """CA-75 / RN-47 / T4: only ASCII digits from 1 to 65535 are valid; others become 47821 and name APP_PORT."""
    config = _load(tmp_path, full_text_settings() | {"APP_PORT": written})

    assert config.app_port == DEFAULT_PORT
    assert settings_named(config.settings_to_fix) == {"APP_PORT"}


def test_t4_ca74_ignored_image_key_with_anthropic_text_leaves_image_key_empty(tmp_path):
    """CA-74 / RN-05 / T4: Anthropic text, no image provider and an image key: the image key is empty, with a notice."""
    settings = full_text_settings(provider="anthropic") | {
        "IMAGE_PROVIDER": "",
        "IMAGE_API_KEY": FAKE_IMAGE_KEY,
    }
    config = _load(tmp_path, settings)

    assert config.image_api_key.reveal() == ""
    assert settings_named(config.notices) == {"IMAGE_API_KEY"}
    assert config.settings_to_fix == ()
