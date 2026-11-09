"""Windows release zip build: frontend, embeddable Python, dependencies, layout, smoke test.

Details: specs/plan.md, section 9.5 (spec RN-02, RN-27). Usage: python release/build_release.py
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent
VERSIONS_FILE = Path(__file__).resolve().parent / "versions.json"
BUILD_DIR = Path(__file__).resolve().parent / "build"

PTH_NAME = "python312._pth"
START_FILE = "Start Card Factory.cmd"

# Explicit include list (plan section 9.5): {tracked prefix: archive prefix}.
INCLUDED_FOLDERS = {"backend/": "app/backend/", "launcher/": "launcher/"}
INCLUDED_FILES = {
    "README.md": "README.md",
    "VERSION": "VERSION",
    ".env.example": ".env",
    f"launcher/{START_FILE}": START_FILE,
}
# Test configuration and development-only files inside the included folders.
EXCLUDED_NAMES = {"conftest.py", "pytest.ini", "requirements-dev.txt"}

SMOKE_TEST_CODE = (
    "import sqlite3, django, rest_framework, waitress\n"
    "connection = sqlite3.connect(':memory:')\n"
    "connection.execute('CREATE VIRTUAL TABLE smoke USING fts5(body)')\n"
    "connection.execute(\"INSERT INTO smoke VALUES ('fictional card text')\")\n"
    "assert connection.execute(\"SELECT count(*) FROM smoke WHERE smoke MATCH 'card'\").fetchone()[0] == 1\n"
    "print('django', django.get_version(), '| sqlite', sqlite3.sqlite_version, '| FTS5 ok')\n"
)


class BuildError(Exception):
    """A build step failed; the message says which one."""


def python_pth_text():
    """Content of the embeddable Python path file: standard library, site-packages, import site."""
    return "python312.zip\n.\nLib\\site-packages\nimport site\n"


def _is_left_out(relative_path):
    parts = PurePosixPath(relative_path).parts
    name = parts[-1]
    return (
        "tests" in parts
        or "__pycache__" in parts
        or name in EXCLUDED_NAMES
        or name.endswith((".pyc", ".pyo"))
        or (name.startswith("test_") and name.endswith(".py"))
        or name == ".env"
        or (name.startswith(".env.") and relative_path != ".env.example")
    )


def _files_under(folder):
    folder = Path(folder)
    return sorted(path for path in folder.rglob("*") if path.is_file())


def assemble_layout(tracked_files, root, python_dir, frontend_dist):
    """{archive posix path: source file} from tracked files, the prepared Python and the build."""
    root = Path(root)
    layout = {}
    for relative_path in tracked_files:
        relative_path = PurePosixPath(relative_path).as_posix()
        source = root / relative_path
        if _is_left_out(relative_path) and relative_path not in INCLUDED_FILES:
            continue
        if not source.is_file():
            continue
        if relative_path in INCLUDED_FILES:
            layout[INCLUDED_FILES[relative_path]] = source
            continue
        for prefix, archive_prefix in INCLUDED_FOLDERS.items():
            if relative_path.startswith(prefix):
                layout[archive_prefix + relative_path[len(prefix):]] = source
                break
    layout.setdefault("VERSION", root / "VERSION")
    for source in _files_under(python_dir):
        layout["python/" + source.relative_to(python_dir).as_posix()] = source
    for source in _files_under(frontend_dist):
        layout["app/frontend/" + source.relative_to(frontend_dist).as_posix()] = source
    return layout


def write_zip(layout, destination, version):
    """Write the zip from the layout; the VERSION entry holds `version`."""
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for archive_path in sorted(layout):
            if archive_path == "VERSION":
                archive.writestr("VERSION", f"{version}\n")
            else:
                archive.write(layout[archive_path], archive_path)


def _run(command, cwd, step):
    print(f"> {step}", flush=True)
    result = subprocess.run(command, cwd=cwd)
    if result.returncode != 0:
        raise BuildError(f"{step} failed (exit code {result.returncode}).")


def tracked_files(root):
    """Files in the git index, as POSIX paths relative to root."""
    result = subprocess.run(["git", "ls-files", "-z", "--cached"], cwd=root, capture_output=True, check=True)
    return sorted({name for name in result.stdout.decode("utf-8").split("\0") if name})


def dirty_included_paths(root):
    """`git status --porcelain` lines for uncommitted changes in the paths the zip is built from."""
    paths = ["backend", "launcher", "frontend", "README.md", "VERSION", ".env.example"]
    result = subprocess.run(
        ["git", "status", "--porcelain", "--", *paths], cwd=root, capture_output=True, check=True
    )
    return [line for line in result.stdout.decode("utf-8").splitlines() if line.strip()]


def require_clean_tree(root):
    """Stop the build when the included paths differ from the commit the zip must match."""
    dirty = dirty_included_paths(root)
    if dirty:
        listing = "\n".join(f"  {line}" for line in dirty)
        raise BuildError(
            "The working tree has uncommitted changes in paths the zip is built from; "
            f"commit or stash them first:\n{listing}"
        )


def build_frontend(root):
    npm = shutil.which("npm")
    if npm is None:
        raise BuildError("npm was not found: building the release requires Node (plan section 13).")
    frontend = root / "frontend"
    _run([npm, "ci"], frontend, "npm ci")
    _run([npm, "run", "build"], frontend, "npm run build")
    dist = frontend / "dist"
    if not (dist / "index.html").is_file():
        raise BuildError("The frontend build produced no dist/index.html.")
    return dist


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def download_python(pin, downloads_dir):
    """The pinned embeddable package, downloaded once and checked against its SHA-256."""
    downloads_dir.mkdir(parents=True, exist_ok=True)
    target = downloads_dir / PurePosixPath(pin["url"]).name
    if target.is_file() and _sha256(target) == pin["sha256"]:
        return target
    print(f"> download {pin['url']}", flush=True)
    partial = target.with_suffix(".part")
    try:
        with urllib.request.urlopen(pin["url"], timeout=60) as response, open(partial, "wb") as handle:
            shutil.copyfileobj(response, handle)
        actual = _sha256(partial)
        if actual != pin["sha256"]:
            raise BuildError(f"SHA-256 mismatch for {pin['url']}: expected {pin['sha256']}, got {actual}.")
        partial.replace(target)
    finally:
        partial.unlink(missing_ok=True)
    return target


def prepare_python(package, python_dir, requirements):
    """Extract the embeddable package, write the path file and install the pinned requirements."""
    if python_dir.exists():
        shutil.rmtree(python_dir)
    python_dir.mkdir(parents=True)
    with zipfile.ZipFile(package) as archive:
        archive.extractall(python_dir)
    (python_dir / PTH_NAME).write_text(python_pth_text(), encoding="utf-8", newline="\r\n")
    site_packages = python_dir / "Lib" / "site-packages"
    site_packages.mkdir(parents=True)
    _run(
        [
            sys.executable, "-m", "pip", "install",
            # The host's pip configuration must not redirect the index (plan section 9.5).
            "--isolated", "--index-url", "https://pypi.org/simple",
            "--target", str(site_packages),
            "--only-binary=:all:",
            "--platform", "win_amd64",
            "--python-version", "3.12",
            "--implementation", "cp",
            "--no-input", "--disable-pip-version-check",
            "-r", str(requirements),
        ],
        python_dir,
        "pip install --target",
    )


def smoke_test(zip_path):
    """Run the zip's own python.exe: import the dependencies and create an FTS5 table."""
    with tempfile.TemporaryDirectory(prefix="card-factory-smoke-") as folder:
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(folder)
        python = Path(folder) / "python" / "python.exe"
        _run([str(python), "-c", SMOKE_TEST_CODE], folder, "smoke test with the zip's python.exe")


def main():
    if os.name != "nt":
        print("The release build runs on Windows: the smoke test needs the zip's python.exe.", file=sys.stderr)
        return 2
    try:
        require_clean_tree(ROOT)
        _run([sys.executable, str(ROOT / "release" / "check_repo_content.py"), str(ROOT)], ROOT,
             "repository content check")
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        pin = json.loads(VERSIONS_FILE.read_text(encoding="utf-8"))["python"]
        files = tracked_files(ROOT)
        dist = build_frontend(ROOT)
        package = download_python(pin, BUILD_DIR / "downloads")
        python_dir = BUILD_DIR / "staging" / "python"
        prepare_python(package, python_dir, ROOT / "backend" / "requirements.txt")
        destination = BUILD_DIR / f"card-factory-{version}-windows.zip"
        destination.unlink(missing_ok=True)
        print(f"> write {destination}", flush=True)
        write_zip(assemble_layout(files, ROOT, python_dir, dist), destination, version)
        smoke_test(destination)
    except (BuildError, OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Release build failed: {error}", file=sys.stderr)
        return 1
    print(f"Release zip ready: {destination}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
