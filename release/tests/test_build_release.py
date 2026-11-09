"""Tests for the local release zip build (task T75; spec RN-02, RN-27, CA-23, CA-45; plan 9.5).

They need no network, no Node and no Python download. The real build (download, pip install
--target, frontend build and the smoke test with the zip's own python.exe) is checked by hand.

API of release/build_release.py exercised here:

- assemble_layout(tracked_files, root, python_dir, frontend_dist) -> dict
    tracked_files: repository-relative posix paths (as listed by git); root: repository root;
    python_dir: prepared embeddable Python folder; frontend_dist: built frontend folder.
    Returns {archive posix path: source file path}. Only the explicit include list makes it in.
- write_zip(layout, destination, version) writes the zip from the layout; the VERSION entry
    holds `version`.
- python_pth_text() -> str: the content of PTH_NAME ("python312._pth").
- release/versions.json: {"python": {"version", "url", "sha256"}} for the embeddable package.
"""

import importlib.util
import json
import re
import zipfile
from pathlib import Path

import pytest

from repo_check_helpers import REPO_ROOT, write_files

BUILD_SCRIPT = REPO_ROOT / "release" / "build_release.py"
VERSIONS_FILE = REPO_ROOT / "release" / "versions.json"

ENV_EXAMPLE_BYTES = (
    b"# Fictional configuration template.\r\n"
    b"# Provider for card text: openai, anthropic or google\r\n"
    b"LLM_PROVIDER=\r\n"
    b"LLM_API_KEY=\r\n"
    b"APP_PORT=47821\r\n"
    b"# Odd characters stay intact: \xc3\xa7\xc3\xa3o \xe2\x80\x94 {W/U} \xe2\x9c\x93\n"
)
LOCAL_ENV_BYTES = b"LLM_PROVIDER=openai\nLLM_API_KEY=sk-fake-local-0000000000000000\n"

INCLUDED_ENTRIES = {
    "README.md": "# Card Factory\n",
    "VERSION": "0.0.1\n",
    ".env.example": ENV_EXAMPLE_BYTES,
    "backend/manage.py": "print('manage')\n",
    "backend/requirements.txt": "Django==5.2\n",
    "backend/config/settings.py": "DEBUG = False\n",
    "backend/core/__init__.py": "",
    "backend/core/startup.py": "def serve():\n    pass\n",
    "launcher/start.pyw": "print('start')\n",
    "launcher/startup_checks.py": "def check():\n    pass\n",
    "launcher/Start Card Factory.cmd": "@echo off\r\n",
}

EXCLUDED_ENTRIES = {
    # Local configuration and runtime data.
    ".env": LOCAL_ENV_BYTES,
    "backend/.env": LOCAL_ENV_BYTES,
    "data/.gitkeep": "",
    "data/cardfactory.sqlite3": b"SQLite format 3\x00",
    "data/logs/app.log": "fictional log line\n",
    # Tests and test configuration.
    "conftest.py": "",
    "backend/conftest.py": "",
    "backend/tests/network_guard.py": "",
    "backend/tests/e2e/test_flow.py": "",
    "backend/core/tests/__init__.py": "",
    "backend/core/tests/test_startup.py": "",
    "backend/core/test_paths.py": "",
    "backend/catalog/conftest.py": "",
    "launcher/tests/conftest.py": "",
    "launcher/tests/test_startup_checks.py": "",
    "launcher/tests/fixtures/instance.json": "{}",
    "launcher/test_launcher_extra.py": "",
    # Bytecode caches.
    "backend/core/__pycache__/startup.cpython-312.pyc": b"\x00\x01",
    "launcher/__pycache__/startup_checks.cpython-312.pyc": b"\x00\x01",
    # Repository-only material outside the include list.
    "CLAUDE.md": "# Project notes\n",
    ".gitignore": "data/\n",
    ".gitattributes": "* text=auto\n",
    ".github/workflows/tests.yml": "name: tests\n",
    ".claude/agents/qa.md": "# qa\n",
    "docs/DECISIONS.md": "# Decisions\n",
    "specs/spec.md": "# Spec\n",
    "release/build_release.py": "print('build')\n",
    "release/check_repo_content.py": "print('check')\n",
    "release/versions.json": "{}",
    "frontend/package.json": "{}",
    "frontend/src/main.tsx": "export {};\n",
    "frontend/index.html": "<!doctype html>\n",
}

PYTHON_FILES = {
    "python.exe": b"MZ fake",
    "pythonw.exe": b"MZ fake",
    "python312.zip": b"PK fake",
    "python312._pth": "python312.zip\n.\nLib\\site-packages\nimport site\n",
    "Lib/site-packages/waitress/__init__.py": "",
}

FRONTEND_DIST_FILES = {
    "index.html": "<!doctype html><title>Card Factory</title>\n",
    "assets/index-abc123.js": "console.log('fake');\n",
    "assets/index-abc123.css": "body{}\n",
}

ALLOWED_ROOT_FILES = {"Start Card Factory.cmd", ".env", "README.md", "VERSION"}
ALLOWED_PREFIXES = ("python/", "app/backend/", "app/frontend/", "launcher/")


def load_build_module():
    """Import the build script as a module without running its command line entry point."""
    if not BUILD_SCRIPT.is_file():
        pytest.fail(f"Missing build script: {BUILD_SCRIPT.relative_to(REPO_ROOT).as_posix()}")
    spec = importlib.util.spec_from_file_location("build_release_under_test", BUILD_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def build():
    return load_build_module()


@pytest.fixture
def fake_tree(tmp_path):
    """A fictional repository, a prepared embeddable Python and a built frontend."""
    root = write_files(tmp_path / "repo", {**INCLUDED_ENTRIES, **EXCLUDED_ENTRIES})
    python_dir = write_files(tmp_path / "staging" / "python", PYTHON_FILES)
    frontend_dist = write_files(tmp_path / "staging" / "dist", FRONTEND_DIST_FILES)
    tracked = sorted([*INCLUDED_ENTRIES, *EXCLUDED_ENTRIES])
    return {"root": root, "python_dir": python_dir, "frontend_dist": frontend_dist, "tracked": tracked}


@pytest.fixture
def layout(build, fake_tree):
    return build.assemble_layout(
        fake_tree["tracked"], fake_tree["root"], fake_tree["python_dir"], fake_tree["frontend_dist"]
    )


@pytest.fixture
def built_zip(build, layout, tmp_path):
    destination = tmp_path / "out" / "card-factory-9.8.7-windows.zip"
    destination.parent.mkdir(parents=True)
    build.write_zip(layout, destination, "9.8.7")
    with zipfile.ZipFile(destination) as archive:
        yield archive


def same_file(a, b):
    return Path(a).resolve() == Path(b).resolve()


def file_names(archive):
    return [name for name in archive.namelist() if not name.endswith("/")]


def test_rn27_layout_has_the_zip_root_entries(layout):
    """RN-27 / CA-45: python/, app/, launcher/, the start file, .env, README.md and VERSION."""
    paths = set(layout)
    for root_file in ALLOWED_ROOT_FILES:
        assert root_file in paths, f"missing {root_file!r} at the zip root"
    for prefix in ("python/", "app/backend/", "app/frontend/", "launcher/"):
        assert any(path.startswith(prefix) for path in paths), f"nothing under {prefix!r}"


def test_rn27_layout_maps_sources_to_their_archive_paths(layout, fake_tree):
    """RN-27: backend goes to app/backend, the build to app/frontend, Python to python/."""
    root = fake_tree["root"]
    assert same_file(layout["app/backend/core/startup.py"], root / "backend/core/startup.py")
    assert same_file(layout["app/backend/requirements.txt"], root / "backend/requirements.txt")
    assert same_file(layout["launcher/start.pyw"], root / "launcher/start.pyw")
    assert same_file(layout["Start Card Factory.cmd"], root / "launcher/Start Card Factory.cmd")
    assert same_file(layout["README.md"], root / "README.md")
    assert same_file(layout["app/frontend/index.html"], fake_tree["frontend_dist"] / "index.html")
    assert same_file(
        layout["app/frontend/assets/index-abc123.js"], fake_tree["frontend_dist"] / "assets/index-abc123.js"
    )
    assert same_file(layout["python/python.exe"], fake_tree["python_dir"] / "python.exe")
    assert same_file(
        layout["python/Lib/site-packages/waitress/__init__.py"],
        fake_tree["python_dir"] / "Lib/site-packages/waitress/__init__.py",
    )


def test_rn27_env_in_layout_comes_from_env_example_not_local_env(layout, fake_tree):
    """RN-27: the zip's .env is taken from .env.example, never from the local .env."""
    assert same_file(layout[".env"], fake_tree["root"] / ".env.example")


def test_rn27_layout_uses_posix_relative_archive_paths(layout):
    """RN-27: archive paths are relative, use forward slashes and never climb out."""
    for path in layout:
        assert "\\" not in path, path
        assert not path.startswith("/"), path
        assert ".." not in path.split("/"), path
        assert not re.match(r"^[A-Za-z]:", path), path


@pytest.mark.parametrize("path", sorted(EXCLUDED_ENTRIES))
def test_rn27_excluded_entry_never_reaches_the_layout(layout, fake_tree, path):
    """RN-27 / RN-02: no data/, tests, conftest.py, __pycache__, local .env or repo-only files."""
    excluded_source = (fake_tree["root"] / path).resolve()
    sources = {Path(source).resolve() for source in layout.values()}
    assert excluded_source not in sources, f"{path} was included"


def test_rn27_layout_has_no_data_test_or_cache_paths(layout):
    """RN-27 / RN-02: no archive path names data/, a tests folder, a test file or a cache."""
    for path in layout:
        if path.startswith("python/"):
            continue
        parts = path.split("/")
        name = parts[-1]
        assert parts[0] != "data", path
        assert "tests" not in parts, path
        assert "__pycache__" not in parts, path
        assert not (name.startswith("test_") and name.endswith(".py")), path
        assert name != "conftest.py", path
        assert not name.endswith(".pyc"), path


def test_rn27_only_the_explicit_include_list_reaches_the_layout(layout):
    """RN-27: every archive path is one of the zip root files or under an included folder."""
    for path in layout:
        assert path in ALLOWED_ROOT_FILES or path.startswith(ALLOWED_PREFIXES), f"unexpected {path!r}"


def test_rn27_untracked_files_are_left_out(build, fake_tree):
    """RN-27: files on disk that git does not list never reach the layout (tracked files only)."""
    untracked = fake_tree["root"] / "backend" / "core" / "scratch_notes.py"
    untracked.write_text("print('untracked')\n", encoding="utf-8")
    result = build.assemble_layout(
        fake_tree["tracked"], fake_tree["root"], fake_tree["python_dir"], fake_tree["frontend_dist"]
    )
    assert "app/backend/core/scratch_notes.py" not in result
    assert untracked.resolve() not in {Path(source).resolve() for source in result.values()}


def test_rn27_zip_env_is_a_byte_copy_of_env_example(built_zip):
    """RN-27: the zip's .env equals .env.example byte for byte (CRLF and UTF-8 kept)."""
    assert built_zip.read(".env") == ENV_EXAMPLE_BYTES


def test_rn27_zip_writes_the_given_version(built_zip):
    """RN-27: the VERSION entry of the zip holds the version passed to the build."""
    assert built_zip.read("VERSION").decode("utf-8").strip() == "9.8.7"


def test_rn27_zip_has_each_entry_once_and_matches_the_layout(built_zip, layout):
    """RN-27: the zip holds exactly the layout's files, each once, with no extra file."""
    names = file_names(built_zip)
    assert len(names) == len(set(names)), "duplicate entries in the zip"
    assert set(names) == set(layout)


def test_rn27_zip_file_contents_equal_their_sources(built_zip, layout):
    """RN-27: every file other than VERSION is copied unchanged from its source."""
    for path, source in layout.items():
        if path == "VERSION":
            continue
        assert built_zip.read(path) == Path(source).read_bytes(), path


def test_rn02_zip_has_no_local_env_secret_or_data(built_zip):
    """RN-02 / RN-27: no local key, database or log ends up inside the zip."""
    for name in file_names(built_zip):
        content = built_zip.read(name)
        assert b"sk-fake-local" not in content, name
        assert not name.startswith("data/"), name
        assert not name.endswith((".sqlite3", ".sqlite", ".db")), name


def test_rn27_pth_file_name(build):
    """RN-27: the path file of the embeddable Python 3.12 is python312._pth."""
    assert build.PTH_NAME == "python312._pth"


def test_rn27_pth_lists_stdlib_site_packages_and_import_site(build):
    """RN-27: python312._pth lists python312.zip, Lib\\site-packages and an active import site."""
    lines = [line.strip() for line in build.python_pth_text().splitlines()]
    assert "python312.zip" in lines
    assert "Lib\\site-packages" in lines
    assert "import site" in lines
    assert "#import site" not in lines


def test_rn27_versions_json_pins_the_embeddable_python():
    """RN-27: release/versions.json pins the embeddable Python version, URL and SHA-256."""
    assert VERSIONS_FILE.is_file(), "missing release/versions.json"
    data = json.loads(VERSIONS_FILE.read_text(encoding="utf-8"))
    python = data["python"]
    version = python["version"]
    assert re.fullmatch(r"3\.12\.\d+", version), version
    assert python["url"] == (
        f"https://www.python.org/ftp/python/{version}/python-{version}-embed-amd64.zip"
    )
    assert re.fullmatch(r"[0-9a-f]{64}", python["sha256"]), python["sha256"]
