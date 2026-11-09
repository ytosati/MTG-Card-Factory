"""Watchdog that stops the application when no tab is left (see spec RN-41).

Details: specs/plan.md, section 9.5, step 8. Only the launcher creates, arms
and installs a watchdog; with none installed, a heartbeat does nothing.
"""

import threading
import time

# Window for the first heartbeat after the launcher opens the browser.
FIRST_HEARTBEAT_SECONDS = 120
# Window after the last heartbeat; a background tab may send one only every minute.
IDLE_SECONDS = 180
CHECK_INTERVAL_SECONDS = 5

_current = None


class Watchdog:
    """Calls `stop` once when no first heartbeat or no further heartbeat arrives in time."""

    def __init__(self, stop, clock=time.monotonic):
        self._stop = stop
        self._clock = clock
        self._lock = threading.Lock()
        self._armed_at = None
        self._last_heartbeat = None
        self._stopped = False

    def arm(self):
        """Start the window for the first heartbeat."""
        with self._lock:
            self._armed_at = self._clock()

    def heartbeat(self):
        """Record a heartbeat from a tab."""
        with self._lock:
            self._last_heartbeat = self._clock()

    def check(self):
        """Call `stop` when the stop time is reached; never more than once."""
        with self._lock:
            if self._stopped or not self._expired():
                return
            self._stopped = True
        self._stop()

    def start(self):
        """Run `check()` every CHECK_INTERVAL_SECONDS on a daemon thread."""
        thread = threading.Thread(target=self._loop, name="card-factory-watchdog", daemon=True)
        thread.start()
        return thread

    def _loop(self):
        while not self._stopped:
            time.sleep(CHECK_INTERVAL_SECONDS)
            self.check()

    def _expired(self):
        if self._armed_at is None:
            return False
        now = self._clock()
        if self._last_heartbeat is not None:
            return now - self._last_heartbeat >= IDLE_SECONDS
        return now - self._armed_at >= FIRST_HEARTBEAT_SECONDS


def install(watchdog):
    """Register the launcher's watchdog, so API heartbeats reach it."""
    global _current
    _current = watchdog


def uninstall():
    """Remove the registered watchdog."""
    global _current
    _current = None


def current():
    """The registered watchdog, or None."""
    return _current


def heartbeat():
    """Forward a heartbeat to the registered watchdog; nothing happens with none registered."""
    watchdog = _current
    if watchdog is not None:
        watchdog.heartbeat()
