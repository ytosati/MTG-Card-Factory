"""Django serves the built frontend (task T10, spec RN-27, RN-33, CA-38, plan sections 6 and 9.5).

Contract under test:

- Every non-API path answers the built `index.html` unchanged (200, text/html).
- `/assets/<path>` answers the file from `<build>/assets/` unchanged, with the
  content type of its extension, with DEBUG off. A missing asset answers 404,
  never `index.html`; nothing outside the build folder is ever served.
- An unknown `/api/` path still answers 404 in the error envelope (T6).
- With no build present (no `index.html` in the build folder), a non-API path
  answers 503 with a short text page that names the build step
  (`npm run build`, in `frontend/`); the API keeps working.
- The build folder is the Django setting `FRONTEND_BUILD_DIR`, read on every
  request; the tests point it at a fixture folder (tests.frontend_build).

No test reads the real `frontend/dist` or touches the network.
"""

import threading
from urllib.parse import quote

import pytest

from tests.config_files import full_text_settings
from tests.configured_api import assert_error_envelope, configured_api  # noqa: F401 (fixture)
from tests.frontend_build import (
    ASSETS,
    INDEX_MARKER,
    JS_BYTES,
    SECRET_MARKER,
    SIBLING_MARKER,
    STREAM_ASSET,
    STREAM_MARKER,
    STREAM_NAME,
    built_frontend,  # noqa: F401 (fixture)
    content_type,
    deny_reads_under,
    external_resource_references,
    point_app_at,
    response_body,
    write_build,
    write_named_stream,
)

NO_BUILD_STATUS = 503
BUILD_STEP = "npm run build"

# Paths the single-page app owns; the screen switch is hash based, so a hash
# route reaches the server as its path before `#` (the client never sends it).
NON_API_PATHS = [
    "/",
    "/status",
    "/status/",
    "/library",
    "/some/deep/path",
    "/some/deep/path/",
    "/index.html",
    "/cards/123/versions/-1",
    "/0",
    "/apiary",
    "/api-docs",
    "/static/anything.js",
    "/caf%C3%A9/%E2%9C%93%20space",
    "/%F0%9F%83%8F",
    "/search?q=%3Cscript%3E&page=-5",
    "/" + "x" * 2_000,
]


def _asset_url(relative):
    return "/assets/" + quote(relative)


# --- index.html on every non-API path -------------------------------------------------


@pytest.mark.parametrize("path", NON_API_PATHS)
def test_t10_rn27_unknown_non_api_path_returns_the_built_index(built_frontend, client, path):
    """RN-27 / T10 / plan 9.5: every non-API path answers the built index.html (200, text/html)."""
    response = client.get(path)

    assert response.status_code == 200, (path, response.status_code)
    assert content_type(response) == "text/html"
    assert response_body(response) == built_frontend.index_bytes


@pytest.mark.parametrize("debug", [False, True])
def test_t10_rn27_index_is_served_with_debug_off_and_on(built_frontend, client, settings, debug):
    """RN-27 / T10: the release runs with DEBUG off; the index is served either way."""
    settings.DEBUG = debug

    response = client.get("/")

    assert response.status_code == 200
    assert response_body(response) == built_frontend.index_bytes


def test_t10_rn33_ca38_index_is_the_file_as_built(built_frontend, client):
    """RN-33 / CA-38 / T10: index.html is sent byte for byte as built, never rendered as a
    template and never rewritten, so the app adds no address of its own to the page."""
    response = client.get("/library")

    body = response_body(response)
    assert response.status_code == 200
    assert body == built_frontend.index_bytes
    assert b"{{ not_a_template }}" in body
    assert b"\r\n" in body


def test_t10_index_follows_the_build_folder_setting_on_each_request(built_frontend, client, settings, tmp_path):
    """T10: the build folder is read per request, so a rebuilt or moved folder is served."""
    other_build = write_build(tmp_path / "other" / "dist")
    (other_build / "index.html").write_bytes(b"<!doctype html><title>other fixture build</title>\n")

    first = response_body(client.get("/"))
    point_app_at(settings, other_build)
    second = response_body(client.get("/"))

    assert first == built_frontend.index_bytes
    assert second == b"<!doctype html><title>other fixture build</title>\n"


def test_t10_ca38_index_response_headers_hold_no_external_address(built_frontend, client):
    """CA-38 / T10: the served page carries no header that points the browser elsewhere."""
    response = client.get("/")

    for name, value in response.headers.items():
        assert "://" not in value, (name, value)


# --- /assets/* ----------------------------------------------------------------------


@pytest.mark.parametrize("relative", sorted(ASSETS))
def test_t10_rn27_asset_is_served_with_its_content_type(built_frontend, client, relative):
    """RN-27 / T10 / plan 9.5: /assets/<file> answers the built file with the content type of its
    extension (JavaScript, CSS, SVG, PNG), with DEBUG off."""
    content, accepted_types = built_frontend.assets[relative]

    response = client.get(_asset_url(relative))

    assert response.status_code == 200, (relative, response.status_code)
    assert content_type(response) in accepted_types, (relative, response.get("Content-Type"))


@pytest.mark.parametrize("relative", sorted(ASSETS))
def test_t10_rn33_ca38_asset_bytes_are_unchanged(built_frontend, client, relative):
    """RN-33 / CA-38 / T10: an asset (images included) is sent as built, byte for byte, from the
    local application: empty, binary, non-ASCII, nested and large files alike."""
    content, _types = built_frontend.assets[relative]

    response = client.get(_asset_url(relative))

    assert response.status_code == 200
    assert response_body(response) == content


@pytest.mark.parametrize("debug", [False, True])
def test_t10_javascript_asset_type_with_debug_off_and_on(built_frontend, client, settings, debug):
    """RN-27 / T10: the module script keeps a JavaScript content type with DEBUG off and on;
    a browser refuses a module script served with any other type."""
    settings.DEBUG = debug

    response = client.get("/assets/index-Fx7a9Q2b.js")

    assert response.status_code == 200
    assert content_type(response) in ("text/javascript", "application/javascript")


def test_t10_asset_with_query_string_is_served(built_frontend, client):
    """T10: a cache-busting query string does not change the file served."""
    response = client.get("/assets/index-B2c4dE8f.css?v=-1&x=%E2%9C%93")

    assert response.status_code == 200
    assert content_type(response) == "text/css"
    assert response_body(response) == built_frontend.assets["index-B2c4dE8f.css"][0]


@pytest.mark.parametrize(
    "path",
    [
        "/assets/missing-00000000.js",
        "/assets/missing.css",
        "/assets/chunks/missing.js",
        "/assets/index-Fx7a9Q2b.js.map",
        "/assets/INDEX-FX7A9Q2B.JS.missing",
        "/assets/%E2%9C%93-missing.svg",
        "/assets/" + "m" * 200 + ".js",
    ],
)
def test_t10_missing_asset_answers_404_not_the_index(built_frontend, client, path):
    """T10 / plan 9.5: a missing asset answers 404, never index.html (a browser would otherwise
    run the page as a script)."""
    response = client.get(path)

    assert response.status_code == 404, (path, response.status_code)
    assert INDEX_MARKER not in response_body(response)


@pytest.mark.parametrize("path", ["/assets/", "/assets/chunks/", "/assets/chunks"])
def test_t10_asset_folder_answers_404_without_a_listing(built_frontend, client, path):
    """T10: a folder under /assets/ is not a file: 404, no directory listing, not the index."""
    response = client.get(path)

    body = response_body(response)
    assert response.status_code == 404, (path, response.status_code)
    assert INDEX_MARKER not in body
    assert b"nested-M5n6B7v8" not in body
    assert b"index-Fx7a9Q2b" not in body


# --- nothing outside the build folder -------------------------------------------------


def _traversal_paths(built):
    absolute_secret = built.secret_file.as_posix()
    return [
        "/assets/../secret.txt",
        "/assets/../../secret.txt",
        "/assets/../../web/secret.txt",
        "/assets/%2e%2e/%2e%2e/secret.txt",
        "/assets/%2E%2E/%2E%2E/secret.txt",
        "/assets/..%2f..%2fsecret.txt",
        "/assets/..%2F..%2Fsecret.txt",
        "/assets/%2e%2e%2f%2e%2e%2fsecret.txt",
        "/assets/..\\..\\secret.txt",
        "/assets/..%5c..%5csecret.txt",
        "/assets/%2e%2e%5c%2e%5c%2e%2e%5csecret.txt",
        "/assets/chunks/../../../secret.txt",
        "/assets/....//....//secret.txt",
        "/assets/../../distx/assets/sibling.js",
        "/assets/..%2f..%2fdistx%2fassets%2fsibling.js",
        "/assets/" + absolute_secret,
        "/assets/" + quote(absolute_secret, safe=""),
        "/assets//" + absolute_secret,
        "/assets/" + str(built.secret_file),
        "/assets/../secret.txt%00.js",
        "/../secret.txt",
        "/%2e%2e/secret.txt",
    ]


def test_t10_path_traversal_never_serves_files_outside_the_build(built_frontend, client):
    """T10 / plan 9.5: no path under /assets/ (dot segments, encoded dots and slashes,
    backslashes, absolute and drive paths, a sibling folder with the same name prefix, a NUL
    byte) serves a file outside the build folder, and none fails with a server error."""
    for path in _traversal_paths(built_frontend):
        response = client.get(path)

        body = response_body(response)
        assert SECRET_MARKER not in body, path
        assert SIBLING_MARKER not in body, path
        assert response.status_code < 500, (path, response.status_code)


@pytest.mark.parametrize("path", ["/assets/index-Fx7a9Q2b.js%00", "/assets/%00", "/assets/a%00b.css"])
def test_t10_nul_byte_in_asset_path_is_refused_without_server_error(built_frontend, client, path):
    """T10: a NUL byte in an asset path is refused (400 or 404), never a server error."""
    response = client.get(path)

    assert response.status_code in (400, 404), (path, response.status_code)


# --- the API stays the API --------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "/api/does-not-exist",
        "/api/",
        "/api/index.html",
        "/api/assets/index-Fx7a9Q2b.js",
        "/api/status/extra",
        "/api/some/deep/path/",
    ],
)
def test_t10_unknown_api_path_still_answers_the_envelope(built_frontend, configured_api, path):
    """T6 regression / plan section 6 / T10: with a build present, an unknown /api/ path answers
    404 in the envelope, never the built index.html."""
    configured_api.configure(full_text_settings())

    response = configured_api.get(path)

    assert_error_envelope(response, 404, "not_found")
    assert INDEX_MARKER not in response.content


def test_t10_status_endpoint_still_answers_json_with_a_build(built_frontend, configured_api):
    """T6 regression / T10: GET /api/status keeps answering JSON when the frontend is served."""
    configured_api.configure(full_text_settings())

    response = configured_api.get("/api/status")

    assert response.status_code == 200
    assert response["Content-Type"].startswith("application/json")
    assert INDEX_MARKER not in response.content


def _plain_api_routes():
    """Every API route without parameters, from the URL configuration itself."""
    from django.urls import URLPattern

    from api import urls as api_urls

    routes = []
    for pattern in api_urls.urlpatterns:
        if not isinstance(pattern, URLPattern):
            continue
        route = str(pattern.pattern)
        if route and "<" not in route and not route.startswith("^"):
            routes.append(route)
    return routes


@pytest.mark.django_db
def test_t10_no_api_route_answers_the_index(built_frontend, configured_api):
    """Plan section 6 / T10: no route of the API configuration answers the built index.html,
    whatever endpoints later tasks add."""
    configured_api.configure(full_text_settings())
    routes = _plain_api_routes()
    assert routes, "The API URL configuration has no plain route to check."

    for route in routes:
        response = configured_api.get("/api/" + route)

        assert response["Content-Type"].startswith("application/json"), route
        assert INDEX_MARKER not in response.content, route


# --- no build present ---------------------------------------------------------------------


def _no_build_folders(tmp_path):
    missing = tmp_path / "never-built" / "dist"
    empty = tmp_path / "empty-build" / "dist"
    empty.mkdir(parents=True)
    assets_only = write_build(tmp_path / "assets-only" / "dist", with_index=False)
    return {"missing folder": missing, "empty folder": empty, "assets without index": assets_only}


@pytest.mark.parametrize("case", ["missing folder", "empty folder", "assets without index"])
@pytest.mark.parametrize("path", ["/", "/status", "/some/deep/path"])
def test_t10_rn27_no_build_answers_a_message_naming_the_build_step(client, settings, tmp_path, case, path):
    """RN-27 / T10: with no build present, a non-API path answers 503 with a clear text message
    that names the build step (`npm run build` in frontend/), not a Django error page."""
    settings.DEBUG = False
    point_app_at(settings, _no_build_folders(tmp_path)[case])

    response = client.get(path)

    body = response_body(response).decode("utf-8")
    assert response.status_code == NO_BUILD_STATUS, (case, path, response.status_code)
    assert content_type(response) in ("text/html", "text/plain")
    assert BUILD_STEP in body
    assert "frontend" in body


def test_t10_rn27_no_build_message_with_debug_on(client, settings, tmp_path):
    """RN-27 / T10: the message is the same in development (DEBUG on), not a debug error page."""
    settings.DEBUG = True
    point_app_at(settings, tmp_path / "never-built" / "dist")

    response = client.get("/")

    assert response.status_code == NO_BUILD_STATUS
    assert BUILD_STEP in response_body(response).decode("utf-8")


def test_t10_ca38_no_build_message_loads_nothing_from_outside(client, settings, tmp_path):
    """RN-33 / CA-38 / T10: the page written by the application loads no resource (image,
    script, style, font) from an address outside the local application."""
    point_app_at(settings, tmp_path / "never-built" / "dist")

    response = client.get("/")

    assert external_resource_references(response_body(response)) == []
    for name, value in response.headers.items():
        assert "://" not in value, (name, value)


def test_t10_no_build_missing_asset_is_not_a_server_error(client, settings, tmp_path):
    """T10: with no build present, an asset request fails cleanly (no 200, no server error)."""
    settings.DEBUG = False
    point_app_at(settings, tmp_path / "never-built" / "dist")

    response = client.get("/assets/index-Fx7a9Q2b.js")

    assert response.status_code in (404, NO_BUILD_STATUS)


def test_t10_no_build_keeps_the_api_working(configured_api, settings, tmp_path):
    """RN-27 / T10: with no build present, GET /api/status still answers JSON and an unknown
    /api/ path still answers the 404 envelope."""
    point_app_at(settings, tmp_path / "never-built" / "dist")
    configured_api.configure(full_text_settings())

    status = configured_api.get("/api/status")
    unknown = configured_api.get("/api/does-not-exist")

    assert status.status_code == 200
    assert status["Content-Type"].startswith("application/json")
    assert_error_envelope(unknown, 404, "not_found")


def test_t10_build_appearing_later_is_served_without_restart(client, settings, tmp_path):
    """RN-27 / T10: once the build step has run, the next request serves it with no restart."""
    build_dir = tmp_path / "late" / "dist"
    point_app_at(settings, build_dir)

    before = client.get("/")
    write_build(build_dir)
    after = client.get("/")

    assert before.status_code == NO_BUILD_STATUS
    assert after.status_code == 200
    assert INDEX_MARKER in response_body(after)


def test_t10_build_folder_setting_accepts_a_string_path(client, settings, tmp_path):
    """T10: the setting holds a path; a string path works as well as a Path."""
    build_dir = write_build(tmp_path / "as-text" / "dist")
    point_app_at(settings, str(build_dir))

    response = client.get("/")

    assert response.status_code == 200
    assert INDEX_MARKER in response_body(response)


# --- Windows file names, content types, methods, unreadable build -------------------------


def _stream_build(built):
    if not write_named_stream(built.build_dir):
        pytest.skip("Named NTFS streams are not available on this file system.")
    return built


@pytest.mark.parametrize(
    "suffix",
    [
        ":" + STREAM_NAME,
        ":" + STREAM_NAME + ":$DATA",
        "%3A" + STREAM_NAME,
        "%3a" + STREAM_NAME + "%3a%24DATA",
    ],
)
def test_t10_named_ntfs_stream_is_never_served(built_frontend, client, suffix):
    """T10 / plan 9.5: a named NTFS stream of an asset (here a Zone.Identifier holding a local
    path) answers 404 and its text never appears in the response."""
    _stream_build(built_frontend)

    response = client.get("/assets/" + STREAM_ASSET + suffix)

    body = response_body(response)
    assert response.status_code == 404, (suffix, response.status_code)
    assert STREAM_MARKER not in body
    assert b"Downloads" not in body


@pytest.mark.parametrize(
    "path",
    [
        "/assets/{asset}::$DATA",
        "/assets/{asset}%3A%3A%24DATA",
        "/assets/{asset}.",
        "/assets/{asset}..",
        "/assets/{asset}%20",
        "/assets/{asset}%20.",
        "/assets/{asset}.%20",
        "/assets/{asset}:",
        "/assets/chunks:x/nested-M5n6B7v8.js",
        "/assets/chunks/nested-M5n6B7v8.js:extra",
        "/assets/C:nested-M5n6B7v8.js",
        "/assets/:{asset}",
    ],
)
def test_t10_asset_name_must_match_the_file_exactly(built_frontend, client, path):
    """T10 / plan 9.5: Windows resolves `name::$DATA`, `name.` and `name ` to `name`; the
    served name must match the file exactly, and any path segment with `:` is refused: 404,
    never the file, never a server error. Holds on any platform."""
    url = path.format(asset="index-Fx7a9Q2b.js")

    response = client.get(url)

    body = response_body(response)
    assert response.status_code == 404, (url, response.status_code)
    assert body != JS_BYTES, url


def _rogue_mimetypes(monkeypatch):
    """Simulate a platform registry that maps .js, .mjs and .css to text/plain."""
    import mimetypes

    mimetypes.init()
    rogue = mimetypes.MimeTypes()
    for extension in (".js", ".mjs", ".css"):
        rogue.add_type("text/plain", extension)
        monkeypatch.setitem(mimetypes.types_map, extension, "text/plain")
    monkeypatch.setattr(mimetypes, "_db", rogue)
    monkeypatch.setattr(mimetypes, "guess_type", rogue.guess_type)
    assert mimetypes.guess_type("x.js")[0] == "text/plain"


@pytest.mark.parametrize(
    "relative, accepted",
    [
        ("index-Fx7a9Q2b.js", ("text/javascript", "application/javascript")),
        ("chunks/nested-M5n6B7v8.js", ("text/javascript", "application/javascript")),
        ("index-B2c4dE8f.css", ("text/css",)),
    ],
)
def test_t10_rn27_content_type_does_not_depend_on_the_platform_registry(
    built_frontend, client, monkeypatch, relative, accepted
):
    """RN-27 / T10: on Windows the registry can map .js to text/plain, and a browser then
    refuses the module script. JavaScript and CSS keep their types whatever the global
    `mimetypes` table says."""
    _rogue_mimetypes(monkeypatch)

    response = client.get(_asset_url(relative))

    assert response.status_code == 200
    assert content_type(response) in accepted, (relative, response.get("Content-Type"))


def _get_with_deadline(client, path, seconds=10):
    """GET `path` in a thread; a device name opened as a file could block forever."""
    outcome = {}

    def call():
        try:
            outcome["response"] = client.get(path)
        except BaseException as error:  # noqa: BLE001 (re-raised in the test thread)
            outcome["error"] = error

    worker = threading.Thread(target=call, daemon=True)
    worker.start()
    worker.join(seconds)
    assert not worker.is_alive(), f"{path} did not answer within {seconds} s (a device was opened?)"
    if "error" in outcome:
        raise outcome["error"]
    return outcome["response"]


@pytest.mark.parametrize(
    "name",
    [
        "CON",
        "con",
        "NUL",
        "nul.js",
        "aux.js",
        "AUX",
        "PRN.css",
        "COM1",
        "com9.js",
        "LPT1.txt",
        "CONIN$",
        "CONOUT$",
        "CON.%20js",
        "chunks/CON",
        "chunks/nul.js",
    ],
)
def test_t10_windows_device_names_answer_404(built_frontend, client, name):
    """T10: a Windows device name under /assets/ is not a file of the build: 404, never a
    server error and never a hang."""
    response = _get_with_deadline(client, "/assets/" + name)

    assert response.status_code == 404, (name, response.status_code)


@pytest.mark.parametrize(
    "path, expected",
    [
        ("/", "index"),
        ("/some/deep/path", "index"),
        ("/assets/index-Fx7a9Q2b.js", "index-Fx7a9Q2b.js"),
        ("/assets/empty-0a0a0a0a.css", "empty-0a0a0a0a.css"),
        ("/assets/large-L4r9e3G1.js", "large-L4r9e3G1.js"),
    ],
)
def test_t10_head_answers_200_with_the_length_and_no_body(built_frontend, client, path, expected):
    """T10: HEAD on the index or an asset answers 200 with the Content-Length of the file and
    an empty body."""
    content = built_frontend.index_bytes if expected == "index" else built_frontend.assets[expected][0]

    response = client.head(path)

    assert response.status_code == 200, (path, response.status_code)
    assert int(response["Content-Length"]) == len(content)
    assert response_body(response) == b""


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
@pytest.mark.parametrize("path", ["/", "/status", "/assets/index-Fx7a9Q2b.js"])
def test_t10_write_methods_on_the_frontend_answer_405(built_frontend, method, path):
    """T10: the built frontend is read only: POST, PUT, PATCH and DELETE on a page or an asset
    answer 405, never the index or the file."""
    from django.test import Client

    response = getattr(Client(enforce_csrf_checks=False), method)(path)

    body = response_body(response)
    assert response.status_code == 405, (method, path, response.status_code)
    assert INDEX_MARKER not in body
    assert body != JS_BYTES


def test_t10_unreadable_build_answers_the_no_build_message(built_frontend, client, monkeypatch):
    """RN-27 / T10: when the build folder cannot be read (access denied), / answers 503 with
    the message naming the build step, never a server error."""
    deny_reads_under(monkeypatch, built_frontend.build_dir)

    response = client.get("/")

    assert response.status_code == NO_BUILD_STATUS, response.status_code
    assert BUILD_STEP in response_body(response).decode("utf-8")


def test_t10_unreadable_build_asset_is_not_a_server_error(built_frontend, client, monkeypatch):
    """T10: an asset in a build folder that cannot be read answers 404 or 503, never 500."""
    deny_reads_under(monkeypatch, built_frontend.build_dir)

    response = client.get("/assets/index-Fx7a9Q2b.js")

    assert response.status_code in (404, NO_BUILD_STATUS), response.status_code
    assert response_body(response) != JS_BYTES
