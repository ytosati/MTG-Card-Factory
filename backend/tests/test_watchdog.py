"""Watchdog that stops the application when no tab is left (task T8, spec RN-41, CA-47).

Details: specs/plan.md, section 9.5, step 8. Only the launcher creates and arms
the watchdog (when it opens the browser); `runserver` and the tests never stop
on their own. Holds for running jobs come with T13 and are not tested here.

API under test, module `core.watchdog`:

    FIRST_HEARTBEAT_SECONDS = 120   window for the first heartbeat after arm()
    IDLE_SECONDS = 180              window after the last heartbeat
    CHECK_INTERVAL_SECONDS = 5      period of the background check loop

    class Watchdog:
        def __init__(self, stop, clock=time.monotonic): ...
            `stop` is a callable with no arguments; `clock` returns seconds as a
            float (monotonic). Creating it neither arms it nor starts a thread.
        def arm(self): ...
            Starts the window for the first heartbeat at clock().
        def heartbeat(self): ...
            Records clock() as the time of the last heartbeat.
        def check(self): ...
            Calls `stop` when the stop time is reached: armed with no heartbeat
            and clock() - armed_at >= FIRST_HEARTBEAT_SECONDS, or
            clock() - last_heartbeat >= IDLE_SECONDS. `stop` is called at most
            once over the life of the watchdog. Before arm(), never stops.
        def start(self): ...
            Starts a daemon thread that calls check() every
            CHECK_INTERVAL_SECONDS (thin; not exercised here).

    def install(watchdog): ...   the launcher registers its watchdog
    def uninstall(): ...         removes the registered one (tests)
    def current(): ...           the registered watchdog, or None
    def heartbeat(): ...         forwards to current().heartbeat(); does nothing
                                 when no watchdog is registered

The heartbeat endpoint (tests/test_api_instance.py) calls `core.watchdog.heartbeat()`.
Time comes from a fake clock; nothing sleeps.
"""

import pytest


class FakeClock:
    """A monotonic clock the test moves by hand."""

    def __init__(self, start=1000.0):
        self.now = float(start)

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class StopRecorder:
    """The stop callback: counts its calls."""

    def __init__(self):
        self.calls = 0

    def __call__(self):
        self.calls += 1


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def stop():
    return StopRecorder()


@pytest.fixture
def watchdog(clock, stop):
    from core.watchdog import Watchdog

    return Watchdog(stop=stop, clock=clock)


def _run_checks(watchdog, clock, seconds, step=5):
    """Advance the clock by `seconds` in steps of the check interval, checking after each step."""
    elapsed = 0
    while elapsed < seconds:
        move = min(step, seconds - elapsed)
        clock.advance(move)
        elapsed += move
        watchdog.check()


def test_t8_rn41_timing_constants_match_the_plan():
    """RN-41 / T8: 120 s for the first heartbeat, 180 s after the last one, a check every 5 s."""
    import core.watchdog

    assert core.watchdog.FIRST_HEARTBEAT_SECONDS == 120
    assert core.watchdog.IDLE_SECONDS == 180
    assert core.watchdog.CHECK_INTERVAL_SECONDS == 5


def test_t8_rn41_stops_120_seconds_after_arming_with_no_heartbeat(watchdog, clock, stop):
    """RN-41 / CA-47 / T8: no tab connects within two minutes of the start: the watchdog stops at 120 s."""
    watchdog.arm()

    _run_checks(watchdog, clock, 119, step=1)
    assert stop.calls == 0

    clock.advance(1)
    watchdog.check()
    assert stop.calls == 1


def test_t8_rn41_does_not_stop_before_it_is_armed(watchdog, clock, stop):
    """RN-41 / T8: the window starts when the launcher arms it (browser opened), so a long
    upgrade before arming does not use it up."""
    _run_checks(watchdog, clock, 600)
    assert stop.calls == 0

    watchdog.arm()
    _run_checks(watchdog, clock, 115)
    assert stop.calls == 0


def test_t8_rn41_no_stop_while_heartbeats_arrive_every_15_seconds(watchdog, clock, stop):
    """RN-41 / CA-47 / T8: an open tab (a heartbeat every 15 s) keeps the application running."""
    watchdog.arm()
    clock.advance(10)
    for _ in range(100):
        watchdog.heartbeat()
        _run_checks(watchdog, clock, 15)

    assert stop.calls == 0


def test_t8_rn41_no_stop_with_heartbeat_gaps_of_60_seconds(watchdog, clock, stop):
    """RN-41 / CA-47 / T8: a background tab throttled to one heartbeat a minute does not stop it."""
    watchdog.arm()
    clock.advance(60)
    for _ in range(20):
        watchdog.heartbeat()
        _run_checks(watchdog, clock, 60)

    assert stop.calls == 0


def test_t8_rn41_first_heartbeat_late_in_the_window_keeps_it_running(watchdog, clock, stop):
    """RN-41 / T8: a first heartbeat at 115 s ends the first-heartbeat window; the 180 s rule applies after it."""
    watchdog.arm()
    _run_checks(watchdog, clock, 115)
    watchdog.heartbeat()

    _run_checks(watchdog, clock, 175)
    assert stop.calls == 0


def test_t8_rn41_stops_180_seconds_after_the_last_heartbeat(watchdog, clock, stop):
    """RN-41 / CA-47 / T8: the last tab closed: the watchdog stops 180 s after the last heartbeat."""
    watchdog.arm()
    clock.advance(30)
    watchdog.heartbeat()
    _run_checks(watchdog, clock, 15)
    watchdog.heartbeat()

    _run_checks(watchdog, clock, 179, step=1)
    assert stop.calls == 0

    clock.advance(1)
    watchdog.check()
    assert stop.calls == 1


def test_t8_rn41_stop_callback_is_called_once(watchdog, clock, stop):
    """RN-41 / T8: after the stop, more checks and even a late heartbeat never call the callback again."""
    watchdog.arm()
    _run_checks(watchdog, clock, 120)
    assert stop.calls == 1

    _run_checks(watchdog, clock, 600)
    watchdog.heartbeat()
    _run_checks(watchdog, clock, 600)

    assert stop.calls == 1


def test_t8_rn41_stop_callback_is_called_once_after_idle_stop(watchdog, clock, stop):
    """RN-41 / T8: the idle stop (180 s after a heartbeat) also fires only once."""
    watchdog.arm()
    watchdog.heartbeat()
    _run_checks(watchdog, clock, 180)
    _run_checks(watchdog, clock, 300)

    assert stop.calls == 1


def test_t8_rn41_heartbeat_with_no_watchdog_does_nothing():
    """RN-41 / T8: with no watchdog registered (runserver, tests), a heartbeat is a no-op."""
    import core.watchdog

    core.watchdog.uninstall()

    assert core.watchdog.current() is None
    core.watchdog.heartbeat()


def test_t8_rn41_registered_watchdog_receives_heartbeats(clock, stop):
    """RN-41 / T8: the module-level heartbeat reaches the watchdog the launcher registered."""
    import core.watchdog
    from core.watchdog import Watchdog

    watchdog = Watchdog(stop=stop, clock=clock)
    core.watchdog.install(watchdog)
    try:
        assert core.watchdog.current() is watchdog
        watchdog.arm()
        _run_checks(watchdog, clock, 100)
        core.watchdog.heartbeat()
        _run_checks(watchdog, clock, 100)
        assert stop.calls == 0
    finally:
        core.watchdog.uninstall()

    assert core.watchdog.current() is None


def test_t8_rn41_loading_django_registers_no_watchdog():
    """RN-41 / T8: only the launcher creates the watchdog; the settings and app loading never do."""
    import django.apps

    import core.watchdog

    assert django.apps.apps.ready
    assert core.watchdog.current() is None
