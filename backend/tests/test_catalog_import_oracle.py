"""Oracle Cards import with Commander legality (task T16, spec RN-01, RN-04).

Details: specs/plan.md, sections 4 (OracleCard), 5 (catalog.ingest), 7
(all-or-nothing build) and 10 (bulk files are read as a stream).

API under test:

    catalog.ingest.iter_bulk_records(fileobj)
        `fileobj` is a binary file object holding a bulk file as the data
        source publishes it: one JSON array of card objects. Yields one dict
        per card, in file order, reading the file in bounded pieces and never
        loading it whole.

    catalog.ingest.import_oracle(records)
        `records` is an iterable of Oracle Cards records (dicts shaped as in
        the bulk file). Stores one `OracleCard` per record: name, mana cost,
        mana value, type line, rules text, colors, color identity, keywords,
        power, toughness, layout, faces (from `card_faces`), Commander
        legality (from `legalities.commander`), the Game Changer flag and the
        EDHREC rank.

Out of scope here (later tasks): the transaction, deleting previous rows,
the FTS rebuild and the JSON-lines extraction (T21), role tagging (T20).

Every card below is fictional and written by hand.
"""

import io
import json
import uuid

import pytest

# --- Fictional Oracle Cards records ----------------------------------------------------

LONG_TEXT = (
    "Whenever a \"fictional\" spell resolves, scry 1. [Note: \\ backslash, ] bracket, },{ brace.] "
    "Chapter — ünïcödé ✦ “curly” ‘quotes’ −3: draw a card.\n"
) * 160  # about 20,000 characters

NORMAL_CREATURE = {
    "object": "card",
    "id": "5c1f6a2e-0b7d-4c1a-9e41-0f2b6d8a1001",
    "oracle_id": "a1000000-0000-4000-8000-000000000001",
    "name": "Thornwick Sentry",
    "lang": "en",
    "layout": "normal",
    "mana_cost": "{2}{G}",
    "cmc": 3.0,
    "type_line": "Creature — Elf Scout",
    "oracle_text": "Reach\nWhen Thornwick Sentry enters, you gain 2 life.",
    "power": "2",
    "toughness": "3",
    "colors": ["G"],
    "color_identity": ["G"],
    "keywords": ["Reach"],
    "legalities": {"standard": "not_legal", "commander": "legal", "vintage": "legal"},
    "game_changer": False,
    "edhrec_rank": 4821,
    "prices": {"usd": None, "eur": "0.10"},
    "image_uris": {"png": "https://example.invalid/front/thornwick.png"},
    "related_uris": {},
}

TWO_FACED = {
    "object": "card",
    "id": "5c1f6a2e-0b7d-4c1a-9e41-0f2b6d8a1002",
    "oracle_id": "a1000000-0000-4000-8000-000000000002",
    "name": "Ember Vow // Cinder Ward",
    "lang": "en",
    "layout": "modal_dfc",
    "cmc": 3.0,
    "type_line": "Sorcery // Instant",
    "color_identity": ["R", "W"],
    "keywords": [],
    "card_faces": [
        {
            "object": "card_face",
            "name": "Ember Vow",
            "mana_cost": "{2}{R}",
            "type_line": "Sorcery",
            "oracle_text": "Ember Vow deals 3 damage to any target.",
            "colors": ["R"],
            "image_uris": {"png": "https://example.invalid/front/ember.png"},
        },
        {
            "object": "card_face",
            "name": "Cinder Ward",
            "mana_cost": "{1}{W}",
            "type_line": "Instant",
            "oracle_text": "Prevent all damage that would be dealt to target creature this turn.",
            "colors": ["W"],
            "image_uris": {"png": "https://example.invalid/back/cinder.png"},
        },
    ],
    "legalities": {"commander": "legal"},
    "game_changer": False,
    "edhrec_rank": 9001,
}

BANNED = {
    "object": "card",
    "id": "5c1f6a2e-0b7d-4c1a-9e41-0f2b6d8a1003",
    "oracle_id": "a1000000-0000-4000-8000-000000000003",
    "name": "Vault of Endless Hoards",
    "layout": "normal",
    "mana_cost": "{0}",
    "cmc": 0.0,
    "type_line": "Artifact",
    "oracle_text": "{T}: Add three mana of any one color.",
    "colors": [],
    "color_identity": [],
    "keywords": [],
    "legalities": {"commander": "banned", "vintage": "restricted"},
    "game_changer": False,
    "edhrec_rank": 250,
}

NOT_LEGAL = {
    "object": "card",
    "id": "5c1f6a2e-0b7d-4c1a-9e41-0f2b6d8a1004",
    "oracle_id": "a1000000-0000-4000-8000-000000000004",
    "name": "Half-Built Contraption",
    "layout": "normal",
    "mana_cost": "{½}",
    "cmc": 0.5,
    "type_line": "Artifact — Contraption",
    "oracle_text": "Whenever you roll a die, tinker with Half-Built Contraption.",
    "colors": [],
    "color_identity": [],
    "keywords": [],
    "legalities": {"commander": "not_legal"},
    "game_changer": False,
    "edhrec_rank": 30500,
}

NO_RANK = {
    "object": "card",
    "id": "5c1f6a2e-0b7d-4c1a-9e41-0f2b6d8a1005",
    "oracle_id": "a1000000-0000-4000-8000-000000000005",
    "name": "Quietwater Heron",
    "layout": "normal",
    "mana_cost": "{U}",
    "cmc": 1.0,
    "type_line": "Creature — Bird",
    "oracle_text": "Flying",
    "power": "1",
    "toughness": "1",
    "colors": ["U"],
    "color_identity": ["U"],
    "keywords": ["Flying"],
    "legalities": {"commander": "legal"},
    # No "edhrec_rank" and no "game_changer" key.
}

GAME_CHANGER = {
    "object": "card",
    "id": "5c1f6a2e-0b7d-4c1a-9e41-0f2b6d8a1006",
    "oracle_id": "a1000000-0000-4000-8000-000000000006",
    "name": "Grave Tide Colossus",
    "layout": "normal",
    "mana_cost": "{X}{B}{B}",
    "cmc": 2.0,
    "type_line": "Creature — Zombie Giant",
    "oracle_text": "Grave Tide Colossus's power is equal to the number of creature cards in all graveyards.",
    "power": "*",
    "toughness": "1+*",
    "colors": ["B"],
    "color_identity": ["B"],
    "keywords": [],
    "legalities": {"commander": "legal"},
    "game_changer": True,
    "edhrec_rank": 12,
}

ODD_TEXT = {
    "object": "card",
    "id": "5c1f6a2e-0b7d-4c1a-9e41-0f2b6d8a1007",
    "oracle_id": "a1000000-0000-4000-8000-000000000007",
    "name": "Æthelwyn, the “Quiet” Lóreweaver",
    "layout": "normal",
    "mana_cost": "{W/U}{2/B}{G/P}{C}",
    "cmc": 5.0,
    "type_line": "Legendary Planeswalker — Æthelwyn",
    "oracle_text": LONG_TEXT,
    "loyalty": "4",
    "colors": ["W", "U", "B", "G"],
    "color_identity": ["W", "U", "B", "G"],
    "keywords": ["Scry"],
    "legalities": {"commander": "legal"},
    "game_changer": False,
    "edhrec_rank": 77,
}

NO_COMMANDER_LEGALITY = {
    "object": "card",
    "id": "5c1f6a2e-0b7d-4c1a-9e41-0f2b6d8a1008",
    "oracle_id": "a1000000-0000-4000-8000-000000000008",
    "name": "Unlisted Wanderer",
    "layout": "normal",
    "mana_cost": "{1}{R}",
    "cmc": 2.0,
    "type_line": "Creature — Goblin",
    "oracle_text": "Haste",
    "power": "2",
    "toughness": "1",
    "colors": ["R"],
    "color_identity": ["R"],
    "keywords": ["Haste"],
    "legalities": {"standard": "legal"},
    "game_changer": False,
    "edhrec_rank": 15000,
}

ALL_RECORDS = [NORMAL_CREATURE, TWO_FACED, BANNED, NOT_LEGAL, NO_RANK, GAME_CHANGER, ODD_TEXT, NO_COMMANDER_LEGALITY]


def _bulk_bytes(records):
    """A bulk file in the published layout: a JSON array, one record per line."""
    if not records:
        return b"[]\n"
    lines = ",\n".join(json.dumps(record, ensure_ascii=False) for record in records)
    return ("[\n" + lines + "\n]\n").encode("utf-8")


class BoundedReader(io.BufferedIOBase):
    """A binary file that refuses whole-file reads and counts the bytes handed out."""

    MAX_PIECE = 1024 * 1024

    def __init__(self, data):
        super().__init__()
        self._inner = io.BytesIO(data)
        self.size = len(data)
        self.consumed = 0

    def _check(self, size):
        if size is None or size < 0:
            raise AssertionError("the bulk file was read whole (read() without a size)")
        if size > self.MAX_PIECE:
            raise AssertionError(f"the bulk file was read in a piece of {size} bytes")

    def _count(self, chunk):
        self.consumed += len(chunk)
        return chunk

    def readable(self):
        return True

    def read(self, size=-1):
        self._check(size)
        return self._count(self._inner.read(size))

    def read1(self, size=-1):
        self._check(size)
        return self._count(self._inner.read(size))

    def readinto(self, buffer):
        self._check(len(buffer))
        chunk = self._count(self._inner.read(len(buffer)))
        buffer[: len(chunk)] = chunk
        return len(chunk)

    def readline(self, size=-1):
        return self._count(self._inner.readline(size))

    def readlines(self, hint=-1):
        raise AssertionError("the bulk file was read whole (readlines())")


def _ingest():
    from catalog import ingest

    return ingest


def _import(records):
    ingest = _ingest()
    ingest.import_oracle(ingest.iter_bulk_records(io.BytesIO(_bulk_bytes(records))))


def _card(record):
    from catalog.models import OracleCard

    return OracleCard.objects.get(oracle_id=uuid.UUID(record["oracle_id"]))


# --- Streaming the bulk file -----------------------------------------------------------


def test_iter_bulk_records_yields_every_record_in_file_order():
    """RN-01: the bulk file is read record by record, each record a dict equal
    to the one in the file, in file order."""
    records = list(_ingest().iter_bulk_records(io.BytesIO(_bulk_bytes(ALL_RECORDS))))
    assert records == ALL_RECORDS


def test_iter_bulk_records_of_an_empty_array_yields_nothing():
    """RN-01: an empty bulk file (an empty JSON array) yields no record."""
    assert list(_ingest().iter_bulk_records(io.BytesIO(b"[]\n"))) == []


def test_iter_bulk_records_keeps_brackets_quotes_and_escapes_inside_strings():
    """RN-01: brackets, braces, commas, quotes, backslashes, newlines and
    non-ASCII text inside strings belong to the record, not to the array."""
    record = dict(NORMAL_CREATURE, oracle_text='a ] b }, { c [ "d" \\ e\nf — ñ ✦ “g”')
    records = list(_ingest().iter_bulk_records(io.BytesIO(_bulk_bytes([record, BANNED]))))
    assert records == [record, BANNED]


def test_iter_bulk_records_of_a_truncated_file_raises():
    """RN-01, RN-03: a bulk file cut in the middle of a record is an error,
    never a silently shorter catalog."""
    data = _bulk_bytes(ALL_RECORDS)
    truncated = data[: len(data) // 2]
    ingest = _ingest()
    with pytest.raises(ingest.BulkFileError):
        list(ingest.iter_bulk_records(io.BytesIO(truncated)))


def test_iter_bulk_records_never_reads_the_whole_file_at_once():
    """RN-01 (plan section 10): the bulk file is consumed in bounded pieces;
    a read without a size, or of more than 1 MiB at once, fails the test."""
    reader = BoundedReader(_bulk_bytes(ALL_RECORDS))
    records = list(_ingest().iter_bulk_records(reader))
    assert [record["oracle_id"] for record in records] == [r["oracle_id"] for r in ALL_RECORDS]


def test_iter_bulk_records_yields_the_first_record_before_reading_most_of_the_file():
    """RN-01 (plan section 10): records come out one at a time: the first one
    is available while most of a large bulk file is still unread."""
    filler = [
        dict(NORMAL_CREATURE, oracle_id=str(uuid.UUID(int=index + 1)), oracle_text="Filler text. " * 80)
        for index in range(8000)
    ]
    reader = BoundedReader(_bulk_bytes([NORMAL_CREATURE, *filler]))
    assert reader.size > 8 * 1024 * 1024

    first = next(iter(_ingest().iter_bulk_records(reader)))

    assert first == NORMAL_CREATURE
    assert reader.consumed < reader.size // 2, (reader.consumed, reader.size)


@pytest.mark.django_db
def test_import_from_a_bulk_file_never_calls_json_load_on_the_file(monkeypatch):
    """RN-01 (plan section 10): the import never parses the whole bulk file in
    one call; it still stores every card."""
    from catalog.models import OracleCard

    def refuse(*args, **kwargs):
        raise AssertionError("json.load was called on the whole bulk file")

    monkeypatch.setattr(json, "load", refuse)
    ingest = _ingest()
    ingest.import_oracle(ingest.iter_bulk_records(BoundedReader(_bulk_bytes(ALL_RECORDS))))

    assert OracleCard.objects.count() == len(ALL_RECORDS)


# --- Stored rows ---------------------------------------------------------------------


@pytest.mark.django_db
def test_import_stores_one_oracle_card_per_record():
    """RN-01: the import stores one OracleCard per record, keyed by oracle_id."""
    from catalog.models import OracleCard

    _import(ALL_RECORDS)

    stored = set(OracleCard.objects.values_list("oracle_id", flat=True))
    assert stored == {uuid.UUID(record["oracle_id"]) for record in ALL_RECORDS}


@pytest.mark.django_db
def test_import_of_an_empty_bulk_file_stores_nothing():
    """RN-01: an empty bulk file stores no card and raises nothing."""
    from catalog.models import OracleCard

    _import([])

    assert OracleCard.objects.count() == 0


@pytest.mark.django_db
def test_import_stores_the_fields_of_a_normal_creature():
    """RN-01, RN-04: a single-faced creature keeps its name, cost, mana value,
    type line, rules text, colors, identity, keywords, power, toughness and
    layout."""
    _import(ALL_RECORDS)
    card = _card(NORMAL_CREATURE)

    assert card.name == "Thornwick Sentry"
    assert card.mana_cost == "{2}{G}"
    assert card.cmc == 3.0
    assert card.type_line == "Creature — Elf Scout"
    assert card.oracle_text == "Reach\nWhen Thornwick Sentry enters, you gain 2 life."
    assert card.colors == ["G"]
    assert card.color_identity == ["G"]
    assert card.keywords == ["Reach"]
    assert card.power == "2"
    assert card.toughness == "3"
    assert card.layout == "normal"
    assert card.commander_legality == "legal"
    assert card.game_changer is False
    assert card.edhrec_rank == 4821


@pytest.mark.django_db
def test_import_stores_the_faces_of_a_two_faced_card():
    """RN-01: a two-faced card keeps its full name, layout, identity and, in
    `faces`, the name, mana cost, type line and rules text of each face in
    order. Missing top-level cost, text and colors do not stop the import."""
    _import(ALL_RECORDS)
    card = _card(TWO_FACED)

    assert card.name == "Ember Vow // Cinder Ward"
    assert card.layout == "modal_dfc"
    assert card.cmc == 3.0
    assert card.type_line == "Sorcery // Instant"
    assert card.color_identity == ["R", "W"]
    assert len(card.faces) == 2
    for stored, source in zip(card.faces, TWO_FACED["card_faces"]):
        for key in ("name", "mana_cost", "type_line", "oracle_text"):
            assert stored[key] == source[key], key


@pytest.mark.django_db
def test_two_faced_card_faces_keep_mana_costs_and_texts_apart():
    """RN-01: each face keeps its own mana cost and text; the back face is not
    merged into the front."""
    _import([TWO_FACED])
    front, back = _card(TWO_FACED).faces

    assert (front["mana_cost"], back["mana_cost"]) == ("{2}{R}", "{1}{W}")
    assert "Prevent all damage" not in front["oracle_text"]
    assert "deals 3 damage" not in back["oracle_text"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("record", "expected"),
    [
        (NORMAL_CREATURE, "legal"),
        (TWO_FACED, "legal"),
        (BANNED, "banned"),
        (NOT_LEGAL, "not_legal"),
    ],
    ids=["legal", "two-faced legal", "banned", "not_legal"],
)
def test_import_stores_commander_legality(record, expected):
    """RN-04: Commander legality comes from `legalities.commander` (legal,
    banned, not_legal); the legality of other formats is ignored."""
    _import(ALL_RECORDS)

    assert _card(record).commander_legality == expected


@pytest.mark.django_db
def test_card_banned_in_commander_is_banned_even_when_restricted_elsewhere():
    """RN-04: a card banned in Commander is stored as banned whatever its
    status in other formats."""
    _import([BANNED])

    assert _card(BANNED).commander_legality == "banned"


@pytest.mark.django_db
def test_card_without_a_commander_legality_is_not_legal():
    """RN-04: a record with no Commander entry in `legalities` is never stored
    as legal (only cards legal in Commander serve as comparables)."""
    _import([NO_COMMANDER_LEGALITY])

    assert _card(NO_COMMANDER_LEGALITY).commander_legality == "not_legal"


@pytest.mark.django_db
def test_import_stores_the_game_changer_flag():
    """RN-04 (plan section 9.1): the Game Changer flag is stored; a record
    without the key is not a Game Changer."""
    _import(ALL_RECORDS)

    assert _card(GAME_CHANGER).game_changer is True
    assert _card(NORMAL_CREATURE).game_changer is False
    assert _card(NO_RANK).game_changer is False


@pytest.mark.django_db
def test_import_stores_edhrec_rank_or_none_when_absent():
    """RN-04 (plan section 9.1): the EDHREC rank is stored; a record without
    one is stored with no rank, not zero."""
    _import(ALL_RECORDS)

    assert _card(GAME_CHANGER).edhrec_rank == 12
    assert _card(NOT_LEGAL).edhrec_rank == 30500
    assert _card(NO_RANK).edhrec_rank is None


@pytest.mark.django_db
def test_card_without_rank_or_flag_keeps_its_other_fields():
    """RN-01: optional keys missing from a record do not change its other
    fields."""
    _import([NO_RANK])
    card = _card(NO_RANK)

    assert card.name == "Quietwater Heron"
    assert card.keywords == ["Flying"]
    assert card.commander_legality == "legal"


@pytest.mark.django_db
def test_import_keeps_unicode_quotes_hybrid_symbols_and_very_long_text():
    """RN-01: names, type lines, mana costs and rules text are stored exactly,
    with non-ASCII letters, curly quotes, hybrid and Phyrexian symbols and a
    rules text of about 20,000 characters."""
    _import(ALL_RECORDS)
    card = _card(ODD_TEXT)

    assert len(LONG_TEXT) > 15_000
    assert card.name == "Æthelwyn, the “Quiet” Lóreweaver"
    assert card.type_line == "Legendary Planeswalker — Æthelwyn"
    assert card.mana_cost == "{W/U}{2/B}{G/P}{C}"
    assert card.oracle_text == LONG_TEXT
    assert card.colors == ["W", "U", "B", "G"]
    assert card.power is None
    assert card.toughness is None


@pytest.mark.django_db
def test_import_keeps_star_power_and_fractional_mana_value():
    """RN-01: power and toughness such as "*" and "1+*" are kept as text, and a
    fractional mana value and a "{½}" cost are kept as published."""
    _import(ALL_RECORDS)

    colossus = _card(GAME_CHANGER)
    assert (colossus.power, colossus.toughness) == ("*", "1+*")
    assert colossus.mana_cost == "{X}{B}{B}"

    contraption = _card(NOT_LEGAL)
    assert contraption.cmc == 0.5
    assert contraption.mana_cost == "{½}"


@pytest.mark.django_db
def test_import_ignores_fields_it_does_not_store():
    """RN-01: unknown keys of a record (prices, image links, other formats)
    are ignored without error."""
    record = dict(NORMAL_CREATURE, unexpected={"nested": [1, {"deep": None}]}, all_parts=[])
    _import([record])

    assert _card(record).name == "Thornwick Sentry"


# --- Maintainer decisions on edge records ----------------------------------------------


def _record(oracle_id, **fields):
    """A minimal fictional single-faced record with the given overrides."""
    record = {
        "object": "card",
        "oracle_id": oracle_id,
        "name": "Mossback Courier",
        "layout": "normal",
        "mana_cost": "{1}{G}",
        "cmc": 2.0,
        "type_line": "Creature — Turtle",
        "oracle_text": "Vigilance",
        "colors": ["G"],
        "color_identity": ["G"],
        "keywords": ["Vigilance"],
        "legalities": {"commander": "legal"},
    }
    record.update(fields)
    return record


@pytest.mark.django_db
def test_card_restricted_in_commander_is_stored_as_legal():
    """RN-04: a `legalities.commander` value of "restricted" is stored as legal."""
    record = _record("b2000000-0000-4000-8000-000000000001", legalities={"commander": "restricted"})
    _import([record])

    assert _card(record).commander_legality == "legal"


MULTI_FACE_NO_TOP_LEVEL = {
    "object": "card",
    "oracle_id": "b2000000-0000-4000-8000-000000000002",
    "name": "Dawnspire Pact // Duskspire Debt",
    "layout": "modal_dfc",
    "cmc": 4.0,
    "type_line": "Instant // Sorcery",
    "color_identity": ["B", "W"],
    "keywords": [],
    "card_faces": [
        {
            "object": "card_face",
            "name": "Dawnspire Pact",
            "mana_cost": "{2}{W}",
            "type_line": "Instant",
            "oracle_text": "You gain 4 life.",
            "colors": ["W"],
        },
        {
            "object": "card_face",
            "name": "Duskspire Debt",
            "mana_cost": "{3}{B}",
            "type_line": "Sorcery",
            "oracle_text": "Each opponent loses 2 life.",
            "colors": ["B", "W"],
        },
    ],
    "legalities": {"commander": "legal"},
}


def _without(record, *keys, oracle_id):
    """A copy of `record` without `keys` and with a new oracle_id."""
    copy = {key: value for key, value in record.items() if key not in keys}
    copy["oracle_id"] = oracle_id
    return copy


@pytest.mark.django_db
def test_multi_face_card_without_top_level_fields_takes_them_from_its_faces():
    """RN-01: a multi-face record with no top-level mana_cost, oracle_text or
    colors takes the front face's mana cost, the face texts joined with
    "\\n//\\n" and the union of the face colors."""
    _import([MULTI_FACE_NO_TOP_LEVEL])
    card = _card(MULTI_FACE_NO_TOP_LEVEL)

    assert card.mana_cost == "{2}{W}"
    assert card.oracle_text == "You gain 4 life.\n//\nEach opponent loses 2 life."
    assert sorted(card.colors) == ["B", "W"]


@pytest.mark.django_db
def test_multi_face_card_without_top_level_type_line_joins_face_type_lines():
    """RN-01: a missing top-level type line is built from the face type lines
    joined with " // "."""
    record = _without(MULTI_FACE_NO_TOP_LEVEL, "type_line", oracle_id="b2000000-0000-4000-8000-000000000005")
    _import([record])

    assert _card(record).type_line == "Instant // Sorcery"


@pytest.mark.django_db
def test_multi_face_card_without_any_cmc_has_mana_value_zero():
    """RN-01: a record with no mana value at top level nor on its front face
    is stored with mana value 0.0."""
    record = _without(MULTI_FACE_NO_TOP_LEVEL, "cmc", oracle_id="b2000000-0000-4000-8000-000000000004")
    _import([record])

    assert _card(record).cmc == 0.0


_WISP_FACE = {
    "object": "card_face",
    "oracle_id": "b2000000-0000-4000-8000-000000000003",
    "name": "Lanternfen Wisp",
    "mana_cost": "{1}{U}",
    "cmc": 2.0,
    "type_line": "Creature — Spirit",
    "oracle_text": "Flying",
    "colors": ["U"],
    "power": "1",
    "toughness": "2",
}

REVERSIBLE = {
    "object": "card",
    "name": "Lanternfen Wisp // Lanternfen Wisp",
    "layout": "reversible_card",
    "color_identity": ["U"],
    "keywords": [],
    "card_faces": [dict(_WISP_FACE), dict(_WISP_FACE)],
    "legalities": {"commander": "legal"},
}


@pytest.mark.django_db
def test_reversible_card_takes_oracle_id_type_line_and_cmc_from_its_faces():
    """RN-01: a record without a top-level oracle_id (layout reversible_card)
    takes card_faces[0].oracle_id; a missing type line is the face type lines
    joined with " // " and a missing mana value is the front face's."""
    from catalog.models import OracleCard

    _import([REVERSIBLE])

    card = OracleCard.objects.get(oracle_id=uuid.UUID(_WISP_FACE["oracle_id"]))
    assert card.layout == "reversible_card"
    assert card.type_line == "Creature — Spirit // Creature — Spirit"
    assert card.cmc == 2.0


@pytest.mark.django_db
def test_record_without_any_oracle_id_is_skipped():
    """RN-01: a record with no oracle_id at top level nor on any face is
    skipped; the other records are still stored."""
    from catalog.models import OracleCard

    orphan = dict(REVERSIBLE)
    orphan["card_faces"] = [
        {key: value for key, value in face.items() if key != "oracle_id"} for face in REVERSIBLE["card_faces"]
    ]
    keeper = _record("b2000000-0000-4000-8000-000000000006")
    _import([orphan, keeper])

    assert list(OracleCard.objects.values_list("oracle_id", flat=True)) == [uuid.UUID(keeper["oracle_id"])]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "layout",
    ["token", "double_faced_token", "emblem", "art_series", "vanguard", "scheme", "planar"],
)
def test_non_card_layouts_are_skipped(layout):
    """RN-01, RN-04: records that are not playable cards (tokens, emblems, art
    series, Vanguard, schemes and planes) are not stored."""
    from catalog.models import OracleCard

    skipped = _record("b2000000-0000-4000-8000-000000000007", layout=layout)
    keeper = _record("b2000000-0000-4000-8000-000000000008")
    _import([skipped, keeper])

    assert list(OracleCard.objects.values_list("oracle_id", flat=True)) == [uuid.UUID(keeper["oracle_id"])]


@pytest.mark.django_db
def test_duplicate_oracle_id_in_one_file_is_stored_once():
    """RN-01: a repeated oracle_id in the same bulk file is stored once and
    raises no IntegrityError."""
    from catalog.models import OracleCard

    first = _record("b2000000-0000-4000-8000-000000000009", name="Echoing Lark")
    again = _record("b2000000-0000-4000-8000-000000000009", name="Echoing Lark")
    _import([first, again])

    assert OracleCard.objects.filter(oracle_id=uuid.UUID(first["oracle_id"])).count() == 1


class OneByteReader(io.RawIOBase):
    """A binary file that hands out at most one byte per read call."""

    def __init__(self, data):
        super().__init__()
        self._inner = io.BytesIO(data)

    def readable(self):
        return True

    def read(self, size=-1):
        return self._inner.read(1 if size is None or size < 0 else min(size, 1))

    def readinto(self, buffer):
        chunk = self._inner.read(1)
        buffer[: len(chunk)] = chunk
        return len(chunk)


MULTIBYTE = _record(
    "b2000000-0000-4000-8000-000000000010",
    name="Ætherwynd, Søren’s “Lórekeeper” ✦ 龍",
    oracle_text="Chapter — ü ✦ 𝔊 “x” −3: draw a card.",
)


def test_iter_bulk_records_decodes_multibyte_characters_split_across_reads():
    """RN-01: a multi-byte UTF-8 character split between two reads of the
    bulk file is decoded correctly (reads of one byte each)."""
    data = _bulk_bytes([MULTIBYTE, NORMAL_CREATURE])
    records = list(_ingest().iter_bulk_records(OneByteReader(data)))

    assert records == [MULTIBYTE, NORMAL_CREATURE]


def test_iter_bulk_records_decodes_a_multibyte_character_on_the_256_kib_boundary():
    """RN-01: a record straddling the 256 KiB read boundary, with a
    multi-byte UTF-8 character split across it, is decoded correctly."""
    boundary = 256 * 1024
    char = "✦"  # three bytes in UTF-8
    marker = "MARKER"
    probe = _bulk_bytes([_record("b2000000-0000-4000-8000-000000000011", oracle_text=marker)])
    head = probe.index(marker.encode("utf-8"))
    # The first byte of the character is the last byte of the first 256 KiB.
    record = _record("b2000000-0000-4000-8000-000000000011", oracle_text="a" * (boundary - 1 - head) + char + " tail")
    data = _bulk_bytes([record, NORMAL_CREATURE])
    position = data.index(char.encode("utf-8"))
    assert position == boundary - 1

    records = list(_ingest().iter_bulk_records(io.BytesIO(data)))

    assert records == [record, NORMAL_CREATURE]


# --- Reader robustness -----------------------------------------------------------------


@pytest.mark.parametrize("read_size", [1, 2, 3, 7, 4096])
def test_iter_bulk_records_is_independent_of_the_read_size(monkeypatch, read_size):
    """RN-01: the records are the same whatever the size of each read, so a
    record, a string or a multi-byte character cut by any boundary is kept."""
    ingest = _ingest()
    monkeypatch.setattr(ingest, "READ_SIZE", read_size)

    records = list(ingest.iter_bulk_records(io.BytesIO(_bulk_bytes(ALL_RECORDS))))

    assert records == ALL_RECORDS


def test_malformed_record_early_in_a_large_file_fails_before_reading_it_all(monkeypatch):
    """RN-01, RN-03: a malformed record near the start of a large bulk file
    raises BulkFileError without reading the rest of the file."""
    ingest = _ingest()
    monkeypatch.setattr(ingest, "MAX_RECORD_CHARS", 4096)
    filler = [
        dict(NORMAL_CREATURE, oracle_id=str(uuid.UUID(int=index + 1)), oracle_text="Filler text. " * 80)
        for index in range(8000)
    ]
    good = _bulk_bytes([NORMAL_CREATURE, *filler])
    first_end = good.index(b"\n", 2)  # end of the first record line
    data = good[:first_end] + b',\n{"oracle_id": "broken", "name": }' + good[first_end:]
    reader = BoundedReader(data)
    assert reader.size > 8 * 1024 * 1024

    with pytest.raises(ingest.BulkFileError):
        list(ingest.iter_bulk_records(reader))

    assert reader.consumed < reader.size // 2, (reader.consumed, reader.size)


def test_invalid_utf8_bytes_raise_bulk_file_error():
    """RN-01, RN-03: bytes that are not valid UTF-8 raise BulkFileError."""
    ingest = _ingest()
    data = _bulk_bytes([NORMAL_CREATURE]).replace(b"Thornwick", b"Thorn\xff\xfewick", 1)

    with pytest.raises(ingest.BulkFileError):
        list(ingest.iter_bulk_records(io.BytesIO(data)))


def test_trailing_garbage_after_the_array_raises_bulk_file_error():
    """RN-01, RN-03: content after the closing bracket of the array raises
    BulkFileError."""
    ingest = _ingest()
    data = _bulk_bytes([NORMAL_CREATURE]) + b'{"name": "Stray"}\n'

    with pytest.raises(ingest.BulkFileError):
        list(ingest.iter_bulk_records(io.BytesIO(data)))


def test_utf8_byte_order_mark_at_the_start_is_accepted():
    """RN-01: a UTF-8 byte order mark before the array is accepted."""
    data = b"\xef\xbb\xbf" + _bulk_bytes([NORMAL_CREATURE, TWO_FACED])

    assert list(_ingest().iter_bulk_records(io.BytesIO(data))) == [NORMAL_CREATURE, TWO_FACED]


# --- Split card and row shape ----------------------------------------------------------

SPLIT_CARD = {
    "object": "card",
    "oracle_id": "b2000000-0000-4000-8000-000000000012",
    "name": "Spark // Squall",
    "layout": "split",
    "mana_cost": "{1}{R} // {2}{U}",
    "cmc": 5.0,
    "type_line": "Instant // Instant",
    "colors": ["R", "U"],
    "color_identity": ["R", "U"],
    "keywords": [],
    "card_faces": [
        {
            "object": "card_face",
            "name": "Spark",
            "mana_cost": "{1}{R}",
            "type_line": "Instant",
            "oracle_text": "Spark deals 2 damage to any target.",
        },
        {
            "object": "card_face",
            "name": "Squall",
            "mana_cost": "{2}{U}",
            "type_line": "Instant",
            "oracle_text": "Tap up to two target creatures.",
        },
    ],
    "legalities": {"commander": "legal"},
}


@pytest.mark.django_db
def test_split_card_keeps_its_combined_top_level_mana_cost():
    """RN-01: a split card with a top-level combined mana cost keeps it as
    published, not the front face's cost."""
    _import([SPLIT_CARD])

    assert _card(SPLIT_CARD).mana_cost == "{1}{R} // {2}{U}"


@pytest.mark.parametrize("record", [NORMAL_CREATURE, TWO_FACED], ids=["normal", "two-faced"])
def test_oracle_row_is_json_serializable(record):
    """RN-01: oracle_row turns a record into a JSON-serializable dict."""
    row = _ingest().oracle_row(record)

    assert isinstance(row, dict)
    json.dumps(row)


def test_oracle_row_of_a_skipped_layout_is_none():
    """RN-01, RN-04: oracle_row returns None for a layout that is not stored."""
    assert _ingest().oracle_row(_record("b2000000-0000-4000-8000-000000000013", layout="token")) is None
