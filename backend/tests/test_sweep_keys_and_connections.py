"""Key-leak and outgoing connection sweep (task T61; spec RN-06, RN-29, CA-06, CA-19; plan sections 6, 8, 11).

Test 1 sends every endpoint of the URL configuration, with every HTTP method, through a
fake configuration whose text and image keys are distinctive fake values, including failure
paths (invalid bodies, unknown and malformed ids) and generations that end with a provider
error. No key value, and no distinctive fragment of one, may appear in a response (body,
headers, cookies), in the application log output or in the contract samples. The endpoint list
is read from the URL configuration, so later endpoints are swept without editing this file.

Test 2 checks that connections are only attempted by the modules allowed to open them
(the provider transport, the ingest downloader and, once it exists, the base image fetch),
with a static import sweep of production code and a runtime check on the socket entry points.

Keys and cards are fictional.
"""

import ast
import io
import logging
import re
import uuid
from pathlib import Path

import pytest
from django.urls import URLPattern, URLResolver, get_resolver
from django.urls.resolvers import RegexPattern, RoutePattern

from providers.base import Usage
from providers.errors import AuthError, InvalidResponse, ModelNotFound, ProviderUnavailable, QuotaError
from tests.config_files import DEFAULT_PORT, FAKE_IMAGE_KEY, FAKE_TEXT_KEY, full_text_settings
from tests.configured_api import assert_no_key_in_response, configured_api  # noqa: F401 (fixture)
from tests.generation_api_helpers import (
    GENERATIONS_URL,
    GREEN_WHITE_REQUEST,
    MODEL,
    PROVIDER,
    card_path,
    install_fake,
    job_path,
    script_approved,
    script_revision_failure,
    seed_catalog,
)
from tests.job_helpers import inline_runner
from tests.settings_probe import REPOSITORY_ROOT
from tests.setup_api_helpers import mark_ready

BACKEND = Path(__file__).resolve().parent.parent
SAMPLES = REPOSITORY_ROOT / "frontend" / "src" / "api" / "contract" / "samples.ts"

# Distinctive parts of the fake keys: a masked or partial echo of a key would still contain one.
KEY_FRAGMENTS = (
    "TEXTKEY",
    "IMAGEKEY",
    FAKE_TEXT_KEY[:14],
    FAKE_IMAGE_KEY[:14],
    FAKE_TEXT_KEY[-12:],
    FAKE_IMAGE_KEY[-12:],
)
ALL_VALUES = (FAKE_TEXT_KEY, FAKE_IMAGE_KEY, *KEY_FRAGMENTS)

METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD")
BODIES = (None, {}, {"idea": "x" * 5000, "color_identity": "?", "power_level": None})
_CONVERTER = re.compile(r"<(?:(?P<kind>\w+):)?\w+>")
SELF_ECHO = f"The provider says the key {FAKE_TEXT_KEY} / {FAKE_IMAGE_KEY} is wrong (masked: sk-fake-text-****1111)"

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------- enumeration of the URL configuration


def _pattern_text(pattern):
    if isinstance(pattern, RoutePattern):
        return str(pattern)
    if isinstance(pattern, RegexPattern):
        return pattern.regex.pattern
    raise AssertionError(f"Unknown URL pattern type: {type(pattern).__name__}")


def _routes(resolver=None, prefix=""):
    """Every API route text, converters left in place; the catch-all regex becomes an unknown path."""
    resolver = resolver if resolver is not None else get_resolver()
    found = []
    for entry in resolver.url_patterns:
        text = prefix + _pattern_text(entry.pattern)
        if isinstance(entry, URLResolver):
            found.extend(_routes(entry, text))
        elif isinstance(entry, URLPattern):
            if isinstance(entry.pattern, RegexPattern):
                found.append(prefix + "no-such-endpoint")
            elif text.startswith("api/"):
                found.append(text)
    return found


def _fill(route, uuid_value):
    def fill(match):
        kind = match.group("kind") or "str"
        if kind == "uuid":
            return uuid_value
        if kind == "int":
            return "1"
        return "fictional"

    return "/" + _CONVERTER.sub(fill, route)


def _paths(route, known_ids):
    """Concrete paths for a route: unknown, malformed and real ids for each uuid converter."""
    if not _CONVERTER.search(route):
        return ["/" + route]
    values = [str(uuid.uuid4()), "not-a-uuid", *known_ids]
    return [_fill(route, value) for value in values]


# ---------------------------------------------------------------- scenario and log capture


class _LogCapture:
    """Collects what the application's log handlers would write: same format, same key filter."""

    def __init__(self):
        from core.app_log import FILE_FORMAT
        from core.log_redaction import KeyRedactionFilter

        self.stream = io.StringIO()
        self.handler = logging.StreamHandler(self.stream)
        self.handler.setLevel(logging.DEBUG)
        self.handler.setFormatter(logging.Formatter(FILE_FORMAT))
        self.handler.addFilter(KeyRedactionFilter())
        self._previous_level = logging.getLogger().level
        self._offsets = {}

    @staticmethod
    def _log_files():
        from django.conf import settings

        names = (handler.get("filename") for handler in settings.LOGGING.get("handlers", {}).values())
        return [Path(name) for name in names if name]

    def __enter__(self):
        # The log file is shared by the whole session: only what this test appends is read, so a
        # record of an earlier test (with a key-like text no configuration of its own held) is ignored.
        self._offsets = {path: path.stat().st_size if path.exists() else 0 for path in self._log_files()}
        root = logging.getLogger()
        root.addHandler(self.handler)
        root.setLevel(logging.DEBUG)
        return self

    def __exit__(self, *exc):
        root = logging.getLogger()
        root.removeHandler(self.handler)
        root.setLevel(self._previous_level)

    def text(self):
        parts = [self.stream.getvalue()]
        for path in self._log_files():
            if not path.exists():
                continue
            data = path.read_bytes()
            offset = self._offsets.get(path, 0)
            # A smaller file was rotated during the test: everything in it was written by this test.
            parts.append(data[offset if len(data) >= offset else 0 :].decode("utf-8", errors="replace"))
        return "\n".join(parts)


def _assert_clean_text(text, where):
    for value in ALL_VALUES:
        assert value not in text, f"A key value or fragment ({len(value)} characters) appears in {where}."


def _error_script(error):
    def script(fake, rows):
        fake.add_error(error)

    return script


def _revision_failure_script(error):
    def script(fake, rows):
        script_revision_failure(fake, rows, error)

    return script


def _run_generation(api, fake, rows, script):
    """Script the fake adapter, run one generation to the end and return (job id, job body)."""
    script(fake, rows)
    response = api.request("POST", GENERATIONS_URL, data=GREEN_WHITE_REQUEST)
    assert response.status_code == 202, response.content[:500]
    job_id = response.json()["id"]
    job = api.get(job_path(job_id))
    assert job.status_code == 200, job.content[:500]
    return job_id, job.json()


@pytest.fixture
def api(configured_api):
    configured_api.configure(
        full_text_settings(provider=PROVIDER, model=MODEL)
        | {"IMAGE_PROVIDER": "openai", "IMAGE_API_KEY": FAKE_IMAGE_KEY, "IMAGE_MODEL": "fake-image-model-1"}
    )
    configured_api.set_running_port(DEFAULT_PORT)
    for value in ALL_VALUES:
        configured_api.add_secret(value)
    mark_ready()
    return configured_api


# ---------------------------------------------------------------- test 1: keys never appear

PROVIDER_ERRORS = [
    AuthError(SELF_ECHO),
    QuotaError(SELF_ECHO),
    InvalidResponse(SELF_ECHO, usage=Usage(5, 5)),
    ModelNotFound(SELF_ECHO, "LLM_MODEL"),
    ProviderUnavailable(SELF_ECHO),
    RuntimeError(SELF_ECHO),
]


def test_t61_rn06_ca06_every_endpoint_and_provider_error_leaks_no_key(api, monkeypatch):
    """RN-06 / CA-06 / T61: every route of the URL configuration, with every method, valid and
    invalid bodies and unknown, malformed and real ids, plus generations ending in each provider
    error, leave no key value or fragment in any response or in the log output."""
    rows = seed_catalog()
    fake = install_fake(monkeypatch)
    known = []
    scripts = [_error_script(error) for error in PROVIDER_ERRORS]
    scripts += [_revision_failure_script(error) for error in PROVIDER_ERRORS]
    scripts.append(script_approved)

    with _LogCapture() as logs, inline_runner():
        for script in scripts:
            job_id, job = _run_generation(api, fake, rows, script)
            known.append(job_id)
            assert job["status"] in ("done", "failed"), job
            if job["status"] == "done":
                card_id = job["result"]["card"]
                known.append(card_id)
                assert api.get(card_path(card_id)).status_code == 200
        assert known, "No generation ended."

        walked = 0
        for route in _routes():
            for path in _paths(route, known):
                for method in METHODS:
                    for body in BODIES:
                        if body is not None and method in ("GET", "HEAD", "OPTIONS"):
                            continue
                        api.request(method, path, data=body)
                        walked += 1
                    if method in ("POST", "PUT", "PATCH"):
                        # A malformed JSON body that carries a key value.
                        raw = getattr(api.client, method.lower())(
                            path, data="{not json " + FAKE_TEXT_KEY, content_type="application/json"
                        )
                        assert_no_key_in_response(raw, ALL_VALUES)
                        walked += 1
        assert walked > 50, "The walk found too few requests."
        log_text = logs.text()

    assert log_text.strip(), "No log output was captured."
    _assert_clean_text(log_text, "the application log output")


def test_t61_rn06_sweep_enumerates_the_url_configuration():
    """T61: the walk sees the endpoints delivered so far, so an empty walk cannot pass."""
    routes = set(_routes())

    assert {"api/status", "api/jobs/<uuid:job_id>", "api/generations", "api/cards/<uuid:card_id>"} <= routes


def test_t61_ca06_the_key_check_catches_a_leak():
    """CA-06 / T61: the check fails on a response or text that holds a key value or fragment (control)."""
    from django.http import JsonResponse

    with pytest.raises(AssertionError):
        assert_no_key_in_response(JsonResponse({"message": f"bad {FAKE_TEXT_KEY}"}), [FAKE_TEXT_KEY])
    with pytest.raises(AssertionError):
        _assert_clean_text("echo TEXTKEY", "a control")


def test_t61_rn06_contract_samples_hold_no_key():
    """RN-06 / T61: frontend/src/api/contract/samples.ts holds no key value or fragment."""
    text = SAMPLES.read_text(encoding="utf-8")

    _assert_clean_text(text, "the contract samples")
    assert not re.search(r"sk-[A-Za-z0-9_-]{16,}", text)
    assert not re.search(r"AIza[0-9A-Za-z_-]{20,}", text)


# ---------------------------------------------------------------- test 2: outgoing connections

# Modules allowed to open connections: the provider transport (text and image adapters) and the
# ingest downloader. The base image fetch is listed here once its task adds the module.
CONNECTION_MODULES = {
    "providers/transport.py",
    "catalog/download.py",
}
# Modules that use a networking library for a local purpose only.
LOCAL_ONLY = {
    "core/startup.py": {"socket"},  # the listening socket on 127.0.0.1
}
NETWORK_MODULES = {
    "socket",
    "ssl",
    "http.client",
    "http.server",
    "urllib.request",
    "urllib.error",
    "urllib3",
    "requests",
    "httpx",
    "aiohttp",
    "websocket",
    "websockets",
    "ftplib",
    "smtplib",
    "telnetlib",
    "xmlrpc.client",
    "imaplib",
    "poplib",
}
PRODUCTION_FOLDERS = ("api", "cards", "catalog", "core", "generation", "providers", "validators", "cardfactory")


def _production_files():
    files = [BACKEND / "manage.py"]
    for folder in PRODUCTION_FOLDERS:
        files.extend(p for p in (BACKEND / folder).rglob("*.py") if "migrations" not in p.parts)
    return files


def _imported_modules(tree):
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module)
            modules.update(f"{node.module}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Call):
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name in ("__import__", "import_module"):
                modules.add(name)
    return modules


def test_t61_rn29_ca19_only_the_allowed_modules_import_networking():
    """RN-29 / CA-19 / T61: production code imports socket, ssl, http.client, urllib.request, requests
    and similar libraries only in the transport, the ingest downloader and local-only modules."""
    offenders = []
    for path in _production_files():
        relative = path.relative_to(BACKEND).as_posix()
        if relative in CONNECTION_MODULES:
            continue
        for name in sorted(_imported_modules(ast.parse(path.read_text(encoding="utf-8")))):
            if name in ("__import__", "import_module"):
                offenders.append(f"{relative}: dynamic import")
            elif name in NETWORK_MODULES and name not in LOCAL_ONLY.get(relative, set()):
                offenders.append(f"{relative}: {name}")
    assert not offenders, offenders


def test_t61_rn29_the_allow_lists_name_real_files():
    """T61: the allow-lists name existing files, so a renamed module cannot silently widen them."""
    for relative in list(CONNECTION_MODULES) + list(LOCAL_ONLY):
        assert (BACKEND / relative).is_file(), relative


def test_t61_rn29_local_server_binds_only_to_loopback():
    """RN-29 / T61: the one socket outside the connection modules is the listening socket on 127.0.0.1."""
    text = (BACKEND / "core" / "startup.py").read_text(encoding="utf-8")

    assert "127.0.0.1" in text
    assert not re.search(r"""bind\(\(\s*["'](0\.0\.0\.0|::)?["']""", text)


def test_t61_ca19_runtime_requests_open_no_connection(api, monkeypatch):
    """CA-19 / T61: serving every route and running a generation (fake provider) attempts no outgoing
    connection; every attempt is recorded at the socket entry points and none may occur."""
    attempts = []

    def record(self, address, *args):
        attempts.append(address)
        raise ConnectionRefusedError("recorded by the sweep")

    monkeypatch.setattr("socket.socket.connect", record)
    monkeypatch.setattr("socket.socket.connect_ex", record)
    rows = seed_catalog()
    fake = install_fake(monkeypatch)
    with inline_runner():
        _run_generation(api, fake, rows, script_approved)
        for route in _routes():
            for path in _paths(route, []):
                api.request("GET", path)

    assert attempts == []
