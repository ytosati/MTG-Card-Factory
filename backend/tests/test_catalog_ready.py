"""Source registry, catalog version and readiness (task T14, spec RN-01, RN-03).

Details: specs/plan.md, section 7 ("Catalog version").

API under test:

    catalog.sources.CATALOG_VERSION
        a positive integer; a milestone that adds a source increments it.
    catalog.sources.SOURCES
        the source registry: one entry per source, each with a unique `name`
        that is a `SourceRecord.source` value. Milestone 2 registers
        "scryfall_oracle". How an entry reads its size, downloads and imports
        comes with later tasks (T15, T16, T21) and is not tested here.
    catalog.selectors.is_ready() -> bool
        True only when a BuildRun with catalog_version == CATALOG_VERSION
        exists. It reads the constant when called, so raising the constant
        makes it False again.
"""

import pytest
from django.utils import timezone


def _sources():
    from catalog import sources

    return sources


def _selectors():
    from catalog import selectors

    return selectors


def _build_run(catalog_version):
    from catalog.models import BuildRun

    now = timezone.now()
    return BuildRun.objects.create(catalog_version=catalog_version, started_at=now, finished_at=now)


def _set_catalog_version(monkeypatch, value):
    """Raise the constant where it is defined, and where the selectors module
    keeps its own name for it, if it does."""
    monkeypatch.setattr(_sources(), "CATALOG_VERSION", value)
    selectors = _selectors()
    if hasattr(selectors, "CATALOG_VERSION"):
        monkeypatch.setattr(selectors, "CATALOG_VERSION", value)


# --- Registry -------------------------------------------------------------------------


def test_catalog_version_is_a_positive_integer():
    """RN-03 (plan section 7): the catalog version is an integer of at least 1."""
    version = _sources().CATALOG_VERSION
    assert isinstance(version, int) and not isinstance(version, bool)
    assert version >= 1


def test_registry_has_the_oracle_cards_source():
    """RN-01 (Milestone 2): the registry lists Scryfall Oracle Cards."""
    names = [entry.name for entry in _sources().SOURCES]
    assert "scryfall_oracle" in names


def test_registry_names_are_unique_source_record_values():
    """RN-01: each registry entry is recorded as a SourceRecord, so its name is
    one of the source values and appears once."""
    from catalog.models import SourceRecord

    names = [entry.name for entry in _sources().SOURCES]
    allowed = {value for value, _label in SourceRecord._meta.get_field("source").choices}
    assert names
    assert len(names) == len(set(names))
    assert set(names) <= allowed


# --- is_ready() -----------------------------------------------------------------------


@pytest.mark.django_db
def test_is_ready_false_on_an_empty_catalog():
    """RN-03, CA-07: with no completed build, the database is not ready."""
    assert _selectors().is_ready() is False


@pytest.mark.django_db
def test_is_ready_false_with_source_records_but_no_build_run():
    """RN-03, CA-07: downloaded sources alone do not make the database ready."""
    from catalog.models import SourceRecord

    SourceRecord.objects.create(
        source="scryfall_oracle",
        url="https://example.invalid/fictional/oracle-cards.json",
        published_at=timezone.now(),
        downloaded_at=timezone.now(),
        sha256="ab" * 32,
        size=0,
    )
    assert _selectors().is_ready() is False


@pytest.mark.django_db
def test_is_ready_true_with_a_build_run_of_the_current_version():
    """RN-03: a completed build with the current catalog version makes it ready."""
    _build_run(_sources().CATALOG_VERSION)
    assert _selectors().is_ready() is True


@pytest.mark.django_db
@pytest.mark.parametrize("offset", [-1, 1])
def test_is_ready_false_with_a_build_run_of_another_version(offset):
    """RN-03 (plan section 7): a build of an older or newer catalog version does
    not make the database ready."""
    _build_run(_sources().CATALOG_VERSION + offset)
    assert _selectors().is_ready() is False


@pytest.mark.django_db
def test_is_ready_false_again_when_the_catalog_version_is_raised(monkeypatch):
    """RN-03 (plan section 7): ready with the current version, not ready once
    the constant is raised, and ready again after a build of the new version."""
    current = _sources().CATALOG_VERSION
    _build_run(current)
    assert _selectors().is_ready() is True

    _set_catalog_version(monkeypatch, current + 1)
    assert _selectors().is_ready() is False

    _build_run(current + 1)
    assert _selectors().is_ready() is True


@pytest.mark.django_db
def test_is_ready_true_when_an_old_build_and_a_current_build_exist():
    """RN-03: a leftover build of an earlier version does not hide a current one."""
    current = _sources().CATALOG_VERSION
    _build_run(current - 1)
    _build_run(current)
    assert _selectors().is_ready() is True
