"""Tests for the launcher prerequisite checks (spec RN-40, CA-17; plan section 9.5, step 2).

Unwritable folders are simulated by monkeypatching, since Windows ignores `chmod` on folders.
"""

import builtins
import io
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
LAUNCHER_DIR = REPO_ROOT / "launcher"

if str(LAUNCHER_DIR) not in sys.path:
    sys.path.insert(0, str(LAUNCHER_DIR))

_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC


class MessageRecorder:
    """Stands in for the message box: records each (problem, fix) call."""

    def __init__(self):
        self.calls = []

    def __call__(self, problem, fix):
        self.calls.append((problem, fix))


def _inside(path, folder):
    """True when `path` is `folder` itself or an entry directly inside it."""
    try:
        candidate = Path(os.fspath(path)).resolve()
    except TypeError:
        return False
    target = Path(folder).resolve()
    return candidate == target or candidate.parent == target


def deny_writing(monkeypatch, folder):
    """Simulate a folder without write permission: creating or writing entries in it fails."""

    def refuse(path):
        raise PermissionError(13, "Permission denied (simulated by the test)", os.fspath(path))

    original_open = builtins.open
    original_io_open = io.open
    original_os_open = os.open
    original_mkdir = os.mkdir
    original_access = os.access

    def writes(mode):
        return any(flag in mode for flag in "wax+")

    def fake_open(file, mode="r", *args, **kwargs):
        if writes(mode) and _inside(file, folder):
            refuse(file)
        return original_open(file, mode, *args, **kwargs)

    def fake_io_open(file, mode="r", *args, **kwargs):
        if writes(mode) and _inside(file, folder):
            refuse(file)
        return original_io_open(file, mode, *args, **kwargs)

    def fake_os_open(path, flags, *args, **kwargs):
        if flags & _WRITE_FLAGS and _inside(path, folder):
            refuse(path)
        return original_os_open(path, flags, *args, **kwargs)

    def fake_mkdir(path, *args, **kwargs):
        if _inside(path, folder):
            refuse(path)
        return original_mkdir(path, *args, **kwargs)

    def fake_access(path, mode, *args, **kwargs):
        if mode & os.W_OK and _inside(path, folder):
            return False
        return original_access(path, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)
    monkeypatch.setattr(io, "open", fake_io_open)
    monkeypatch.setattr(os, "open", fake_os_open)
    monkeypatch.setattr(os, "mkdir", fake_mkdir)
    monkeypatch.setattr(os, "access", fake_access)


@pytest.fixture
def checks():
    import startup_checks

    return startup_checks


@pytest.fixture
def home(tmp_path):
    """A home that passes every check: writable, with `data/` and a `.env` file."""
    folder = tmp_path / "Card Factory"
    folder.mkdir()
    (folder / "data").mkdir()
    (folder / ".env").write_text("# Fictional configuration for the test\n", encoding="utf-8")
    return folder


def _assert_one_message(recorder, *names):
    assert len(recorder.calls) == 1, recorder.calls
    problem, fix = recorder.calls[0]
    assert isinstance(problem, str) and problem.strip()
    assert isinstance(fix, str) and fix.strip()
    assert problem.strip() != fix.strip()
    assert any(name in problem for name in names), problem
    return problem, fix


def test_rn40_a_ready_home_passes_with_no_message(checks, home):
    """RN-40: a writable home with `data/` and `.env` passes and shows no message."""
    recorder = MessageRecorder()
    assert checks.run_checks(home, recorder) is True
    assert recorder.calls == []


def test_rn40_first_start_without_data_folder_passes(checks, home):
    """RN-40: on a first start `data/` does not exist yet; a writable home is enough."""
    (home / "data").rmdir()
    recorder = MessageRecorder()
    assert checks.run_checks(home, recorder) is True
    assert recorder.calls == []


def test_rn40_ca17_read_only_home_shows_one_message(checks, home, monkeypatch):
    """RN-40 / CA-17: a home without write permission shows one message naming it and the fix."""
    deny_writing(monkeypatch, home)
    recorder = MessageRecorder()
    assert checks.run_checks(home, recorder) is False
    _assert_one_message(recorder, str(home), home.name)


def test_rn40_ca17_read_only_data_folder_shows_one_message(checks, home, monkeypatch):
    """RN-40 / CA-17: a `data/` folder without write permission shows one message naming it and the fix."""
    deny_writing(monkeypatch, home / "data")
    recorder = MessageRecorder()
    assert checks.run_checks(home, recorder) is False
    _assert_one_message(recorder, "data")


def test_rn40_ca17_missing_env_shows_one_message(checks, home):
    """RN-40 / CA-17: a missing `.env` shows one message naming it and the fix."""
    (home / ".env").unlink()
    recorder = MessageRecorder()
    assert checks.run_checks(home, recorder) is False
    _assert_one_message(recorder, ".env")


def test_rn40_ca17_env_as_folder_shows_one_message(checks, home):
    """RN-40 / CA-17: a `.env` that is a folder, not a file, shows one message naming it and the fix."""
    (home / ".env").unlink()
    (home / ".env").mkdir()
    recorder = MessageRecorder()
    assert checks.run_checks(home, recorder) is False
    _assert_one_message(recorder, ".env")


def test_rn40_checks_accept_a_home_with_odd_characters(checks, tmp_path):
    """RN-40: a home path with spaces, accents and symbols passes like any other."""
    folder = tmp_path / "Cartas & Ação (cópia) #2"
    folder.mkdir()
    (folder / ".env").write_text("", encoding="utf-8")
    recorder = MessageRecorder()
    assert checks.run_checks(folder, recorder) is True
    assert recorder.calls == []


@pytest.mark.skipif(sys.platform != "win32", reason="the message box uses the Windows API")
def test_rn40_message_box_shows_problem_and_fix_through_ctypes(checks, monkeypatch):
    """RN-40: the default message is a Windows message box through ctypes holding problem and fix."""
    import ctypes

    shown = []

    def fake_message_box(hwnd, text, caption, flags):
        shown.append((text, caption))
        return 1

    monkeypatch.setattr(ctypes.windll.user32, "MessageBoxW", fake_message_box)
    checks.message_box("Fictional problem sentence.", "Fictional fix sentence.")
    assert len(shown) == 1
    text, _caption = shown[0]
    assert "Fictional problem sentence." in text
    assert "Fictional fix sentence." in text


def test_rn40_checks_import_no_django_and_no_network():
    """RN-40 / plan 9.5 step 2: importing the checks loads no Django and no network module."""
    probe = (
        "import sys; sys.path.insert(0, sys.argv[1]); import startup_checks; "
        "bad = sorted(m for m in sys.modules if m.split('.')[0] in "
        "{'django', 'rest_framework', 'socket', 'http', 'urllib', 'ssl', 'core'}); "
        "print(','.join(bad))"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", probe, str(LAUNCHER_DIR)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""


def test_rn40_start_pyw_runs_the_checks():
    """RN-40: `launcher/start.pyw` exists and calls the checks module."""
    entry = LAUNCHER_DIR / "start.pyw"
    assert entry.is_file()
    text = entry.read_text(encoding="utf-8")
    assert "startup_checks" in text
    assert "run_checks" in text


def test_version_file_is_semantic_version():
    """T73: `VERSION` at the repository root holds MAJOR.MINOR.PATCH, with no `v` prefix."""
    version_file = REPO_ROOT / "VERSION"
    assert version_file.is_file()
    value = version_file.read_text(encoding="utf-8").strip()
    assert re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", value), value


def test_rn40_ca17_start_cmd_checks_its_files_next_to_it():
    """RN-40 / CA-17: the `.cmd` checks `python\\pythonw.exe` and `launcher\\start.pyw` relative to `%~dp0`."""
    cmd = LAUNCHER_DIR / "Start Card Factory.cmd"
    assert cmd.is_file()
    text = cmd.read_text(encoding="utf-8", errors="replace")
    lowered = text.lower()
    assert "%~dp0" in text
    assert "python\\pythonw.exe" in lowered
    assert "launcher\\start.pyw" in lowered
    assert "if not exist" in lowered
    assert "pause" in lowered
