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


def set_mtime_ns(path, mtime_ns):
    """Set the modification time to an exact value, keeping the access time."""
    stat = os.stat(path)
    os.utime(path, ns=(stat.st_atime_ns, mtime_ns))


def write_env_bytes(directory, content, name=".env"):
    """Write raw bytes to `directory/name` (other encodings, stray bytes) and return the path."""
    path = directory / name
    path.write_bytes(content)
    return path


def _same_file(candidate, target):
    try:
        text = os.fspath(candidate)
    except TypeError:
        # A file descriptor or another object that is not a path.
        return False
    if isinstance(text, bytes):
        text = os.fsdecode(text)
    return os.path.normcase(os.path.abspath(text)) == os.path.normcase(os.path.abspath(target))


class OpeningDenied:
    """Makes every attempt to open one file fail with a permission error, as a Windows ACL would.

    Granting real permissions back and forth is not portable in tests, so the
    opening functions of the standard library (`open`, `io.open`, `os.open`)
    are wrapped: a call for the target path raises PermissionError while the
    denial is on; every other path, and `os.stat` of the target, work as usual.
    The file itself is never changed, so its modification time and size stay
    the same when the denial is lifted (spec CA-73).
    """

    def __init__(self, monkeypatch, path):
        import builtins
        import io

        self.path = path
        self.denied = True
        self.attempts = 0
        original_open = builtins.open
        original_io_open = io.open
        original_os_open = os.open

        def guard(file):
            if self.denied and _same_file(file, self.path):
                self.attempts += 1
                raise PermissionError(13, "Permission denied (simulated by the test)", os.fspath(self.path))

        def fake_open(file, *args, **kwargs):
            guard(file)
            return original_open(file, *args, **kwargs)

        def fake_io_open(file, *args, **kwargs):
            guard(file)
            return original_io_open(file, *args, **kwargs)

        def fake_os_open(file, *args, **kwargs):
            guard(file)
            return original_os_open(file, *args, **kwargs)

        monkeypatch.setattr(builtins, "open", fake_open)
        monkeypatch.setattr(io, "open", fake_io_open)
        monkeypatch.setattr(os, "open", fake_os_open)

    def allow(self):
        """The file can be opened again (a permission fixed without editing the file)."""
        self.denied = False

    def deny(self):
        self.denied = True


def deny_opening(monkeypatch, path):
    """Deny opening `path` until `.allow()` is called on the returned OpeningDenied."""
    return OpeningDenied(monkeypatch, path)


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
