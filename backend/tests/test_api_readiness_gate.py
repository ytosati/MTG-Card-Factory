"""Readiness gate (task T22, spec RN-28, CA-18; plan section 6, "Readiness gate").

A default DRF permission requires a ready catalog (a `BuildRun` of the current
`CATALOG_VERSION`). Until then every API endpoint answers the error envelope
with code `database_not_ready`, except the views that opt out explicitly:
status, connection test, setup (GET and the build), jobs, instance and
heartbeat. An unknown `/api/` path keeps answering 404 `not_found` (plan
section 6), so the catch-all route is listed with the opt-outs.

The walk enumerates the URL configuration, so endpoints added by later
milestones are covered without editing this file: a new endpoint is gated
unless it is added to OPT_OUTS. Each route is called with OPTIONS, which runs
the permission checks of a DRF view and has no side effect.

`database_not_ready` answers HTTP 503 (maintainer decision for T22).
"""

import re
import uuid

import pytest
from django.urls import URLPattern, URLResolver, get_resolver
from django.urls.resolvers import RegexPattern, RoutePattern

from tests.config_files import DEFAULT_PORT, full_text_settings
from tests.configured_api import configured_api  # noqa: F401 (fixture)
from tests.job_helpers import inline_runner
from tests.readiness_gate_urls import PROBE_ROUTE
from tests.setup_api_helpers import (
    BUILD_URL,
    CODE_DATABASE_NOT_READY,
    SetupEnvironment,
    clear_listing_cache,
    is_not_ready_answer,
    mark_ready,
    own_origin,
)

pytestmark = [pytest.mark.django_db, pytest.mark.urls("tests.readiness_gate_urls")]

NOT_READY_STATUS = 503
UNKNOWN_ROUTE = "api/<unknown path>"
CONNECTION_TEST_ROUTE = "api/status/connection-test"

# The views that work without a ready database (plan section 6). Converters are
# written as `<>`; the catch-all of unknown API paths is UNKNOWN_ROUTE.
OPT_OUTS = frozenset(
    {
        "api/status",
        CONNECTION_TEST_ROUTE,
        "api/setup",
        "api/setup/build",
        "api/jobs/<>",
        "api/instance",
        "api/heartbeat",
        UNKNOWN_ROUTE,
    }
)
# Opt-outs that a later milestone adds (the connection test endpoint, T45).
NOT_YET_REQUIRED = frozenset({CONNECTION_TEST_ROUTE})

_CONVERTER = re.compile(r"<(?:(?P<kind>\w+):)?\w+>")
_SAMPLE_VALUES = {"uuid": None, "int": "1", "slug": "fictional-slug", "str": "fictional", "path": "fictional/path"}


def _api_routes(resolver=None, prefix=""):
    """[(route text, concrete path)] for every API URL pattern of the current URL configuration."""
    resolver = resolver if resolver is not None else get_resolver()
    routes = []
    for entry in resolver.url_patterns:
        if isinstance(entry, URLResolver):
            routes.extend(_api_routes(entry, prefix + _pattern_text(entry.pattern)))
        elif isinstance(entry, URLPattern):
            text = prefix + _pattern_text(entry.pattern)
            if text.startswith("api/"):
                routes.append(_route(text, entry))
    return routes


def _pattern_text(pattern):
    if isinstance(pattern, RoutePattern):
        return str(pattern)
    if isinstance(pattern, RegexPattern):
        return pattern.regex.pattern
    raise AssertionError(f"Unknown URL pattern type: {type(pattern).__name__}")


def _route(text, entry):
    if isinstance(entry.pattern, RegexPattern):
        assert entry.pattern.regex.pattern == "", (
            f"The readiness walk does not know how to call the regex route {text!r}; teach it."
        )
        return UNKNOWN_ROUTE, "/api/readiness-walk-unknown-path"
    normalized = _CONVERTER.sub("<>", text)

    def sample(match):
        kind = match.group("kind") or "str"
        assert kind in _SAMPLE_VALUES, f"The readiness walk has no sample value for <{kind}:...> in {text!r}."
        return _SAMPLE_VALUES[kind] or str(uuid.uuid4())

    return normalized, "/" + _CONVERTER.sub(sample, text)


@pytest.fixture
def env(configured_api, monkeypatch):
    configured_api.configure(full_text_settings())
    configured_api.set_running_port(DEFAULT_PORT)
    with inline_runner():
        environment = SetupEnvironment(monkeypatch)
        environment.api = configured_api
        yield environment
    clear_listing_cache()


def _walk(env):
    """{route: response} of OPTIONS on every API route."""
    return {route: env.api.request("OPTIONS", path) for route, path in _api_routes()}


# ---------------------------------------------------------------- the gate is the default permission


def test_t22_rn28_gate_is_a_default_drf_permission():
    """RN-28 / T22 / plan section 6: the REST framework settings name a default permission class (the gate)."""
    from django.conf import settings

    assert settings.REST_FRAMEWORK.get("DEFAULT_PERMISSION_CLASSES"), (
        "The readiness gate is a default DRF permission: DEFAULT_PERMISSION_CLASSES must name it."
    )


def test_t22_walk_finds_the_api_routes(env):
    """T22: the walk sees the routes of this milestone and the gated probe, so an empty walk cannot pass."""
    routes = {route for route, _ in _api_routes()}

    assert OPT_OUTS - NOT_YET_REQUIRED <= routes, sorted(OPT_OUTS - NOT_YET_REQUIRED - routes)
    assert PROBE_ROUTE in routes


# ---------------------------------------------------------------- before a ready build


def test_t22_rn28_ca18_before_the_build_only_the_opt_outs_answer(env):
    """RN-28 / CA-18 / T22: before a ready build every API route answers `database_not_ready` except the
    opt-outs (status, connection test, setup, jobs, instance, heartbeat, and unknown paths' 404)."""
    answers = _walk(env)

    gated = {route for route in answers if route not in OPT_OUTS}
    assert gated, "No gated route was walked."
    for route, response in answers.items():
        if route in OPT_OUTS:
            assert not is_not_ready_answer(response), f"{route} must work before the database is ready."
        else:
            assert response.status_code == NOT_READY_STATUS, (route, response.status_code)
            assert is_not_ready_answer(response), f"{route} must answer {CODE_DATABASE_NOT_READY} until ready."


def test_t22_rn28_gated_endpoint_answers_the_envelope_before_the_build(env):
    """RN-28 / T22: a gated endpoint answers the plan's error envelope with `database_not_ready`, no setting,
    no fields and a message."""
    response = env.api.get("/" + PROBE_ROUTE)

    assert response.status_code == NOT_READY_STATUS
    assert response["Content-Type"].startswith("application/json")
    payload = response.json()
    assert set(payload) == {"error"}
    assert set(payload["error"]) == {"code", "message", "setting", "fields"}
    assert payload["error"]["code"] == CODE_DATABASE_NOT_READY
    assert payload["error"]["message"].strip()
    assert payload["error"]["setting"] is None and payload["error"]["fields"] is None


def test_t22_rn28_unknown_api_path_stays_not_found_before_the_build(env):
    """RN-28 / T22 / plan section 6: an unknown API path answers 404 `not_found`, never the gate."""
    response = env.api.get("/api/no-such-endpoint")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_t22_rn28_older_catalog_version_keeps_the_gate_closed(env, monkeypatch):
    """RN-28 / RN-03 / T22: a ready build of an older catalog version does not open the gate."""
    from catalog import sources

    mark_ready()
    monkeypatch.setattr(sources, "CATALOG_VERSION", sources.CATALOG_VERSION + 1)

    assert is_not_ready_answer(env.api.get("/" + PROBE_ROUTE))


# ---------------------------------------------------------------- after a ready build


def test_t22_rn28_ca18_after_a_ready_build_no_route_answers_the_gate(env):
    """RN-28 / CA-18 / T22: after a build started through POST /api/setup/build reaches ready, no API route
    answers `database_not_ready` and the gated endpoint works."""
    response = env.api.request("POST", BUILD_URL, data={}, **own_origin(DEFAULT_PORT))
    assert response.status_code == 202, response.content[:500]

    answers = _walk(env)

    for route, answer in answers.items():
        assert not is_not_ready_answer(answer), f"{route} still answers {CODE_DATABASE_NOT_READY} after the build."
    probe = env.api.get("/" + PROBE_ROUTE)
    assert probe.status_code == 200
    assert probe.json() == {"probe": "ok"}


def test_t22_rn28_stored_ready_build_opens_the_gate(env):
    """RN-28 / T22: a stored ready build of the current catalog version opens the gate."""
    assert is_not_ready_answer(env.api.get("/" + PROBE_ROUTE))

    mark_ready()

    assert env.api.get("/" + PROBE_ROUTE).status_code == 200
