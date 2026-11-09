"""GET /api/instance and POST /api/heartbeat (task T8, spec RN-41, RN-47, CA-47).

Instance contract (plan section 6), a contract between versions: a newer
launcher probes an older instance, so these fields never change meaning and
readers ignore extra fields.

    app      str   always "card-factory"
    version  str   the text of the VERSION file in the application home, without
                   surrounding whitespace; "0.0.0+unknown" when the file is missing
    home     str   the application home (the folder that holds `.env` and `data/`)

POST /api/heartbeat takes a JSON body (`{}`) and answers 204 with no body. It
forwards to the watchdog the launcher registered (`core.watchdog`, see
tests/test_watchdog.py); with no watchdog, it does nothing.

Requests go through tests.configured_api (temporary home, no network).
"""

import os

import pytest

from tests.config_files import full_text_settings
from tests.configured_api import assert_error_envelope, configured_api  # noqa: F401 (fixture)

INSTANCE_URL = "/api/instance"
HEARTBEAT_URL = "/api/heartbeat"
APP_NAME = "card-factory"
UNKNOWN_VERSION = "0.0.0+unknown"


def _same_path(first, second):
    return os.path.normcase(os.path.realpath(first)) == os.path.normcase(os.path.realpath(second))


def _instance(api):
    response = api.get(INSTANCE_URL)
    assert response.status_code == 200, response.content[:500]
    assert response["Content-Type"].startswith("application/json")
    return response.json()


# --- GET /api/instance ---


def test_t8_rn47_instance_identifies_card_factory_and_its_home(configured_api):
    """RN-47 / RN-41 / T8: the instance answers app "card-factory", a version and this home,
    so the launcher can tell a Card Factory from this folder from another program."""
    configured_api.configure(full_text_settings())
    (configured_api.home / "VERSION").write_text("1.4.2\n", encoding="utf-8")

    body = _instance(configured_api)

    assert {"app", "version", "home"} <= set(body)
    assert body["app"] == APP_NAME
    assert body["version"] == "1.4.2"
    assert isinstance(body["home"], str)
    assert _same_path(body["home"], configured_api.home)


def test_t8_rn47_instance_version_is_unknown_when_the_version_file_is_missing(configured_api):
    """RN-47 / T8: with no VERSION file in the home, the version is "0.0.0+unknown"."""
    configured_api.configure(full_text_settings())
    assert not (configured_api.home / "VERSION").exists()

    body = _instance(configured_api)

    assert body["app"] == APP_NAME
    assert body["version"] == UNKNOWN_VERSION


def test_t8_rn47_instance_version_ignores_surrounding_whitespace(configured_api):
    """RN-47 / T8: spaces and a CRLF line ending around the version are not part of it."""
    configured_api.configure(full_text_settings())
    (configured_api.home / "VERSION").write_bytes(b"  2.0.10 \r\n")

    assert _instance(configured_api)["version"] == "2.0.10"


def test_t8_rn47_instance_answers_with_no_configuration_file(configured_api):
    """RN-47 / RN-40 / T8: the probe works even when `.env` is missing, so a second start still finds the instance."""
    configured_api.remove_configuration()

    body = _instance(configured_api)

    assert body["app"] == APP_NAME
    assert _same_path(body["home"], configured_api.home)


# --- POST /api/heartbeat ---


def test_t8_rn41_heartbeat_with_json_body_answers_204_with_no_body(configured_api):
    """RN-41 / T8: a heartbeat `{}` answers 204 with an empty body; with no watchdog it does nothing."""
    import core.watchdog

    configured_api.configure(full_text_settings())
    core.watchdog.uninstall()

    response = configured_api.request("POST", HEARTBEAT_URL, data={})

    assert response.status_code == 204, response.content[:500]
    assert response.content == b""
    assert core.watchdog.current() is None


def test_t8_rn41_heartbeat_reaches_the_registered_watchdog(configured_api):
    """RN-41 / CA-47 / T8: a heartbeat through the API counts for the watchdog: armed at 0, a heartbeat
    at 100 s keeps it running past the 120 s window, and it stops 180 s after that heartbeat."""
    import core.watchdog
    from core.watchdog import Watchdog

    now = [0.0]
    stops = []
    watchdog = Watchdog(stop=lambda: stops.append(now[0]), clock=lambda: now[0])
    configured_api.configure(full_text_settings())
    core.watchdog.install(watchdog)
    try:
        watchdog.arm()
        now[0] = 100.0
        response = configured_api.request("POST", HEARTBEAT_URL, data={})
        assert response.status_code == 204

        now[0] = 150.0
        watchdog.check()
        assert stops == []

        now[0] = 280.0
        watchdog.check()
        assert stops == [280.0]
    finally:
        core.watchdog.uninstall()


@pytest.mark.parametrize("method", ["GET", "PUT", "DELETE"])
def test_t8_heartbeat_accepts_only_post(configured_api, method):
    """T8 / plan section 6: another method on the heartbeat answers 405 in the error envelope."""
    configured_api.configure(full_text_settings())

    response = configured_api.request(method, HEARTBEAT_URL)

    assert_error_envelope(response, 405, "method_not_allowed")


def test_t8_instance_accepts_only_get(configured_api):
    """T8 / plan section 6: a POST to the instance answers 405 in the error envelope."""
    configured_api.configure(full_text_settings())

    response = configured_api.request("POST", INSTANCE_URL, data={})

    assert_error_envelope(response, 405, "method_not_allowed")
