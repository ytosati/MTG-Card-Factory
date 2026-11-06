"""Test helper: calls API endpoints with a fake configuration and checks every response for keys.

Each test gets a temporary application home with its own `.env`, a cleared
process environment and the API test client. The repository `.env` is never
read. Every response returned by the helper has already been checked: no key
value (text or image, set, ignored or pasted into the wrong setting) appears in
its body, headers or cookies (spec RN-06, CA-06).

Reused by the contract samples (T126) and the key sweep over every endpoint
(T61). Usage:

    from tests.configured_api import configured_api  # noqa: F401 (fixture)

    def test_something(configured_api):
        configured_api.configure(full_text_settings())
        response = configured_api.get("/api/status")

The port the running server was started with is the Django setting
`RUNNING_PORT`, read once when the settings load (plan section 8: the port is
read once at startup). `set_running_port()` overrides it for one test.

Values are fictional; keys only look like keys.
"""

import json
import os
import time

import pytest

from tests.config_files import FAKE_IMAGE_KEY, FAKE_TEXT_KEY, env_text, write_env
from tests.project_environment import is_project_variable

# Settings whose value is a key; any value written to them is a secret to look for.
KEY_SETTINGS = ("LLM_API_KEY", "IMAGE_API_KEY")

# Shorter values would match ordinary text; the log filter uses the same limit
# (core.log_redaction, plan section 8). Every fake key in the tests is longer.
MIN_SECRET_LENGTH = 8

RUNNING_PORT_SETTING = "RUNNING_PORT"

ENVELOPE_FIELDS = {"code", "message", "setting", "fields"}


def _encoded_forms(secret):
    """The byte strings under which `secret` could appear in a response."""
    forms = {secret.encode("utf-8")}
    # JSON may escape non-ASCII characters or quotes inside the value.
    forms.add(json.dumps(secret, ensure_ascii=True)[1:-1].encode("ascii"))
    forms.add(json.dumps(secret, ensure_ascii=False)[1:-1].encode("utf-8"))
    return forms


def _response_body(response):
    """The body bytes; a streaming body is read once and put back for the caller."""
    if getattr(response, "streaming", False):
        body = b"".join(response.streaming_content)
        response.streaming_content = [body]
        return body
    return response.content


def _strings_in(value):
    """Every string inside a decoded JSON value, keys included."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for name, item in value.items():
            yield name
            yield from _strings_in(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings_in(item)


def assert_no_key_in_response(response, secrets):
    """Fail when any secret value appears in the body, a header or a cookie of `response`.

    Values shorter than MIN_SECRET_LENGTH are skipped. The failure message
    never prints the secret itself.
    """
    secrets = [s for s in set(secrets) if isinstance(s, str) and len(s) >= MIN_SECRET_LENGTH]
    if not secrets:
        return
    body = _response_body(response)
    header_text = "\n".join(f"{name}: {value}" for name, value in response.headers.items())
    cookie_text = response.cookies.output() if response.cookies else ""
    decoded_strings = []
    try:
        decoded_strings = list(_strings_in(json.loads(body.decode("utf-8"))))
    except (UnicodeDecodeError, ValueError):
        # Not JSON: the byte checks below still apply.
        pass
    for index, secret in enumerate(secrets):
        label = f"secret #{index} ({len(secret)} characters)"
        for form in _encoded_forms(secret):
            assert form not in body, f"A key value ({label}) appears in the response body."
        assert secret not in header_text, f"A key value ({label}) appears in a response header."
        assert secret not in cookie_text, f"A key value ({label}) appears in a response cookie."
        for text in decoded_strings:
            assert secret not in text, f"A key value ({label}) appears in the decoded JSON body."


def assert_error_envelope(response, status, code):
    """Check the error envelope of plan section 6 and return its `error` object."""
    assert response.status_code == status, response.content[:500]
    assert response["Content-Type"].startswith("application/json")
    payload = json.loads(response.content.decode("utf-8"))
    assert set(payload) == {"error"}, payload
    error = payload["error"]
    assert set(error) == ENVELOPE_FIELDS, error
    assert error["code"] == code
    assert isinstance(error["message"], str) and error["message"].strip()
    assert error["setting"] is None or isinstance(error["setting"], str)
    assert error["fields"] is None or isinstance(error["fields"], dict)
    return error


class ConfiguredApi:
    """The API test client bound to a temporary home whose `.env` the test writes."""

    def __init__(self, home, client, django_settings):
        self.home = home
        self.client = client
        self._settings = django_settings
        self._secrets = {FAKE_TEXT_KEY, FAKE_IMAGE_KEY}
        self._writes = 0

    @property
    def env_path(self):
        return self.home / ".env"

    @property
    def secrets(self):
        """Every value the responses are checked against."""
        return frozenset(self._secrets)

    def add_secret(self, value):
        """Also check responses for `value` (for example a key pasted into a provider setting)."""
        self._secrets.add(value)

    def configure(self, settings=None, *, text=None, secrets=()):
        """Write `.env` from a mapping or from raw text and return its path.

        Values of key settings are recorded as secrets; so is each value in
        `secrets`. Each write moves the modification time forward, so a change
        is seen on any file system.
        """
        if (settings is None) == (text is None):
            raise ValueError("Pass either settings or text.")
        if settings is not None:
            for name in KEY_SETTINGS:
                if settings.get(name):
                    self._secrets.add(settings[name])
            text = env_text(settings)
        for value in secrets:
            self._secrets.add(value)
        path = write_env(self.home, text)
        self._writes += 1
        mtime = time.time_ns() + self._writes * 10_000_000_000
        os.utime(path, ns=(mtime, mtime))
        return path

    def remove_configuration(self):
        """Delete `.env`, so the configuration reads as empty."""
        if self.env_path.exists():
            self.env_path.unlink()

    def set_running_port(self, port):
        """Pretend the server was started on `port` (the Django setting read once at startup)."""
        from django.conf import settings as current

        assert hasattr(current, RUNNING_PORT_SETTING), (
            f"Django settings must define {RUNNING_PORT_SETTING}: the port read once at startup "
            "(plan section 8)."
        )
        setattr(self._settings, RUNNING_PORT_SETTING, port)

    def request(self, method, path, data=None, **extra):
        """Send a request and return the response after checking it holds no key."""
        call = getattr(self.client, method.lower())
        if data is None:
            response = call(path, **extra)
        else:
            response = call(path, data, format="json", **extra)
        assert_no_key_in_response(response, self._secrets)
        return response

    def get(self, path, **extra):
        return self.request("GET", path, **extra)


@pytest.fixture
def configured_api(monkeypatch, tmp_path, settings):
    """A ConfiguredApi on a temporary home with no `.env` yet and a cleared environment."""
    from rest_framework.test import APIClient

    for name in list(os.environ):
        if is_project_variable(name):
            monkeypatch.delenv(name, raising=False)
    home = tmp_path / "api-home"
    (home / "data").mkdir(parents=True)
    monkeypatch.setenv("CARDFACTORY_HOME", str(home))
    return ConfiguredApi(home, APIClient(), settings)
