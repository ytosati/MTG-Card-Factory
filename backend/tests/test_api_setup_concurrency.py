"""GET /api/setup polled from two tabs at once (task T22, spec RN-28).

Two concurrent GETs with an empty listing cache share one listing read: the
second waits for the first instead of asking the data source again. The
requests run on real threads with their own database connections, so the
database is used with `transaction=True`. No test touches the network.
"""

import threading

import pytest
from django.db import connections

from tests.catalog_build_helpers import LISTING_URL, FakeDataSource, bulk_bytes
from tests.config_files import full_text_settings
from tests.configured_api import configured_api  # noqa: F401 (fixture)
from tests.setup_api_helpers import SETUP_URL, SetupEnvironment, clear_listing_cache

pytestmark = pytest.mark.django_db(transaction=True)

WAIT_SECONDS = 10.0
# Time given to the second request to reach the shared read before the first one is released.
OVERLAP_SECONDS = 0.5


class _BlockingListing:
    """An `on_request` hook: the first listing request waits until the test releases it."""

    def __init__(self):
        self.entered = threading.Event()
        self.release = threading.Event()
        self._first = True
        self._lock = threading.Lock()

    def __call__(self, url):
        if url != LISTING_URL:
            return
        with self._lock:
            first, self._first = self._first, False
        if first:
            self.entered.set()
            assert self.release.wait(WAIT_SECONDS), "The test never released the listing."


def _get_setup(results, index):
    from rest_framework.test import APIClient

    try:
        results[index] = APIClient().get(SETUP_URL)
    except BaseException as error:  # reported by the test thread
        results[index] = error
    finally:
        connections.close_all()


def test_t22_rn28_concurrent_polls_share_one_listing_read(configured_api, monkeypatch):
    """RN-28 / T22: two GET /api/setup at once with an empty cache make one listing request, and both
    answer the download size."""
    configured_api.configure(full_text_settings())
    environment = SetupEnvironment(monkeypatch)
    blocker = _BlockingListing()
    environment.use_source(FakeDataSource(on_request=blocker))
    results = [None, None]
    first = threading.Thread(target=_get_setup, args=(results, 0))
    second = threading.Thread(target=_get_setup, args=(results, 1))
    try:
        first.start()
        assert blocker.entered.wait(WAIT_SECONDS), "The first poll never asked for the listing."
        second.start()
        second.join(OVERLAP_SECONDS)
        blocker.release.set()
        first.join(WAIT_SECONDS)
        second.join(WAIT_SECONDS)
    finally:
        blocker.release.set()
        clear_listing_cache()

    assert not first.is_alive() and not second.is_alive()
    for response in results:
        assert not isinstance(response, BaseException), response
        assert response.status_code == 200, response.content[:500]
        assert response.json()["download_size"] == len(bulk_bytes())
    assert environment.source.urls().count(LISTING_URL) == 1
