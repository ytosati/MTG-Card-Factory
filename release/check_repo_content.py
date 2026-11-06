"""Repository content check: fails when card data, rules text, images or databases are present.

Details: specs/spec.md (RN-02, CA-23). Usage: python release/check_repo_content.py [ROOT]
"""

import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

MAX_FILE_BYTES = 1048576
EXCLUDED_PATHS = ("release/tests/fixtures",)

BULK_DATA_NAME = re.compile(
    r"^(oracle-cards|default-cards|all-cards|unique-artwork|rulings)([-_].*)?\.json$",
    re.IGNORECASE,
)
RULES_TEXT_NAME = re.compile(r"^magiccomprules", re.IGNORECASE)
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".gif")
DATABASE_SUFFIXES = (".sqlite3", ".sqlite", ".db")

EXIT_PASSED = 0
EXIT_FLAGGED = 1
EXIT_USAGE_ERROR = 2

GITLINK_MODE = "160000"


def default_root():
    return Path(__file__).resolve().parent.parent


def is_excluded(relative_path):
    """Whether a POSIX path relative to the root lies under an entry of EXCLUDED_PATHS."""
    parts = PurePosixPath(relative_path).parts
    for entry in EXCLUDED_PATHS:
        excluded_parts = PurePosixPath(entry).parts
        if parts[: len(excluded_parts)] == excluded_parts:
            return True
    return False


def git_listed_files(root):
    """Tracked files and untracked files that are not ignored, as POSIX paths relative to root."""
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        capture_output=True,
        check=True,
    )
    names = result.stdout.decode("utf-8", errors="surrogateescape").split("\0")
    return sorted({name for name in names if name})


def git_index_sizes(root):
    """Size in bytes of the index blob of each tracked or staged file, keyed by POSIX path.

    Reads object metadata only (git cat-file --batch-check), never file contents.
    Submodule entries have no blob in this repository and are left out.
    """
    listing = subprocess.run(
        ["git", "ls-files", "-z", "--stage"],
        cwd=root,
        capture_output=True,
        check=True,
    )
    blob_ids = {}
    for entry in listing.stdout.decode("utf-8", errors="surrogateescape").split("\0"):
        if not entry:
            continue
        metadata, relative_path = entry.split("\t", 1)
        mode, blob_id, _stage = metadata.split(" ")
        if mode == GITLINK_MODE:
            continue
        blob_ids.setdefault(relative_path, set()).add(blob_id)
    unique_ids = sorted({blob_id for ids in blob_ids.values() for blob_id in ids})
    if not unique_ids:
        return {}
    batch = subprocess.run(
        ["git", "cat-file", "--batch-check=%(objectname) %(objectsize)"],
        cwd=root,
        input="".join(blob_id + "\n" for blob_id in unique_ids).encode("ascii"),
        capture_output=True,
        check=True,
    )
    blob_sizes = {}
    for line in batch.stdout.decode("ascii").splitlines():
        blob_id, size = line.split(" ")
        blob_sizes[blob_id] = int(size)
    # A path in a merge conflict has one blob per stage: the largest one counts.
    return {
        relative_path: max(blob_sizes[blob_id] for blob_id in ids)
        for relative_path, ids in blob_ids.items()
    }


def walked_files(root):
    """Every file under root, recursively, as POSIX paths relative to root."""
    found = []
    for folder, subfolders, files in os.walk(root):
        relative_folder = Path(folder).relative_to(root).as_posix()
        prefix = "" if relative_folder == "." else relative_folder + "/"
        subfolders[:] = [name for name in subfolders if not is_excluded(prefix + name)]
        found.extend(prefix + name for name in files)
    return sorted(found)


def reason_for(relative_path, size):
    """The reason a file is flagged, or None. Only the name and size are used, never the content.

    A size of None (a listed path with neither a blob nor a file on disk) skips only the size rule.
    """
    name = PurePosixPath(relative_path).name
    lowered = name.lower()
    if BULK_DATA_NAME.match(name):
        return "Scryfall bulk data file name"
    if RULES_TEXT_NAME.match(name):
        return "Comprehensive Rules file name"
    if lowered.endswith(IMAGE_SUFFIXES):
        return "image file"
    if lowered.endswith(DATABASE_SUFFIXES):
        return "database file"
    if size is not None and size > MAX_FILE_BYTES:
        return f"larger than {MAX_FILE_BYTES} bytes ({size} bytes)"
    return None


def flagged_files(root, relative_paths, index_sizes=None):
    """Pairs of (path, reason) for every listed file that breaks a rule.

    Name rules apply to every listed path, on disk or not. The size comes from index_sizes
    when the path is there (git mode), otherwise from the disk.
    """
    index_sizes = index_sizes or {}
    flagged = []
    for relative_path in relative_paths:
        if is_excluded(relative_path):
            continue
        size = index_sizes.get(relative_path)
        if size is None:
            path = root / relative_path
            size = path.stat().st_size if path.is_file() else None
        reason = reason_for(relative_path, size)
        if reason:
            flagged.append((relative_path, reason))
    return flagged


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    root = Path(argv[0]) if argv else default_root()
    if not root.is_dir():
        print(f"Root is not a folder: {root}", file=sys.stderr)
        return EXIT_USAGE_ERROR
    root = root.resolve()

    index_sizes = None
    if (root / ".git").exists():
        try:
            relative_paths = git_listed_files(root)
            index_sizes = git_index_sizes(root)
        except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
            print(f"Could not list the repository files with git: {error}", file=sys.stderr)
            return EXIT_USAGE_ERROR
    else:
        relative_paths = walked_files(root)

    flagged = flagged_files(root, relative_paths, index_sizes)
    for relative_path, reason in flagged:
        print(f"{relative_path}: {reason}")
    if flagged:
        print(f"{len(flagged)} file(s) must not be in the repository (see spec RN-02).")
        return EXIT_FLAGGED
    print(f"Checked {len(relative_paths)} file(s): nothing to flag.")
    return EXIT_PASSED


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
