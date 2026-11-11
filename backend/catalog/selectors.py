"""Read queries of the catalog app.
Details: specs/plan.md, sections 5 and 7.
"""

import re
import unicodedata

from django.db import connection
from django.db.models.expressions import RawSQL

from catalog import sources
from catalog.models import BuildRun, OracleCard, SourceRecord

TYPOGRAPHIC_APOSTROPHES = str.maketrans({"’": "'", "‘": "'", "ʼ": "'"})


def normalize_name(name):
    """A card name as names are compared: case folded, single spaces, no surrounding spaces, straight apostrophes."""
    # Kept equal to validators.name.normalize_name: catalog does not import the validators (plan section 3).
    return " ".join(name.translate(TYPOGRAPHIC_APOSTROPHES).casefold().split())


def is_ready() -> bool:
    """True when a completed build of the current catalog version exists (see spec RN-03)."""
    return BuildRun.objects.filter(catalog_version=sources.CATALOG_VERSION).exists()


def list_sources():
    """The stored source records, with origin, publication date and download date (see spec RN-01)."""
    return list(SourceRecord.objects.order_by("source"))


def power_toughness(oracle_ids):
    """Power and toughness by oracle id, for the cards that have them (None for the others)."""
    rows = OracleCard.objects.filter(oracle_id__in=list(oracle_ids)).values_list("oracle_id", "power", "toughness")
    return {str(oracle_id): (power, toughness) for oracle_id, power, toughness in rows}


def existing_card_names():
    """The normalized names of every reference card and of each of its faces (see spec RN-51)."""
    names = set()
    for name, faces in OracleCard.objects.values_list("name", "faces").iterator():
        names.add(normalize_name(name))
        for face in faces or []:
            face_name = face.get("name") if isinstance(face, dict) else None
            if isinstance(face_name, str):
                names.add(normalize_name(face_name))
    names.discard("")
    return frozenset(names)


# Fewer comparables than this widen the filters (plan section 9.1).
MINIMUM_RESULTS = 10
# The candidates handed to the draft call; enough to pick comparables from.
MAX_RESULTS = 40
# Bounds the MATCH expression a long keyword list builds.
MAX_QUERY_TOKENS = 64
# Mana values this far beyond the requested range still pass the first widening stage.
MANA_VALUE_TOLERANCE = 1

# Fixed statement; the MATCH expression is always a bound parameter.
_FTS_SCORES = "SELECT oracle_id, bm25(oracle_fts) FROM oracle_fts WHERE oracle_fts MATCH %s"
_FTS_IDS = "SELECT oracle_id FROM oracle_fts WHERE oracle_fts MATCH %s"
_UNRANKED = float("inf")

# Rules-text words that say little about what a card does; a card matching only these ranks after any card
# matching another keyword (plan section 9.1).
COMMON_WORDS = frozenset(
    "a an and any all are as at be by can card cards control controls creature creatures each end for from "
    "get gets have if in into is it its of on one or other player players target that the then this to "
    "turn until you your".split()
)
_WORD = re.compile(r"\w+")


def _words(text):
    """The words of `text` as the full-text index folds them: case and diacritics removed."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return _WORD.findall("".join(char for char in decomposed if not unicodedata.combining(char)))


def _query_tokens(query):
    """The distinct words of `query` that hold a letter or digit, at most MAX_QUERY_TOKENS."""
    tokens = []
    seen = set()
    for token in query.split() if isinstance(query, str) else []:
        key = token.casefold()
        if key in seen or not any(char.isalnum() for char in token):
            continue
        seen.add(key)
        tokens.append(token)
        if len(tokens) == MAX_QUERY_TOKENS:
            break
    return tokens


def _match_expression(tokens):
    """Each token as a quoted FTS5 string joined by OR, or None when there is none.

    Quoting makes operators, column filters and prefixes plain text (plan section 9.1).
    """
    return " OR ".join('"' + token.replace('"', '""') + '"' for token in tokens) or None


def _creature_subtypes(type_line):
    """The folded words after the dash of each creature face of the type line."""
    subtypes = set()
    for face in type_line.split("//"):
        head, dash, tail = face.partition("—")
        if dash and "creature" in _words(head):
            subtypes.update(_words(tail))
    return subtypes


def _keyword_relevance(card, keywords):
    """(has no creature subtype keyword, matches no uncommon keyword).

    A keyword matches when all its words are in the name, type line or rules text of the card.
    """
    subtypes = _creature_subtypes(card.type_line)
    words = set(_words(f"{card.name} {card.type_line} {card.oracle_text}"))
    subtype_match = False
    uncommon = False
    for parts in keywords:
        if subtypes & set(parts):
            subtype_match = True
        if parts and all(part in words for part in parts) and not all(part in COMMON_WORDS for part in parts):
            uncommon = True
    return (not subtype_match, not uncommon)


def _card_types(type_line):
    """The words before the dash of each face of the type line, folded: card types and supertypes."""
    return {word.casefold() for face in type_line.split("//") for word in face.split("—")[0].split()}


def _search_item(card):
    """The candidate context the draft call reads (plan section 9.1)."""
    return {
        "oracle_id": str(card.oracle_id),
        "name": card.name,
        "mana_cost": card.mana_cost,
        "mana_value": card.cmc,
        "type_line": card.type_line,
        "oracle_text": card.oracle_text,
        "color_identity": list(card.color_identity),
        "roles": list(card.roles),
        "game_changer": card.game_changer,
        "edhrec_rank": card.edhrec_rank,
        "counterexample": card.commander_legality == OracleCard.CommanderLegality.BANNED,
    }


POWER_LEVELS = ("casual", "medium", "strong")
# The fields the filters, the ordering and the search items read.
_SEARCH_FIELDS = (
    "oracle_id",
    "name",
    "mana_cost",
    "cmc",
    "type_line",
    "oracle_text",
    "color_identity",
    "roles",
    "game_changer",
    "edhrec_rank",
    "commander_legality",
)


def search_cards(query, filters):
    """Candidate comparables for a request, banned cards marked as counterexamples (see spec RN-04, RN-12).

    Details: specs/plan.md, section 9.1 (filters, power level, ranking, widening).
    """
    power_level = filters["power_level"]
    if power_level not in POWER_LEVELS:
        raise ValueError(f"Unknown power level: {power_level!r}.")
    candidates = OracleCard.objects.only(*_SEARCH_FIELDS).filter(
        commander_legality__in=[OracleCard.CommanderLegality.LEGAL, OracleCard.CommanderLegality.BANNED],
    )
    if power_level == "casual":
        candidates = candidates.filter(game_changer=False)

    tokens = _query_tokens(query)
    keywords = [_words(token) for token in tokens]
    expression = _match_expression(tokens)
    scores = None
    if expression is not None:
        with connection.cursor() as cursor:
            cursor.execute(_FTS_SCORES, [expression])
            scores = {str(oracle_id): score for oracle_id, score in cursor.fetchall()}
        # A subquery, not the ids as parameters: a common word can match more cards than SQLite binds.
        candidates = candidates.filter(oracle_id__in=RawSQL(_FTS_IDS, [expression]))

    requested = set(filters["color_identity"])
    roles = set(filters.get("roles") or [])
    kept = [
        card
        for card in candidates
        if set(card.color_identity) <= requested and (not roles or roles & set(card.roles))
    ]

    stages = _widening_stages(filters)
    for index, matches in enumerate(stages):
        found = [card for card in kept if matches(card)]
        comparables = sum(card.commander_legality == OracleCard.CommanderLegality.LEGAL for card in found)
        if comparables >= MINIMUM_RESULTS or index == len(stages) - 1:
            break

    if scores is None:
        # No usable keyword: popularity is the only order left.
        found.sort(key=lambda card: _popularity_order(card, 0.0))
        return [_search_item(card) for card in found[:MAX_RESULTS]]

    def score(card):
        return scores.get(card.oracle_id.hex, _UNRANKED)

    # Relevance (tier, then BM25) picks the candidates; strong then reorders inside each tier.
    tiers = {card.oracle_id: _keyword_relevance(card, keywords) for card in found}
    found.sort(key=lambda card: _relevance_order(card, tiers[card.oracle_id], score(card)))
    found = found[:MAX_RESULTS]
    if power_level == "strong":
        found = _rank_sum_order(found, tiers, score)
    return [_search_item(card) for card in found]


def _widening_stages(filters):
    """Card predicates from the strictest to the widest: mana value (with tolerance) goes first, then card types."""
    low, high = filters.get("mana_value_min"), filters.get("mana_value_max")
    types = {card_type.casefold() for card_type in filters.get("card_types") or []}

    def in_tolerated_range(card):
        return (low is None or card.cmc >= low - MANA_VALUE_TOLERANCE) and (
            high is None or card.cmc <= high + MANA_VALUE_TOLERANCE
        )

    def of_type(card):
        return not types or bool(types & _card_types(card.type_line))

    return [
        lambda card: in_tolerated_range(card) and of_type(card),
        of_type,
        lambda card: True,
    ]


def _relevance_order(card, tier, score):
    # bm25() is lower for a better match.
    return (tier, score, card.name, card.oracle_id.hex)


def _popularity_order(card, score):
    rank = card.edhrec_rank
    return (rank is None, rank or 0, score, card.name, card.oracle_id.hex)


def _competition_ranks(values):
    """The 1-based rank of each value, lowest first; equal values share the lowest rank (competition ranking)."""
    ordered = sorted(values)
    return [ordered.index(value) + 1 for value in values]


def _rank_sum_order(cards, tiers, score):
    """Cards ordered by tier, then by the sum of the BM25 rank and the EDHREC rank within the tier.

    Both ranks are taken among the cards of the tier; a card with no EDHREC rank ranks after the others.
    Ties go to BM25, then name, then id.
    """
    by_tier = {}
    for card in cards:
        by_tier.setdefault(tiers[card.oracle_id], []).append(card)
    ordered = []
    for tier in sorted(by_tier):
        group = by_tier[tier]
        bm25_ranks = _competition_ranks([score(card) for card in group])
        popularity_ranks = _competition_ranks([_UNRANKED if card.edhrec_rank is None else card.edhrec_rank for card in group])
        keyed = [
            (bm25_rank + popularity_rank, score(card), card.name, card.oracle_id.hex, card)
            for card, bm25_rank, popularity_rank in zip(group, bm25_ranks, popularity_ranks)
        ]
        ordered.extend(entry[-1] for entry in sorted(keyed, key=lambda entry: entry[:-1]))
    return ordered
