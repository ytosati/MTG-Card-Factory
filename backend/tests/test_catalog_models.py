"""Catalog models and the card full-text table (task T14, spec RN-01, RN-03, RN-04).

Details: specs/plan.md, sections 4 (catalog models, full-text tables), 7
(all-or-nothing build) and 9.1 (FTS5 availability, parameterized queries).

API under test:

    catalog.models.SourceRecord
        source         one of the source names of plan section 4
                       (scryfall_oracle, scryfall_default, scryfall_all,
                       comprehensive_rules), declared as field choices
        url, published_at, downloaded_at, sha256, size

    catalog.models.BuildRun
        one row per completed build: catalog_version, started_at, finished_at.
        It has no live state (status, progress, error): that is the build's Job.

    catalog.models.OracleCard
        oracle_id (primary key), name, mana_cost, cmc, type_line, oracle_text,
        colors, color_identity, keywords, power, toughness, layout,
        faces (JSON), commander_legality (choices: legal, banned, not_legal),
        game_changer, edhrec_rank, roles (JSON list)

    oracle_fts
        an SQLite FTS5 virtual table created by a migration with fixed SQL. Its
        indexed columns include `name`, `type_line` and `oracle_text` (plan
        section 9.1: BM25 over name, type line and rules text). It is written
        and queried only with parameters.

Every card below is fictional and written by hand.
"""

import datetime
import sqlite3
import uuid

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, connection, connections, transaction
from django.utils import timezone

SOURCE_NAMES_IN_PLAN = {"scryfall_oracle", "scryfall_default", "scryfall_all", "comprehensive_rules"}
LEGALITY_VALUES = {"legal", "banned", "not_legal"}
ORACLE_CARD_FIELDS = {
    "oracle_id",
    "name",
    "mana_cost",
    "cmc",
    "type_line",
    "oracle_text",
    "colors",
    "color_identity",
    "keywords",
    "power",
    "toughness",
    "layout",
    "faces",
    "commander_legality",
    "game_changer",
    "edhrec_rank",
    "roles",
}
FTS_TEXT_COLUMNS = ("name", "type_line", "oracle_text")
# A source file larger than a signed 32-bit integer (the All Cards file is gigabytes).
HUGE_SIZE = 5 * 1024**3 + 7
FICTIONAL_SHA256 = "3f" * 32
HOSTILE_TEXT = "Lantern'); DROP TABLE oracle_fts; -- \"quoted\" %s ? ; \\ tail"


def _models():
    from catalog import models

    return models


def _field_names(model):
    return {field.name for field in model._meta.get_fields()}


def _fictional_card(**overrides):
    values = {
        "oracle_id": str(uuid.uuid4()),
        "name": "Lantern Warden of Vell",
        "mana_cost": "{2}{W}",
        "cmc": 3.0,
        "type_line": "Creature — Human Cleric",
        "oracle_text": "Vigilance\nWhen Lantern Warden of Vell enters, you gain 2 life.",
        "colors": ["W"],
        "color_identity": ["W"],
        "keywords": ["Vigilance"],
        "power": "2",
        "toughness": "3",
        "layout": "normal",
        "faces": [],
        "commander_legality": "legal",
        "game_changer": False,
        "edhrec_rank": 1234,
        "roles": [],
    }
    values.update(overrides)
    return values


def _fts_insert(rowid, name, type_line, oracle_text):
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO oracle_fts (rowid, name, type_line, oracle_text) VALUES (%s, %s, %s, %s)",
            [rowid, name, type_line, oracle_text],
        )


def _fts_match(query):
    with connection.cursor() as cursor:
        cursor.execute("SELECT rowid FROM oracle_fts WHERE oracle_fts MATCH %s ORDER BY rowid", [query])
        return [row[0] for row in cursor.fetchall()]


def _table_sql(name):
    with connection.cursor() as cursor:
        cursor.execute("SELECT sql FROM sqlite_master WHERE name = %s", [name])
        row = cursor.fetchone()
    return row[0] if row else None


# --- Migrations on an empty database -------------------------------------------------


@pytest.fixture
def empty_database(tmp_path, django_db_blocker):
    """A new, empty SQLite file used as the default database for one test."""
    path = tmp_path / "empty-cardfactory.sqlite3"
    original = connections["default"]
    wrapper = original.__class__({**original.settings_dict, "NAME": str(path)}, alias="default")
    connections["default"] = wrapper
    try:
        with django_db_blocker.unblock():
            yield path
    finally:
        wrapper.close()
        connections["default"] = original


def _sqlite_names(path):
    db = sqlite3.connect(path)
    try:
        return {row[0]: row[1] for row in db.execute("SELECT name, sql FROM sqlite_master")}
    finally:
        db.close()


def test_migrations_apply_on_an_empty_database_and_create_the_catalog_tables(empty_database):
    """RN-01, RN-03: every migration applies on an empty database and creates
    the tables of SourceRecord, BuildRun and OracleCard and the FTS5 table
    `oracle_fts`."""
    call_command("migrate", verbosity=0, interactive=False)
    connections["default"].close()

    models = _models()
    tables = _sqlite_names(empty_database)
    for model in (models.SourceRecord, models.BuildRun, models.OracleCard):
        assert model._meta.db_table in tables, model.__name__
    assert "oracle_fts" in tables
    assert "fts5" in tables["oracle_fts"].lower()


@pytest.mark.django_db
def test_models_have_no_missing_migration():
    """RN-03: the catalog models match their migrations, so the database built
    on an empty data folder is the one the code expects."""
    _models()
    call_command("makemigrations", "catalog", "--check", "--dry-run", verbosity=0)


# --- FTS5 in the running Python --------------------------------------------------------


def test_running_python_sqlite_has_fts5():
    """RN-01 (plan section 9.1): the SQLite of the running Python creates and
    queries an FTS5 table, with a parameter for MATCH."""
    db = sqlite3.connect(":memory:")
    try:
        db.execute("CREATE VIRTUAL TABLE probe USING fts5(body)")
        db.execute("INSERT INTO probe (body) VALUES (?)", ("a fictional lantern spell",))
        rows = db.execute("SELECT body FROM probe WHERE probe MATCH ?", ("lantern",)).fetchall()
    finally:
        db.close()
    assert rows == [("a fictional lantern spell",)], sqlite3.sqlite_version


@pytest.mark.django_db
def test_oracle_fts_is_an_fts5_table_with_name_type_line_and_text_columns():
    """RN-01, RN-04 (plan sections 4 and 9.1): `oracle_fts` is an FTS5 table
    over the name, type line and rules text of a card."""
    sql = _table_sql("oracle_fts")
    assert sql is not None, "oracle_fts was not created by the migrations"
    assert "fts5" in sql.lower()
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM oracle_fts LIMIT 0")
        columns = {description[0] for description in cursor.description}
    assert set(FTS_TEXT_COLUMNS) <= columns


@pytest.mark.django_db
def test_oracle_fts_accepts_parameterized_inserts_and_match():
    """RN-01 (plan section 4): rows go into `oracle_fts` with parameters and
    MATCH takes the query as a parameter, never as SQL built from text."""
    _fts_insert(1, "Lantern Warden of Vell", "Creature — Human Cleric", "Vigilance. You gain 2 life.")
    _fts_insert(2, "Brine Oracle of Tessk", "Creature — Merfolk Wizard", "Flying. Draw a card.")
    _fts_insert(3, "Ashen Lantern", "Artifact", "Tap: Add one mana of any color.")

    assert _fts_match("lantern") == [1, 3]
    assert _fts_match("merfolk") == [2]
    assert _fts_match('"draw a card"') == [2]
    assert _fts_match("nonexistentword") == []


@pytest.mark.django_db
def test_oracle_fts_stores_hostile_text_verbatim_as_a_parameter():
    """RN-01: text with quotes, semicolons, SQL keywords and placeholder marks is
    stored as data; the table survives and the row is found by its words."""
    _fts_insert(7, HOSTILE_TEXT, "Artifact", HOSTILE_TEXT)

    assert _table_sql("oracle_fts") is not None
    with connection.cursor() as cursor:
        cursor.execute("SELECT name FROM oracle_fts WHERE rowid = %s", [7])
        assert cursor.fetchone()[0] == HOSTILE_TEXT
    assert _fts_match("lantern") == [7]


@pytest.mark.django_db
def test_oracle_fts_hostile_match_parameter_is_quoted_as_a_phrase():
    """RN-01: a MATCH parameter holding SQL text, quoted as an FTS5 phrase,
    finds nothing and changes nothing."""
    _fts_insert(1, "Lantern Warden of Vell", "Creature — Human Cleric", "Vigilance.")
    phrase = '"' + "x'); DROP TABLE oracle_fts; --".replace('"', '""') + '"'

    assert _fts_match(phrase) == []
    assert _fts_match("lantern") == [1]


@pytest.mark.django_db
def test_oracle_fts_handles_huge_and_unicode_text():
    """RN-01: very long rules text and non-ASCII names go in and are matched."""
    huge = ("Whenever a fictional creature enters, scry 1. " * 4000) + "Zyxquor"
    _fts_insert(1, "Æther Séance of Ūlm", "Legendary Enchantment — Shrine", huge)
    _fts_insert(2, "Empty Rules Golem", "Artifact Creature — Golem", "")

    assert _fts_match("zyxquor") == [1]
    assert _fts_match("shrine") == [1]
    assert _fts_match("golem") == [2]


# --- SourceRecord ---------------------------------------------------------------------


@pytest.mark.django_db
def test_source_record_keeps_origin_publication_and_download_dates():
    """RN-01: a source record keeps its origin, the date the source published it
    and the date it was downloaded, with its checksum and size."""
    models = _models()
    published = datetime.datetime(2026, 10, 30, 9, 15, tzinfo=datetime.timezone.utc)
    downloaded = datetime.datetime(2026, 11, 2, 18, 40, tzinfo=datetime.timezone.utc)
    models.SourceRecord.objects.create(
        source="scryfall_oracle",
        url="https://example.invalid/fictional/oracle-cards.json",
        published_at=published,
        downloaded_at=downloaded,
        sha256=FICTIONAL_SHA256,
        size=HUGE_SIZE,
    )

    record = models.SourceRecord.objects.get()
    assert record.source == "scryfall_oracle"
    assert record.url == "https://example.invalid/fictional/oracle-cards.json"
    assert record.published_at == published
    assert record.downloaded_at == downloaded
    assert record.sha256 == FICTIONAL_SHA256
    assert record.size == HUGE_SIZE


def test_source_record_names_are_the_sources_of_the_plan():
    """RN-01: the source field is a closed list, taken from plan section 4."""
    field = _models().SourceRecord._meta.get_field("source")
    names = {value for value, _label in field.choices}
    assert names
    assert names <= SOURCE_NAMES_IN_PLAN
    assert "scryfall_oracle" in names


@pytest.mark.django_db
def test_source_record_rejects_an_unknown_source():
    """RN-01: a source outside the list fails validation."""
    record = _models().SourceRecord(
        source="fictional_mirror",
        url="https://example.invalid/fictional.json",
        published_at=timezone.now(),
        downloaded_at=timezone.now(),
        sha256=FICTIONAL_SHA256,
        size=10,
    )
    with pytest.raises(ValidationError):
        record.full_clean()


# --- BuildRun -------------------------------------------------------------------------


@pytest.mark.django_db
def test_build_run_records_a_completed_build_with_its_catalog_version():
    """RN-03 (plan section 4): a build run row stores the catalog version and
    when the build started and finished."""
    models = _models()
    started = timezone.now() - datetime.timedelta(minutes=4)
    finished = timezone.now()
    models.BuildRun.objects.create(catalog_version=3, started_at=started, finished_at=finished)

    run = models.BuildRun.objects.get()
    assert run.catalog_version == 3
    assert run.started_at == started
    assert run.finished_at == finished


def test_build_run_holds_no_live_build_state():
    """RN-03 (plan section 4): BuildRun holds completed builds only; the live
    state of a build is its Job, so a crash never leaves a build "running"."""
    names = _field_names(_models().BuildRun)
    assert {"catalog_version", "started_at", "finished_at"} <= names
    assert not names & {"status", "state", "progress", "error"}


# --- OracleCard -----------------------------------------------------------------------


def test_oracle_card_has_the_fields_of_the_plan():
    """RN-01, RN-04 (plan section 4): OracleCard has every field the plan lists,
    with `oracle_id` as the primary key."""
    model = _models().OracleCard
    assert ORACLE_CARD_FIELDS <= _field_names(model)
    assert model._meta.pk.name == "oracle_id"


def test_oracle_card_commander_legality_choices():
    """RN-04: Commander legality is one of legal, banned or not_legal."""
    field = _models().OracleCard._meta.get_field("commander_legality")
    assert {value for value, _label in field.choices} == LEGALITY_VALUES


@pytest.mark.django_db
def test_oracle_card_rejects_an_unknown_legality():
    """RN-04: a legality outside the three values fails validation."""
    card = _models().OracleCard(**_fictional_card(commander_legality="restricted"))
    with pytest.raises(ValidationError) as error:
        card.full_clean()
    assert "commander_legality" in error.value.message_dict


@pytest.mark.django_db
@pytest.mark.parametrize("legality", sorted(LEGALITY_VALUES))
def test_oracle_card_stores_each_legality(legality):
    """RN-04: each legality value is stored and read back as written."""
    models = _models()
    values = _fictional_card(commander_legality=legality)
    models.OracleCard.objects.create(**values)
    assert models.OracleCard.objects.get(pk=values["oracle_id"]).commander_legality == legality


@pytest.mark.django_db
def test_oracle_card_round_trip_with_faces_and_odd_characters():
    """RN-01, RN-04: a fictional double-faced card with non-ASCII text, a star
    power, no EDHREC rank and the Game Changer flag is stored as written."""
    models = _models()
    faces = [
        {
            "name": "Séance-Keeper Ūlm",
            "mana_cost": "{1}{U/B}{U/B}",
            "type_line": "Legendary Creature — Spirit",
            "oracle_text": "Flying\n“Whisper,” it said — and the lantern went dark.",
            "power": "*",
            "toughness": "1+*",
        },
        {
            "name": "Ūlm, the Emptied Hall",
            "mana_cost": "",
            "type_line": "Legendary Land",
            "oracle_text": "{T}: Add {U} or {B}.",
        },
    ]
    values = _fictional_card(
        name="Séance-Keeper Ūlm // Ūlm, the Emptied Hall",
        mana_cost="{1}{U/B}{U/B}",
        type_line="Legendary Creature — Spirit // Legendary Land",
        oracle_text="",
        colors=["U", "B"],
        color_identity=["B", "U"],
        keywords=["Flying"],
        power="*",
        toughness="1+*",
        layout="modal_dfc",
        faces=faces,
        commander_legality="banned",
        game_changer=True,
        edhrec_rank=None,
        roles=["card_draw"],
    )
    models.OracleCard.objects.create(**values)

    card = models.OracleCard.objects.get(pk=values["oracle_id"])
    assert str(card.oracle_id) == values["oracle_id"]
    assert card.name == values["name"]
    assert card.type_line == values["type_line"]
    assert card.power == "*"
    assert card.toughness == "1+*"
    assert card.faces == faces
    assert card.commander_legality == "banned"
    assert card.game_changer is True
    assert card.edhrec_rank is None
    assert card.roles == ["card_draw"]


@pytest.mark.django_db
def test_oracle_card_without_power_or_rank_and_with_zero_cost():
    """RN-01: a fictional non-creature with no power, no toughness, mana value
    zero and no EDHREC rank is stored."""
    models = _models()
    values = _fictional_card(
        name="Hollow Pebble",
        mana_cost="{0}",
        cmc=0.0,
        type_line="Artifact",
        oracle_text="",
        colors=[],
        color_identity=[],
        keywords=[],
        power=None,
        toughness=None,
        edhrec_rank=None,
    )
    models.OracleCard.objects.create(**values)

    card = models.OracleCard.objects.get(pk=values["oracle_id"])
    assert card.cmc == 0
    assert card.power is None
    assert card.toughness is None
    assert card.edhrec_rank is None


@pytest.mark.django_db
def test_oracle_card_cmc_keeps_a_fraction():
    """RN-01: the mana value keeps a fractional value as the source gives it."""
    models = _models()
    values = _fictional_card(name="Half-Lit Wisp", mana_cost="{½}", cmc=0.5)
    models.OracleCard.objects.create(**values)
    assert models.OracleCard.objects.get(pk=values["oracle_id"]).cmc == 0.5


@pytest.mark.django_db
def test_oracle_card_oracle_id_is_unique():
    """RN-03: one row per oracle_id, so a rebuild cannot duplicate a card."""
    models = _models()
    values = _fictional_card()
    models.OracleCard.objects.create(**values)
    with pytest.raises(IntegrityError), transaction.atomic():
        models.OracleCard.objects.create(**{**values, "name": "Lantern Warden Again"})
    assert models.OracleCard.objects.count() == 1


@pytest.mark.django_db
def test_oracle_fts_rows_link_to_their_card_by_oracle_id():
    """RN-01, RN-04 (plan sections 4 and 9.1): each full-text row keeps the
    `oracle_id` of its card, so a MATCH leads back to the right OracleCard."""
    models = _models()
    card = models.OracleCard.objects.create(**_fictional_card(name="Lantern Warden of Vell", oracle_text="Vigilance."))
    other = models.OracleCard.objects.create(**_fictional_card(name="Quiet Ember Drake", type_line="Creature — Drake", oracle_text="Flying."))
    with connection.cursor() as cursor:
        for row in (card, other):
            cursor.execute(
                "INSERT INTO oracle_fts (oracle_id, name, type_line, oracle_text) VALUES (%s, %s, %s, %s)",
                [str(row.pk), row.name, row.type_line, row.oracle_text],
            )
        cursor.execute("SELECT oracle_id FROM oracle_fts WHERE oracle_fts MATCH %s", ['"Lantern"'])
        found = [value for (value,) in cursor.fetchall()]
    assert found == [str(card.pk)]
    assert models.OracleCard.objects.get(pk=found[0]).name == "Lantern Warden of Vell"
