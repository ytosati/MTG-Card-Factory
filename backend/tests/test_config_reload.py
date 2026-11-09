"""Reading `.env` again and the `.env.example` template (tasks T4 and T127, spec RN-08, RN-27, CA-73).

Every loader test uses a temporary file and a cleared environment, never the
repository `.env`.
"""

import os

import pytest

from tests.config_files import (
    FAKE_TEXT_KEY,
    SETTING_NAMES,
    bump_mtime,
    clean_environment,  # noqa: F401 (fixture)
    full_text_settings,
    set_mtime_ns,
    settings_named,
    write_settings,
)
from tests.settings_probe import REPOSITORY_ROOT

pytestmark = pytest.mark.usefixtures("clean_environment")


def _get(path=None):
    from core.config import get_config

    return get_config() if path is None else get_config(path)


def _without_key():
    settings = full_text_settings()
    settings["LLM_API_KEY"] = ""
    return settings


def test_t4_ca73_added_key_is_seen_without_restart(tmp_path):
    """CA-73 / RN-08 / T4: after the missing key is added to the file, get_config() reports no setting to fix."""
    path = write_settings(tmp_path, _without_key())
    assert settings_named(_get(path).settings_to_fix) == {"LLM_API_KEY"}

    write_settings(tmp_path, full_text_settings())
    bump_mtime(path)
    config = _get(path)

    assert config.settings_to_fix == ()
    assert config.llm_api_key.reveal() == FAKE_TEXT_KEY


def test_t4_ca73_changed_model_is_seen_without_restart(tmp_path):
    """CA-73 / RN-08 / T4: a changed setting is read again when the file's modification time changed."""
    path = write_settings(tmp_path, full_text_settings(model="fake-text-model-1"))
    assert _get(path).llm_model == "fake-text-model-1"

    write_settings(tmp_path, full_text_settings(model="fake-text-model-2"))
    bump_mtime(path)

    assert _get(path).llm_model == "fake-text-model-2"


def test_t127_ca73_size_change_with_same_mtime_is_read_again(tmp_path):
    """CA-73 / RN-08 / T127: a rewrite of a different size and the same modification time is read again."""
    path = write_settings(tmp_path, full_text_settings(model="fake-text-model-1"))
    original_mtime_ns = os.stat(path).st_mtime_ns
    original_size = os.stat(path).st_size
    assert _get(path).llm_model == "fake-text-model-1"

    write_settings(tmp_path, full_text_settings(model="fake-text-model-with-a-longer-name-2"))
    set_mtime_ns(path, original_mtime_ns)
    assert os.stat(path).st_mtime_ns == original_mtime_ns
    assert os.stat(path).st_size != original_size

    assert _get(path).llm_model == "fake-text-model-with-a-longer-name-2"


def test_t127_ca73_added_key_with_same_mtime_is_seen(tmp_path):
    """CA-73 / RN-08 / T127: a key added within the timestamp precision (same modification time) is seen."""
    path = write_settings(tmp_path, _without_key())
    original_mtime_ns = os.stat(path).st_mtime_ns
    assert settings_named(_get(path).settings_to_fix) == {"LLM_API_KEY"}

    write_settings(tmp_path, full_text_settings())
    set_mtime_ns(path, original_mtime_ns)
    config = _get(path)

    assert config.settings_to_fix == ()
    assert config.llm_api_key.reveal() == FAKE_TEXT_KEY


def test_t4_ca73_unchanged_file_is_not_read_again(tmp_path):
    """CA-73 / RN-08 / T4: with the same modification time, get_config() returns the config already loaded."""
    path = write_settings(tmp_path, full_text_settings())

    first = _get(path)
    second = _get(path)

    assert second is first


def test_t4_ca73_get_config_defaults_to_env_in_application_home(clean_environment):
    """CA-73 / RN-08 / T4: get_config() without a path reads `.env` in the application home and follows its changes."""
    path = write_settings(clean_environment, _without_key())
    assert settings_named(_get().settings_to_fix) == {"LLM_API_KEY"}

    write_settings(clean_environment, full_text_settings())
    bump_mtime(path)

    assert _get().settings_to_fix == ()


def test_t4_ca73_get_config_follows_a_different_path(tmp_path):
    """RN-08 / T4: get_config() with another file path returns that file's configuration."""
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()
    first = write_settings(first_dir, full_text_settings(model="fake-text-model-1"))
    second = write_settings(second_dir, full_text_settings(model="fake-text-model-2"))

    assert _get(first).llm_model == "fake-text-model-1"
    assert _get(second).llm_model == "fake-text-model-2"


# --- Template (RN-27) ---


def _example_lines():
    path = REPOSITORY_ROOT / ".env.example"
    return path.read_text(encoding="utf-8").splitlines()


@pytest.mark.parametrize("setting", SETTING_NAMES)
def test_t4_rn27_env_example_has_a_comment_for_each_setting(setting):
    """RN-27 / T4: `.env.example` has each setting once, right below a comment line."""
    lines = _example_lines()
    positions = [i for i, line in enumerate(lines) if line.strip().startswith(f"{setting}=")]

    assert len(positions) == 1
    assert positions[0] > 0
    assert lines[positions[0] - 1].strip().startswith("#")


def test_t4_rn27_env_example_has_no_key_and_no_debug_flag():
    """RN-06 / RN-27 / T4: the template carries no key value and no CARDFACTORY_DEBUG setting."""
    lines = [line.strip() for line in _example_lines() if line.strip() and not line.strip().startswith("#")]

    assert all(not line.startswith("CARDFACTORY_DEBUG") for line in lines)
    for line in lines:
        name, _, value = line.partition("=")
        if name.strip() in {"LLM_API_KEY", "IMAGE_API_KEY"}:
            assert value.strip() == ""


def test_t4_rn27_env_example_loads_with_default_port(tmp_path):
    """RN-27 / RN-47 / T4: the template loads without error, with port 47821 and the text settings to fill in."""
    from core.config import load_config

    config = load_config(REPOSITORY_ROOT / ".env.example")

    assert config.app_port == 47821
    assert {"LLM_PROVIDER", "LLM_API_KEY", "LLM_MODEL"} <= settings_named(config.settings_to_fix)
    assert "APP_PORT" not in settings_named(config.settings_to_fix)


def test_t4_rn47_app_port_is_the_current_file_value(tmp_path):
    """RN-47 / RN-08 / T4: the loader returns the port written in the file now; keeping the startup port is not its job."""
    path = write_settings(tmp_path, full_text_settings() | {"APP_PORT": "47821"})
    assert _get(path).app_port == 47821

    write_settings(tmp_path, full_text_settings() | {"APP_PORT": "47900"})
    bump_mtime(path)

    assert _get(path).app_port == 47900


def test_t4_rn08_env_example_does_not_claim_changes_need_a_restart():
    """RN-08 / RN-27 / T4: the template header does not say every change needs a restart."""
    lines = _example_lines()
    first_setting = next(i for i, line in enumerate(lines) if line.strip() and not line.strip().startswith("#"))
    header = " ".join(lines[:first_setting]).lower()

    assert "restart" not in header
    assert "after the application is restarted" not in " ".join(lines).lower()


def test_t4_rn47_env_example_says_port_takes_effect_at_next_start():
    """RN-47 / RN-08 / RN-27 / T4: the comment above APP_PORT says a change takes effect at the next start."""
    lines = _example_lines()
    position = next(i for i, line in enumerate(lines) if line.strip().startswith("APP_PORT="))
    comment = []
    for line in reversed(lines[:position]):
        if not line.strip().startswith("#"):
            break
        comment.append(line.lower())

    assert "next start" in " ".join(comment)
