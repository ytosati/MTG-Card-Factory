"""Test helpers for the setup endpoints and the readiness gate (task T22).

Details: specs/plan.md, sections 6 (endpoints, readiness gate, error codes) and
7 (catalog version, all-or-nothing build). Every value below is fictional.

Seams used by the tests (none touches the network):

- the data source: `catalog.download.urllib_transport` is replaced with a
  `tests.catalog_build_helpers.FakeDataSource`, so the listing read by
  `GET /api/setup` and the build started by `POST /api/setup/build` both use it;
- the pause between download attempts: the `time` module seen by
  `catalog.download` is replaced with one whose `sleep` only records the call;
- the free disk space: `shutil.disk_usage` is replaced with `FakeDiskUsage`
  (the setup service reads it on the drive of the data folder when it answers);
- the listing cache: the setup service keeps the listing for the session
  because the screen polls; the tests empty it between tests through a function
  named `clear_listing_cache()` defined in a module of the `catalog`, `core` or
  `api` package.
"""

import importlib
import json
from contextlib import contextmanager
import pkgutil
import shutil
import time
from collections import namedtuple
from datetime import timedelta
from types import SimpleNamespace

from tests.catalog_build_helpers import LISTING_URL, ORACLE_URI, PUBLISHED_AT, FakeDataSource, FakeSleep

SETUP_URL = "/api/setup"
BUILD_URL = "/api/setup/build"
STATUS_URL = "/api/status"
JOBS_URL = "/api/jobs"

CODE_DATABASE_NOT_READY = "database_not_ready"
CODE_INSUFFICIENT_SPACE = "insufficient_space"
CODE_SOURCE_UNREACHABLE = "source_unreachable"

# The free disk space needed is the download size times this factor (downloads,
# database and the write-ahead log of the import).
EXPECTED_SPACE_FACTOR = 3

# More free space than any fictional build needs: 1 PB.
PLENTY_OF_SPACE = 10**15
DISK_TOTAL = 2 * 10**15

# Packages searched for the named constant and the cache reset hook.
SEARCHED_PACKAGES = ("catalog", "core", "api")
SKIPPED_SUBPACKAGES = ("migrations", "management")

DiskUsage = namedtuple("DiskUsage", "total used free")


class FakeDiskUsage:
    """Stands in for `shutil.disk_usage`: answers `free` bytes and records each path asked about.

    With `error` set, every call raises it instead (a drive that cannot be read).
    """

    def __init__(self, free=PLENTY_OF_SPACE, total=DISK_TOTAL):
        self.free = free
        self.total = max(total, free)
        self.error = None
        self.calls = []

    def __call__(self, path):
        self.calls.append(path)
        if self.error is not None:
            raise self.error
        return DiskUsage(self.total, self.total - self.free, self.free)


def searched_modules():
    """Every top-level module of the searched packages, imported."""
    modules = []
    for package_name in SEARCHED_PACKAGES:
        package = importlib.import_module(package_name)
        modules.append(package)
        for info in pkgutil.iter_modules(package.__path__):
            if info.name in SKIPPED_SUBPACKAGES:
                continue
            modules.append(importlib.import_module(f"{package_name}.{info.name}"))
    return modules


def defined_functions(name):
    """Functions called `name` defined (not merely imported) in a searched module."""
    found = []
    for module in searched_modules():
        candidate = vars(module).get(name)
        if callable(candidate) and getattr(candidate, "__module__", None) == module.__name__:
            found.append(candidate)
    return found


def constant_values(name):
    """{module name: value} for every searched module that holds the attribute `name`."""
    return {module.__name__: vars(module)[name] for module in searched_modules() if name in vars(module)}


def clear_listing_cache():
    """Empty the listing cache of the setup service (T22: cached for the session)."""
    hooks = defined_functions("clear_listing_cache")
    assert len(hooks) == 1, (
        "T22: GET /api/setup caches the data source listing for the session; the tests need exactly one "
        "`clear_listing_cache()` function, defined in a catalog, core or api module, to empty it between "
        f"tests (found {len(hooks)})."
    )
    hooks[0]()


def listing_body(*, size, download_uri=ORACLE_URI, updated_at=PUBLISHED_AT, extra_entries=()):
    """A data source listing whose Oracle Cards entry has the given size (fictional values)."""
    entries = [
        {
            "object": "bulk_data",
            "id": "00000000-0000-4000-8000-0000000000a1",
            "type": "oracle_cards",
            "name": "Fictional Oracle Cards",
            "download_uri": download_uri,
            "updated_at": updated_at,
            "size": size,
            "content_type": "application/json",
            "content_encoding": "gzip",
        },
        *extra_entries,
    ]
    return json.dumps({"object": "list", "has_more": False, "data": entries}).encode("utf-8")


# The size of the Default Cards entry FakeDataSource lists (not in the registry of Milestone 2).
DEFAULT_CARDS_SIZE = 987654
DEFAULT_CARDS_LISTING_TYPE = "default_cards"
DEFAULT_CARDS_HOSTS = ("data.scryfall.io",)


class SetupEnvironment:
    """The seams of one test: a fictional data source, recorded pauses and a fake free space."""

    def __init__(self, monkeypatch, source=None, free=PLENTY_OF_SPACE):
        import catalog.download

        self._monkeypatch = monkeypatch
        self._download = catalog.download
        self.sleep = FakeSleep()
        self.disk = FakeDiskUsage(free)
        monkeypatch.setattr(shutil, "disk_usage", self.disk)
        monkeypatch.setattr(
            catalog.download,
            "time",
            SimpleNamespace(sleep=self.sleep, monotonic=time.monotonic, time=time.time, perf_counter=time.perf_counter),
        )
        self.source = None
        self.use_source(source if source is not None else FakeDataSource())
        clear_listing_cache()

    def use_source(self, source):
        """Serve `source` from now on (the listing cache is left as it is)."""
        self.source = source
        self._monkeypatch.setattr(self._download, "urllib_transport", source)
        return source

    def set_free_space(self, free):
        self.disk.free = free
        self.disk.total = max(self.disk.total, free)

    def bulk_requests(self):
        """How many times the bulk file was asked for."""
        return self.source.urls().count(ORACLE_URI)

    def listing_requests(self):
        """How many times the listing was asked for."""
        return self.source.urls().count(LISTING_URL)


class DuringDownload:
    """A FakeDataSource `on_request` hook: calls `action()` once, from inside the build, when the bulk
    file is first requested, and keeps what it returned in `results`."""

    def __init__(self, action):
        self.action = action
        self.results = []

    def __call__(self, url):
        if url == ORACLE_URI and not self.results:
            self.results.append(self.action())


def own_origin(port):
    """The Origin header of the application's own page on `port`."""
    return {"HTTP_ORIGIN": f"http://127.0.0.1:{port}"}


def mark_ready(version=None):
    """Store a completed build of `version` (the current CATALOG_VERSION by default)."""
    from django.utils import timezone

    from catalog import sources
    from catalog.models import BuildRun

    now = timezone.now()
    return BuildRun.objects.create(
        catalog_version=sources.CATALOG_VERSION if version is None else version,
        started_at=now - timedelta(minutes=3),
        finished_at=now,
    )


def is_not_ready_answer(response):
    """True when `response` is the `database_not_ready` error envelope."""
    try:
        payload = json.loads(response.content.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return False
    return (
        isinstance(payload, dict)
        and isinstance(payload.get("error"), dict)
        and payload["error"].get("code") == CODE_DATABASE_NOT_READY
    )


def download_files(home):
    """Files under `<home>/data/downloads/`."""
    folder = home / "data" / "downloads"
    if not folder.exists():
        return []
    return [path for path in folder.rglob("*") if path.is_file()]


# Catalog tables whose reads tell readiness and the source records.
READINESS_TABLES = ("catalog_buildrun", "catalog_sourcerecord")


@contextmanager
def readiness_failing(message="database is locked"):
    """Make every statement on the readiness tables raise OperationalError on this thread's connection.

    Works at the SQL level, so it does not depend on which selector reads readiness.
    Yields the list of refused statements.
    """
    from django.db import OperationalError, connection

    refused = []

    def wrapper(execute, sql, params, many, context):
        if any(table in str(sql).lower() for table in READINESS_TABLES):
            refused.append(sql)
            raise OperationalError(message)
        return execute(sql, params, many, context)

    with connection.execute_wrapper(wrapper):
        yield refused
