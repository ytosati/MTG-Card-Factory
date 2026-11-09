"""Tests for the launcher startup sequence (task T74; plan section 9.5, steps 1 to 8).

Covers RN-29, RN-40, RN-41, RN-42, RN-47, CA-20, CA-47, CA-48 and CA-53 with fakes:
no real browser, no real server, no network.

Launcher API under test (`launcher/launch.py`):

    main(home, *, deps) -> int

`home` is the Card Factory folder (a string). `deps` is any object with these
attributes; `launch.default_deps()` returns the real ones:

    run_checks(home, show_message) -> bool      T73 checks (startup_checks.run_checks)
    show_message(problem, fix)                  message box (startup_checks.message_box)
    acquire_lock(path) -> handle or None        takes data/launcher.lock; None when held
    port_is_free(port) -> bool                  exclusive bind check; True skips the probe
    load_settings() -> settings                 Django settings; `.RUNNING_PORT` is the port
    http_connection(host, port, timeout=...)    http.client.HTTPConnection-like, for the probe
    upgrade_database()                          T72 (core.startup.upgrade_database)
    start_server(stop_event) -> handle          binds (StartupError on failure), serves in a
                                                thread until `stop_event` is set; the handle
                                                has join(timeout=None) and is_alive()
    open_browser(url)                           default browser (webbrowser.open)
    make_watchdog(stop) -> watchdog             T8 (core.startup.Watchdog), arm() and start()
    install_watchdog(watchdog)                  T8 (core.startup.install)
    sleep(seconds), clock() -> float            for the 30-second wait for instance.json

The launcher writes `data/instance.json` itself (its port and process id) and
reads it back in a second start; the tests never assume its key names: a first
launcher run writes it, and the second-start tests reuse that file.
"""

import http.client
import importlib.util
import json
import os
import sys
import threading
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

from core.startup import StartupError

REPO_ROOT = Path(__file__).resolve().parents[2]
INSTANCE_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "instance.json"

DEFAULT_PORT = 47821
FAKE_KEY = "sk-fake-0000-not-a-real-key-launcher-test"


def _launch():
    import launch

    return launch


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeResponse:
    def __init__(self, status, body, content_type="application/json"):
        self.status = status
        self.reason = "OK" if status == 200 else "Other"
        self._body = body
        self._content_type = content_type

    def read(self, *args):
        return self._body

    def getheader(self, name, default=None):
        if name.lower() == "content-type":
            return self._content_type
        return default

    def close(self):
        pass


class ProbeAnswer:
    """What the fake port answers: refused (nothing listens), a timeout, or a response."""

    def __init__(self, kind, status=200, body=b"", content_type="application/json"):
        self.kind = kind
        self.status = status
        self.body = body
        self.content_type = content_type

    @classmethod
    def refused(cls):
        return cls("refused")

    @classmethod
    def timeout(cls):
        return cls("timeout")

    @classmethod
    def instance(cls, home):
        payload = json.loads(INSTANCE_FIXTURE.read_text(encoding="utf-8"))
        if home is not None:
            payload["home"] = home
        return cls("response", body=json.dumps(payload).encode("utf-8"))

    @classmethod
    def response(cls, status, body, content_type="application/json"):
        return cls("response", status=status, body=body, content_type=content_type)


class FakeConnectionFactory:
    """Stands in for http.client.HTTPConnection and records how it was used."""

    def __init__(self, answer, log):
        self.answer = answer
        self.log = log
        self.created = []
        self.requests = []

    def __call__(self, host, port=None, timeout=None, **kwargs):
        self.log.append("probe")
        self.created.append({"host": host, "port": port, "timeout": timeout})
        return _FakeConnection(self)


class _FakeConnection:
    def __init__(self, factory):
        self._factory = factory

    def _fail_if_refused(self):
        if self._factory.answer.kind == "refused":
            raise ConnectionRefusedError(10061, "No connection could be made (fake)")

    def connect(self):
        self._fail_if_refused()

    def request(self, method, url, body=None, headers=None, **kwargs):
        self._factory.requests.append((method, url))
        self._fail_if_refused()

    def getresponse(self):
        answer = self._factory.answer
        self._fail_if_refused()
        if answer.kind == "timeout":
            raise TimeoutError("timed out (fake)")
        return FakeResponse(answer.status, answer.body, answer.content_type)

    def close(self):
        pass


class FakeServerHandle:
    """`error` set: the serving thread already ended with that exception after the bind."""

    def __init__(self, stop_event, error=None):
        self.stop_event = stop_event
        self.error = error

    def join(self, timeout=None):
        if self.error is not None:
            return
        # Bounded, so a launcher that never sets the event cannot hang the suite.
        self.stop_event.wait(5 if timeout is None else min(timeout, 5))

    def is_alive(self):
        return self.error is None and not self.stop_event.is_set()


class FakeWatchdog:
    """Calls its stop callback from a thread as soon as it is started, as a fired watchdog does."""

    def __init__(self, stop, deps):
        self.stop = stop
        self._deps = deps
        self.armed = False
        self.started = False

    def arm(self):
        self._deps.log.append("watchdog.arm")
        self.armed = True

    def start(self):
        self._deps.log.append("watchdog.start")
        self.started = True
        thread = threading.Thread(target=self._fire, daemon=True)
        thread.start()
        return thread

    def heartbeat(self):
        pass

    def check(self):
        pass

    def _fire(self):
        self._deps.log.append("watchdog.stop")
        self.stop()


class FakeDeps:
    """Every collaborator of the launcher, recording calls into one ordered log."""

    def __init__(self, home, port=DEFAULT_PORT, probe=None, lock_held=False, checks_pass=True, port_free=False):
        self.home = home
        self.port_free = port_free
        self.port = port
        self.lock_held = lock_held
        self.checks_pass = checks_pass
        self.log = []
        self.messages = []
        self.browser_urls = []
        self.lock_paths = []
        self.server_stop_events = []
        self.watchdogs = []
        self.installed = []
        self.slept = 0.0
        self.now = 1000.0
        self.instance_file_at_serve = None
        self.instance_file_at_browser = None
        self.instance_text_at_browser = None
        self.on_sleep = None
        self.failures = {}
        self.server_error = None
        self.http_connection = FakeConnectionFactory(probe or ProbeAnswer.refused(), self.log)

    def _maybe_fail(self, step):
        if step in self.failures:
            raise self.failures[step]

    def _instance_path(self):
        return Path(self.home) / "data" / "instance.json"

    def run_checks(self, home, show_message):
        self.log.append("checks")
        return self.checks_pass

    def show_message(self, problem, fix):
        self.log.append("message")
        self.messages.append((problem, fix))

    def acquire_lock(self, path):
        self.log.append("lock")
        self.lock_paths.append(os.fspath(path))
        if self.lock_held:
            return None
        return object()

    def port_is_free(self, port):
        self.log.append("port_is_free")
        return self.port_free

    def load_settings(self):
        self.log.append("settings")
        self._maybe_fail("settings")

        class Settings:
            RUNNING_PORT = self.port

        return Settings()

    def upgrade_database(self):
        self.log.append("upgrade")
        self._maybe_fail("upgrade")

    def start_server(self, stop_event):
        self.log.append("serve")
        self.instance_file_at_serve = self._instance_path().exists()
        self._maybe_fail("serve")
        self.server_stop_events.append(stop_event)
        return FakeServerHandle(stop_event, self.server_error)

    def open_browser(self, url):
        self.log.append("browser")
        self._maybe_fail("browser")
        self.browser_urls.append(url)
        path = self._instance_path()
        self.instance_file_at_browser = path.exists()
        if path.exists():
            self.instance_text_at_browser = path.read_text(encoding="utf-8")
        return True

    def make_watchdog(self, stop):
        self.log.append("watchdog.create")
        watchdog = FakeWatchdog(stop, self)
        self.watchdogs.append(watchdog)
        return watchdog

    def install_watchdog(self, watchdog):
        self.log.append("watchdog.install")
        self.installed.append(watchdog)

    def sleep(self, seconds):
        self.slept += seconds
        self.now += seconds
        if self.on_sleep is not None:
            self.on_sleep(self)

    def clock(self):
        return self.now


@pytest.fixture
def home(tmp_path):
    folder = tmp_path / "Card Factory"
    (folder / "data").mkdir(parents=True)
    (folder / ".env").write_text("LLM_PROVIDER=openai\n", encoding="utf-8")
    return str(folder)


def _message_text(deps):
    return "\n".join(f"{problem}\n{fix}" for problem, fix in deps.messages)


def _run(home, deps):
    return _launch().main(home, deps=deps)


def _instance_file_written_by_a_first_launcher(home, port):
    """Run a first launcher in `home` and return the data/instance.json text it wrote."""
    first = FakeDeps(home, port=port)
    _run(home, first)
    text = first.instance_text_at_browser
    assert text is not None, "the first launcher did not write data/instance.json before the browser"
    return text


def _place_instance_file(home, text):
    (Path(home) / "data" / "instance.json").write_text(text, encoding="utf-8")


def _assert_no_second_server(deps):
    assert "upgrade" not in deps.log
    assert "serve" not in deps.log
    assert deps.watchdogs == []


# ---------------------------------------------------------------------------
# Step 1: bootstrap in start.pyw
# ---------------------------------------------------------------------------


def test_rn40_bootstrap_sets_home_paths_and_null_streams(monkeypatch):
    """RN-40 / plan 9.5 step 1: start.pyw resolves the home from its own file, puts the code
    folder and launcher/ on sys.path, sets CARDFACTORY_HOME, and replaces missing streams."""
    monkeypatch.setattr(sys, "path", [p for p in sys.path if p not in {str(REPO_ROOT / "backend"), str(REPO_ROOT / "launcher")}])
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    monkeypatch.delenv("CARDFACTORY_HOME", raising=False)
    path = REPO_ROOT / "launcher" / "start.pyw"
    loader = SourceFileLoader("cardfactory_start_pyw_under_test", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    try:
        loader.exec_module(module)
        assert os.path.normcase(os.path.realpath(os.environ["CARDFACTORY_HOME"])) == os.path.normcase(
            os.path.realpath(REPO_ROOT)
        )
        normalized = {os.path.normcase(os.path.realpath(p)) for p in sys.path if p}
        assert os.path.normcase(os.path.realpath(REPO_ROOT / "backend")) in normalized
        assert os.path.normcase(os.path.realpath(REPO_ROOT / "launcher")) in normalized
        assert sys.stdout is not None and sys.stderr is not None
        sys.stdout.write("discarded")
    finally:
        for stream in (sys.stdout, sys.stderr):
            if stream is not None:
                stream.close()


# ---------------------------------------------------------------------------
# Steps 2 to 8: the order of the sequence
# ---------------------------------------------------------------------------


def test_rn41_rn42_ca47_steps_run_in_order(home):
    """RN-41 / RN-42 / CA-47: checks, lock, settings, probe, upgrade, bind and serve,
    data/instance.json, browser on http://127.0.0.1:<port>/, watchdog armed."""
    deps = FakeDeps(home)

    result = _run(home, deps)

    assert result == 0
    assert deps.messages == []
    order = ["checks", "lock", "settings", "probe", "upgrade", "serve", "browser", "watchdog.arm"]
    positions = [deps.log.index(step) for step in order]
    assert positions == sorted(positions), deps.log
    assert deps.log.index("watchdog.start") > deps.log.index("browser")
    assert os.path.normcase(deps.lock_paths[0]) == os.path.normcase(os.path.join(home, "data", "launcher.lock"))
    assert deps.instance_file_at_serve is False
    assert deps.instance_file_at_browser is True
    assert deps.browser_urls == [f"http://127.0.0.1:{DEFAULT_PORT}/"]
    assert len(deps.watchdogs) == 1 and deps.installed == deps.watchdogs
    assert deps.watchdogs[0].armed and deps.watchdogs[0].started


def test_rn41_instance_file_holds_the_running_port_and_process_id(home):
    """RN-41 / plan 9.5 step 7: data/instance.json is written with the port and the process id."""
    deps = FakeDeps(home, port=50123)

    _run(home, deps)

    values = json.loads(deps.instance_text_at_browser).values()
    assert 50123 in values
    assert os.getpid() in values


def test_rn40_failed_check_stops_before_the_lock(home):
    """RN-40: a failed prerequisite check (already shown by run_checks) stops the launcher."""
    deps = FakeDeps(home, checks_pass=False)

    result = _run(home, deps)

    assert result != 0
    assert deps.log == ["checks"]


def test_rn29_probe_uses_http_client_on_loopback_with_two_second_timeout(home):
    """RN-29 / RN-47: the probe asks GET /api/instance on 127.0.0.1 at the running port,
    with a 2-second timeout; the default connection is http.client (never urllib)."""
    deps = FakeDeps(home, port=51000)

    _run(home, deps)

    created = deps.http_connection.created
    assert created and created[0]["host"] == "127.0.0.1"
    assert created[0]["port"] == 51000
    assert created[0]["timeout"] == 2
    assert deps.http_connection.requests[0] == ("GET", "/api/instance")
    assert _launch().default_deps().http_connection is http.client.HTTPConnection
    source = (REPO_ROOT / "launcher" / "launch.py").read_text(encoding="utf-8")
    assert "urllib" not in source


def test_rn41_default_deps_use_the_backend_and_t73_collaborators():
    """RN-40 / RN-41 / RN-42: the real collaborators are the T7, T8, T72 and T73 functions."""
    import core.startup
    import startup_checks

    deps = _launch().default_deps()

    assert deps.run_checks is startup_checks.run_checks
    assert deps.show_message is startup_checks.message_box
    assert deps.upgrade_database is core.startup.upgrade_database
    assert deps.make_watchdog is core.startup.Watchdog
    assert deps.install_watchdog is core.startup.install


# ---------------------------------------------------------------------------
# Step 3: second start (lock held)
# ---------------------------------------------------------------------------


def test_rn41_ca47_second_start_opens_a_tab_and_starts_no_server(home):
    """RN-41 / CA-47: with the lock held, a second start opens a tab of the running port and exits."""
    _place_instance_file(home, _instance_file_written_by_a_first_launcher(home, DEFAULT_PORT))
    deps = FakeDeps(home, lock_held=True, probe=ProbeAnswer.instance(home))

    _run(home, deps)

    assert deps.browser_urls == [f"http://127.0.0.1:{DEFAULT_PORT}/"]
    assert deps.messages == []
    _assert_no_second_server(deps)


def test_rn41_rn47_second_start_after_app_port_changed_uses_the_running_port(home):
    """RN-41 / RN-47: after APP_PORT changed, a second start opens a tab of the port in
    data/instance.json, not of the new setting."""
    _place_instance_file(home, _instance_file_written_by_a_first_launcher(home, 48000))
    deps = FakeDeps(home, port=49999, lock_held=True, probe=ProbeAnswer.instance(home))

    _run(home, deps)

    assert deps.browser_urls == ["http://127.0.0.1:48000/"]
    assert deps.messages == []
    _assert_no_second_server(deps)


def test_rn41_rn42_second_start_while_first_upgrades_waits_for_instance_file(home):
    """RN-41 / RN-42: while the first launcher upgrades, data/instance.json appears later;
    the second waits (under 30 seconds), then opens a tab of that port, with no server."""
    text = _instance_file_written_by_a_first_launcher(home, 48100)
    (Path(home) / "data" / "instance.json").unlink()
    deps = FakeDeps(home, lock_held=True, probe=ProbeAnswer.instance(home))
    sleeps = {"count": 0}

    def appear_after_a_while(fake):
        sleeps["count"] += 1
        if fake.slept >= 10 and not (Path(home) / "data" / "instance.json").exists():
            _place_instance_file(home, text)

    deps.on_sleep = appear_after_a_while

    _run(home, deps)

    assert sleeps["count"] > 0
    assert deps.slept <= 30
    assert deps.browser_urls == ["http://127.0.0.1:48100/"]
    assert deps.messages == []
    _assert_no_second_server(deps)


# ---------------------------------------------------------------------------
# Step 5: the port probe
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform != "win32", reason="case-insensitive paths are a Windows rule")
def test_rn41_rn47_same_home_other_case_and_trailing_separator_opens_a_tab(home):
    """RN-41 / RN-47: a Card Factory whose home is this one, written in another case and with
    a trailing separator, gets a tab; the launcher exits with no server of its own."""
    deps = FakeDeps(home, probe=ProbeAnswer.instance(home.upper() + os.sep))

    _run(home, deps)

    assert deps.browser_urls == [f"http://127.0.0.1:{DEFAULT_PORT}/"]
    assert deps.messages == []
    _assert_no_second_server(deps)


def test_rn47_ca53_another_home_on_the_port_names_app_port_and_another_card_factory(home):
    """RN-47 / CA-53: a Card Factory from another folder on the port → a message that names
    the port and APP_PORT and says another Card Factory uses it; no tab, no server."""
    deps = FakeDeps(home, probe=ProbeAnswer.instance(None))  # the fixture's home: C:\CardFactory

    _run(home, deps)

    text = _message_text(deps)
    assert len(deps.messages) == 1
    assert "APP_PORT" in text
    assert str(DEFAULT_PORT) in text
    assert "another card factory" in text.lower()
    assert deps.browser_urls == []
    _assert_no_second_server(deps)


@pytest.mark.parametrize(
    "answer",
    [
        pytest.param(ProbeAnswer.response(200, b"<html><body>Router login</body></html>", "text/html"), id="html"),
        pytest.param(ProbeAnswer.response(200, b"\xff\xfe\x00garbage{", "application/json"), id="not-json"),
        pytest.param(ProbeAnswer.response(200, b"[1, 2, 3]"), id="json-list"),
        pytest.param(ProbeAnswer.response(200, b'{"app": "other-tool", "home": "C:\\\\x"}'), id="other-app"),
        pytest.param(ProbeAnswer.response(404, b'{"detail": "Not found."}'), id="status-404"),
        pytest.param(ProbeAnswer.timeout(), id="timeout"),
    ],
)
def test_rn47_ca53_other_answer_or_timeout_names_app_port(home, answer):
    """RN-47 / CA-53: any answer that is not the instance JSON, or a timeout, gives a message
    that names the port and APP_PORT (not another Card Factory); no tab, no server."""
    deps = FakeDeps(home, probe=answer)

    _run(home, deps)

    text = _message_text(deps)
    assert len(deps.messages) == 1
    assert "APP_PORT" in text
    assert str(DEFAULT_PORT) in text
    assert "another card factory" not in text.lower()
    assert deps.browser_urls == []
    _assert_no_second_server(deps)


def test_rn47_free_port_skips_the_http_probe(home):
    """RN-47: when the exclusive bind check finds the port free, no HTTP connection is made
    and the start continues to the server."""
    deps = FakeDeps(home, port_free=True)

    result = _run(home, deps)

    assert result == 0
    assert deps.http_connection.created == []
    assert "port_is_free" in deps.log
    assert "serve" in deps.log
    assert deps.browser_urls == [f"http://127.0.0.1:{DEFAULT_PORT}/"]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("step", ["settings", "upgrade", "serve"])
def test_rn40_rn42_startup_error_is_a_message_box_with_problem_and_fix(home, step):
    """RN-40 / RN-42 / CA-48: a StartupError from the settings, the upgrade or the bind is shown
    as a message box with its problem and fix; no browser and no instance file follow."""
    problem = f"Fictional problem raised at the {step} step."
    fix = f"Fictional fix for the {step} step."
    deps = FakeDeps(home)
    deps.failures[step] = StartupError(problem, fix)

    result = _run(home, deps)

    assert result != 0
    assert deps.messages == [(problem, fix)]
    assert deps.browser_urls == []
    assert not (Path(home) / "data" / "instance.json").exists()
    assert deps.watchdogs == []


@pytest.mark.parametrize("step", ["settings", "upgrade", "serve"])
def test_rn40_unexpected_exception_shows_fixed_message_without_its_text(home, step):
    """RN-40: any other exception shows a fixed message pointing to data/logs/app.log and never
    the exception text (which could hold a key)."""
    deps = FakeDeps(home)
    deps.failures[step] = RuntimeError(f"boom with LLM_API_KEY={FAKE_KEY}")

    result = _run(home, deps)

    text = _message_text(deps)
    assert result != 0
    assert len(deps.messages) == 1
    assert "data/logs/app.log" in text.replace("\\", "/")
    assert FAKE_KEY not in text
    assert "boom" not in text
    assert "RuntimeError" not in text
    assert deps.browser_urls == []


def _fail_instance_write(home, deps):
    # A folder where the launcher writes its temporary instance file makes that write fail.
    (Path(home) / "data" / "instance.json.tmp").mkdir()


def _fail_browser(home, deps):
    deps.failures["browser"] = RuntimeError(f"browser failed with LLM_API_KEY={FAKE_KEY}")


@pytest.mark.parametrize(
    "make_fail",
    [pytest.param(_fail_instance_write, id="instance-write"), pytest.param(_fail_browser, id="browser")],
)
def test_rn40_rn41_failure_after_the_bind_stops_the_server(home, make_fail):
    """RN-40 / RN-41: a step that fails after the bind stops the server it started (no orphan
    server keeps the port after the launcher exits) and shows the fixed message."""
    deps = FakeDeps(home)
    make_fail(home, deps)

    result = _run(home, deps)

    assert result != 0
    assert len(deps.server_stop_events) == 1
    assert deps.server_stop_events[0].is_set()
    assert len(deps.messages) == 1
    text = _message_text(deps)
    assert "data/logs/app.log" in text.replace("\\", "/")
    assert FAKE_KEY not in text


@pytest.mark.parametrize(
    "error, expected",
    [
        pytest.param(
            StartupError("Fictional problem while serving.", "Fictional fix while serving."),
            ("Fictional problem while serving.", "Fictional fix while serving."),
            id="startup-error",
        ),
        pytest.param(RuntimeError(f"serving failed with LLM_API_KEY={FAKE_KEY}"), None, id="unexpected"),
    ],
)
def test_rn40_server_failing_after_the_bind_is_a_message_box(home, error, expected):
    """RN-40: when the server thread ends with an error after the bind, the launcher shows it
    (a StartupError with its problem and fix, anything else the fixed message) and fails."""
    deps = FakeDeps(home)
    deps.server_error = error

    result = _run(home, deps)

    assert result != 0
    assert len(deps.messages) == 1
    if expected is not None:
        assert deps.messages == [expected]
    else:
        text = _message_text(deps)
        assert "data/logs/app.log" in text.replace("\\", "/")
        assert FAKE_KEY not in text
        assert "serving failed" not in text


# ---------------------------------------------------------------------------
# Step 8: the watchdog stops the launcher
# ---------------------------------------------------------------------------


def test_rn41_ca47_watchdog_stop_sets_server_stop_event_and_launcher_exits(home):
    """RN-41 / CA-47: the watchdog's stop callback sets the server's stop event, and the
    launcher returns once the server has stopped."""
    deps = FakeDeps(home)

    result = _run(home, deps)

    assert result == 0
    assert "watchdog.stop" in deps.log
    assert len(deps.server_stop_events) == 1
    assert deps.server_stop_events[0].is_set()
