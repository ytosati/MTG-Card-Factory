"""Tests that .gitignore keeps runtime folders, the secret file and the built frontend out (see spec RN-02, CA-23)."""

import pytest

from repo_check_helpers import FAKE_BULK_DIR, REPO_ROOT, git, require_git


def is_ignored(relative_path):
    """Whether .gitignore ignores the path, whether or not it exists or is tracked."""
    result = git(REPO_ROOT, "check-ignore", "-q", "--no-index", relative_path)
    assert result.returncode in (0, 1), result.stderr
    return result.returncode == 0


@pytest.fixture(autouse=True)
def _git_available():
    require_git()


@pytest.mark.parametrize(
    "relative_path",
    [
        "data/cardfactory.sqlite3",
        "data/downloads/oracle-cards-20260101000000.json",
        "data/images/cards/fictional-id/fictional-image.png",
        "data/secret_key",
        "runtime/prepared.json",
        "runtime/python/python.exe",
        ".env",
        "frontend/dist/index.html",
        "frontend/dist/assets/fictional.js",
    ],
)
def test_rn02_runtime_secret_and_build_paths_are_ignored(relative_path):
    """RN-02, CA-23: data/, runtime/, .env and the built frontend never enter the repository."""
    assert is_ignored(relative_path), f"{relative_path} is not ignored by .gitignore"


@pytest.mark.parametrize(
    "relative_path",
    [
        ".env.example",
        "release/check_repo_content.py",
        "release/tests/test_repo_content_check.py",
        "frontend/src/main.tsx",
        "backend/core/paths.py",
    ],
)
def test_ca23_source_files_are_not_ignored(relative_path):
    """CA-23: the ignore rules do not hide the sources, the settings template or the check."""
    assert not is_ignored(relative_path), f"{relative_path} is ignored by .gitignore"


def test_rn02_fake_bulk_fixture_is_not_ignored():
    """RN-02: the fake bulk card fixture is committed, so the check needs its explicit exclusion."""
    for path in FAKE_BULK_DIR.iterdir():
        relative = path.relative_to(REPO_ROOT).as_posix()
        assert not is_ignored(relative), f"{relative} is ignored by .gitignore"
