"""Shared fixtures of the end-to-end suite (specs/plan.md, section 14; specs/tasks.md, "Delivery method").

Each flow gets a temporary application home with its own configuration file,
the fictional data source behind the fake transport, a fake free disk space,
the real job runner on a thread pool, and the network guard of the whole
session. The fake text and image provider joins these fixtures with
Milestone 3 (task T35); no flow of Milestone 2 calls a provider.
"""

import socket
from concurrent.futures import ThreadPoolExecutor

import pytest

from tests.config_files import DEFAULT_PORT, full_text_settings
from tests.configured_api import configured_api  # noqa: F401 (fixture)
from tests.e2e.helpers import E2EApp
from tests.job_helpers import runner_installed
from tests.network_guard import NetworkAccessBlocked
from tests.setup_api_helpers import SetupEnvironment, clear_listing_cache


@pytest.fixture(autouse=True)
def network_guarded():
    """Every flow runs with outgoing connections blocked (see spec RN-29)."""
    with pytest.raises(NetworkAccessBlocked):
        socket.create_connection(("data.scryfall.io", 443), timeout=1)


@pytest.fixture
def real_runner(transactional_db):
    """The real JobRunner on a thread pool, installed for the flow and shut down before the database is flushed."""
    from core.jobs import MAX_WORKERS

    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="e2e-job")
    try:
        with runner_installed(executor) as runner:
            yield runner
    finally:
        executor.shutdown(wait=True)


@pytest.fixture
def app(configured_api, monkeypatch, real_runner):  # noqa: F811 (fixture)
    """The application on a temporary home with an empty data folder and a valid configuration."""
    configured_api.configure(full_text_settings())
    configured_api.set_running_port(DEFAULT_PORT)
    environment = SetupEnvironment(monkeypatch)
    try:
        yield E2EApp(configured_api, environment, real_runner, DEFAULT_PORT)
    finally:
        clear_listing_cache()
