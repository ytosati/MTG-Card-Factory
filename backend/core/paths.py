"""Application home, data folder and built frontend folder: the only place that
resolves them, and the containment check for files served from `assets/`.
Details: specs/plan.md, sections 7 and 9.5.
"""

import os
import re
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def app_home():
    """Absolute path of the folder that holds `.env` and `data/`."""
    # Read on every call, not at import: the launcher and the tests set the
    # variable, and a relative value follows the current working directory.
    value = os.environ.get("CARDFACTORY_HOME", "").strip()
    if not value:
        return REPOSITORY_ROOT
    return Path(os.path.abspath(value))


def data_dir():
    """Absolute path of the runtime data folder under the application home."""
    return app_home() / "data"


def frontend_build_dir(code_root=None):
    """Absolute path of the built frontend folder, whether or not it exists yet.

    `code_root` is the folder that holds `backend/`. Details: specs/plan.md, section 9.5.
    """
    root = Path(os.path.abspath(code_root if code_root is not None else REPOSITORY_ROOT))
    frontend = root / "frontend"
    # A clone keeps the frontend source next to its build; the source index.html
    # is Vite's entry point, never the built page.
    if (frontend / "package.json").is_file():
        return frontend / "dist"
    return frontend


def built_index(build_dir):
    """The built `index.html`, or None when no build is present."""
    index = Path(build_dir) / "index.html"
    return index if index.is_file() else None


def _exact_segment(segment):
    # Windows opens `name:stream` as an NTFS stream and drops a trailing dot or
    # space, so such a segment could serve a file under a name it does not have.
    return ":" not in segment and not segment.endswith((".", " "))


def built_asset(build_dir, relative):
    """The file under `<build_dir>/assets/` named by `relative`, or None.

    None for a missing file, a folder, or any path that leaves the assets folder.
    """
    if "\x00" in relative or not all(map(_exact_segment, re.split(r"[\\/]", relative))):
        return None
    try:
        assets_dir = (Path(build_dir) / "assets").resolve()
        candidate = (assets_dir / relative).resolve()
        # Containment is checked on resolved paths, so dot segments, backslashes,
        # absolute paths and a sibling folder with the same name prefix all fail.
        if not candidate.is_relative_to(assets_dir) or not candidate.is_file():
            return None
    except (OSError, ValueError):
        return None
    return candidate
