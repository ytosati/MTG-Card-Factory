"""The comparables ranking after the first evaluation (task T160, spec RN-04, RN-12, CA-24).

Details: specs/plan.md, section 9.1 (filters, power level shaping, FTS5 BM25
ranking) and specs/manual-checks.md, "Search quality evaluation (T26), first run".

Contracts under test, all through the API of catalog.selectors.search_cards:

    creature types   a keyword that is a creature subtype (a word after the dash
                     of a creature type line, case-insensitive) ranks the cards
                     whose type line has it before the others.
    common words     a card matching only common rules-text words ranks after a
                     card matching a less common keyword.
    two roles        a plan with several roles returns the cards with any of them.
    within a tier    medium and casual order by BM25 alone; strong orders by the
                     sum of the BM25 rank and the EDHREC rank (unranked last), ties
                     by BM25, then name, then id; popularity never crosses a tier;
                     casual still excludes Game Changer cards.
    mana value       the first stage widens the requested range by
                     MANA_VALUE_TOLERANCE on each side; cards beyond it come back
                     only through the widening.
    counterexamples  a banned card keeps its flag (CA-24).

Every catalog row is fictional and written by hand. The helpers follow the
T23 search tests (tests/test_catalog_search.py), which are not changed here.
"""

import uuid

import pytest
from django.db import connection

LEVELS = ("casual", "medium", "strong")

# Rules text made only of common words: the words named in T160 and some more.
COMMON_TEXT = (
    "Creatures you control get +1/+1 until end of turn. "
    "Creatures you control gain all keywords until the turn ends."
)
MANA_TEXT = "Add mana from a forest. Draw a card."
QUIET_TEXT = "Scry one, then shuffle."

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


def _oids(*cards):
    return [_oid(card.oracle_id) for card in cards]


def _in_order(results, *cards):
    """The oracle ids of the given cards, in the order of the results."""
    wanted = _cards_ids(*cards)
    return [oid for oid in _ids(results) if oid in wanted]


_BM25_SCORES = "SELECT oracle_id, bm25(oracle_fts) FROM oracle_fts WHERE oracle_fts MATCH %s"


def _bm25_scores(query, *cards):
    """The BM25 scores of the cards for the query, in the order of the cards (a lower score is a better match).

    The match expression is built as the search builds it.
    """
    expression = " OR ".join('"' + word + '"' for word in query.split())
    with connection.cursor() as cursor:
        cursor.execute(_BM25_SCORES, [expression])
        scores = {_oid(oracle_id): score for oracle_id, score in cursor.fetchall()}
    return [scores[_oid(card.oracle_id)] for card in cards]


def _bm25_order(query, *cards):
    """The oracle ids of the cards ordered by BM25 alone; the scores must differ so the order is defined."""
    scores = _bm25_scores(query, *cards)
    assert len(set(scores)) == len(scores), "the BM25 scores must differ to define an order"
    return [oid for _, oid in sorted(zip(scores, _oids(*cards)))]


def _quiet(count=6):
    """Cards holding none of the query words: they give the words a positive weight in BM25."""
    return [_card(f"Quiet Meadow Hermit {n}", "Gains reach.", type_line="Creature — Human Monk") for n in range(count)]


def _wisp(name, cmc):
    return _card(name, "Flying.", type_line="Creature — Spirit", cmc=cmc)


def _constant(name):
    from catalog import selectors

    return getattr(selectors, name)


FILLER = (
    "Tap an untapped creature you control. Put a counter on target permanent. "
    "Each player shuffles. Scry one. Then the turn continues as normal. "
)


def _common_corpus(common=4, quiet=25):
    """Cards that make the common words common (about a fifth of the corpus holds
    them) and the rest of the corpus quiet. Every name is free of the query words."""
    for n in range(common):
        _card(f"Garden Crier {n}", COMMON_TEXT, type_line="Creature — Human Soldier")
    for n in range(quiet):
        _card(f"Quiet Meadow Hermit {n}", QUIET_TEXT, type_line="Creature — Human Monk")


def _mana_corpus():
    """Creatures whose rules text holds four common-ish words of the query, so that
    the words together outweigh one rare word; returns the three of them that lack
    the creature subtype."""
    for n in range(5):
        _card(f"Grove Tender {n}", MANA_TEXT, type_line="Creature — Human Monk")
    for n in range(20):
        _card(f"Quiet Meadow Hermit {n}", QUIET_TEXT, type_line="Creature — Human Monk")
    return [
        _card("Brass Conjurer", MANA_TEXT, type_line="Creature — Human Wizard", edhrec_rank=20),
        _card("Ember Conjurer", MANA_TEXT, type_line="Creature — Human Wizard", edhrec_rank=30),
        _card("Dust Conjurer", MANA_TEXT, type_line="Creature — Human Wizard", edhrec_rank=40),
    ]


# --- Creature types: a subtype keyword ranks the cards that have it ---------


@pytest.mark.django_db
@pytest.mark.parametrize("level", LEVELS)
@pytest.mark.parametrize("keyword", ["elf", "ELF", "Elf"])
def test_t160_rn12_creature_subtype_keyword_ranks_the_matching_type_first(keyword, level):
    """T160 creature types, RN-12: "elf" in the type line of a creature ranks it before
    creatures that match more words in their rules text, at every power level and
    whatever the case of the keyword."""
    subtype_card = _card(
        "Mossveil Druid",
        "Tap this creature for {G}.",
        type_line="Creature — Elf Druid",
        edhrec_rank=9000,
    )
    rules = _mana_corpus()
    _index()

    results = _search(f"{keyword} add mana forest draw", power_level=level)

    assert _oid(subtype_card.oracle_id) in _ids(results)
    assert _position(results, subtype_card) < min(_position(results, card) for card in rules)


@pytest.mark.django_db
@pytest.mark.parametrize("level", LEVELS)
@pytest.mark.parametrize(
    ("keyword", "type_line"),
    [
        ("werewolf", "Creature — Human Werewolf // Creature — Werewolf"),
        ("wolf", "Creature — Human Werewolf // Creature — Wolf"),
    ],
)
def test_t160_rn12_subtype_on_either_face_of_a_double_faced_type_line_counts(keyword, type_line, level):
    """T160 creature types, RN-12: a subtype on the front or the back face of a
    double-faced type line ("//") ranks the card before the rules-heavy creatures."""
    flipped = _card("Thornback Seer", "Tap this creature for {G}.", type_line=type_line, edhrec_rank=9000)
    rules = _mana_corpus()
    _index()

    results = _search(f"{keyword} add mana forest draw", power_level=level)

    assert _oid(flipped.oracle_id) in _ids(results)
    assert _position(results, flipped) < min(_position(results, card) for card in rules)


@pytest.mark.django_db
@pytest.mark.parametrize("level", LEVELS)
@pytest.mark.parametrize("keyword", ["ánimo", "ÁNIMO"])
def test_t160_rn12_creature_subtype_match_ignores_the_case_of_non_ascii_letters(keyword, level):
    """T160 creature types, RN-12: the subtype comparison is case-insensitive for
    non-ASCII letters too."""
    subtype_card = _card(
        "Sprig Marsh",
        "Tap this creature for {G}.",
        type_line="Creature — Ánimo Sprite",
        edhrec_rank=9000,
    )
    rules = _mana_corpus()
    _index()

    results = _search(f"{keyword} add mana forest draw", power_level=level)

    assert _position(results, subtype_card) < min(_position(results, card) for card in rules)


@pytest.mark.django_db
@pytest.mark.parametrize("level", LEVELS)
def test_t160_rn12_keyword_that_is_not_a_creature_subtype_gets_no_boost(level):
    """T160 creature types, RN-12: "scry" and "mill" are not creature subtypes, so the
    "Elf" of the first card gives it no boost. The order inside the tier is the BM25
    order: the card holding both words, one of them twice, ranks first. Quiet cards
    keep the idf of the words positive."""
    subtype_card = _card("Mossveil Druid", "Scry.", type_line="Creature — Elf Druid", edhrec_rank=50)
    matching_more = _card("Brass Conjurer", "Scry. Mill. Scry.", type_line="Creature — Human Wizard", edhrec_rank=5000)
    _quiet()
    _index()

    results = _search("scry mill", power_level=level)

    expected = _bm25_order("scry mill", subtype_card, matching_more)
    assert expected == _oids(matching_more, subtype_card)
    assert _in_order(results, subtype_card, matching_more) == expected


@pytest.mark.django_db
@pytest.mark.parametrize("level", LEVELS)
def test_t160_rn12_subtype_word_of_a_non_creature_type_line_is_not_promoted(level):
    """T160 creature types, RN-12: "Aura" after the dash of an enchantment type line is
    not a creature subtype; the creature that uses the word more often still comes first."""
    aura = _card(
        "Gilded Chain",
        "Enchant creature. Enchanted creature can't attack.",
        type_line="Enchantment — Aura",
        edhrec_rank=9000,
    )
    rules = _card("Moss Conjurer", "Aura. Aura. Aura.", type_line="Creature — Human Wizard", edhrec_rank=20)
    _index()

    results = _search("aura", power_level=level)

    assert _position(results, rules) < _position(results, aura)


@pytest.mark.django_db
@pytest.mark.parametrize("level", LEVELS)
def test_t160_rn12_subtype_match_outranks_a_huge_rules_text(level):
    """T160 creature types, RN-12: a card with the subtype still ranks first when the
    other candidate's rules text is very long (about two thousand repeated words)."""
    subtype_card = _card(
        "Mossveil Druid",
        "Tap this creature for {G}.",
        type_line="Creature — Elf Druid",
        edhrec_rank=9000,
    )
    huge = _card("Brass Conjurer", "Add mana. " * 2000, type_line="Creature — Human Wizard", edhrec_rank=20)
    _index()

    results = _search("elf add mana forest draw", power_level=level)

    assert _position(results, subtype_card) < _position(results, huge)


@pytest.mark.django_db
@pytest.mark.parametrize("level", LEVELS)
def test_t160_rn12_subtype_keyword_first_in_a_query_longer_than_the_token_cap(level):
    """T160 creature types, RN-12: a long keyword list keeps the subtype keyword (the
    first word) and the subtype card still ranks first; no error is raised."""
    subtype_card = _card(
        "Mossveil Druid",
        "Tap this creature for {G}.",
        type_line="Creature — Elf Druid",
        edhrec_rank=9000,
    )
    rules = _mana_corpus()
    _index()
    query = " ".join(["elf", "add", "mana", "forest", "draw", *[f"glyph{n}" for n in range(70)]])

    results = _search(query, power_level=level)

    assert _position(results, subtype_card) < min(_position(results, card) for card in rules)


@pytest.mark.django_db
@pytest.mark.parametrize("level", LEVELS)
@pytest.mark.parametrize(
    "query",
    [
        "— elf add mana forest draw",
        "elf {G/U} {2/W} add mana forest draw",
        "elf -- add mana forest draw",
        'elf "add" mana forest draw',
        "elf 'mana' add forest draw",
        "elf (add mana) forest draw",
    ],
)
def test_t160_rn12_subtype_ranking_with_hybrid_symbols_and_punctuation_in_the_query(query, level):
    """T160 creature types, RN-12: dashes, hybrid mana symbols and quotes in the query
    are plain text; the subtype card is still returned and ranked first."""
    subtype_card = _card(
        "Mossveil Druid",
        "Tap this creature for {G}.",
        type_line="Creature — Elf Druid",
        edhrec_rank=9000,
    )
    rules = _mana_corpus()
    _index()

    results = _search(query, power_level=level)

    assert _oid(subtype_card.oracle_id) in _ids(results)
    assert _position(results, subtype_card) < min(_position(results, card) for card in rules)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "type_line",
    ["Creature", "Creature —", "Creature — ", "Creature — //", "Creature — Elf //", "//", ""],
)
def test_t160_rn12_malformed_type_line_is_searched_without_error(type_line):
    """T160 creature types, RN-12: a type line without a subtype, with an empty side
    of the dash or the "//", or empty, is searched without error and the card is
    still returned for a word of its rules text."""
    card = _card("Hollow Stag", "Scry one.", type_line=type_line)
    _index()

    results = _search("elf scry")

    assert _oid(card.oracle_id) in _ids(results)


# --- Common words weigh less ------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("level", LEVELS)
@pytest.mark.parametrize("keyword", ["indestructible", "hexproof"])
def test_t160_rn12_card_matching_only_common_words_ranks_after_a_less_common_match(keyword, level):
    """T160 common words, RN-12: a card whose matches are only common rules words
    (creatures, control, until, turn, ...) ranks after a card that matches the less
    common keyword, even though the first matches more words; popularity (EDHREC)
    is on the common-word card, so the strong order is tested too."""
    _common_corpus()
    common = [
        _card(f"Warlord Banner {n}", COMMON_TEXT, type_line="Creature — Human Soldier", edhrec_rank=10 + n)
        for n in range(3)
    ]
    specific = _card(
        "Stoneward Knight",
        f"{keyword.capitalize()}.",
        type_line="Creature — Human Knight",
        edhrec_rank=9000,
    )
    _index()

    results = _search(f"{keyword} creatures control until turn", power_level=level)

    assert _oid(specific.oracle_id) in _ids(results)
    assert all(_position(results, specific) < _position(results, card) for card in common)


@pytest.mark.django_db
@pytest.mark.parametrize("level", LEVELS)
def test_t160_rn12_common_words_alone_still_find_cards(level):
    """T160 common words, RN-12: a query made only of common words still finds the
    cards that hold them; the lower weight ranks them, it does not drop them."""
    _common_corpus()
    common = _card("Warlord Banner", COMMON_TEXT, type_line="Creature — Human Soldier")
    _index()

    results = _search("creatures control until turn", power_level=level)

    assert _oid(common.oracle_id) in _ids(results)


# --- Two roles --------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("level", LEVELS)
@pytest.mark.parametrize("roles", [["tokens", "combat_boost"], ["protection", "card_draw"]])
def test_t160_rn12_plan_with_two_roles_returns_cards_with_either_role(roles, level):
    """T160 two roles, RN-12: a plan with two roles returns the cards with either role,
    the cards with both, and never a card with neither (the T23 test covers
    the same filter with a single query; this one uses the roles of the evaluation)."""
    first = _card("Herald Pilgrim", "Create a token.", roles=[roles[0]])
    second = _card("Banner Crier", "Creatures get +1/+0.", roles=[roles[1]])
    both = _card("Chorus Marshal", "Create a token. Creatures get +1/+0.", roles=list(roles))
    neither = _card("Idle Monument", "Create a token. Creatures get nothing.", roles=[])
    _index()

    results = _search("create token creatures get", power_level=level, roles=roles)

    assert _cards_ids(first, second, both) <= _id_set(results)
    assert _oid(neither.oracle_id) not in _ids(results)


# --- Power level shaping ----------------------------------------------------


@pytest.mark.django_db
def test_t160_rn12_strong_does_not_lift_a_popular_card_without_the_creature_type():
    """T160 power level, RN-12: under strong, a popular card that matches only common
    words stays below a less popular card that has the creature subtype asked for."""
    _common_corpus()
    popular = _card("Warlord Banner", COMMON_TEXT, type_line="Creature — Human Soldier", edhrec_rank=10)
    niche = _card("Mossveil Druid", "Tap this creature for {G}.", type_line="Creature — Elf Druid", edhrec_rank=4000)
    _index()

    results = _search("elf creatures control until turn", power_level="strong")

    assert _position(results, niche) < _position(results, popular)


@pytest.mark.django_db
def test_t160_rn12_strong_puts_an_unranked_card_last_among_equal_bm25_cards():
    """T160 contract 3 and tie convention, RN-12: cards with the same text have the same
    BM25 score and share its rank, so under strong popularity alone orders them, and the
    card with no EDHREC rank comes last."""
    first = _card("Ashen Wisp", "Ember.", edhrec_rank=50)
    second = _card("Cinder Moth", "Ember.", edhrec_rank=5000)
    unranked = _card("Dusk Heron", "Ember.", edhrec_rank=None)
    _quiet()
    _index()
    cards = (first, second, unranked)

    results = _search("ember", power_level="strong")

    assert len(set(_bm25_scores("ember", *cards))) == 1
    assert _in_order(results, *cards) == _oids(*cards)


@pytest.mark.django_db
def test_t160_rn12_strong_equal_bm25_is_decided_by_popularity_not_by_name():
    """T160 contract 3 and tie convention, RN-12: equal BM25 scores share a rank, so the
    more popular card comes first even when its name sorts after the other card's."""
    obscure = _card("Ashen Wisp", "Ember.", edhrec_rank=5000)
    popular = _card("Zephyr Wisp", "Ember.", edhrec_rank=50)
    _quiet()
    _index()

    results = _search("ember", power_level="strong")

    assert len(set(_bm25_scores("ember", obscure, popular))) == 1
    assert _in_order(results, obscure, popular) == _oids(popular, obscure)


@pytest.mark.django_db
def test_t160_rn12_casual_excludes_a_game_changer_card_with_the_creature_type():
    """T160 power level, RN-12: casual leaves out a Game Changer card even when it has
    the creature subtype asked for."""
    changer = _card(
        "Engine Elf",
        "Tap this creature for {G}.",
        type_line="Creature — Elf Druid",
        game_changer=True,
        edhrec_rank=5,
    )
    plain = _card("Mossveil Druid", "Tap this creature for {G}.", type_line="Creature — Elf Druid", edhrec_rank=4000)
    _index()

    results = _search("elf", power_level="casual")

    assert _id_set(results) == _cards_ids(plain)
    assert _oid(changer.oracle_id) not in _ids(results)


@pytest.mark.django_db
def test_t160_rn12_strong_keeps_a_game_changer_card_with_the_creature_type():
    """T160 power level, RN-12: strong keeps the Game Changer card that has the
    creature subtype, and ranks it by the new rules."""
    changer = _card(
        "Engine Elf",
        "Tap this creature for {G}.",
        type_line="Creature — Elf Druid",
        game_changer=True,
        edhrec_rank=5,
    )
    rules = _mana_corpus()
    _index()

    results = _search("elf add mana forest draw", power_level="strong")

    assert _oid(changer.oracle_id) in _ids(results)
    assert _position(results, changer) < min(_position(results, card) for card in rules)


@pytest.mark.django_db
def test_t160_rn12_medium_ranks_a_subtype_card_by_relevance_not_by_popularity():
    """T160 power level, RN-12: medium ranks by relevance alone: the creature type
    ranks the card first, and a very popular card that matches only common words stays
    after it."""
    _common_corpus()
    subtype_card = _card(
        "Mossveil Druid",
        "Tap this creature for {G}.",
        type_line="Creature — Elf Druid",
        edhrec_rank=9000,
    )
    popular = _card("Warlord Banner", COMMON_TEXT, type_line="Creature — Human Soldier", edhrec_rank=1)
    _index()

    results = _search("elf creatures control until turn", power_level="medium")

    assert _position(results, subtype_card) < _position(results, popular)


# --- Banned cards stay counterexamples (CA-24) ------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("level", LEVELS)
def test_t160_ca24_banned_card_with_the_creature_type_is_still_a_counterexample(level):
    """CA-24 / T160: a banned card that has the creature subtype asked for, even with
    a very high popularity, is returned once, flagged, and never as a comparable."""
    legal = _card("Mossveil Druid", "Tap this creature for {G}.", type_line="Creature — Elf Druid", edhrec_rank=500)
    banned = _card(
        "Tyrant Elf",
        "Tap this creature for {G}.",
        type_line="Creature — Elf Druid",
        legality="banned",
        edhrec_rank=1,
    )
    _index()

    results = _search("elf", power_level=level)

    assert _item(results, banned)["counterexample"] is True
    assert _item(results, legal)["counterexample"] is False
    comparables = [item for item in results if not item["counterexample"]]
    assert _oid(banned.oracle_id) not in _ids(comparables)


@pytest.mark.django_db
@pytest.mark.parametrize("level", LEVELS)
def test_t160_ca24_banned_card_matching_only_common_words_is_still_a_counterexample(level):
    """CA-24 / T160: the lower weight of common words does not drop a banned card
    that matches the request: it comes back flagged as a counterexample."""
    _common_corpus()
    banned = _card("Warlord Banner", COMMON_TEXT, type_line="Creature — Human Soldier", legality="banned")
    legal = _card("Stoneward Knight", "Indestructible.", type_line="Creature — Human Knight")
    _index()

    results = _search("indestructible creatures control until turn", power_level=level)

    assert _item(results, banned)["counterexample"] is True
    assert _item(results, legal)["counterexample"] is False


# --- Diacritics fold like the full-text index --------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("level", LEVELS)
def test_t160_rn12_unaccented_keyword_matches_an_accented_word_in_the_uncommon_tier(level):
    """T160 common words, RN-12: "eowyn" matches "Éowyn" in the index, so the card ranks
    before the cards that match only common words."""
    _common_corpus()
    common = _card("Warlord Banner", COMMON_TEXT, type_line="Creature — Human Soldier", edhrec_rank=1)
    accented = _card("Éowyn Scout", "Scry one.", type_line="Creature — Human Knight", edhrec_rank=9000)
    _index()

    results = _search("eowyn creatures control until turn", power_level=level)

    assert _position(results, accented) < _position(results, common)


@pytest.mark.django_db
@pytest.mark.parametrize("level", LEVELS)
def test_t160_rn12_unaccented_keyword_matches_an_accented_creature_subtype(level):
    """T160 creature types, RN-12: "anima" matches the subtype "Ánima" and ranks first."""
    subtype_card = _card("Sprig Marsh", "Tap this creature for {G}.", type_line="Creature — Ánima Sprite", edhrec_rank=9000)
    rules = _mana_corpus()
    _index()

    results = _search("anima add mana forest draw", power_level=level)

    assert _position(results, subtype_card) < min(_position(results, card) for card in rules)


# --- Second round: BM25 inside a tier, rank sum under strong, mana tolerance ---

SHORT_TEXT = "{T}: Add {C}{C}."
LONG_TEXT = (
    "Whenever another permanent enters the battlefield under your control, you may exile the top card of your "
    "library and add it to your hand. Each opponent may pay two life to ignore this effect, and any artifact "
    "spell they cast costs {C} less. Mana abilities of this card are never countered."
)


@pytest.mark.django_db
@pytest.mark.parametrize("level", ["medium", "casual"])
def test_t160_rn12_within_a_tier_medium_and_casual_order_by_bm25_not_by_keyword_count(level):
    """T160 contract 2, RN-12: within the same tier, medium and casual order by BM25
    alone. The short card holds "add" and "c" densely; the long card holds all four
    keywords once each. The number of keywords matched is not a rank: the order is
    the BM25 order, and the short card comes first."""
    short = _card("Sol Pendant", SHORT_TEXT, type_line="Artifact")
    long = _card("Grand Reliquary", LONG_TEXT, type_line="Artifact")
    _quiet()
    _index()
    query = "add mana artifact c"

    results = _search(query, power_level=level)

    expected = _bm25_order(query, short, long)
    assert expected == _oids(short, long)
    assert _in_order(results, short, long) == expected


@pytest.mark.django_db
def test_t160_rn12_strong_ranks_a_tier_by_the_sum_of_bm25_and_popularity_ranks():
    """T160 contract 3, RN-12: under strong, within a tier the order is the sum of the
    BM25 rank and the EDHREC rank. The middle card (second on BM25, first on popularity)
    comes first; the best BM25 card with poor popularity comes second. The pure BM25
    order and the pure popularity order are both different from the result."""
    best_match = _card("Ashen Wisp", "Ember ember ember.", edhrec_rank=None)
    middle_match = _card("Cinder Moth", "Ember. " + FILLER, edhrec_rank=50)
    weak_match = _card("Dusk Heron", "Ember. " + FILLER * 4, edhrec_rank=5000)
    _quiet()
    _index()
    cards = (best_match, middle_match, weak_match)

    results = _search("ember", power_level="strong")

    assert _bm25_order("ember", *cards) == _oids(best_match, middle_match, weak_match)
    assert _in_order(results, *cards) == _oids(middle_match, best_match, weak_match)


@pytest.mark.django_db
def test_t160_rn12_strong_lets_a_second_popularity_card_beat_the_most_popular_one():
    """T160 contract 3, RN-12: under strong, the most popular card that is last on BM25
    does not win outright: the card best on BM25 with the second popularity rank comes
    first (rank sum 3), the most popular card second (4), the middle card last (5)."""
    best_match = _card("Ashen Wisp", "Ember ember ember.", edhrec_rank=2000)
    middle_match = _card("Cinder Moth", "Ember. " + FILLER, edhrec_rank=3000)
    weak_match = _card("Dusk Heron", "Ember. " + FILLER * 4, edhrec_rank=100)
    _quiet()
    _index()
    cards = (best_match, middle_match, weak_match)

    results = _search("ember", power_level="strong")

    assert _bm25_order("ember", *cards) == _oids(best_match, middle_match, weak_match)
    assert _in_order(results, *cards) == _oids(best_match, weak_match, middle_match)


@pytest.mark.django_db
def test_t160_rn12_strong_breaks_a_rank_sum_tie_by_bm25():
    """T160 contract 3, RN-12: the best BM25 card with popularity rank 2 and the second
    BM25 card with popularity rank 1 both sum to 3; BM25 decides the tie."""
    best_match = _card("Ashen Wisp", "Ember ember ember.", edhrec_rank=5000)
    middle_match = _card("Cinder Moth", "Ember. " + FILLER, edhrec_rank=50)
    _quiet()
    _index()

    results = _search("ember", power_level="strong")

    assert _in_order(results, best_match, middle_match) == _oids(best_match, middle_match)


@pytest.mark.django_db
def test_t160_rn12_strong_never_lets_a_popular_lower_tier_card_overtake():
    """T160 contract 3, RN-12: a card matching only common words, with the best EDHREC
    rank, never comes before a card matching a less common keyword, even one with no
    rank: popularity does not cross tiers."""
    _common_corpus()
    popular = _card("Warlord Banner", COMMON_TEXT, type_line="Creature — Human Soldier", edhrec_rank=1)
    specific = _card("Stoneward Knight", "Indestructible.", type_line="Creature — Human Knight", edhrec_rank=None)
    _index()

    results = _search("indestructible creatures control until turn", power_level="strong")

    assert _position(results, specific) < _position(results, popular)


def test_t160_rn12_mana_value_tolerance_is_one():
    """T160 mana tolerance: the named constant of the first stage is 1."""
    assert _constant("MANA_VALUE_TOLERANCE") == 1


@pytest.mark.django_db
@pytest.mark.parametrize("level", LEVELS)
def test_t160_rn12_first_stage_accepts_one_mana_value_beyond_each_bound(level):
    """T160 mana tolerance, RN-12: with 3 to 5 requested and ten or more cards in range,
    the first stage keeps the cards of mana value 2 and 6 (one beyond each bound) and
    drops the cards of mana value 1 and 7 (two beyond)."""
    in_range = [_wisp(f"Ember Wisp {n}", float(cmc)) for n, cmc in enumerate([3, 4, 5] * 4)]
    low = _wisp("Ember Wisp Low", 2.0)
    high = _wisp("Ember Wisp High", 6.0)
    far_low = _wisp("Ember Wisp Far Low", 1.0)
    far_high = _wisp("Ember Wisp Far High", 7.0)
    _index()

    results = _search("wisp", power_level=level, mana_value_min=3, mana_value_max=5)

    assert _cards_ids(low, high) <= _id_set(results)
    assert _cards_ids(*in_range) <= _id_set(results)
    assert not _id_set(results) & _cards_ids(far_low, far_high)


@pytest.mark.django_db
@pytest.mark.parametrize("level", LEVELS)
def test_t160_rn12_cards_beyond_the_tolerance_come_back_only_through_the_widening(level):
    """T160 mana tolerance, RN-12: with fewer than MINIMUM_RESULTS comparables in the
    widened range, the widening drops the range and the cards of mana value 1 and 7
    are returned."""
    minimum = _constant("MINIMUM_RESULTS")
    in_range = [_wisp(f"Ember Wisp {n}", 3.0) for n in range(minimum - 1)]
    far = [_wisp("Ember Wisp Far Low", 1.0), _wisp("Ember Wisp Far High", 7.0)]
    _index()

    results = _search("wisp", power_level=level, mana_value_min=3, mana_value_max=5)

    assert _id_set(results) == _cards_ids(*in_range, *far)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("bounds", "in_range", "inside", "outside"),
    [
        ({"mana_value_min": 4}, [4.0 + n for n in range(10)], 3.0, 2.0),
        ({"mana_value_max": 4}, [float(n % 5) for n in range(10)], 5.0, 6.0),
    ],
)
def test_t160_rn12_one_sided_mana_range_widens_only_its_open_bound(bounds, in_range, inside, outside):
    """T160 mana tolerance, RN-12: with only a minimum of 4 or only a maximum of 4, and
    ten cards in range, the first stage keeps one mana value beyond the bound it has
    (3 or 5) and drops two (2 or 6)."""
    for n, cmc in enumerate(in_range):
        _wisp(f"Ember Wisp {n}", cmc)
    near = _wisp("Ember Wisp Near", inside)
    far = _wisp("Ember Wisp Far", outside)
    _index()

    results = _search("wisp", **bounds)

    assert _oid(near.oracle_id) in _ids(results)
    assert _oid(far.oracle_id) not in _ids(results)
