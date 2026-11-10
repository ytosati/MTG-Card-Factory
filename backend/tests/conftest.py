"""Shared fixtures for the backend test suite."""

import pytest


@pytest.fixture(autouse=True)
def empty_seen_keys(monkeypatch):
    """Each test starts with no remembered key values (RN-06, plan section 8).

    The key redaction filter remembers every key value seen in the process in
    `core.log_redaction._seen_keys`; without a fresh set per test, a test using
    the same fictional key as an earlier one could pass because of the memory
    the earlier test left behind.
    """
    import core.log_redaction

    monkeypatch.setattr(core.log_redaction, "_seen_keys", set())


@pytest.fixture(scope="session")
def django_db_modify_db_settings():
    """The test database is a SQLite file in the temporary home (task T13).

    Job threads open their own connections; an in-memory database is not
    shared reliably between them, a file is.
    """
    from django.conf import settings

    from tests.isolation import TEST_HOME

    settings.DATABASES["default"].setdefault("TEST", {})["NAME"] = str(TEST_HOME / "data" / "test-cardfactory.sqlite3")


@pytest.fixture(autouse=True)
def empty_full_text_tables(request, django_db_blocker):
    """The flush between transactional tests empties model tables only, so the
    FTS5 table keeps rows that a `transaction=True` test committed (RN-03 tests
    check that a failed build leaves no full-text rows)."""
    yield
    marker = request.node.get_closest_marker("django_db")
    if marker is None or not marker.kwargs.get("transaction"):
        return
    from django.db import connection

    with django_db_blocker.unblock():
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM oracle_fts")
