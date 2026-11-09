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
