"""The mana cost validator (task T28, spec RN-17, CA-02, CA-66).

RN-17: official mana symbols, in the printed order ({X}, which may repeat, then
at most one generic number, then {C}, then {S}, then one group of colored,
hybrid and Phyrexian symbols in any order among themselves); the mana value is
computed as the Comprehensive Rules define it and the stated value must match;
a card with no mana cost is accepted with mana value 0 and is different from a
cost of {0}.

The requests ask for every color, so a later color identity check (T29) never
rejects these cards; the assertions read the `mana_cost` causes.
"""

import time

import pytest

from tests.validator_helpers import NO_LEXICON, card, land, request


def _stored(draft):
    from validators import validate

    return validate(draft, NO_LEXICON, request()).to_dict()


def _mana_causes(draft):
    return [cause for cause in _stored(draft)["causes"] if cause["check"] == "mana_cost"]


def _assert_accepted(draft):
    stored = _stored(draft)
    assert "mana_cost" in stored["checks_run"]
    assert [c for c in stored["causes"] if c["check"] == "mana_cost"] == [], draft["mana_cost"]
    assert stored["status"] == "approved", stored


def _assert_rejected(draft):
    stored = _stored(draft)
    causes = [c for c in stored["causes"] if c["check"] == "mana_cost"]
    assert stored["status"] == "rejected", draft["mana_cost"]
    assert causes, f"no mana_cost cause for {draft['mana_cost']!r}"
    return causes


def _mana_value(cost):
    from validators.mana_cost import mana_value

    return mana_value(cost)


# --- CA-02 -------------------------------------------------------------------


def test_t28_ca02_two_generic_plus_green_stated_as_four_is_rejected_and_the_cause_is_named():
    """CA-02 (RN-17): {2}{G} has mana value 3; a stated value of 4 is rejected with a named cause."""
    causes = _assert_rejected(card(mana_cost="{2}{G}", mana_value=4))

    cause = next(c for c in causes if c["code"] == "mana_value_mismatch")
    assert "4" in cause["message"] and "3" in cause["message"], cause["message"]


def test_t28_ca02_two_generic_plus_green_stated_as_three_is_accepted():
    """CA-02 (RN-17): the same cost with its correct value 3 is accepted."""
    _assert_accepted(card(mana_cost="{2}{G}", mana_value=3))


@pytest.mark.parametrize("stated", [0, 2, 5, -3, 999999])
def test_t28_rn17_any_other_stated_value_is_a_mismatch(stated):
    """RN-17 / CA-02: a stated value other than the computed one (zero, lower, higher, negative, huge) is rejected."""
    causes = _assert_rejected(card(mana_cost="{2}{G}", mana_value=stated))

    assert any(c["code"] == "mana_value_mismatch" for c in causes)


@pytest.mark.parametrize("stated", ["3", 3.5, None, True, [3], {"value": 3}])
def test_t28_rn17_a_stated_value_that_is_not_an_integer_is_rejected(stated):
    """RN-17: a malformed provider response (text, fraction, null, boolean, list, object) never matches."""
    _assert_rejected(card(mana_cost="{2}{G}", mana_value=stated))


def test_t28_rn17_a_missing_stated_value_is_rejected():
    """RN-17: a draft that states no mana value cannot match its cost."""
    draft = card(mana_cost="{2}{G}")
    del draft["mana_value"]

    _assert_rejected(draft)


# --- CA-66 -------------------------------------------------------------------


def test_t28_ca66_x_two_white_hybrid_green_phyrexian_has_mana_value_three():
    """CA-66 (RN-17): {X}{2/W}{G/P} has mana value 3 (X is 0, {2/W} is 2, {G/P} is 1)."""
    assert _mana_value("{X}{2/W}{G/P}") == 3
    _assert_accepted(card(mana_cost="{X}{2/W}{G/P}", mana_value=3))


def test_t28_ca66_x_two_white_hybrid_green_phyrexian_stated_otherwise_is_rejected():
    """CA-66 (RN-17): stating 4 (counting X) or 2 (counting {2/W} as 1) for {X}{2/W}{G/P} is rejected."""
    for stated in (4, 2):
        causes = _assert_rejected(card(mana_cost="{X}{2/W}{G/P}", mana_value=stated))
        assert any(c["code"] == "mana_value_mismatch" for c in causes)


def test_t28_ca66_land_with_no_mana_cost_is_accepted_with_mana_value_zero():
    """CA-66 (RN-17): a land with no mana cost is accepted and has mana value 0."""
    assert _mana_value("") == 0
    _assert_accepted(land())


def test_t28_ca66_symbol_order_generic_after_colored_is_rejected():
    """CA-66 (RN-17): {G}{2} is rejected for symbol order."""
    causes = _assert_rejected(card(mana_cost="{G}{2}", mana_value=3))

    assert any(c["code"] == "symbol_order" for c in causes), causes


@pytest.mark.parametrize(
    ("cost", "value"),
    [
        ("{2}{C}{S}{G}", 5),
        ("{G}{U}", 2),
        ("{U}{G}", 2),
        ("{1}{G}{G/W}{W}", 4),
    ],
)
def test_t28_ca66_costs_in_printed_order_are_accepted(cost, value):
    """CA-66 (RN-17): {2}{C}{S}{G}, {G}{U}, {U}{G} and {1}{G}{G/W}{W} are accepted."""
    assert _mana_value(cost) == value
    _assert_accepted(card(mana_cost=cost, mana_value=value))


def test_t28_ca66_two_generic_numbers_are_rejected():
    """CA-66 (RN-17): {1}{1}{G} is rejected (at most one generic number)."""
    causes = _assert_rejected(card(mana_cost="{1}{1}{G}", mana_value=3))

    assert any(c["code"] != "mana_value_mismatch" for c in causes), causes


# --- Missing cost and {0} ----------------------------------------------------


def test_t28_rn17_zero_cost_is_accepted_with_mana_value_zero():
    """RN-17: the cost {0} is well formed and has mana value 0."""
    assert _mana_value("{0}") == 0
    _assert_accepted(card(name="Glimmerdust Trinket", mana_cost="{0}", mana_value=0, type_line="Artifact"))


def test_t28_rn17_missing_cost_is_different_from_zero_cost():
    """RN-17: a card with no mana cost is different from {0}; validation keeps each cost as given."""
    missing = land()
    zero = land(mana_cost="{0}")

    _assert_accepted(missing)
    _assert_accepted(zero)
    assert missing["mana_cost"] == ""
    assert zero["mana_cost"] == "{0}"


def test_t28_rn17_missing_cost_with_a_nonzero_stated_value_is_rejected():
    """RN-17: a card with no mana cost has mana value 0, so a stated 1 is a mismatch."""
    causes = _assert_rejected(land(mana_value=1))

    assert any(c["code"] == "mana_value_mismatch" for c in causes)


# --- Mana value as the Comprehensive Rules define it --------------------------


@pytest.mark.parametrize(
    ("cost", "value"),
    [
        ("{W}", 1),
        ("{X}", 0),
        ("{X}{R}", 1),
        ("{X}{X}{R}", 1),
        ("{X}{X}{X}{B}{B}", 2),
        ("{10}{G}", 11),
        ("{16}", 16),
        ("{C}", 1),
        ("{C}{C}", 2),
        ("{S}", 1),
        ("{S}{S}{G}", 3),
        ("{2/W}", 2),
        ("{2/U}{2/U}{2/U}", 6),
        ("{G/P}", 1),
        ("{W/P}{W/P}", 2),
        ("{G/U/P}", 1),
        ("{R/W}", 1),
        ("{B/G}{B/G}", 2),
        ("{3}{W}{U}{B}{R}{G}", 8),
        ("{X}{1}{C}{S}{2/B}{B/R}{R/P}{R}", 8),
    ],
)
def test_t28_rn17_mana_value_follows_the_comprehensive_rules(cost, value):
    """RN-17: X counts 0, a number its value, {C}, {S}, colored, hybrid and Phyrexian symbols 1, {2/W} counts 2."""
    assert _mana_value(cost) == value
    _assert_accepted(card(mana_cost=cost, mana_value=value))


# --- Printed order ------------------------------------------------------------


@pytest.mark.parametrize(
    "cost",
    [
        "{2}{X}",  # X comes first
        "{G}{X}",
        "{X}{2}{X}",  # every X comes before the rest
        "{C}{2}",  # the generic number comes before {C}
        "{S}{C}",  # {C} comes before {S}
        "{G}{C}",  # {C} comes before the colored group
        "{G}{S}",  # {S} comes before the colored group
        "{G}{C}{U}",  # one group of colored symbols, not split
        "{G/P}{1}",
        "{2/W}{1}",
        "{2}{3}{G}",  # at most one generic number
        "{C}{S}{C}",
    ],
)
def test_t28_rn17_symbols_out_of_printed_order_are_rejected(cost):
    """RN-17: {X}, then one generic number, then {C}, then {S}, then one colored, hybrid and Phyrexian group."""
    draft = card(mana_cost=cost, mana_value=0)
    causes = _assert_rejected(draft)

    assert any(c["code"] != "mana_value_mismatch" for c in causes), causes


@pytest.mark.parametrize(
    "cost",
    [
        "{W}{U}{B}{R}{G}",
        "{G}{R}{U}",
        "{G/W}{W}{G}",
        "{G/P}{G}{2/G}",
        "{1}{2/W}{W/U}{U/P}{U}",
    ],
)
def test_t28_rn17_colored_hybrid_and_phyrexian_symbols_go_in_any_order_among_themselves(cost):
    """RN-17: inside the colored group the order of colored, hybrid and Phyrexian symbols is free."""
    _assert_accepted(card(mana_cost=cost, mana_value=_mana_value(cost)))


# --- Official symbols and malformed costs ------------------------------------


@pytest.mark.parametrize(
    "cost",
    [
        "{Q}",  # not a mana symbol (untap)
        "{T}",  # not a mana symbol (tap)
        "{E}",  # energy, not mana
        "{g}",  # lowercase
        "{P}",  # Phyrexian marker alone
        "{W/G}",  # the official hybrid is {G/W}
        "{G/G}",
        "{2/X}",
        "{-1}",  # negative generic
        "{1.5}",
        "{}",
        "{2}{G",  # unclosed brace
        "2}{G}",
        "{{G}}",
        "2G",  # no braces
        "{2} {G}",  # space between symbols
        " {2}{G}",
        "{2}{G}​",  # zero-width space
        "{Ｇ}",  # full-width G
        "{G}\n{U}",
        "{G}<script>",
    ],
)
def test_t28_rn17_unofficial_or_malformed_costs_are_rejected(cost):
    """RN-17: only official mana symbols, written as on printed cards, form a cost."""
    causes = _assert_rejected(card(mana_cost=cost, mana_value=2))

    assert any(c["code"] != "mana_value_mismatch" for c in causes), causes
    for cause in causes:
        assert cause["message"].strip()


@pytest.mark.parametrize("cost", [None, 3, ["{2}", "{G}"], {"cost": "{2}{G}"}])
def test_t28_rn17_a_cost_that_is_not_text_is_rejected(cost):
    """RN-17: a malformed provider response with a non-text cost is rejected, not raised."""
    _assert_rejected(card(mana_cost=cost, mana_value=3))


def test_t28_rn17_huge_malformed_cost_is_rejected_quickly():
    """RN-17: a very long malformed cost is rejected without error and in reasonable time."""
    cost = "{2/" * 50000 + "G"
    started = time.monotonic()

    _assert_rejected(card(mana_cost=cost, mana_value=3))

    assert time.monotonic() - started < 5


def test_t28_rn17_long_well_formed_colored_group_has_its_full_mana_value():
    """RN-17: a long, well formed group of colored symbols counts each symbol."""
    cost = "{G}" * 40

    assert _mana_value(cost) == 40
    _assert_accepted(card(mana_cost=cost, mana_value=40))
