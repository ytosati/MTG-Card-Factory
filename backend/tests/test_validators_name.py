"""The name validator against existing cards (task T138, spec RN-51, CA-79).

RN-51: the card's name is not the name of an existing card in the reference
database, or of one of its faces. Names are compared ignoring case,
surrounding and repeated spaces, and the apostrophe style.

The validator imports no Django code: the pipeline reads the normalized
existing names with a catalog selector and passes them to
`validate(card, lexicon, request, existing_names=...)`. These tests use no
database; the sets below are written by hand in the normalized form (case
folded, single spaces, no surrounding spaces, straight apostrophes).

Every name is fictional. Assertions read only the `name` causes, so the other
checks never decide these results.
"""

import time

import pytest

from tests.validator_helpers import NO_LEXICON, card, land, request

CHECK = "name"
# The stable code of a cause for a name that an existing card or face already has.
EXISTING_CODE = "existing_name"

# CA-79: an existing card "Lantern Warden", a two-faced card "Ember // Ash"
# and a card whose name has a straight apostrophe, normalized.
EXISTING = frozenset({"lantern warden", "ember // ash", "ember", "ash", "oswin's ledger"})


def _stored(draft, existing_names=EXISTING):
    from validators import validate

    return validate(draft, NO_LEXICON, request(), existing_names=existing_names).to_dict()


def _name_causes(stored):
    return [cause for cause in stored["causes"] if cause["check"] == CHECK]


def _assert_rejected(name, existing_names=EXISTING):
    stored = _stored(card(name=name), existing_names)
    causes = _name_causes(stored)
    assert stored["status"] == "rejected", name
    assert causes, f"no name cause for {name!r}"
    for cause in causes:
        assert cause["code"] == EXISTING_CODE, cause
        assert isinstance(cause["message"], str) and cause["message"].strip(), cause
    return causes


def _assert_accepted(name, existing_names=EXISTING):
    stored = _stored(card(name=name), existing_names)
    assert CHECK in stored["checks_run"], stored["checks_run"]
    assert _name_causes(stored) == [], name
    assert stored["status"] == "approved", stored


# --- CA-79 -------------------------------------------------------------------


def test_t138_ca79_exact_name_of_an_existing_card_is_rejected_with_the_cause():
    """CA-79 (RN-51): a card named "Lantern Warden" is rejected with an `existing_name` cause."""
    _assert_rejected("Lantern Warden")


def test_t138_ca79_name_differing_only_in_case_and_repeated_spaces_is_rejected():
    """CA-79 (RN-51): "lantern  warden" (lower case, two spaces) is the existing "Lantern Warden"."""
    _assert_rejected("lantern  warden")


@pytest.mark.parametrize("name", ["LANTERN WARDEN", "LaNtErN wArDeN", "  Lantern Warden", "Lantern Warden   ", "  lantern     WARDEN  "])
def test_t138_rn51_case_and_surrounding_or_repeated_spaces_are_ignored(name):
    """RN-51: names are compared ignoring case and surrounding and repeated spaces."""
    _assert_rejected(name)


def test_t138_ca79_name_of_one_face_of_a_two_faced_card_is_rejected():
    """CA-79 (RN-51): "Ash", the back face of "Ember // Ash", is rejected."""
    _assert_rejected("Ash")


def test_t138_rn51_name_of_the_front_face_is_rejected():
    """RN-51: "Ember", the front face of "Ember // Ash", is rejected."""
    _assert_rejected("Ember")


def test_t138_rn51_full_name_of_a_two_faced_card_is_rejected():
    """RN-51: the full name "Ember // Ash" is the name of an existing card."""
    _assert_rejected("ember  //  ASH")


@pytest.mark.parametrize("apostrophe", ["’", "‘", "ʼ"])
def test_t138_ca79_typographic_apostrophe_in_place_of_a_straight_one_is_rejected(apostrophe):
    """CA-79 (RN-51): "Oswin's Ledger" written with a typographic apostrophe is the existing card."""
    _assert_rejected(f"Oswin{apostrophe}s Ledger")


def test_t138_rn51_straight_apostrophe_matches_an_existing_typographic_one():
    """RN-51: the apostrophe style is ignored both ways; existing names arrive normalized to the
    straight apostrophe, so a straight apostrophe in the card matches."""
    _assert_rejected("Oswin's Ledger")


def test_t138_ca79_a_new_name_is_accepted():
    """CA-79 (RN-51): a name no existing card or face has passes the name check."""
    _assert_accepted("Bramblegate Wayfinder")


@pytest.mark.parametrize(
    "name",
    [
        "Lantern Warden's Oath",  # contains an existing name: not the same name
        "Warden",
        "Lantern",
        "Ember Ash",  # the faces without the separator
        "Ashen Ember",
        "Lantern-Warden",  # only case, spaces and apostrophes are ignored
        "Lanternwarden",
        "Lantérn Warden",
        "Oswins Ledger",
    ],
)
def test_t138_rn51_names_that_only_resemble_an_existing_name_are_accepted(name):
    """RN-51: only an equal name after normalization is rejected; partial or near matches pass."""
    _assert_accepted(name)


def test_t138_rn51_the_cause_message_names_the_rule():
    """RN-51: the cause tells the user that an existing card already has the name."""
    cause = _assert_rejected("Lantern Warden")[0]
    message = cause["message"].lower()
    assert "name" in message and "exist" in message, cause["message"]


def test_t138_rn51_one_cause_for_one_existing_name():
    """RN-51: a name equal to one existing name gives one `existing_name` cause."""
    assert len(_assert_rejected("Lantern Warden")) == 1


# --- Composition with validate() ---------------------------------------------


def test_t138_rn51_name_is_a_named_check_of_validate():
    """RN-51 (plan section 7): validate() runs the name check under the stable name "name"."""
    stored = _stored(card(name="Bramblegate Wayfinder"))
    assert CHECK in stored["checks_run"], stored["checks_run"]


def test_t138_rn51_t28_calls_without_existing_names_keep_working():
    """T28 calls `validate(card, lexicon, request)` keep working and approve a valid card."""
    from validators import validate

    stored = validate(card(name="Lantern Warden"), NO_LEXICON, request()).to_dict()
    assert _name_causes(stored) == []
    assert stored["status"] == "approved", stored


def test_t138_rn51_empty_set_of_existing_names_accepts_any_name():
    """RN-51 (edge): with no existing names, no name is rejected."""
    _assert_accepted("Lantern Warden", existing_names=frozenset())


@pytest.mark.parametrize("container", [set, frozenset, list, tuple])
def test_t138_rn51_existing_names_may_be_any_collection(container):
    """RN-51: the pipeline passes a set; any collection of normalized names gives the same result."""
    names = container(EXISTING)
    _assert_rejected("Lantern Warden", existing_names=names)
    _assert_accepted("Bramblegate Wayfinder", existing_names=names)


def test_t138_rn51_name_cause_does_not_hide_other_causes():
    """RN-51 with RN-17: a card with an existing name and a wrong mana value gets both causes."""
    stored = _stored(card(name="Lantern Warden", mana_cost="{2}{G}", mana_value=4))
    checks = {cause["check"] for cause in stored["causes"]}
    assert {"name", "mana_cost"} <= checks, stored["causes"]


def test_t138_rn51_land_with_an_existing_name_is_rejected():
    """RN-51: the rule applies to every card, a land with no mana cost included."""
    stored = _stored(land(name="Ember"))
    assert [c["code"] for c in _name_causes(stored)] == [EXISTING_CODE]


def test_t138_rn51_card_mapping_is_not_modified():
    """The validator reads the card and does not rewrite its name to the normalized form."""
    draft = card(name="  lantern  WARDEN ")
    before = dict(draft)
    _stored(draft)
    assert draft == before


# --- Edge cases --------------------------------------------------------------


@pytest.mark.parametrize("name", ["", "   ", None, 42, ["Lantern Warden"]])
def test_t138_rn51_empty_or_malformed_name_does_not_crash_the_name_check(name):
    """Edge: an empty, blank, missing or non-text name from a malformed provider response
    never raises and is never treated as an existing card's name."""
    stored = _stored(card(name=name))
    assert CHECK in stored["checks_run"]
    assert all(cause["code"] != EXISTING_CODE for cause in _name_causes(stored)), stored["causes"]


def test_t138_rn51_card_without_a_name_field_does_not_crash():
    """Edge: a draft that lacks the name field entirely never raises."""
    draft = card()
    del draft["name"]
    stored = _stored(draft)
    assert CHECK in stored["checks_run"]


@pytest.mark.parametrize("name", ["Glimmer \U0001F525 Warden", "Wardén of Æther", "灰の番人", "Lantern​Warden"])
def test_t138_rn51_odd_characters_in_a_new_name_are_accepted(name):
    """Edge: emoji, accents, ligatures, CJK and zero-width characters in a new name pass."""
    _assert_accepted(name)


def test_t138_rn51_huge_name_is_checked_quickly():
    """Edge: a 100,000-character name is accepted without slowing the check down."""
    started = time.perf_counter()
    _assert_accepted("Lantern " * 12_500)
    assert time.perf_counter() - started < 1.0


def test_t138_rn51_large_set_of_existing_names_is_checked_quickly():
    """Edge: the reference database holds tens of thousands of names; one check stays fast."""
    names = frozenset(f"fictional card {index}" for index in range(50_000)) | EXISTING
    started = time.perf_counter()
    _assert_rejected("Lantern Warden", existing_names=names)
    _assert_accepted("Bramblegate Wayfinder", existing_names=names)
    assert time.perf_counter() - started < 1.0
