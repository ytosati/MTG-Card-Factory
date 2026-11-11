"""The version service `save_version()` (task T37, spec RN-25, RN-26).

Details: specs/plan.md, sections 5 (`cards.services`) and 7 (versions numbered
per card inside the IMMEDIATE transaction of `save_version()`, unique
`(card, number)` constraint, concurrency).

API under test:

    cards.services.save_version(card, **fields) -> CardVersion
        `card` is a saved Card; `fields` are the version fields of plan
        section 4 that Milestone 3 stores (see tests/cards_helpers.py). In one
        transaction it numbers the version (1 for the first version of the
        card, then the next number), creates it and moves
        `card.current_version` to it. On any error nothing is left behind: no
        new version, and `current_version` keeps its previous value.

Every card below is fictional and written by hand.
"""

import threading

import pytest
from django.db import connection, connections

from tests.cards_helpers import models, new_card, save_version, version_fields

WAIT_SECONDS = 30.0


def _versions(card):
    return list(models().CardVersion.objects.filter(card_id=card.pk).order_by("number"))


def _current_version_id(card):
    return models().Card.objects.get(pk=card.pk).current_version_id


# --- Numbering and current version -----------------------------------------------------------------


@pytest.mark.django_db
def test_t37_rn25_first_version_is_number_one_and_becomes_current():
    """RN-25 / T37: the first version of a card is number 1 and becomes its current version."""
    card = new_card()
    version = save_version(card, **version_fields())
    assert version.pk is not None
    assert version.number == 1
    assert version.card_id == card.pk
    assert _current_version_id(card) == version.pk


@pytest.mark.django_db
def test_t37_rn25_each_save_creates_the_next_number_and_moves_current_version():
    """RN-25 / T37: every change creates a version; numbers go 1, 2, 3 and the current version is
    always the last one saved."""
    card = new_card()
    saved = []
    for index in range(3):
        version = save_version(card, **version_fields(name=f"Thornveil Courier {index}"))
        saved.append(version)
        assert _current_version_id(card) == version.pk
    assert [version.number for version in _versions(card)] == [1, 2, 3]
    assert [version.pk for version in _versions(card)] == [version.pk for version in saved]


@pytest.mark.django_db
def test_t37_rn25_numbering_is_per_card():
    """RN-25 / T37: versions are numbered per card; saving on one card does not move the other."""
    first_card = new_card()
    second_card = new_card()
    save_version(first_card, **version_fields())
    save_version(first_card, **version_fields())
    other = save_version(second_card, **version_fields())
    third = save_version(first_card, **version_fields())
    assert other.number == 1
    assert third.number == 3
    assert _current_version_id(second_card) == other.pk
    assert _current_version_id(first_card) == third.pk


@pytest.mark.django_db
def test_t37_rn25_numbering_ignores_a_stale_card_instance():
    """RN-25 / T37: the number is computed inside the transaction from the database, not from what an
    in-memory card instance remembers."""
    card = new_card()
    stale = models().Card.objects.get(pk=card.pk)
    save_version(card, **version_fields())
    second = save_version(stale, **version_fields())
    assert second.number == 2
    assert _current_version_id(card) == second.pk


# --- Atomic save -----------------------------------------------------------------------------------


class _BlockCardUpdates:
    """A SQLite trigger that makes every UPDATE of the card table fail, so `save_version()` fails while
    moving `current_version`, after the version row was written. The SQL is fixed; the table name
    comes from the model."""

    NAME = "t37_block_card_update"

    def __enter__(self):
        table = connection.ops.quote_name(models().Card._meta.db_table)
        with connection.cursor() as cursor:
            cursor.execute(
                f"CREATE TRIGGER {self.NAME} BEFORE UPDATE ON {table} "
                "BEGIN SELECT RAISE(ABORT, 't37 forced failure'); END"
            )
        return self

    def __exit__(self, *exc):
        with connection.cursor() as cursor:
            cursor.execute(f"DROP TRIGGER IF EXISTS {self.NAME}")
        return False


@pytest.mark.django_db(transaction=True)
def test_t37_rn25_failed_first_save_leaves_no_version():
    """RN-25 / T37: when moving `current_version` fails, the version created in the same transaction is
    rolled back: the card has no version and no current version."""
    card = new_card()
    with _BlockCardUpdates():
        with pytest.raises(Exception):
            save_version(card, **version_fields())
    assert _versions(card) == []
    assert _current_version_id(card) is None


@pytest.mark.django_db(transaction=True)
def test_t37_rn25_failed_later_save_keeps_the_previous_current_version():
    """RN-25 / T37: a failed save of a later version leaves the earlier versions and the current version
    as they were, and the next successful save takes the next free number."""
    card = new_card()
    first = save_version(card, **version_fields())
    with _BlockCardUpdates():
        with pytest.raises(Exception):
            save_version(card, **version_fields(name="Never Saved"))
    assert [version.pk for version in _versions(card)] == [first.pk]
    assert _current_version_id(card) == first.pk
    assert not models().CardVersion.objects.filter(name="Never Saved").exists()

    second = save_version(card, **version_fields())
    assert second.number == 2
    assert _current_version_id(card) == second.pk


@pytest.mark.django_db
def test_t37_rn25_unknown_field_is_refused_and_leaves_nothing():
    """RN-25 / T37: a malformed call (a field the version does not have) raises and creates nothing."""
    card = new_card()
    first = save_version(card, **version_fields())
    with pytest.raises(Exception):
        save_version(card, **version_fields(colour_of_the_frame="purple"))
    assert [version.pk for version in _versions(card)] == [first.pk]
    assert _current_version_id(card) == first.pk


# --- Concurrency -----------------------------------------------------------------------------------


def _save_many(card_id, count, errors, start):
    try:
        start.wait(WAIT_SECONDS)
        card = models().Card.objects.get(pk=card_id)
        for _ in range(count):
            save_version(card, **version_fields())
    except BaseException as error:  # reported by the test thread
        errors.append(error)
    finally:
        connections.close_all()


@pytest.mark.django_db(transaction=True)
def test_t37_rn25_concurrent_saves_get_distinct_consecutive_numbers():
    """RN-25 / T37: saves from several threads at once (plan section 7, job threads) each get their own
    number inside the transaction: 1..N with no gap or duplicate, and the current version is number N."""
    card = new_card()
    threads_count, per_thread = 4, 3
    errors = []
    start = threading.Event()
    threads = [
        threading.Thread(target=_save_many, args=(card.pk, per_thread, errors, start))
        for _ in range(threads_count)
    ]
    for thread in threads:
        thread.start()
    start.set()
    for thread in threads:
        thread.join(WAIT_SECONDS)
    assert not any(thread.is_alive() for thread in threads), "A save never finished."
    assert errors == []
    total = threads_count * per_thread
    numbers = [version.number for version in _versions(card)]
    assert numbers == list(range(1, total + 1))
    current = models().CardVersion.objects.get(pk=_current_version_id(card))
    assert current.number == total
