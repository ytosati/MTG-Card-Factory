"""Origin check on non-GET requests and JSON-only parsers (task T85, spec RN-29, plan section 6).

Origin check: every non-GET request whose `Origin` header (or, when it is
absent, `Referer`) is not the application's own origin is refused with the
error envelope and the code `origin_refused`. Plan section 6 lists the code but
names no status; these tests use 403 Forbidden, the status for a refused
request that authentication cannot fix. `http://127.0.0.1:<port>` and
`http://localhost:<port>` both count as the own origin, where `<port>` is the
Django setting `RUNNING_PORT`. A request with neither header is accepted.

Parsers: the API parses JSON only. A malformed JSON body (400), an unsupported
media type (415) and an `Accept` header the API cannot satisfy (406) answer with
the code `bad_request`, a fixed message and their own status.

The only POST endpoint in this milestone is the heartbeat (T8), so it carries
the non-GET cases. Requests go through tests.configured_api (temporary home, no
network, every response checked for keys).
"""

import json

import pytest

from tests.config_files import full_text_settings
from tests.configured_api import (
    assert_error_envelope,
    assert_no_key_in_response,
    configured_api,  # noqa: F401 (fixture)
)

HEARTBEAT_URL = "/api/heartbeat"
INSTANCE_URL = "/api/instance"
ORIGIN_REFUSED_STATUS = 403

# A port that is not the default, so the check is seen to follow RUNNING_PORT.
PORT = 51234


@pytest.fixture
def api(configured_api):
    configured_api.configure(full_text_settings())
    configured_api.set_running_port(PORT)
    return configured_api


def _post_heartbeat(api, **headers):
    return api.request("POST", HEARTBEAT_URL, data={}, **headers)


def _post_raw(api, body, content_type, **headers):
    """POST a raw body with its own content type, bypassing the JSON encoding of the helper."""
    response = api.client.post(HEARTBEAT_URL, data=body, content_type=content_type, **headers)
    assert_no_key_in_response(response, api.secrets)
    return response


def _own_origins():
    return [f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}"]


# --- Origin check ---


@pytest.mark.parametrize(
    "origin",
    [
        pytest.param("http://evil.example", id="foreign-host"),
        pytest.param("https://evil.example:51234", id="foreign-host-same-port"),
        pytest.param("http://127.0.0.1:1234", id="loopback-other-port"),
        pytest.param("http://localhost", id="localhost-no-port"),
        pytest.param("https://127.0.0.1:51234", id="loopback-https"),
        pytest.param("http://127.0.0.1.evil.example:51234", id="loopback-prefix-host"),
        pytest.param("http://192.168.0.10:51234", id="lan-address"),
        pytest.param("null", id="opaque-null"),
        pytest.param("http://ẽvil✓.example", id="odd-characters"),
        pytest.param("http://" + "a" * 5000 + ".example", id="huge"),
    ],
)
def test_t85_rn29_post_from_another_origin_is_refused(api, origin):
    """RN-29 / T85: a POST whose Origin is not the application's own origin answers origin_refused
    in the error envelope."""
    response = _post_heartbeat(api, HTTP_ORIGIN=origin)

    error = assert_error_envelope(response, ORIGIN_REFUSED_STATUS, "origin_refused")
    assert error["setting"] is None


def test_t85_rn29_refused_origin_message_does_not_echo_the_origin(api):
    """RN-29 / T85: the refusal message is fixed and does not repeat the foreign origin."""
    response = _post_heartbeat(api, HTTP_ORIGIN="http://evil-marker.example")

    error = assert_error_envelope(response, ORIGIN_REFUSED_STATUS, "origin_refused")
    assert "evil-marker" not in error["message"]


def test_t85_rn29_refused_heartbeat_does_not_reach_the_watchdog(api):
    """RN-29 / RN-41 / T85: a refused heartbeat from another origin does not keep the application alive."""
    import core.watchdog
    from core.watchdog import Watchdog

    now = [0.0]
    stops = []
    watchdog = Watchdog(stop=lambda: stops.append(now[0]), clock=lambda: now[0])
    core.watchdog.install(watchdog)
    try:
        watchdog.arm()
        now[0] = 100.0
        response = _post_heartbeat(api, HTTP_ORIGIN="http://evil.example")
        assert response.status_code == ORIGIN_REFUSED_STATUS

        # With no accepted heartbeat, the 120 s window from arming applies.
        now[0] = 125.0
        watchdog.check()
        assert stops == [125.0]
    finally:
        core.watchdog.uninstall()


@pytest.mark.parametrize(
    "referer",
    [
        pytest.param("http://evil.example/page", id="foreign-host"),
        pytest.param("http://127.0.0.1:1234/", id="loopback-other-port"),
        pytest.param("not a url", id="malformed"),
    ],
)
def test_t85_rn29_post_without_origin_and_with_a_foreign_referer_is_refused(api, referer):
    """RN-29 / T85: with no Origin, a Referer from another origin is refused."""
    response = _post_heartbeat(api, HTTP_REFERER=referer)

    assert_error_envelope(response, ORIGIN_REFUSED_STATUS, "origin_refused")


def test_t85_rn29_foreign_origin_wins_over_a_same_origin_referer(api):
    """RN-29 / T85: the Referer is read only when Origin is absent; a foreign Origin is refused
    even with a same-origin Referer."""
    response = _post_heartbeat(
        api, HTTP_ORIGIN="http://evil.example", HTTP_REFERER=f"http://127.0.0.1:{PORT}/status"
    )

    assert_error_envelope(response, ORIGIN_REFUSED_STATUS, "origin_refused")


@pytest.mark.parametrize("origin", _own_origins(), ids=["127.0.0.1", "localhost"])
def test_t85_rn29_same_origin_post_is_accepted(api, origin):
    """RN-29 / T85: a POST from http://127.0.0.1:<port> or http://localhost:<port> is accepted."""
    response = _post_heartbeat(api, HTTP_ORIGIN=origin)

    assert response.status_code == 204, response.content[:500]


@pytest.mark.parametrize("origin", _own_origins(), ids=["127.0.0.1", "localhost"])
def test_t85_rn29_same_origin_referer_without_origin_is_accepted(api, origin):
    """RN-29 / T85: with no Origin, a Referer from the own origin (with a path) is accepted."""
    response = _post_heartbeat(api, HTTP_REFERER=f"{origin}/library?favorite=true")

    assert response.status_code == 204, response.content[:500]


def test_t85_rn29_own_origin_follows_the_running_port(api, settings):
    """RN-29 / RN-47 / T85: the own origin uses settings.RUNNING_PORT, not a fixed port."""
    api.set_running_port(47999)

    accepted = _post_heartbeat(api, HTTP_ORIGIN="http://127.0.0.1:47999")
    refused = _post_heartbeat(api, HTTP_ORIGIN=f"http://127.0.0.1:{PORT}")

    assert accepted.status_code == 204, accepted.content[:500]
    assert_error_envelope(refused, ORIGIN_REFUSED_STATUS, "origin_refused")


def test_t85_rn29_post_with_neither_origin_nor_referer_is_accepted(api):
    """RN-29 / T85: a local non-browser client sends neither header and is accepted."""
    response = _post_heartbeat(api)

    assert response.status_code == 204, response.content[:500]


def test_t85_rn29_get_from_another_origin_is_not_refused(api):
    """RN-29 / T85: only non-GET requests are checked; a GET with a foreign Origin answers normally."""
    response = api.get(INSTANCE_URL, HTTP_ORIGIN="http://evil.example")

    assert response.status_code == 200, response.content[:500]
    assert response.json()["app"] == "card-factory"


# --- JSON-only parsers and bad_request ---


def _bad_request(response, status):
    error = assert_error_envelope(response, status, "bad_request")
    assert error["setting"] is None
    assert error["fields"] is None
    return error


@pytest.mark.parametrize(
    ("body", "content_type"),
    [
        pytest.param("beat=1", "application/x-www-form-urlencoded", id="form-encoded"),
        pytest.param(
            "--b\r\nContent-Disposition: form-data; name=\"beat\"\r\n\r\n1\r\n--b--\r\n",
            "multipart/form-data; boundary=b",
            id="multipart",
        ),
        pytest.param("{}", "text/plain", id="text-plain"),
    ],
)
def test_t85_rn29_same_origin_non_json_heartbeat_answers_bad_request_415(api, body, content_type):
    """RN-29 / T85: the parsers are JSON only; a same-origin form-encoded (or other non-JSON)
    heartbeat answers bad_request with status 415."""
    response = _post_raw(api, body, content_type, HTTP_ORIGIN=f"http://127.0.0.1:{PORT}")

    _bad_request(response, 415)


@pytest.mark.parametrize(
    "body",
    [
        pytest.param("{", id="truncated"),
        pytest.param("{'beat': 1}", id="single-quotes"),
        pytest.param("{\"beat\": ✓ção}", id="odd-characters"),
        pytest.param("[" * 10000, id="huge-nesting"),
    ],
)
def test_t85_rn29_malformed_json_answers_bad_request_400(api, body):
    """RN-29 / T85: a malformed JSON body answers bad_request with status 400."""
    response = _post_raw(api, body, "application/json", HTTP_ORIGIN=f"http://localhost:{PORT}")

    _bad_request(response, 400)


def test_t85_bad_request_message_is_fixed_and_does_not_echo_the_body(api):
    """T85 / plan section 6: the bad_request message is fixed: two different malformed bodies give
    the same message, which repeats neither the body nor the parser's own text."""
    first = _bad_request(_post_raw(api, "{marker-one", "application/json"), 400)
    second = _bad_request(_post_raw(api, "[marker-two", "application/json"), 400)

    assert first["message"] == second["message"]
    for text in ("marker-one", "marker-two", "JSON parse error", "Expecting"):
        assert text not in first["message"]


@pytest.mark.parametrize(
    "accept",
    [
        pytest.param("application/xml", id="xml"),
        pytest.param("text/xml", id="text-xml"),
    ],
)
def test_t85_accept_only_xml_answers_bad_request_406(api, accept):
    """T85 / plan section 6: a request that accepts only XML answers bad_request with status 406,
    never DRF's own text."""
    response = api.get(INSTANCE_URL, HTTP_ACCEPT=accept)

    error = _bad_request(response, 406)
    assert "Could not satisfy" not in error["message"]


def test_t85_accept_with_json_among_others_is_served(api):
    """T85: an Accept header that also lists JSON is satisfied normally."""
    response = api.get(INSTANCE_URL, HTTP_ACCEPT="application/xml, application/json;q=0.5")

    assert response.status_code == 200, response.content[:500]
    assert json.loads(response.content)["app"] == "card-factory"
