"""Read queries of the catalog app.
Details: specs/plan.md, sections 5 and 7.
"""

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

# Fixed statement; the MATCH expression is always a bound parameter.
_FTS_SCORES = "SELECT oracle_id, bm25(oracle_fts) FROM oracle_fts WHERE oracle_fts MATCH %s"
_FTS_IDS = "SELECT oracle_id FROM oracle_fts WHERE oracle_fts MATCH %s"
_UNRANKED = float("inf")


def _match_expression(query):
    """Each word of `query` as a quoted FTS5 string joined by OR, or None when no word is left.

    Quoting makes operators, column filters and prefixes plain text (plan section 9.1).
    """
    tokens = []
    seen = set()
    for token in query.split() if isinstance(query, str) else []:
        key = token.casefold()
        if key in seen or not any(char.isalnum() for char in token):
            continue
        seen.add(key)
        tokens.append('"' + token.replace('"', '""') + '"')
        if len(tokens) == MAX_QUERY_TOKENS:
            break
    return " OR ".join(tokens) or None


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

    expression = _match_expression(query)
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

    # Relevance picks the candidates; strong then orders them by popularity.
    found.sort(key=lambda card: _relevance_order(card, score(card)))
    found = found[:MAX_RESULTS]
    if power_level == "strong":
        found.sort(key=lambda card: _popularity_order(card, score(card)))
    return [_search_item(card) for card in found]


def _widening_stages(filters):
    """Card predicates from the strictest to the widest: mana value goes first, then card types."""
    low, high = filters.get("mana_value_min"), filters.get("mana_value_max")
    types = {card_type.casefold() for card_type in filters.get("card_types") or []}

    def in_mana_range(card):
        return (low is None or card.cmc >= low) and (high is None or card.cmc <= high)

    def of_type(card):
        return not types or bool(types & _card_types(card.type_line))

    return [
        lambda card: in_mana_range(card) and of_type(card),
        of_type,
        lambda card: True,
    ]


def _relevance_order(card, score):
    # bm25() is lower for a better match.
    return (score, card.name, card.oracle_id.hex)


def _popularity_order(card, score):
    rank = card.edhrec_rank
    return (rank is None, rank or 0, score, card.name, card.oracle_id.hex)
