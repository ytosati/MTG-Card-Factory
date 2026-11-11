"""The selector of normalized existing names (task T138, spec RN-51, CA-79).

RN-51: every card the reference database holds counts, and so does each of its
faces; names are compared ignoring case, surrounding and repeated spaces, and
the apostrophe style. `catalog.selectors.existing_card_names()` returns the
normalized names (case folded, single spaces, no surrounding spaces, straight
apostrophes) that the pipeline passes to `validate(..., existing_names=...)`.

Every catalog row is fictional and written by hand.
"""

import uuid

import pytest

from tests.validator_helpers import NO_LEXICON, card, request


def _oracle_card(name, faces=(), legality="legal", layout="normal"):
    from catalog.models import OracleCard

    return OracleCard.objects.create(
        oracle_id=uuid.uuid4(),
        name=name,
        mana_cost="{1}{R}",
        cmc=2.0,
        type_line="Creature — Spirit",
        oracle_text="",
        colors=["R"],
        color_identity=["R"],
        keywords=[],
        power="2",
        toughness="1",
        layout=layout,
        faces=list(faces),
        commander_legality=legality,
        game_changer=False,
        edhrec_rank=None,
        roles=[],
    )


def _names():
    from catalog.selectors import existing_card_names

    return existing_card_names()


@pytest.mark.django_db
def test_t138_rn51_selector_returns_the_normalized_names_of_cards_and_faces():
    """RN-51 / CA-79: "Lantern Warden" and "Ember // Ash" give the card names and each face name."""
    _oracle_card("Lantern Warden")
    _oracle_card(
        "Ember // Ash",
        faces=[
            {"name": "Ember", "mana_cost": "{1}{R}", "type_line": "Instant"},
            {"name": "Ash", "mana_cost": "{2}{B}", "type_line": "Sorcery"},
        ],
        layout="split",
    )

    assert set(_names()) == {"lantern warden", "ember // ash", "ember", "ash"}


@pytest.mark.django_db
def test_t138_rn51_selector_normalizes_case_spaces_and_apostrophes():
    """RN-51: stored names are folded to lower case, single spaces, no surrounding spaces and
    straight apostrophes, so the validator compares like with like."""
    _oracle_card("  Oswin’s   LEDGER ")
    _oracle_card(
        "Quill of Mar’en // Tide",
        faces=[{"name": "Quill of Mar’en"}, {"name": "  Tide  "}],
        layout="transform",
    )

    assert set(_names()) == {"oswin's ledger", "quill of mar'en // tide", "quill of mar'en", "tide"}


@pytest.mark.django_db
def test_t138_rn51_every_card_counts_whatever_its_legality():
    """RN-51: every card the database holds counts, banned and not legal ones included."""
    _oracle_card("Cinderveil Regent", legality="banned")
    _oracle_card("Mirelight Drifter", legality="not_legal")
    _oracle_card("Thornwick Sentry", legality="legal")

    assert {"cinderveil regent", "mirelight drifter", "thornwick sentry"} <= set(_names())


@pytest.mark.django_db
def test_t138_rn51_empty_catalog_gives_no_names():
    """Edge: with no reference cards, no name is taken."""
    assert set(_names()) == set()


@pytest.mark.django_db
def test_t138_rn51_faces_without_a_name_are_skipped():
    """Edge: a face record without a name, or with an empty one, adds no name and never raises."""
    _oracle_card(
        "Hollow // Bright",
        faces=[{"mana_cost": "{U}"}, {"name": ""}, {"name": "Bright"}],
        layout="modal_dfc",
    )

    assert set(_names()) == {"hollow // bright", "bright"}


@pytest.mark.django_db
def test_t138_rn51_repeated_names_are_returned_once():
    """Edge: a face that shares its name with another card adds one entry, not two."""
    _oracle_card("Ember")
    _oracle_card("Ember // Ash", faces=[{"name": "Ember"}, {"name": "Ash"}], layout="split")

    names = _names()
    assert set(names) == {"ember", "ember // ash", "ash"}
    assert len(list(names)) == 3


@pytest.mark.django_db
def test_t138_ca79_selector_names_reject_existing_names_in_validate():
    """CA-79: the selector output passed to `validate` rejects "lantern  warden", "Ash" and a
    typographic apostrophe, and accepts a new name."""
    from validators import validate

    _oracle_card("Lantern Warden")
    _oracle_card("Ember // Ash", faces=[{"name": "Ember"}, {"name": "Ash"}], layout="split")
    _oracle_card("Oswin's Ledger")
    names = _names()

    for taken in ("lantern  warden", "Ash", "Oswin’s Ledger"):
        stored = validate(card(name=taken), NO_LEXICON, request(), existing_names=names).to_dict()
        assert stored["status"] == "rejected", taken
        assert [c["code"] for c in stored["causes"] if c["check"] == "name"] == ["existing_name"], taken

    stored = validate(card(name="Bramblegate Wayfinder"), NO_LEXICON, request(), existing_names=names).to_dict()
    assert stored["status"] == "approved", stored


# --- The two normalize_name copies agree ------------------------------------------------------------

SHARED_NAMES = [
    "Lantern Warden",
    "  lantern   WARDEN  ",
    "Oswin’s Ledger",
    "Oswin‘s Ledger",
    "Oswinʼs Ledger",
    "Oswin's Ledger",
    "Ember // Ash",
    "ember\t//\nash",
    "",
    "   ",
    "STRASSE Ärger",
    "Straße Ärger",
    "Ñandú of the Glade 🃏",
    " Thornveil Oracle ",
    "x" * 5000,
]


@pytest.mark.parametrize("name", SHARED_NAMES)
def test_t138_rn51_both_normalize_name_copies_give_the_same_result(name):
    """RN-51 / T138: validators.name.normalize_name and catalog.selectors.normalize_name are kept equal,
    so a name stored by the selector matches the name the validator compares."""
    from catalog.selectors import normalize_name as catalog_normalize
    from validators.name import normalize_name as validator_normalize

    assert validator_normalize(name) == catalog_normalize(name)
