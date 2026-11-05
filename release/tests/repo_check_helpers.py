"""Test helpers for the repository content check: paths, a script runner and file builders."""

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECK_SCRIPT = REPO_ROOT / "release" / "check_repo_content.py"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
FAKE_BULK_DIR = FIXTURES_DIR / "fake_bulk_cards"


def run_check(*args, cwd=REPO_ROOT):
    """Run the check script as a separate process and return the completed process."""
    if not CHECK_SCRIPT.is_file():
        pytest.fail(f"Missing check script: {CHECK_SCRIPT.relative_to(REPO_ROOT).as_posix()}")
    return subprocess.run(
        [sys.executable, str(CHECK_SCRIPT), *[str(arg) for arg in args]],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )


def output_of(result):
    return result.stdout + result.stderr


def write_files(root, files):
    """Create files under root from a {relative posix path: bytes or str} mapping."""
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
    return root


def require_git():
    if shutil.which("git") is None:
        pytest.skip("git is not available")


def git(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )


def load_check_module():
    """Import the check script as a module without running its command line entry point."""
    if not CHECK_SCRIPT.is_file():
        pytest.fail(f"Missing check script: {CHECK_SCRIPT.relative_to(REPO_ROOT).as_posix()}")
    spec = importlib.util.spec_from_file_location("check_repo_content_under_test", CHECK_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
