"""Card, CardVersion and UsageRecord models (task T37, spec RN-14, RN-25, RN-26).

Details: specs/plan.md, sections 4 (cards models) and 7 (stable identifiers,
stored JSON formats, no foreign key to a catalog table).

API under test:

    cards.models.Card
        id (UUID4 primary key), created_at, current_version (nullable link to
        CardVersion), and the request the card came from:
        idea, requested_color_identity (JSON list of color letters, an empty
        list for colorless), power_level (choices: casual, medium, strong)

    cards.models.CardVersion
        card, number (1, 2, ...), name, mana_cost, mana_value, type_line,
        rules_text, power, toughness, rarity, design_intent, rationale,
        comparables (JSON list of {oracle_id, name, role}), power_indicator,
        power_justification, status (choices: approved, rejected),
        validation (JSON: {status, checks_run, causes, skipped})
        A saved version cannot be changed: saving it again raises.
        (card, number) is unique.

    cards.models.UsageRecord
        card (nullable), kind, provider, model, input_tokens, output_tokens,
        outcome (choices: ok, failed), created_at. Its service is task T38.

Image, base card and language fields belong to later milestones and are not
tested here. Every card below is fictional and written by hand.
"""

import uuid

import pytest
from django.apps import apps
from django.db import IntegrityError, connection, transaction

from tests.cards_helpers import (
    REJECTED_VALIDATION,
    REQUEST,
    models,
    new_card,
    save_version,
    version_fields,
)

pytestmark = pytest.mark.django_db

CARD_REQUEST_FIELDS = {"id", "created_at", "current_version", "idea", "requested_color_identity", "power_level"}
VERSION_FIELDS_M3 = {
    "card",
    "number",
    "name",
    "mana_cost",
    "mana_value",
    "type_line",
    "rules_text",
    "power",
    "toughness",
    "rarity",
    "design_intent",
    "rationale",
    "comparables",
    "power_indicator",
    "power_justification",
    "status",
    "validation",
}
USAGE_TEXT_FIELDS = {"card", "kind", "provider", "model", "input_tokens", "output_tokens", "outcome", "created_at"}

# 1,000 Unicode characters, the longest idea a request accepts (RN-11), with
# accents, an emoji outside the Basic Multilingual Plane and quotes.
LONGEST_IDEA = ("Elfa ação “x” 🌲 ' \" ; -- " * 40)[:1000]


def _field_names(model):
    return {field.name for field in model._meta.get_fields()}


def _choice_values(model, field_name):
    return {value for value, _label in model._meta.get_field(field_name).choices}


# --- Fields ---------------------------------------------------------------------------------


def test_t37_rn26_card_has_uuid_id_creation_date_current_version_and_request_fields():
    """RN-26 / T37: a card is saved locally with a UUID4 id, its creation date, its current version
    and the request it came from (plan section 4)."""
    card_model = models().Card
    assert CARD_REQUEST_FIELDS <= _field_names(card_model)
    assert card_model._meta.pk.name == "id"
    card = new_card()
    assert isinstance(card.id, uuid.UUID)
    assert card.id.version == 4
    assert card.created_at is not None
    assert card.current_version is None


def test_t37_rn25_card_version_has_the_fields_milestone_3_stores():
    """RN-25 / T37: a version holds the text fields, design intent, rationale, comparables, power
    indicator with its justification, status and validation causes."""
    assert VERSION_FIELDS_M3 <= _field_names(models().CardVersion)


def test_t37_power_level_choices_are_the_three_spec_levels():
    """RN-11 / T37: the stored power level is casual, medium or strong (spec "Power level")."""
    assert _choice_values(models().Card, "power_level") == {"casual", "medium", "strong"}


def test_t37_rn14_version_status_choices_are_approved_and_rejected():
    """RN-14 / T37: a version is either approved or rejected; there is no third state."""
    assert _choice_values(models().CardVersion, "status") == {"approved", "rejected"}


def test_t37_usage_record_has_the_text_usage_fields():
    """RN-09 / T37: UsageRecord exists with the text usage fields; recording it is task T38."""
    usage_model = models().UsageRecord
    assert USAGE_TEXT_FIELDS <= _field_names(usage_model)
    assert usage_model._meta.get_field("card").null is True
    assert {"ok", "failed"} <= _choice_values(usage_model, "outcome")
    assert "text" in _choice_values(usage_model, "kind")


# --- The stored request ----------------------------------------------------------------------


def test_t37_rn26_stored_request_round_trips():
    """RN-26 / T37: the idea, requested color identity and power level are read back as written."""
    card = new_card()
    stored = models().Card.objects.get(pk=card.pk)
    assert stored.idea == REQUEST["idea"]
    assert stored.requested_color_identity == ["G", "U"]
    assert stored.power_level == "medium"


def test_t37_rn26_colorless_request_is_stored_as_an_empty_identity():
    """RN-26 / T37: a colorless request is stored, distinct from a missing identity (plan section 4,
    "possibly colorless")."""
    card = new_card(requested_color_identity=[])
    stored = models().Card.objects.get(pk=card.pk)
    assert stored.requested_color_identity == []
    assert stored.requested_color_identity is not None


def test_t37_rn26_five_color_request_keeps_every_color():
    """RN-26 / T37: a five-color request keeps all five letters."""
    card = new_card(requested_color_identity=["W", "U", "B", "R", "G"])
    assert models().Card.objects.get(pk=card.pk).requested_color_identity == ["W", "U", "B", "R", "G"]


def test_t37_rn26_longest_idea_with_odd_characters_round_trips():
    """RN-26 / T37: an idea of 1,000 Unicode characters with accents, an emoji and SQL-like quotes is
    stored unchanged."""
    assert len(LONGEST_IDEA) == 1000
    card = new_card(idea=LONGEST_IDEA, power_level="strong")
    stored = models().Card.objects.get(pk=card.pk)
    assert stored.idea == LONGEST_IDEA
    assert stored.power_level == "strong"


def test_t37_rn25_request_is_unchanged_by_new_versions():
    """RN-25 / T37: revalidation reads the stored request, so saving versions never changes it."""
    card = new_card(requested_color_identity=["B"], power_level="casual")
    save_version(card, **version_fields())
    save_version(card, **version_fields(name="Thornveil Courier, Revised"))
    stored = models().Card.objects.get(pk=card.pk)
    assert stored.idea == REQUEST["idea"]
    assert stored.requested_color_identity == ["B"]
    assert stored.power_level == "casual"


# --- Version contents --------------------------------------------------------------------------


def test_t37_rn25_version_fields_round_trip():
    """RN-25 / T37: every stored field of a version is read back as written, the JSON fields in the
    formats of plan section 7."""
    card = new_card()
    fields = version_fields()
    version = save_version(card, **fields)
    stored = models().CardVersion.objects.get(pk=version.pk)
    for name, value in fields.items():
        assert getattr(stored, name) == value, name
    assert stored.card_id == card.pk


def test_t37_rn14_rejected_version_keeps_its_status_and_causes():
    """RN-14 / T37: a rejected version is stored as rejected with every cause (check, code, message)."""
    card = new_card()
    version = save_version(card, **version_fields(status="rejected", validation=REJECTED_VALIDATION))
    stored = models().CardVersion.objects.get(pk=version.pk)
    assert stored.status == "rejected"
    assert stored.validation == REJECTED_VALIDATION
    assert [cause["check"] for cause in stored.validation["causes"]] == ["mana_cost", "color_identity"]


def test_t37_rn25_version_without_power_toughness_or_cost_is_stored():
    """RN-25 / T37: a land with no mana cost (mana value 0) and no power or toughness is stored."""
    card = new_card(requested_color_identity=[])
    fields = version_fields(
        name="Hollowmere Basin",
        mana_cost="",
        mana_value=0,
        type_line="Land",
        rules_text="{T}: Add {C}.",
        rarity="common",
    )
    del fields["power"], fields["toughness"]
    version = save_version(card, **fields)
    stored = models().CardVersion.objects.get(pk=version.pk)
    assert stored.mana_cost == ""
    assert stored.mana_value == 0
    assert not stored.power
    assert not stored.toughness


def test_t37_rn25_hybrid_symbols_odd_power_and_long_text_round_trip():
    """RN-25 / T37: hybrid and Phyrexian symbols, a negative or star power and a long rules text with
    typographic characters are stored unchanged."""
    long_text = ("Whenever a creature you control dies, put a +1/+1 counter on Thornveil — “it grows”. " * 60).strip()
    fields = version_fields(
        mana_cost="{X}{W/U}{2/B}{G/P}{C}",
        mana_value=5,
        power="-1",
        toughness="1+*",
        rules_text=long_text,
        name="Ação d'Ébano 🌲",
    )
    card = new_card()
    version = save_version(card, **fields)
    stored = models().CardVersion.objects.get(pk=version.pk)
    assert stored.mana_cost == "{X}{W/U}{2/B}{G/P}{C}"
    assert stored.power == "-1"
    assert stored.toughness == "1+*"
    assert stored.rules_text == long_text
    assert stored.name == "Ação d'Ébano 🌲"


def test_t37_rn25_empty_comparables_and_extra_validation_keys_round_trip():
    """RN-25 / T37: stored JSON formats may gain keys (plan section 7); an empty comparables list and
    an extra key in validation are read back as written."""
    validation = dict(REJECTED_VALIDATION, future_key={"nested": [1, 2]})
    card = new_card()
    version = save_version(card, **version_fields(comparables=[], status="rejected", validation=validation))
    stored = models().CardVersion.objects.get(pk=version.pk)
    assert stored.comparables == []
    assert stored.validation == validation


# --- Immutability ------------------------------------------------------------------------------


def test_t37_rn25_saved_version_cannot_be_changed():
    """RN-25 / T37: versions are immutable; saving a changed version raises and the stored row keeps
    its values, so an earlier version can always be restored as it was."""
    card = new_card()
    version = save_version(card, **version_fields())
    version.name = "Overwritten Name"
    version.rules_text = "Overwritten text."
    with pytest.raises(Exception):
        with transaction.atomic():
            version.save()
    stored = models().CardVersion.objects.get(pk=version.pk)
    assert stored.name == "Thornveil Courier"
    assert stored.rules_text == version_fields()["rules_text"]


def test_t37_rn25_resaving_an_unchanged_version_also_raises():
    """RN-25 / T37: immutability does not depend on whether a field changed: any save of a stored
    version raises."""
    card = new_card()
    version = save_version(card, **version_fields())
    stored = models().CardVersion.objects.get(pk=version.pk)
    with pytest.raises(Exception):
        with transaction.atomic():
            stored.save()


def test_t37_rn25_earlier_version_keeps_its_fields_after_a_later_save():
    """RN-25 / T37: saving a new version leaves the earlier one untouched."""
    card = new_card()
    first = save_version(card, **version_fields())
    save_version(card, **version_fields(name="Thornveil Courier, Revised", mana_cost="{2}{G}", status="rejected",
                                         validation=REJECTED_VALIDATION))
    stored_first = models().CardVersion.objects.get(pk=first.pk)
    for name, value in version_fields().items():
        if name == "comparables":
            continue  # generated with fresh ids per call
        assert getattr(stored_first, name) == value, name
    assert stored_first.comparables == first.comparables


# --- Unique (card, number) ---------------------------------------------------------------------


def test_t37_rn25_card_and_number_are_unique_together():
    """RN-25 / T37: the database refuses a second version with the same number on the same card."""
    card = new_card()
    first = save_version(card, **version_fields())
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            models().CardVersion.objects.create(card=card, number=first.number, **version_fields())
    assert models().CardVersion.objects.filter(card=card).count() == 1


def test_t37_rn25_same_number_on_two_cards_is_allowed():
    """RN-25 / T37: numbering is per card, so two cards each have a version 1."""
    first = save_version(new_card(), **version_fields())
    second = save_version(new_card(), **version_fields())
    assert first.number == second.number == 1


# --- No foreign key to a catalog table -----------------------------------------------------------


def _cards_models():
    return list(apps.get_app_config("cards").get_models())


def test_t37_no_cards_model_relates_to_a_catalog_model():
    """Plan section 7 / T37: user tables never hold a foreign key to a catalog table, because a
    rebuild deletes the reference rows. Every model of the `cards` app is checked."""
    names = {model.__name__ for model in _cards_models()}
    assert {"Card", "CardVersion", "UsageRecord"} <= names
    for model in _cards_models():
        for field in model._meta.get_fields():
            if field.is_relation and field.related_model is not None:
                assert field.related_model._meta.app_label != "catalog", f"{model.__name__}.{field.name}"


def test_t37_no_cards_table_has_a_database_foreign_key_to_a_catalog_table():
    """Plan section 7 / T37: the database schema of every `cards` table has no foreign key to a
    catalog table."""
    assert {"Card", "CardVersion", "UsageRecord"} <= {model.__name__ for model in _cards_models()}
    catalog_tables = {model._meta.db_table for model in apps.get_app_config("catalog").get_models()}
    with connection.cursor() as cursor:
        for model in _cards_models():
            relations = connection.introspection.get_relations(cursor, model._meta.db_table)
            for column, (_other_column, other_table) in relations.items():
                assert other_table not in catalog_tables, f"{model._meta.db_table}.{column} -> {other_table}"


def test_t37_version_survives_the_deletion_of_its_comparable_reference_card():
    """Plan section 7 / T37: a rebuild deletes reference rows; a version that cites a deleted
    reference card keeps its comparables snapshot."""
    from catalog.models import OracleCard

    oracle_id = str(uuid.uuid4())
    OracleCard.objects.create(
        oracle_id=oracle_id,
        name="Mossback Herald of Quill",
        mana_cost="{2}{G}",
        cmc=3.0,
        type_line="Creature — Elf Druid",
        oracle_text="When Mossback Herald of Quill enters, draw a card.",
        colors=["G"],
        color_identity=["G"],
        keywords=[],
        power="2",
        toughness="2",
        layout="normal",
        faces=[],
        commander_legality="legal",
        game_changer=False,
        edhrec_rank=4321,
        roles=["card_draw"],
    )
    snapshot = [{"oracle_id": oracle_id, "name": "Mossback Herald of Quill", "role": "card_draw"}]
    card = new_card()
    version = save_version(card, **version_fields(comparables=snapshot))
    OracleCard.objects.all().delete()
    stored = models().CardVersion.objects.get(pk=version.pk)
    assert stored.comparables == snapshot
    assert models().Card.objects.get(pk=card.pk).current_version_id == version.pk
