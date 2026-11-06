"""Test helper: a fictional built frontend written in a temporary folder.

The tests never depend on the real `frontend/dist`. The app is pointed at the
fixture folder through the Django setting `FRONTEND_BUILD_DIR` (task T10, plan
section 9.5), which the serving views read on every request. Usage:

    from tests.frontend_build import built_frontend  # noqa: F401 (fixture)

    def test_something(built_frontend, client):
        response = client.get("/")
        assert response_body(response) == built_frontend.index_bytes

Every file is fictional and written by hand.
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import pytest

BUILD_DIR_SETTING = "FRONTEND_BUILD_DIR"

# Markers that identify a fixture file in a response body.
INDEX_MARKER = b"FIXTURE-INDEX-7f3a"
SECRET_MARKER = b"SECRET-OUTSIDE-BUILD-91c2"
SIBLING_MARKER = b"SECRET-SIBLING-FOLDER-5d8e"

# The built index.html, as Vite would write it: hashed asset names, a module
# script, CRLF and LF line ends, non-ASCII text and text that looks like a
# Django template, so any rendering or newline rewriting changes the bytes.
INDEX_HTML = (
    b"<!doctype html>\r\n"
    b'<html lang="en">\r\n'
    b"  <head>\n"
    b'    <meta charset="UTF-8" />\n'
    b"    <title>Card Factory fixture \xe2\x9c\x93 \xc3\xa7\xc3\xa3</title>\n"
    b'    <script type="module" crossorigin src="/assets/index-Fx7a9Q2b.js"></script>\n'
    b'    <link rel="stylesheet" crossorigin href="/assets/index-B2c4dE8f.css">\n'
    b"  </head>\n"
    b"  <body>\n"
    b'    <div id="root"></div>\n'
    b"    <!-- " + INDEX_MARKER + b' {{ not_a_template }} {% now "Y" %} -->\n'
    b"  </body>\n"
    b"</html>\n"
)

JS_BYTES = (
    b"// fictional bundle\r\n"
    b'const label = "Fixture \xe2\x9c\x93";\n'
    b"export default function mount(root) { root.textContent = label; }\n"
)
CSS_BYTES = b":root { --fixture-accent: #3a6f5c; }\r\nbody { margin: 0; }\n"
SVG_BYTES = (
    b'<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8">'
    b'<rect width="8" height="8" fill="#3a6f5c"/></svg>\n'
)
# A minimal fictional PNG: signature, then arbitrary bytes, including NUL and 0xFF.
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + bytes(range(256)) + b"\x00\xff\r\n\x00"
# A large asset: 3 MiB of varied bytes.
LARGE_JS_BYTES = b"// large fictional bundle\n" + bytes(i % 251 for i in range(3 * 1024 * 1024))

# Asset files under `assets/`: relative path -> (bytes, accepted content types).
JAVASCRIPT_TYPES = ("text/javascript", "application/javascript")
ASSETS = {
    "index-Fx7a9Q2b.js": (JS_BYTES, JAVASCRIPT_TYPES),
    "index-B2c4dE8f.css": (CSS_BYTES, ("text/css",)),
    "logo-Q1w2E3r4.svg": (SVG_BYTES, ("image/svg+xml",)),
    "frame-Z9y8X7w6.png": (PNG_BYTES, ("image/png",)),
    "empty-0a0a0a0a.css": (b"", ("text/css",)),
    "chunks/nested-M5n6B7v8.js": (JS_BYTES, JAVASCRIPT_TYPES),
    "large-L4r9e3G1.js": (LARGE_JS_BYTES, JAVASCRIPT_TYPES),
    "ícone ✓.svg": (SVG_BYTES, ("image/svg+xml",)),
}


@dataclass
class BuiltFrontend:
    """A fixture build folder and the files outside it that must never be served."""

    root: Path
    build_dir: Path
    secret_file: Path
    sibling_file: Path
    index_bytes: bytes = INDEX_HTML
    assets: dict = field(default_factory=lambda: dict(ASSETS))


def write_build(build_dir, with_index=True):
    """Write the fixture build into `build_dir` and return the folder."""
    assets_dir = build_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    if with_index:
        (build_dir / "index.html").write_bytes(INDEX_HTML)
    for relative, (content, _types) in ASSETS.items():
        path = assets_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return build_dir


def point_app_at(django_settings, build_dir):
    """Make the serving views use `build_dir` as the built frontend."""
    setattr(django_settings, BUILD_DIR_SETTING, build_dir)


def response_body(response):
    """The body bytes; a streaming body is read once and put back for the caller."""
    if getattr(response, "streaming", False):
        body = b"".join(response.streaming_content)
        response.streaming_content = [body]
        return body
    return response.content


def content_type(response):
    """The media type of a response, without parameters, in lower case."""
    return response.get("Content-Type", "").split(";")[0].strip().lower()


# Markup that makes a browser load a resource from another address (CA-38).
_EXTERNAL_RESOURCE_PATTERNS = [
    re.compile(rb"""\bsrc\s*=\s*["']?\s*(?:[a-z][a-z0-9+.-]*:)?//""", re.IGNORECASE),
    re.compile(rb"""\bsrcset\s*=\s*["']?[^"'>]*//""", re.IGNORECASE),
    re.compile(rb"""<link\b[^>]*\bhref\s*=\s*["']?\s*(?:[a-z][a-z0-9+.-]*:)?//""", re.IGNORECASE),
    re.compile(rb"""url\(\s*["']?\s*(?:[a-z][a-z0-9+.-]*:)?//""", re.IGNORECASE),
    re.compile(rb"""@import""", re.IGNORECASE),
]


def external_resource_references(body):
    """Every fragment of `body` that would load a resource from outside the application."""
    found = []
    for pattern in _EXTERNAL_RESOURCE_PATTERNS:
        found.extend(match.group(0) for match in pattern.finditer(body))
    return found


@pytest.fixture
def built_frontend(tmp_path, settings):
    """A fixture build at `<tmp>/web/dist`, with DEBUG off, and the app pointed at it.

    Next to it lie files that must never be served: `<tmp>/web/secret.txt` (the
    parent of the build folder) and `<tmp>/web/distx/assets/sibling.js` (a
    sibling whose name starts with the build folder's name).
    """
    settings.DEBUG = False
    root = tmp_path / "web"
    build_dir = write_build(root / "dist")
    secret_file = root / "secret.txt"
    secret_file.write_bytes(SECRET_MARKER + b"\n")
    sibling_file = root / "distx" / "assets" / "sibling.js"
    sibling_file.parent.mkdir(parents=True)
    sibling_file.write_bytes(SIBLING_MARKER + b"\n")
    point_app_at(settings, build_dir)
    return BuiltFrontend(root, build_dir, secret_file, sibling_file)


# --- NTFS alternate data streams -------------------------------------------------------

# A named stream as Windows writes it on a downloaded file; the path is fictional.
STREAM_ASSET = "app-Ads0Str1.js"
STREAM_NAME = "Zone.Identifier"
STREAM_MARKER = b"STREAM-TEXT-3b7e"
STREAM_TEXT = (
    b"[ZoneTransfer]\r\nZoneId=3\r\n"
    b"ReferrerUrl=C:\Users\someone\Downloads\fixture-release.zip\r\n"
    b"Note=" + STREAM_MARKER + b"\r\n"
)


def write_named_stream(build_dir):
    """Write `assets/<STREAM_ASSET>` with a named NTFS stream; return False when the file
    system has no named streams (not Windows, or not NTFS)."""
    if os.name != "nt":
        return False
    asset = build_dir / "assets" / STREAM_ASSET
    asset.write_bytes(JS_BYTES)
    try:
        with open(f"{asset}:{STREAM_NAME}", "wb") as handle:
            handle.write(STREAM_TEXT)
        with open(f"{asset}:{STREAM_NAME}", "rb") as handle:
            return handle.read() == STREAM_TEXT
    except OSError:
        return False


# --- an unreadable build folder ----------------------------------------------------------


def _path_text(value):
    if isinstance(value, int):
        return None
    try:
        return os.path.abspath(os.fsdecode(os.fspath(value)))
    except TypeError:
        return None


def deny_reads_under(monkeypatch, folder):
    """Make every stat, existence check and open of a path under `folder` raise
    PermissionError, as when the folder's access rights forbid reading it."""
    import builtins
    import io
    import pathlib

    prefix = os.path.normcase(os.path.abspath(folder))

    def denied(value):
        text = _path_text(value)
        return text is not None and os.path.normcase(text).startswith(prefix)

    def guard(original):
        def wrapper(path, *args, **kwargs):
            if denied(path):
                raise PermissionError(13, "Access is denied", str(path))
            return original(path, *args, **kwargs)

        return wrapper

    for module, name in [
        (os, "stat"),
        (os, "lstat"),
        (os, "open"),
        (os, "scandir"),
        (os, "listdir"),
        (builtins, "open"),
        (io, "open"),
    ]:
        monkeypatch.setattr(module, name, guard(getattr(module, name)))
    for name in ["stat", "lstat", "open", "read_bytes", "read_text", "exists", "is_file", "is_dir", "iterdir"]:
        monkeypatch.setattr(pathlib.Path, name, guard(getattr(pathlib.Path, name)))
