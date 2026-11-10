"""Counted watchdog holds for running jobs (task T13, spec RN-41, CA-70).

Extends `core.watchdog` (T8, see tests/test_watchdog.py) with:

    class Watchdog:
        def hold(self): ...      one more running job; while any hold is active, never stops
        def release(self): ...   one job ended; after the last release the watchdog stops
                                 IDLE_SECONDS (180 s) after the later of the last
                                 heartbeat and that release

    def hold(): ...      forwards to current().hold(); does nothing with no watchdog
    def release(): ...   forwards to current().release(); does nothing with no watchdog

Time comes from a fake clock; nothing sleeps.
"""

import pytest

from tests.job_helpers import FakeClock, StopRecorder, run_checks


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


def test_t13_rn41_no_stop_while_a_hold_is_active(watchdog, clock, stop):
    """RN-41 / CA-70 / T13: a job runs with no tab open (no heartbeat for a long time): no stop while held."""
    watchdog.arm()
    watchdog.heartbeat()
    watchdog.hold()

    run_checks(watchdog, clock, 3600)

    assert stop.calls == 0


def test_t13_rn41_hold_also_covers_the_first_heartbeat_window(watchdog, clock, stop):
    """RN-41 / T13: a hold taken before any tab connects keeps it running past the 120 s window."""
    watchdog.arm()
    watchdog.hold()

    run_checks(watchdog, clock, 600)

    assert stop.calls == 0


def test_t13_rn41_hold_taken_after_the_idle_window_passed_unchecked_prevents_the_stop(watchdog, clock, stop):
    """RN-41 / T13: a hold taken before the next check keeps the watchdog from stopping."""
    watchdog.arm()
    watchdog.heartbeat()
    clock.advance(400)
    watchdog.hold()

    run_checks(watchdog, clock, 600)

    assert stop.calls == 0


def test_t13_rn41_no_stop_while_one_of_two_holds_remains(watchdog, clock, stop):
    """RN-41 / CA-70 / T13: holds are counted: releasing one of two keeps the watchdog held."""
    watchdog.arm()
    watchdog.heartbeat()
    watchdog.hold()
    watchdog.hold()
    run_checks(watchdog, clock, 300)

    watchdog.release()
    run_checks(watchdog, clock, 3600)

    assert stop.calls == 0


def test_t13_rn41_stops_180_seconds_after_the_last_release_with_no_heartbeat(watchdog, clock, stop):
    """RN-41 / CA-70 / T13: the last hold released with no heartbeat since: stop 180 s after the release."""
    watchdog.arm()
    watchdog.heartbeat()
    watchdog.hold()
    run_checks(watchdog, clock, 900)

    watchdog.release()
    run_checks(watchdog, clock, 179, step=1)
    assert stop.calls == 0

    clock.advance(1)
    watchdog.check()
    assert stop.calls == 1


def test_t13_rn41_release_with_no_heartbeat_ever_waits_180_seconds_not_120(watchdog, clock, stop):
    """RN-41 / T13: no tab ever connected: after the release the 180 s rule applies, not the first-heartbeat window."""
    watchdog.arm()
    watchdog.hold()
    run_checks(watchdog, clock, 500)

    watchdog.release()
    run_checks(watchdog, clock, 179, step=1)
    assert stop.calls == 0

    clock.advance(1)
    watchdog.check()
    assert stop.calls == 1


def test_t13_rn41_stop_counts_from_the_later_release_of_two_holds(watchdog, clock, stop):
    """RN-41 / CA-70 / T13: two jobs end at different times: the stop is 180 s after the second release."""
    watchdog.arm()
    watchdog.heartbeat()
    watchdog.hold()
    watchdog.hold()
    run_checks(watchdog, clock, 100)
    watchdog.release()
    run_checks(watchdog, clock, 100)

    watchdog.release()
    run_checks(watchdog, clock, 179, step=1)
    assert stop.calls == 0

    clock.advance(1)
    watchdog.check()
    assert stop.calls == 1


def test_t13_rn41_heartbeat_after_the_release_moves_the_stop(watchdog, clock, stop):
    """RN-41 / T13: a heartbeat later than the release counts: the stop is 180 s after that heartbeat."""
    watchdog.arm()
    watchdog.heartbeat()
    watchdog.hold()
    run_checks(watchdog, clock, 300)
    watchdog.release()

    run_checks(watchdog, clock, 100)
    watchdog.heartbeat()
    run_checks(watchdog, clock, 179, step=1)
    assert stop.calls == 0

    clock.advance(1)
    watchdog.check()
    assert stop.calls == 1


def test_t13_rn41_heartbeats_after_the_release_keep_it_running(watchdog, clock, stop):
    """RN-41 / T13: after the job ends, an open tab keeps the application running as before."""
    watchdog.arm()
    watchdog.heartbeat()
    watchdog.hold()
    run_checks(watchdog, clock, 300)
    watchdog.release()

    for _ in range(40):
        watchdog.heartbeat()
        run_checks(watchdog, clock, 15)

    assert stop.calls == 0


def test_t13_rn41_a_new_hold_after_a_release_holds_again(watchdog, clock, stop):
    """RN-41 / T13: a job that starts after another ended holds the watchdog again."""
    watchdog.arm()
    watchdog.heartbeat()
    watchdog.hold()
    watchdog.release()
    run_checks(watchdog, clock, 100)

    watchdog.hold()
    run_checks(watchdog, clock, 1000)

    assert stop.calls == 0


def test_t13_rn41_stop_is_still_called_once_after_holds(watchdog, clock, stop):
    """RN-41 / T13: after the stop that follows a release, the callback is never called again."""
    watchdog.arm()
    watchdog.hold()
    watchdog.release()
    run_checks(watchdog, clock, 180)
    assert stop.calls == 1

    watchdog.hold()
    watchdog.release()
    run_checks(watchdog, clock, 600)

    assert stop.calls == 1


def test_t13_rn41_module_hold_and_release_do_nothing_with_no_watchdog():
    """RN-41 / T13: with no watchdog registered (runserver, tests), a job's hold and release are no-ops."""
    import core.watchdog

    core.watchdog.uninstall()

    core.watchdog.hold()
    core.watchdog.release()

    assert core.watchdog.current() is None


def test_t13_rn41_module_hold_and_release_reach_the_registered_watchdog(clock, stop):
    """RN-41 / CA-70 / T13: the module-level hold and release reach the watchdog the launcher registered."""
    import core.watchdog
    from core.watchdog import Watchdog

    watchdog = Watchdog(stop=stop, clock=clock)
    core.watchdog.install(watchdog)
    try:
        watchdog.arm()
        watchdog.heartbeat()
        core.watchdog.hold()
        run_checks(watchdog, clock, 1000)
        assert stop.calls == 0

        core.watchdog.release()
        run_checks(watchdog, clock, 179, step=1)
        assert stop.calls == 0
        clock.advance(1)
        watchdog.check()
        assert stop.calls == 1
    finally:
        core.watchdog.uninstall()
