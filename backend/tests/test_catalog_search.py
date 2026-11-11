"""The comparables search (task T23, spec RN-04, RN-12, CA-24).

Details: specs/plan.md, sections 5 (catalog.selectors), 7 (selectors never
write) and 9.1 (filters, power level shaping, FTS5 BM25 ranking, deterministic
widening, user text quoted per token for MATCH).

API under test:

    catalog.selectors.search_cards(query, filters) -> list of result items

    query     the search text: the keywords of the search plan joined by
              spaces. Every token is plain text, never an FTS5 operator.
    filters   a mapping:
                color_identity   list of color letters of the request;
                                 [] is a colorless request (required)
                power_level      "casual", "medium" or "strong" (required)
                roles            list of role names of catalog.ingest.ROLES;
                                 a card matches when it has any of them
                card_types       list of card types; a card matches when its
                                 type line holds any of them
                mana_value_min   inclusive lower bound on the mana value
                mana_value_max   inclusive upper bound on the mana value
              The optional keys may be left out (no filter) or empty lists.
              They mirror the search plan of generation.schemas.DESIGN_SCHEMA.
    item      a mapping with at least `oracle_id`, `name` and
              `counterexample` (True only for a card banned in Commander).

Every catalog row is fictional and written by hand. The full-text table is
filled from the card rows with the same fixed statement the build uses.
"""

import uuid

import pytest
from django.db import connection

MINIMUM_RESULTS = 10

FILLER = (
    "Tap an untapped creature you control. Put a counter on target permanent. "
    "Each player shuffles. Scry one. Then the turn continues as normal. "
)

# The fixed statements of the build (plan section 7): the full-text table holds
# the name, type line and rules text of each card row.
_CLEAR_FTS = "DELETE FROM oracle_fts"
_FILL_FTS = (
    "INSERT INTO oracle_fts(oracle_id, name, type_line, oracle_text) "
    "SELECT oracle_id, name, type_line, oracle_text FROM catalog_oraclecard"
)


def _card(
    name,
    text,
    *,
    identity=("G",),
    legality="legal",
    type_line="Creature — Elf Druid",
    cmc=3.0,
    roles=(),
    game_changer=False,
    edhrec_rank=None,
):
    from catalog.models import OracleCard

    return OracleCard.objects.create(
        oracle_id=uuid.uuid4(),
        name=name,
        mana_cost="{2}{G}",
        cmc=cmc,
        type_line=type_line,
        oracle_text=text,
        colors=list(identity),
        color_identity=list(identity),
        keywords=[],
        power="2" if "Creature" in type_line else None,
        toughness="2" if "Creature" in type_line else None,
        layout="normal",
        faces=[],
        commander_legality=legality,
        game_changer=game_changer,
        edhrec_rank=edhrec_rank,
        roles=list(roles),
    )


def _index():
    with connection.cursor() as cursor:
        cursor.execute(_CLEAR_FTS)
        cursor.execute(_FILL_FTS)


def _filters(**overrides):
    values = {"color_identity": ["G"], "power_level": "medium"}
    values.update(overrides)
    return values


def _search(query, **filters):
    from catalog.selectors import search_cards

    return list(search_cards(query, _filters(**filters)))


def _oid(value):
    return str(uuid.UUID(str(value)))


def _ids(results):
    return [_oid(item["oracle_id"]) for item in results]


def _id_set(results):
    return set(_ids(results))


def _cards_ids(*cards):
    return {_oid(card.oracle_id) for card in cards}


def _item(results, card):
    matches = [item for item in results if _oid(item["oracle_id"]) == _oid(card.oracle_id)]
    assert len(matches) == 1, f"{card.name} should appear exactly once, found {len(matches)}"
    return matches[0]


def _position(results, card):
    return _ids(results).index(_oid(card.oracle_id))


def _non_matching_fillers(count=6, identity=("G",)):
    """Cards without the query word, so the word is rare and its BM25 weight positive."""
    return [_card(f"Quiet Meadow Hermit {n}", FILLER, identity=identity) for n in range(count)]


# --- Result shape -----------------------------------------------------------


@pytest.mark.django_db
def test_t23_rn12_search_returns_items_with_oracle_id_name_and_marking():
    """RN-12: each result names the card and says whether it is a counterexample."""
    card = _card("Lanternroot Shaman", "When this creature enters, a lantern glows.")
    _index()

    results = _search("lantern")

    item = _item(results, card)
    assert item["name"] == "Lanternroot Shaman"
    assert item["counterexample"] is False


@pytest.mark.django_db
def test_t23_rn12_search_returns_nothing_when_no_card_matches():
    """RN-12: an empty result is a list, not an error."""
    _card("Lanternroot Shaman", "When this creature enters, a lantern glows.")
    _index()

    assert _search("zephyrquill") == []


@pytest.mark.django_db
def test_t23_rn12_search_on_an_empty_catalog_returns_an_empty_list():
    """RN-12: no card rows and an empty full-text table give no results."""
    _index()

    assert _search("lantern") == []


# --- Color identity ---------------------------------------------------------


@pytest.mark.django_db
def test_t23_rn12_identity_filter_keeps_cards_within_the_requested_identity():
    """RN-12: a green-white request returns mono-green, mono-white, green-white and
    colorless cards, never a card with any other color in its identity."""
    green = _card("Lantern Elk", "A lantern hangs from its antlers.", identity=("G",))
    white = _card("Lantern Acolyte", "A lantern lights the chapel.", identity=("W",))
    both = _card("Lantern Pilgrim", "A lantern guides the way.", identity=("G", "W"))
    colorless = _card("Lantern Golem", "A lantern burns inside.", identity=(), type_line="Artifact Creature — Golem")
    blue = _card("Lantern Diver", "A lantern under the waves.", identity=("U",))
    green_blue = _card("Lantern Mystic", "A lantern of mist.", identity=("G", "U"))
    five = _card("Lantern Prism", "A lantern of every hue.", identity=("W", "U", "B", "R", "G"))
    _index()

    results = _search("lantern", color_identity=["W", "G"])

    assert _id_set(results) == _cards_ids(green, white, both, colorless)
    assert not _id_set(results) & _cards_ids(blue, green_blue, five)


@pytest.mark.django_db
def test_t23_rn12_identity_filter_ignores_the_order_of_the_requested_colors():
    """RN-12: a card with identity ["W", "G"] is within a request given as ["G", "W"]."""
    both = _card("Lantern Pilgrim", "A lantern guides the way.", identity=("W", "G"))
    _index()

    assert _id_set(_search("lantern", color_identity=["G", "W"])) == _cards_ids(both)


@pytest.mark.django_db
def test_t23_rn12_colorless_request_returns_only_colorless_cards():
    """RN-12: an empty requested identity (colorless) returns only cards with an empty identity."""
    golem = _card("Lantern Golem", "A lantern burns inside.", identity=(), type_line="Artifact Creature — Golem")
    relic = _card("Lantern Relic", "A lantern of brass.", identity=(), type_line="Artifact")
    _card("Lantern Elk", "A lantern hangs from its antlers.", identity=("G",))
    _card("Lantern Acolyte", "A lantern lights the chapel.", identity=("W",))
    _index()

    results = _search("lantern", color_identity=[])

    assert _id_set(results) == _cards_ids(golem, relic)


@pytest.mark.django_db
def test_t23_rn12_five_color_request_returns_every_identity():
    """RN-12: a request of all five colors accepts every card identity."""
    cards = [
        _card("Lantern Golem", "A lantern burns inside.", identity=()),
        _card("Lantern Diver", "A lantern under the waves.", identity=("U",)),
        _card("Lantern Prism", "A lantern of every hue.", identity=("W", "U", "B", "R", "G")),
        _card("Lantern Ghoul", "A lantern in the crypt.", identity=("B", "R")),
    ]
    _index()

    results = _search("lantern", color_identity=["W", "U", "B", "R", "G"])

    assert _id_set(results) == _cards_ids(*cards)


# --- Commander legality and counterexamples ---------------------------------


@pytest.mark.django_db
def test_t23_rn04_cards_not_legal_in_commander_are_never_returned():
    """RN-04: a card that is not legal in Commander is neither a comparable nor a counterexample."""
    legal = _card("Lantern Elk", "A lantern hangs from its antlers.")
    not_legal = _card("Lantern Schemer", "A lantern from another game.", legality="not_legal")
    _index()

    results = _search("lantern")

    assert _oid(not_legal.oracle_id) not in _ids(results)
    assert _item(results, legal)["counterexample"] is False


@pytest.mark.django_db
def test_t23_ca24_banned_card_matching_the_request_is_marked_as_counterexample():
    """CA-24 / RN-04: a banned card that matches comes back once, marked as a
    counterexample, and never as a comparable."""
    legal = _card("Lantern Elk", "A lantern hangs from its antlers.")
    banned = _card("Lantern Tyrant", "A lantern that burns every other lantern.", legality="banned")
    _index()

    results = _search("lantern")

    assert _item(results, banned)["counterexample"] is True
    assert _item(results, legal)["counterexample"] is False
    comparables = [item for item in results if not item["counterexample"]]
    assert _oid(banned.oracle_id) not in _ids(comparables)


@pytest.mark.django_db
def test_t23_ca24_only_banned_cards_are_counterexamples():
    """CA-24 / RN-04: every legal result is a comparable; every banned result is a counterexample."""
    legal_cards = [_card(f"Lantern Elk {n}", "A lantern hangs from its antlers.") for n in range(3)]
    banned_cards = [_card(f"Lantern Tyrant {n}", "A lantern of ruin.", legality="banned") for n in range(2)]
    _index()

    results = _search("lantern")

    by_id = {_oid(item["oracle_id"]): item["counterexample"] for item in results}
    for card in legal_cards:
        assert by_id[_oid(card.oracle_id)] is False
    for card in banned_cards:
        assert by_id[_oid(card.oracle_id)] is True


@pytest.mark.django_db
def test_t23_ca24_banned_card_outside_the_identity_is_not_returned():
    """CA-24 / RN-12: a counterexample still has to match the request: a banned card
    outside the requested identity is left out."""
    _card("Lantern Elk", "A lantern hangs from its antlers.")
    banned_blue = _card("Lantern Tyrant", "A lantern of ruin.", identity=("U",), legality="banned")
    _index()

    assert _oid(banned_blue.oracle_id) not in _ids(_search("lantern", color_identity=["G"]))


@pytest.mark.django_db
def test_t23_ca24_banned_card_that_does_not_match_the_query_is_not_returned():
    """CA-24: only a banned card that matches the request is a counterexample."""
    _card("Lantern Elk", "A lantern hangs from its antlers.")
    banned = _card("Gloom Tyrant", "Destroy all creatures.", legality="banned")
    _index()

    assert _oid(banned.oracle_id) not in _ids(_search("lantern"))


# --- Roles, card types and mana value ---------------------------------------


@pytest.mark.django_db
def test_t23_rn12_roles_filter_keeps_cards_with_any_requested_role():
    """RN-12: roles=["removal", "ramp"] keeps a card with either role and drops the rest."""
    removal = _card("Lantern Smiter", "A lantern that burns a foe.", roles=["removal"])
    ramp = _card("Lantern Gardener", "A lantern that grows a land.", roles=["ramp"])
    both = _card("Lantern Warden", "A lantern of many uses.", roles=["card_draw", "removal"])
    draw = _card("Lantern Scholar", "A lantern for reading.", roles=["card_draw"])
    none = _card("Lantern Idler", "A lantern that does nothing.", roles=[])
    _index()

    results = _search("lantern", roles=["removal", "ramp"])

    assert _id_set(results) == _cards_ids(removal, ramp, both)
    assert not _id_set(results) & _cards_ids(draw, none)


@pytest.mark.django_db
def test_t23_rn12_empty_roles_list_is_no_role_filter():
    """RN-12: an empty roles list keeps cards with any roles, including none."""
    cards = [
        _card("Lantern Smiter", "A lantern that burns a foe.", roles=["removal"]),
        _card("Lantern Idler", "A lantern that does nothing.", roles=[]),
    ]
    _index()

    assert _id_set(_search("lantern", roles=[])) == _cards_ids(*cards)


@pytest.mark.django_db
def test_t23_rn12_card_types_filter_keeps_cards_whose_type_line_holds_a_requested_type():
    """RN-12: card_types=["Creature"] keeps creatures, artifact creatures included
    (ten of them, so no widening), and drops the enchantments."""
    creatures = [_card(f"Lantern Elk {n}", "A lantern glows.", type_line="Creature — Elk") for n in range(7)]
    creatures += [
        _card(f"Lantern Golem {n}", "A lantern glows.", type_line="Artifact Creature — Golem") for n in range(3)
    ]
    enchantments = [_card(f"Lantern Shrine {n}", "A lantern glows.", type_line="Enchantment") for n in range(3)]
    _index()

    results = _search("lantern", card_types=["Creature"])

    assert _id_set(results) == _cards_ids(*creatures)
    assert not _id_set(results) & _cards_ids(*enchantments)


@pytest.mark.django_db
def test_t23_rn12_card_types_filter_accepts_any_of_several_types():
    """RN-12: card_types=["Creature", "Instant"] keeps both types and drops sorceries."""
    kept = [_card(f"Lantern Elk {n}", "A lantern glows.", type_line="Creature — Elk") for n in range(6)]
    kept += [_card(f"Lantern Flash {n}", "A lantern glows.", type_line="Instant") for n in range(4)]
    sorceries = [_card(f"Lantern Rite {n}", "A lantern glows.", type_line="Sorcery") for n in range(3)]
    _index()

    results = _search("lantern", card_types=["Creature", "Instant"])

    assert _id_set(results) == _cards_ids(*kept)
    assert not _id_set(results) & _cards_ids(*sorceries)


@pytest.mark.django_db
def test_t23_rn12_mana_value_range_is_inclusive():
    """RN-12: mana_value_min=2 and mana_value_max=4 keep mana values 2, 3 and 4
    (ten cards, so no widening) and drop 1 and 5."""
    kept = [_card(f"Lantern Elk {n}", "A lantern glows.", cmc=float(2 + n % 3)) for n in range(10)]
    cheap = _card("Lantern Spark", "A lantern glows.", cmc=1.0)
    costly = _card("Lantern Titan", "A lantern glows.", cmc=5.0)
    _index()

    results = _search("lantern", mana_value_min=2, mana_value_max=4)

    assert _id_set(results) == _cards_ids(*kept)
    assert not _id_set(results) & _cards_ids(cheap, costly)


@pytest.mark.django_db
def test_t23_rn12_mana_value_minimum_alone_is_a_lower_bound():
    """RN-12: only mana_value_min=4 keeps mana values of 4 and more."""
    kept = [_card(f"Lantern Titan {n}", "A lantern glows.", cmc=float(4 + n)) for n in range(10)]
    cheap = _card("Lantern Spark", "A lantern glows.", cmc=3.0)
    _index()

    results = _search("lantern", mana_value_min=4)

    assert _id_set(results) == _cards_ids(*kept)
    assert _oid(cheap.oracle_id) not in _ids(results)


@pytest.mark.django_db
def test_t23_rn12_mana_value_maximum_zero_keeps_only_zero_cost_cards():
    """RN-12: mana_value_max=0 keeps cards of mana value 0 (lands, zero-cost artifacts)."""
    kept = [
        _card(f"Lantern Hollow {n}", "A lantern glows.", cmc=0.0, type_line="Land")
        for n in range(10)
    ]
    one = _card("Lantern Spark", "A lantern glows.", cmc=1.0)
    _index()

    results = _search("lantern", mana_value_min=0, mana_value_max=0)

    assert _id_set(results) == _cards_ids(*kept)
    assert _oid(one.oracle_id) not in _ids(results)


@pytest.mark.django_db
def test_t23_rn12_inverted_mana_value_range_does_not_raise():
    """RN-12: a minimum above the maximum (a malformed search plan) is not an error."""
    _card("Lantern Elk", "A lantern glows.", cmc=3.0)
    _index()

    assert isinstance(_search("lantern", mana_value_min=6, mana_value_max=2), list)


# --- Power level shaping ----------------------------------------------------


def _ranked_trio():
    """Three matching cards whose BM25 order is strong, middle, weak, with EDHREC
    ranks in the opposite order, plus fillers without the word."""
    strong_match = _card("Ashen Wisp", "Ember ember ember.", edhrec_rank=300)
    middle_match = _card("Cinder Moth", "Ember. " + FILLER, edhrec_rank=200)
    weak_match = _card("Dusk Heron", "Ember. " + FILLER * 4, edhrec_rank=100)
    _non_matching_fillers()
    return strong_match, middle_match, weak_match


@pytest.mark.django_db
def test_t23_rn12_casual_excludes_game_changer_cards():
    """RN-12 (plan 9.1): casual leaves out Game Changer cards, even with fewer than ten results."""
    plain = [_card(f"Lantern Elk {n}", "A lantern glows.") for n in range(2)]
    changers = [_card(f"Lantern Engine {n}", "A lantern glows.", game_changer=True) for n in range(3)]
    _index()

    results = _search("lantern", power_level="casual")

    assert _id_set(results) == _cards_ids(*plain)
    assert not _id_set(results) & _cards_ids(*changers)


@pytest.mark.django_db
def test_t23_rn12_casual_ranks_by_bm25():
    """RN-12 (plan 9.1): casual ranks the remaining candidates by BM25."""
    strong_match, middle_match, weak_match = _ranked_trio()
    _index()

    results = _search("ember", power_level="casual")

    assert _position(results, strong_match) < _position(results, middle_match) < _position(results, weak_match)


@pytest.mark.django_db
def test_t23_rn12_medium_allows_game_changer_cards():
    """RN-12 (plan 9.1): medium keeps Game Changer cards among the candidates."""
    plain = _card("Lantern Elk", "A lantern glows.")
    changer = _card("Lantern Engine", "A lantern glows.", game_changer=True)
    _index()

    assert _id_set(_search("lantern", power_level="medium")) == _cards_ids(plain, changer)


@pytest.mark.django_db
def test_t23_rn12_medium_ranks_by_bm25_alone():
    """RN-12 (plan 9.1): medium ranks by BM25 alone: neither the EDHREC rank nor
    the Game Changer flag moves a card up."""
    strong_match, middle_match, weak_match = _ranked_trio()
    weak_changer = _card("Gloam Engine", "Ember. " + FILLER * 8, game_changer=True, edhrec_rank=1)
    _index()

    results = _search("ember", power_level="medium")

    order = [_position(results, card) for card in (strong_match, middle_match, weak_match, weak_changer)]
    assert order == sorted(order)


@pytest.mark.django_db
def test_t23_rn12_strong_includes_game_changer_cards():
    """RN-12 (plan 9.1): strong includes Game Changer cards."""
    plain = _card("Lantern Elk", "A lantern glows.", edhrec_rank=50)
    changer = _card("Lantern Engine", "A lantern glows.", game_changer=True, edhrec_rank=40)
    _index()

    assert _id_set(_search("lantern", power_level="strong")) == _cards_ids(plain, changer)


@pytest.mark.django_db
def test_t23_rn12_strong_ranks_by_edhrec_rank():
    """RN-12 (plan 9.1): strong ranks by EDHREC rank (lower rank first), whatever the BM25 order."""
    strong_match, middle_match, weak_match = _ranked_trio()
    _index()

    results = _search("ember", power_level="strong")

    assert _position(results, weak_match) < _position(results, middle_match) < _position(results, strong_match)


@pytest.mark.django_db
def test_t23_rn12_strong_puts_cards_without_edhrec_rank_last():
    """RN-12 (plan 9.1): under strong, a card with no EDHREC rank comes after every ranked card."""
    strong_match, middle_match, weak_match = _ranked_trio()
    unranked = _card("Pale Ember Ember Ember", "Ember ember ember ember.", edhrec_rank=None)
    _index()

    results = _search("ember", power_level="strong")

    assert _position(results, unranked) > max(
        _position(results, card) for card in (strong_match, middle_match, weak_match)
    )


# --- BM25 ranking -----------------------------------------------------------


@pytest.mark.django_db
def test_t23_rn12_bm25_ranks_denser_matches_first():
    """RN-12 (plan 9.1): the card where the word is frequent in a short text comes
    before the ones where it is once in a long text."""
    strong_match, middle_match, weak_match = _ranked_trio()
    _index()

    results = _search("ember")

    assert _ids(results)[:3] == _ids([{"oracle_id": c.oracle_id} for c in (strong_match, middle_match, weak_match)])


@pytest.mark.django_db
def test_t23_rn12_bm25_ranks_over_name_type_line_and_rules_text():
    """RN-12 (plan 9.1): the word counts in the name, in the type line and in the rules text."""
    in_name = _card("Thornwick Ember", FILLER)
    in_type = _card("Ashen Hound", FILLER, type_line="Creature — Ember Hound")
    in_text = _card("Gloam Stag", "Ember. " + FILLER)
    _non_matching_fillers()
    _index()

    assert _id_set(_search("ember")) >= _cards_ids(in_name, in_type, in_text)


@pytest.mark.django_db
def test_t23_rn12_search_is_deterministic():
    """RN-12 (plan 9.1): the same query and filters give the same results in the same order."""
    for n in range(12):
        _card(f"Lantern Elk {n}", "A lantern glows. " + FILLER * (n % 3), edhrec_rank=n + 1)
    _index()

    for level in ("casual", "medium", "strong"):
        first = _ids(_search("lantern", power_level=level))
        second = _ids(_search("lantern", power_level=level))
        assert first == second


# --- Deterministic widening -------------------------------------------------


@pytest.mark.django_db
def test_t23_rn12_no_widening_with_ten_results():
    """RN-12 (plan 9.1): exactly ten results is enough: the mana value and type filters stay."""
    in_range = [_card(f"Lantern Elk {n}", "A lantern glows.", cmc=3.0) for n in range(MINIMUM_RESULTS)]
    out_of_range = [_card(f"Lantern Titan {n}", "A lantern glows.", cmc=7.0) for n in range(2)]
    other_type = [_card(f"Lantern Shrine {n}", "A lantern glows.", type_line="Enchantment") for n in range(2)]
    _index()

    results = _search("lantern", card_types=["Creature"], mana_value_min=2, mana_value_max=4)

    assert _id_set(results) == _cards_ids(*in_range)
    assert not _id_set(results) & _cards_ids(*out_of_range, *other_type)


@pytest.mark.django_db
def test_t23_rn12_widening_drops_the_mana_value_first():
    """RN-12 (plan 9.1): with fewer than ten results the mana value range goes first;
    when that reaches ten, the type filter stays."""
    in_range = [_card(f"Lantern Elk {n}", "A lantern glows.", cmc=3.0) for n in range(3)]
    out_of_range = [_card(f"Lantern Titan {n}", "A lantern glows.", cmc=7.0) for n in range(7)]
    other_type = [
        _card(f"Lantern Shrine {n}", "A lantern glows.", cmc=3.0, type_line="Enchantment") for n in range(5)
    ]
    _index()

    results = _search("lantern", card_types=["Creature"], mana_value_min=2, mana_value_max=4)

    assert _id_set(results) == _cards_ids(*in_range, *out_of_range)
    assert not _id_set(results) & _cards_ids(*other_type)


@pytest.mark.django_db
def test_t23_rn12_widening_drops_the_types_after_the_mana_value():
    """RN-12 (plan 9.1): when dropping the mana value still gives fewer than ten,
    the type filter goes too."""
    in_range = [_card(f"Lantern Elk {n}", "A lantern glows.", cmc=3.0) for n in range(3)]
    out_of_range = [_card(f"Lantern Titan {n}", "A lantern glows.", cmc=7.0) for n in range(4)]
    other_type = [
        _card(f"Lantern Shrine {n}", "A lantern glows.", cmc=6.0, type_line="Enchantment") for n in range(3)
    ]
    _index()

    results = _search("lantern", card_types=["Creature"], mana_value_min=2, mana_value_max=4)

    assert _id_set(results) == _cards_ids(*in_range, *out_of_range, *other_type)


@pytest.mark.django_db
def test_t23_rn12_widening_without_mana_value_filter_drops_the_types():
    """RN-12 (plan 9.1): with no mana value range, too few results drop the type filter."""
    creatures = [_card(f"Lantern Elk {n}", "A lantern glows.") for n in range(2)]
    instants = [_card(f"Lantern Flash {n}", "A lantern glows.", type_line="Instant") for n in range(3)]
    _index()

    results = _search("lantern", card_types=["Creature"])

    assert _id_set(results) == _cards_ids(*creatures, *instants)


@pytest.mark.django_db
def test_t23_rn12_widening_keeps_identity_legality_roles_and_power_shaping():
    """RN-04 / RN-12 (plan 9.1): widening only drops the mana value and the types:
    identity, Commander legality, roles and the casual Game Changer exclusion stay."""
    kept = _card("Lantern Smiter", "A lantern glows.", cmc=3.0, roles=["removal"])
    widened = _card("Lantern Razer", "A lantern glows.", cmc=8.0, type_line="Sorcery", roles=["removal"])
    blue = _card("Lantern Diver", "A lantern glows.", identity=("U",), roles=["removal"])
    not_legal = _card("Lantern Schemer", "A lantern glows.", legality="not_legal", roles=["removal"])
    no_role = _card("Lantern Idler", "A lantern glows.", roles=["ramp"])
    changer = _card("Lantern Engine", "A lantern glows.", roles=["removal"], game_changer=True)
    _index()

    results = _search(
        "lantern",
        power_level="casual",
        roles=["removal"],
        card_types=["Creature"],
        mana_value_min=2,
        mana_value_max=4,
    )

    assert _id_set(results) == _cards_ids(kept, widened)
    assert not _id_set(results) & _cards_ids(blue, not_legal, no_role, changer)


# --- Query text is plain text -----------------------------------------------

HOSTILE_QUERIES = [
    '"',
    '"ember',
    'ember"',
    '""',
    "*",
    "ember*",
    "NEAR",
    "NEAR(ember frost)",
    "NEAR(ember frost, 2)",
    "ember OR",
    "OR ember",
    "ember AND",
    "AND",
    "NOT",
    "NOT ember",
    "ember NOT",
    "-",
    "-ember",
    "ember - frost",
    "^",
    "^ember",
    ":",
    "name:ember",
    "oracle_text:ember",
    "{name type_line}:ember",
    "-name:ember",
    "(",
    ")",
    "(ember",
    "ember)",
    "(ember OR frost) AND NOT (cinder)",
    '"ember" + "frost"',
    "ember\tfrost\nash",
    "  ember   frost  ",
    "",
    "   ",
    "émber ✦ 火 überfrost \U0001F525",
    "{G/U} {2/W} {B/P} {C}",
    "'); DROP TABLE oracle_fts; --",
    "%s ? ; \\ %",
    "ember " * 2000,
    "x" * 20000,
]


@pytest.mark.django_db
@pytest.mark.parametrize("query", HOSTILE_QUERIES)
def test_t23_rn12_query_with_fts5_operator_characters_does_not_raise(query):
    """RN-12 (plan 9.1): user text with FTS5 syntax, odd characters or huge length
    is searched as plain text and never raises."""
    _card("Ashen Wisp", "Ember and frost, near the old ember.")
    _non_matching_fillers(2)
    _index()

    results = _search(query)

    assert isinstance(results, list)
    # The full-text table is intact after the query.
    assert _search("ember")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "query",
    [
        '"ember',
        'ember"',
        "(ember)",
        "-ember",
        "ember ::",
        "ember *",
        "ember ^",
        "ember ( )",
    ],
)
def test_t23_rn12_operator_characters_around_a_word_still_find_the_word(query):
    """RN-12 (plan 9.1): quotes, parentheses, dashes and lone symbols around a word
    are not syntax: the word is still searched."""
    card = _card("Ashen Wisp", "Ember glows in the dark.")
    _non_matching_fillers(2)
    _index()

    assert _oid(card.oracle_id) in _ids(_search(query))


@pytest.mark.django_db
def test_t23_rn12_not_is_a_word_not_an_operator():
    """RN-12 (plan 9.1): "frost NOT ember" finds a card that holds the three words;
    as an operator it would exclude the card for holding "ember"."""
    card = _card("Ashen Wisp", "Frost that does not fade, ember that does not cool.")
    _non_matching_fillers(2)
    _index()

    assert _oid(card.oracle_id) in _ids(_search("frost NOT ember"))


@pytest.mark.django_db
@pytest.mark.parametrize("query", ["frost OR ember", "frost AND ember", "NEAR(frost ember)"])
def test_t23_rn12_operator_words_found_as_plain_words(query):
    """RN-12 (plan 9.1): a card holding every word of the query, operator words
    included, is found."""
    card = _card("Ashen Wisp", "Walk near frost or ember, and frost and ember answer.")
    _non_matching_fillers(2)
    _index()

    assert _oid(card.oracle_id) in _ids(_search(query))


@pytest.mark.django_db
def test_t23_rn12_colon_is_not_a_column_filter():
    """RN-12 (plan 9.1): "name:ember" is plain text: it finds a card whose rules
    text says "name ember" though its name lacks the word."""
    card = _card("Coldwater Heron", "Speak the name ember and it answers.")
    _non_matching_fillers(2)
    _index()

    assert _oid(card.oracle_id) in _ids(_search("name:ember"))


@pytest.mark.django_db
def test_t23_rn12_caret_is_not_an_initial_token_operator():
    """RN-12 (plan 9.1): "^ember" is plain text: it finds "ember" anywhere, not only
    as the first word of a column."""
    card = _card("Coldwater Heron", "The old ember glows.")
    _non_matching_fillers(2)
    _index()

    assert _oid(card.oracle_id) in _ids(_search("^ember"))


@pytest.mark.django_db
def test_t23_rn12_asterisk_is_not_a_prefix_operator():
    """RN-12 (plan 9.1): "ember*" is the word "ember", not a prefix: a card that only
    says "emberglow" is not found, a card that says "ember" is."""
    prefix_only = _card("Coldwater Heron", "Emberglow spreads.")
    word = _card("Ashen Wisp", "An ember spreads.")
    _non_matching_fillers(2)
    _index()

    results = _search("ember*")

    assert _oid(word.oracle_id) in _ids(results)
    assert _oid(prefix_only.oracle_id) not in _ids(results)


@pytest.mark.django_db
def test_t23_rn12_query_words_match_regardless_of_case():
    """RN-12 (plan 9.1): "EMBER" finds a card that says "ember"."""
    card = _card("Ashen Wisp", "An ember spreads.")
    _index()

    assert _oid(card.oracle_id) in _ids(_search("EMBER"))


# --- Review additions: relevant set, empty query, caps, legal-only widening --


def _constant(name):
    from catalog import selectors

    return getattr(selectors, name)


@pytest.mark.django_db
def test_t23_rn12_strong_reorders_by_edhrec_only_inside_the_bm25_relevant_set():
    """RN-12 (plan 9.1): strong takes the top results by BM25, then orders them by
    EDHREC rank; many well-ranked cards that share only a common word ("creature")
    never push out an unranked card that matches every specific word."""
    max_results = _constant("MAX_RESULTS")
    for n in range(max_results + 5):
        _card(f"Meadow Hermit {n}", FILLER, type_line="Creature — Elf", edhrec_rank=n + 1)
    specific = _card(
        "Thornspike Warden",
        "Thornspike thornspike gloamseed gloamseed.",
        type_line="Creature — Elf",
        edhrec_rank=None,
    )
    _index()

    results = _search("creature thornspike gloamseed", power_level="strong")

    assert _oid(specific.oracle_id) in _ids(results)
    assert len(results) <= max_results


@pytest.mark.django_db
@pytest.mark.parametrize("query", ["", "::", "   ", '"" * ( )'])
def test_t23_rn12_query_without_usable_token_returns_filtered_candidates_by_edhrec(query):
    """RN-04 / RN-12: a query with no usable word is not an empty result: the
    candidates still pass identity and legality, ordered by EDHREC rank (lower
    first), unranked last."""
    best = _card("Briar Elk", "Gains reach.", edhrec_rank=1)
    second = _card("Fen Stag", "Gains vigilance.", edhrec_rank=5)
    unranked = _card("Moss Hare", "Gains haste.", edhrec_rank=None)
    blue = _card("Tide Diver", "Gains flying.", identity=("U",), edhrec_rank=2)
    not_legal = _card("Odd Schemer", "Gains nothing.", legality="not_legal", edhrec_rank=3)
    banned = _card("Gloom Tyrant", "Gains all.", legality="banned", edhrec_rank=4)
    _index()

    results = _search(query)

    comparables = [item for item in results if not item["counterexample"]]
    assert _ids(comparables) == [_oid(c.oracle_id) for c in (best, second, unranked)]
    assert not _id_set(results) & _cards_ids(blue, not_legal)
    if _oid(banned.oracle_id) in _ids(results):
        assert _item(results, banned)["counterexample"] is True


@pytest.mark.django_db
@pytest.mark.parametrize("query", ["", "::"])
def test_t23_rn12_query_without_usable_token_still_filters_roles(query):
    """RN-12: with no usable word the roles filter still applies."""
    removal = _card("Briar Smiter", "Fights.", roles=["removal"], edhrec_rank=2)
    ramp = _card("Briar Gardener", "Grows.", roles=["ramp"], edhrec_rank=1)
    _index()

    results = _search(query, roles=["removal"])

    assert _id_set(results) == _cards_ids(removal)
    assert _oid(ramp.oracle_id) not in _ids(results)


@pytest.mark.django_db
def test_t23_rn12_results_are_capped_at_max_results():
    """RN-12: 45 matching cards give MAX_RESULTS (40) results."""
    max_results = _constant("MAX_RESULTS")
    assert max_results == 40
    for n in range(max_results + 5):
        _card(f"Lantern Elk {n}", "A lantern glows. " + FILLER * (n % 4))
    _index()

    for level in ("casual", "medium", "strong"):
        assert len(_search("lantern", power_level=level)) == max_results


@pytest.mark.django_db
def test_t23_rn12_query_with_seventy_distinct_words_does_not_raise():
    """RN-12: a query longer than MAX_QUERY_TOKENS words is searched without error,
    and a card holding every word is found."""
    words = [f"glyph{n}" for n in range(70)]
    card = _card("Ashen Wisp", " ".join(words))
    _non_matching_fillers(2)
    _index()

    results = _search(" ".join(words))

    assert _oid(card.oracle_id) in _ids(results)


@pytest.mark.django_db
def test_t23_rn04_widening_counts_legal_results_only():
    """RN-04 / RN-12 (plan 9.1): banned counterexamples do not count toward the
    minimum: 3 legal plus 8 banned cards in range still drop the mana value, and
    the type filter stays once the legal cards reach ten."""
    in_range = [_card(f"Lantern Elk {n}", "A lantern glows.", cmc=3.0) for n in range(3)]
    banned = [_card(f"Lantern Tyrant {n}", "A lantern glows.", cmc=3.0, legality="banned") for n in range(8)]
    out_of_range = [_card(f"Lantern Titan {n}", "A lantern glows.", cmc=7.0) for n in range(7)]
    other_type = [
        _card(f"Lantern Shrine {n}", "A lantern glows.", cmc=3.0, type_line="Enchantment") for n in range(2)
    ]
    _index()

    results = _search("lantern", card_types=["Creature"], mana_value_min=2, mana_value_max=4)

    comparables = [item for item in results if not item["counterexample"]]
    assert _id_set(comparables) == _cards_ids(*in_range, *out_of_range)
    assert not _id_set(results) & _cards_ids(*other_type)
    for item in results:
        if _oid(item["oracle_id"]) in _cards_ids(*banned):
            assert item["counterexample"] is True


@pytest.mark.django_db
def test_t23_rn12_card_types_match_any_face_of_the_type_line():
    """RN-12: "Creature — Elf // Sorcery — Adventure" holds the type Sorcery, so
    card_types=["Sorcery"] keeps it before any widening."""
    adventures = [
        _card(f"Lantern Wanderer {n}", "A lantern glows.", type_line="Creature — Elf // Sorcery — Adventure")
        for n in range(MINIMUM_RESULTS)
    ]
    plain = [_card(f"Lantern Elk {n}", "A lantern glows.", type_line="Creature — Elk") for n in range(2)]
    _index()

    results = _search("lantern", card_types=["Sorcery"])

    assert _id_set(results) == _cards_ids(*adventures)
    assert not _id_set(results) & _cards_ids(*plain)


@pytest.mark.django_db
@pytest.mark.parametrize("level", ["legendary", "", "extreme"])
def test_t23_rn12_unknown_power_level_raises_value_error(level):
    """RN-11 / RN-12: a power level other than casual, medium or strong is a ValueError."""
    _card("Lantern Elk", "A lantern glows.")
    _index()

    with pytest.raises(ValueError):
        _search("lantern", power_level=level)
