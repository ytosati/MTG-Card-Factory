"""Tests for the repository content check (see spec RN-02, CA-23).

Contract of release/check_repo_content.py (standard library only):

- Run as `python release/check_repo_content.py [ROOT]`. ROOT defaults to the
  repository root (the parent of the script's folder) whatever the current
  directory is.
- File list: when ROOT contains a `.git` entry (folder or file), the files are
  the output of `git ls-files --cached --others --exclude-standard` run in ROOT,
  so tracked files and files about to be added are checked and ignored files
  (data/, runtime/, .env) are not; listed files missing from disk are skipped.
  Otherwise every file under ROOT is checked, recursively.
- Paths are compared relative to ROOT, in POSIX form. Paths under an entry of
  the module-level tuple `EXCLUDED_PATHS` are skipped. That list names only the
  check's own fixtures, `release/tests/fixtures`, and matches whole path
  segments (`release/tests/fixtures2/...` is not excluded).
- Flagged, with case-insensitive matching on the file name:
  - Scryfall bulk data names: `oracle-cards`, `default-cards`, `all-cards`,
    `unique-artwork` or `rulings`, alone or followed by `-` or `_` and more
    text, with a `.json` extension (for example `oracle-cards-20260101.json`);
  - Comprehensive Rules names: starting with `MagicCompRules`, any extension;
  - images: `.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`, anywhere (no image is
    allowed in the repository);
  - card databases: `.sqlite3`, `.sqlite`, `.db`;
  - any file larger than `MAX_FILE_BYTES` (module-level, 1 MiB = 1048576
    bytes); a file of exactly that size passes.
- Content is never parsed: a flagged name is flagged even when empty or not
  valid JSON.
- Exit codes: 0 when nothing is flagged, 1 when something is flagged (each
  flagged path, relative to ROOT in POSIX form, is printed on its own line with
  a reason), 2 when ROOT does not exist or is not a folder.
"""

import pytest

from repo_check_helpers import (
    FAKE_BULK_DIR,
    REPO_ROOT,
    git,
    load_check_module,
    output_of,
    require_git,
    run_check,
    write_files,
)

ONE_MIB = 1024 * 1024
HARMLESS_FILES = {
    "README.md": "# Fictional project\n",
    "src/app.py": "print('hello')\n",
    "frontend/package.json": '{"name": "fictional"}\n',
    "release/versions.json": '{"python": "3.12.0"}\n',
    "notes/oracle-cards-notes.md": "Notes about a fictional bulk format.\n",
    "src/rulings.ts": "export const rulings = [];\n",
    "frontend/public/favicon.svg": "<svg xmlns='http://www.w3.org/2000/svg'/>\n",
    "empty.txt": "",
}


def assert_flagged(result, relative_path):
    assert result.returncode == 1, output_of(result)
    assert relative_path in output_of(result), output_of(result)


# --- Done when: the repository passes and the fake bulk fixture fails ---------


def test_ca23_repository_passes_check_with_default_root():
    """CA-23: the repository itself contains no card data, rules text or images."""
    result = run_check()
    assert result.returncode == 0, output_of(result)


def test_ca23_repository_passes_check_with_explicit_root_from_other_cwd(tmp_path):
    """CA-23: an explicit root works whatever the current directory is."""
    result = run_check(REPO_ROOT, cwd=tmp_path)
    assert result.returncode == 0, output_of(result)


def test_ca23_default_root_does_not_depend_on_current_directory(tmp_path):
    """CA-23: without ROOT, the script checks the repository, not the current folder."""
    write_files(tmp_path, {"oracle-cards.json": "[]"})
    result = run_check(cwd=tmp_path)
    assert result.returncode == 0, output_of(result)


def test_rn02_fake_bulk_fixture_folder_fails_check():
    """RN-02: the committed fake bulk card fixture is flagged when checked directly."""
    assert FAKE_BULK_DIR.is_dir()
    result = run_check(FAKE_BULK_DIR)
    assert_flagged(result, "oracle-cards-20260101000000.json")


# --- Exit codes and edge cases -------------------------------------------------


def test_ca23_empty_folder_passes(plain_root):
    """CA-23: an empty folder has nothing to flag."""
    result = run_check(plain_root)
    assert result.returncode == 0, output_of(result)


def test_ca23_harmless_files_pass(plain_root):
    """CA-23: code, config JSON, look-alike names and SVG icons are not flagged."""
    write_files(plain_root, HARMLESS_FILES)
    result = run_check(plain_root)
    assert result.returncode == 0, output_of(result)


def test_rn02_missing_root_is_a_usage_error(tmp_path):
    """RN-02: a root that does not exist is an error, never a silent pass."""
    result = run_check(tmp_path / "does-not-exist")
    assert result.returncode == 2, output_of(result)


def test_rn02_root_that_is_a_file_is_a_usage_error(tmp_path):
    """RN-02: a root that is a file is an error, never a silent pass."""
    file_root = tmp_path / "file.txt"
    file_root.write_text("x", encoding="utf-8")
    result = run_check(file_root)
    assert result.returncode == 2, output_of(result)


# --- Scryfall bulk data names --------------------------------------------------


@pytest.mark.parametrize(
    "relative_path",
    [
        "oracle-cards.json",
        "data-copy/oracle-cards-20260101000000.json",
        "default-cards-20260101000000.json",
        "deep/nested/all-cards-20260101000000.json",
        "unique-artwork-20260101000000.json",
        "rulings-20260101000000.json",
        "Oracle-Cards-20260101.JSON",
        "oracle-cards_backup.json",
        "folder with spaces/default-cards-ção.json",
    ],
)
def test_rn02_scryfall_bulk_file_names_are_flagged(plain_root, relative_path):
    """RN-02: Scryfall bulk data file names are flagged wherever they are."""
    write_files(plain_root, {**HARMLESS_FILES, relative_path: '[{"name": "Fictional Card"}]'})
    result = run_check(plain_root)
    assert_flagged(result, relative_path)


@pytest.mark.parametrize("content", [b"", b"{not json at all", "ção \U0001f0cf".encode("utf-8")])
def test_rn02_bulk_name_is_flagged_without_parsing_content(plain_root, content):
    """RN-02: an empty or malformed file with a bulk data name is still flagged."""
    write_files(plain_root, {"oracle-cards.json": content})
    result = run_check(plain_root)
    assert_flagged(result, "oracle-cards.json")


# --- Comprehensive Rules names -------------------------------------------------


@pytest.mark.parametrize(
    "relative_path",
    [
        "MagicCompRules.txt",
        "MagicCompRules 20260101.txt",
        "docs/magiccomprules-20260101.TXT",
        "rules/MagicCompRules_20260101.pdf",
    ],
)
def test_rn02_comprehensive_rules_file_names_are_flagged(plain_root, relative_path):
    """RN-02: Comprehensive Rules file names are flagged, whatever the extension or case."""
    write_files(plain_root, {**HARMLESS_FILES, relative_path: "100.1. Fictional rule text.\n"})
    result = run_check(plain_root)
    assert_flagged(result, relative_path)


# --- Images and databases ------------------------------------------------------


@pytest.mark.parametrize(
    "relative_path",
    [
        "art.png",
        "frontend/public/frame.jpg",
        "images/base/fictional-front.jpeg",
        "docs/screenshot.webp",
        "spinner.gif",
        "UPPER/CARD.PNG",
        "Ünïcödé card.Png",
    ],
)
def test_rn02_card_and_frame_image_types_are_flagged(plain_root, relative_path):
    """RN-02: image files are flagged anywhere in the repository."""
    write_files(plain_root, {**HARMLESS_FILES, relative_path: b"\x89PNG fictional bytes"})
    result = run_check(plain_root)
    assert_flagged(result, relative_path)


@pytest.mark.parametrize("relative_path", ["cardfactory.sqlite3", "backup/cards.sqlite", "cards.db"])
def test_rn02_card_database_files_are_flagged(plain_root, relative_path):
    """RN-02: database files, which hold card data, are flagged."""
    write_files(plain_root, {relative_path: b"SQLite format 3\x00"})
    result = run_check(plain_root)
    assert_flagged(result, relative_path)


# --- Size limit ------------------------------------------------------------------


def test_rn02_size_limit_is_one_mebibyte():
    """RN-02: the size limit for any file is 1 MiB."""
    assert load_check_module().MAX_FILE_BYTES == ONE_MIB


def test_rn02_file_over_size_limit_is_flagged(plain_root):
    """RN-02: an oversized file is flagged even with a harmless name."""
    write_files(plain_root, {"notes/large-export.txt": b"a" * (ONE_MIB + 1)})
    result = run_check(plain_root)
    assert_flagged(result, "notes/large-export.txt")


def test_rn02_file_at_size_limit_passes(plain_root):
    """RN-02: a file of exactly the limit is accepted."""
    write_files(plain_root, {"notes/at-limit.txt": b"a" * ONE_MIB})
    result = run_check(plain_root)
    assert result.returncode == 0, output_of(result)


# --- Exclusion list --------------------------------------------------------------


def test_rn02_exclusion_list_names_only_the_check_fixtures():
    """RN-02: the explicit exclusion list covers the check's own fixtures and nothing else."""
    excluded = tuple(load_check_module().EXCLUDED_PATHS)
    assert excluded, "EXCLUDED_PATHS must not be empty"
    for entry in excluded:
        assert entry.rstrip("/") == "release/tests/fixtures" or entry.startswith(
            "release/tests/fixtures/"
        ), entry


def test_rn02_fixtures_under_excluded_path_are_skipped(plain_root):
    """RN-02: files under release/tests/fixtures are not flagged."""
    write_files(
        plain_root,
        {
            "release/tests/fixtures/fake_bulk_cards/oracle-cards-20260101000000.json": "[]",
            "release/tests/fixtures/images/fictional.png": b"\x89PNG",
        },
    )
    result = run_check(plain_root)
    assert result.returncode == 0, output_of(result)


@pytest.mark.parametrize(
    "relative_path",
    [
        "release/tests/fixtures2/oracle-cards.json",
        "release/tests/fixtures-extra/oracle-cards.json",
        "other/release/tests/fixtures/oracle-cards.json",
        "release/tests/oracle-cards.json",
    ],
)
def test_rn02_exclusion_matches_whole_path_from_root(plain_root, relative_path):
    """RN-02: the exclusion is anchored at the root and matches whole path segments."""
    write_files(plain_root, {relative_path: "[]"})
    result = run_check(plain_root)
    assert_flagged(result, relative_path)


# --- Git mode: tracked and not-ignored files only --------------------------------


@pytest.fixture
def git_root(tmp_path):
    require_git()
    root = tmp_path / "fictional-repo"
    root.mkdir()
    result = git(root, "init", "-q")
    assert result.returncode == 0, result.stderr
    write_files(root, {".gitignore": "data/\nruntime/\n", "README.md": "# Fictional\n"})
    return root


def test_ca23_git_mode_skips_ignored_runtime_files(git_root):
    """CA-23: card data in ignored runtime folders is not part of the repository."""
    write_files(
        git_root,
        {
            "data/downloads/oracle-cards-20260101000000.json": "[]",
            "data/images/cards/fictional.png": b"\x89PNG",
            "runtime/MagicCompRules 20260101.txt": "Fictional.\n",
        },
    )
    assert git(git_root, "add", "-A").returncode == 0
    result = run_check(git_root)
    assert result.returncode == 0, output_of(result)


def test_rn02_git_mode_flags_tracked_bulk_file(git_root):
    """RN-02: a tracked bulk data file is flagged."""
    write_files(git_root, {"exports/default-cards-20260101000000.json": "[]"})
    assert git(git_root, "add", "-A").returncode == 0
    result = run_check(git_root)
    assert_flagged(result, "exports/default-cards-20260101000000.json")


def test_rn02_git_mode_flags_untracked_file_that_is_not_ignored(git_root):
    """RN-02: a file about to be added (untracked, not ignored) is flagged too."""
    write_files(git_root, {"art/fictional-frame.webp": b"RIFF"})
    result = run_check(git_root)
    assert_flagged(result, "art/fictional-frame.webp")


def test_rn02_git_mode_skips_tracked_file_deleted_from_disk(git_root):
    """RN-02: a tracked file missing from disk does not crash the check."""
    write_files(git_root, {"notes/removed.txt": "fictional\n"})
    assert git(git_root, "add", "-A").returncode == 0
    (git_root / "notes" / "removed.txt").unlink()
    result = run_check(git_root)
    assert result.returncode == 0, output_of(result)
