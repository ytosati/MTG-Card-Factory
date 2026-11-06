"""Test helper: temporary `.env` files and a cleared environment for core.config tests.

Values are fictional; keys only look like keys.
"""

import os

import pytest

from tests.project_environment import is_project_variable

FAKE_TEXT_KEY = "sk-fake-text-0000-TEXTKEY-not-real-1111"
FAKE_IMAGE_KEY = "sk-fake-image-2222-IMAGEKEY-not-real-3333"

DEFAULT_PORT = 47821

SETTING_NAMES = (
    "LLM_PROVIDER",
    "LLM_API_KEY",
    "LLM_MODEL",
    "IMAGE_PROVIDER",
    "IMAGE_API_KEY",
    "IMAGE_MODEL",
    "APP_PORT",
)


def full_text_settings(provider="openai", model="fake-text-model-1", key=FAKE_TEXT_KEY):
    """Text settings that need no fix."""
    return {"LLM_PROVIDER": provider, "LLM_API_KEY": key, "LLM_MODEL": model}


def env_text(settings):
    """Render a mapping as `KEY=VALUE` lines."""
    return "".join(f"{name}={value}\n" for name, value in settings.items())


def write_env(directory, content, name=".env", encoding="utf-8", newline="\n"):
    """Write `content` to `directory/name` and return the path."""
    path = directory / name
    with open(path, "w", encoding=encoding, newline=newline) as handle:
        handle.write(content)
    return path


def write_settings(directory, settings, name=".env"):
    """Write a mapping of settings to a temporary `.env` file."""
    return write_env(directory, env_text(settings), name=name)


def bump_mtime(path, seconds=10):
    """Move the modification time forward so a change is visible on any file system."""
    stat = os.stat(path)
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + seconds * 1_000_000_000))


def settings_named(entries):
    """The setting names of a list of settings to fix or notices."""
    return {entry.setting for entry in entries}


@pytest.fixture
def clean_environment(monkeypatch, tmp_path):
    """No project variable in the process environment; the home is an empty temporary folder."""
    for name in list(os.environ):
        if is_project_variable(name):
            monkeypatch.delenv(name, raising=False)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("CARDFACTORY_HOME", str(home))
    return home
