"""Output schemas of the generation calls (task T46; spec RN-12, RN-13, RN-15, RN-22).

Details: specs/plan.md, sections 9.1 and 9.2. The text model answers three
kinds of call with structured JSON: the design intent with its search plan,
the card draft, and the revision. Each answer is checked against its schema
by `providers.schema.validate_json` before use (RN-10).

API under test:

    generation.schemas.DESIGN_SCHEMA     design intent and search plan
        design_intent: string
        search_plan: object
            keywords: array of string
            roles: array of string
            card_types: array of string
            mana_value_min: integer
            mana_value_max: integer
    generation.schemas.DRAFT_SCHEMA      the card draft
        name, mana_cost, type_line, rules_text, power, toughness: string
            (mana_cost "" means no mana cost; power and toughness "" when absent)
        mana_value: integer
        rarity: string, enum common, uncommon, rare, mythic
        rationale: string
        comparables: array of object {oracle_id, name, role: string}
        power_indicator: string, enum too_strong, in_range, too_weak
        power_justification: string
    generation.schemas.REVISION_SCHEMA   the whole card again (RN-15): the
        same properties as the draft; the design intent stays, so it is not
        part of the revision.

Every module-level `*_SCHEMA` dict in `generation.schemas` is walked, so a
schema added later (quick adjustments, base card) is covered without editing
this file. Every response below is fictional and written by hand.
"""

import copy

import pytest

ALLOWED_KEYWORDS = {"type", "properties", "required", "items", "enum"}
ALLOWED_TYPES = {"object", "array", "string", "integer", "number", "boolean"}

CARD_FIELDS = {
    "name",
    "mana_cost",
    "mana_value",
    "type_line",
    "rules_text",
    "power",
    "toughness",
    "rarity",
}
DRAFT_FIELDS = CARD_FIELDS | {"rationale", "comparables", "power_indicator", "power_justification"}


def _schemas_module():
    from generation import schemas

    return schemas


def _all_schemas():
    module = _schemas_module()
    return {
        name: value
        for name, value in vars(module).items()
        if name.endswith("_SCHEMA") and isinstance(value, dict)
    }


def _validate(data, schema):
    from providers.schema import validate_json

    return validate_json(data, schema)


def _walk(node, path, problems):
    if not isinstance(node, dict):
        problems.append(f"{path}: schema node is not an object")
        return
    extra = set(node) - ALLOWED_KEYWORDS
    if extra:
        problems.append(f"{path}: keywords outside the subset: {sorted(extra)}")
    node_type = node.get("type")
    if not isinstance(node_type, str) or node_type not in ALLOWED_TYPES:
        problems.append(f"{path}: 'type' missing or not one supported type: {node_type!r}")
        return
    if "enum" in node:
        options = node["enum"]
        if not isinstance(options, list) or not options:
            problems.append(f"{path}: enum must be a non-empty list")
        elif node_type == "string" and not all(isinstance(o, str) for o in options):
            problems.append(f"{path}: enum values must match the node type")
    if node_type == "object":
        properties = node.get("properties")
        if not isinstance(properties, dict) or not properties:
            problems.append(f"{path}: object without properties")
            return
        required = node.get("required")
        if not isinstance(required, list) or len(required) != len(set(required)) or set(required) != set(
            properties
        ):
            problems.append(f"{path}: 'required' must list every property exactly once")
        for name, child in properties.items():
            _walk(child, f"{path}.{name}", problems)
    elif "properties" in node or "required" in node:
        problems.append(f"{path}: properties/required on a non-object node")
    if node_type == "array":
        if "items" not in node:
            problems.append(f"{path}: array without items")
        else:
            _walk(node["items"], f"{path}[]", problems)
    elif "items" in node:
        problems.append(f"{path}: items on a non-array node")


def _valid_design():
    return {
        "design_intent": "A green ramp creature that rewards playing lands from the graveyard.",
        "search_plan": {
            "keywords": ["landfall", "graveyard", "land"],
            "roles": ["ramp"],
            "card_types": ["Creature"],
            "mana_value_min": 2,
            "mana_value_max": 4,
        },
    }


def _valid_draft():
    return {
        "name": "Mossgrave Tender",
        "mana_cost": "{2}{G}",
        "mana_value": 3,
        "type_line": "Creature — Elf Druid",
        "rules_text": "You may play lands from your graveyard.\n{T}: Add {G}.",
        "power": "2",
        "toughness": "3",
        "rarity": "rare",
        "rationale": "Pairs land recursion with mana, in line with the cited ramp creatures.",
        "comparables": [
            {"oracle_id": "00000000-0000-4000-8000-000000000001", "name": "Fictional Grove Keeper", "role": "ramp"},
            {"oracle_id": "00000000-0000-4000-8000-000000000002", "name": "Fictional Root Caller", "role": "ramp"},
        ],
        "power_indicator": "in_range",
        "power_justification": "Costs one more than Fictional Grove Keeper for a similar effect.",
    }


# --- The walk over every schema (plan 9.2) -----------------------------------


def test_rn12_rn13_the_three_generation_schemas_exist():
    """RN-12, RN-13, RN-15: design, draft and revision each have a schema."""
    names = set(_all_schemas())
    assert {"DESIGN_SCHEMA", "DRAFT_SCHEMA", "REVISION_SCHEMA"} <= names


def test_plan92_every_schema_uses_only_the_keyword_subset_and_every_node_has_a_type():
    """Plan 9.2 (RN-10): only object, array, string, integer, number, boolean and
    enum; every node has a `type`; every object lists all its properties in
    `required`, so the strict mode of every provider accepts the schema."""
    schemas = _all_schemas()
    assert schemas
    problems: list[str] = []
    for name, schema in schemas.items():
        _walk(schema, name, problems)
    assert problems == []


def test_plan92_every_schema_has_an_object_root():
    """Plan 9.2: structured output needs an object at the root."""
    for name, schema in _all_schemas().items():
        assert schema.get("type") == "object", name


@pytest.mark.parametrize(
    "bad_node",
    [
        {"type": "string", "pattern": "^x$"},
        {"type": "string", "format": "uuid"},
        {"anyOf": [{"type": "string"}, {"type": "integer"}]},
        {"type": ["string", "null"]},
        {"type": "integer", "minimum": 0},
        {"type": "object", "properties": {"a": {"type": "string"}}, "required": []},
        {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"], "additionalProperties": False},
        {"type": "array"},
        {"enum": ["a", "b"]},
    ],
)
def test_plan92_the_walk_refuses_schemas_outside_the_subset(bad_node):
    """Plan 9.2: the walk itself catches each forbidden construct."""
    problems: list[str] = []
    _walk({"type": "object", "properties": {"x": bad_node}, "required": ["x"]}, "probe", problems)
    assert problems


# --- Design intent and search plan (RN-12, plan 9.1) -------------------------


def test_rn12_design_schema_fields():
    """RN-12, plan 9.1: design intent, then keywords, roles, card types and a mana value range."""
    schemas = _schemas_module()
    props = schemas.DESIGN_SCHEMA["properties"]
    assert set(props) == {"design_intent", "search_plan"}
    assert props["design_intent"]["type"] == "string"
    plan = props["search_plan"]
    assert plan["type"] == "object"
    assert set(plan["properties"]) == {"keywords", "roles", "card_types", "mana_value_min", "mana_value_max"}
    for name in ("keywords", "roles", "card_types"):
        assert plan["properties"][name]["type"] == "array"
        assert plan["properties"][name]["items"]["type"] == "string"
    assert plan["properties"]["mana_value_min"]["type"] == "integer"
    assert plan["properties"]["mana_value_max"]["type"] == "integer"


def test_rn12_valid_design_response_passes():
    """RN-12: a well-formed design intent and search plan is accepted."""
    schemas = _schemas_module()
    assert _validate(_valid_design(), schemas.DESIGN_SCHEMA) == []


def test_rn12_design_with_empty_lists_and_zero_range_passes():
    """RN-12: empty keyword lists and a 0–0 range are well formed (widening is the selector's job)."""
    schemas = _schemas_module()
    data = _valid_design()
    data["search_plan"].update(keywords=[], roles=[], card_types=[], mana_value_min=0, mana_value_max=0)
    assert _validate(data, schemas.DESIGN_SCHEMA) == []


@pytest.mark.parametrize("missing", ["design_intent", "search_plan"])
def test_rn12_design_missing_top_level_field_is_rejected(missing):
    """RN-12, RN-10: a design answer without one of its fields is invalid."""
    schemas = _schemas_module()
    data = _valid_design()
    del data[missing]
    assert _validate(data, schemas.DESIGN_SCHEMA)


@pytest.mark.parametrize("missing", ["keywords", "roles", "card_types", "mana_value_min", "mana_value_max"])
def test_rn12_search_plan_missing_field_is_rejected(missing):
    """RN-12, RN-10: a search plan without one of its fields is invalid."""
    schemas = _schemas_module()
    data = _valid_design()
    del data["search_plan"][missing]
    assert _validate(data, schemas.DESIGN_SCHEMA)


@pytest.mark.parametrize(
    "field, value",
    [
        ("keywords", "flying"),
        ("keywords", [1, 2]),
        ("roles", None),
        ("card_types", {"Creature": True}),
        ("mana_value_min", "2"),
        ("mana_value_min", 2.5),
        ("mana_value_max", True),
    ],
)
def test_rn12_search_plan_wrong_types_are_rejected(field, value):
    """RN-12, RN-10: malformed search plan values are invalid."""
    schemas = _schemas_module()
    data = _valid_design()
    data["search_plan"][field] = value
    assert _validate(data, schemas.DESIGN_SCHEMA)


@pytest.mark.parametrize("data", [None, [], "design", 3, {}, {"design_intent": 7, "search_plan": {}}])
def test_rn12_malformed_design_responses_are_rejected(data):
    """RN-10: a design answer that is not the expected object is invalid."""
    schemas = _schemas_module()
    assert _validate(data, schemas.DESIGN_SCHEMA)


# --- Card draft (RN-13, RN-22) -----------------------------------------------


def test_rn13_rn22_draft_schema_fields():
    """RN-13, RN-22: card fields, rationale, comparables and the power indicator
    with its justification; the design intent comes from the first call."""
    schemas = _schemas_module()
    props = schemas.DRAFT_SCHEMA["properties"]
    assert set(props) == DRAFT_FIELDS
    for name in ("name", "mana_cost", "type_line", "rules_text", "power", "toughness", "rarity",
                 "rationale", "power_indicator", "power_justification"):
        assert props[name]["type"] == "string", name
    assert props["mana_value"]["type"] == "integer"
    assert set(props["rarity"]["enum"]) == {"common", "uncommon", "rare", "mythic"}


def test_rn22_power_indicator_enum_matches_the_stored_codes():
    """RN-22: the indicator is one of too strong, in range, too weak, as stored on CardVersion."""
    from cards.models import CardVersion

    schemas = _schemas_module()
    indicator = schemas.DRAFT_SCHEMA["properties"]["power_indicator"]
    assert set(indicator["enum"]) == set(CardVersion.PowerIndicator.values)


def test_rn13_comparable_items_are_snapshots():
    """RN-13, plan 4: each comparable is {oracle_id, name, role}."""
    schemas = _schemas_module()
    comparables = schemas.DRAFT_SCHEMA["properties"]["comparables"]
    assert comparables["type"] == "array"
    item = comparables["items"]
    assert item["type"] == "object"
    assert set(item["properties"]) == {"oracle_id", "name", "role"}
    for name in ("oracle_id", "name", "role"):
        assert item["properties"][name]["type"] == "string"


def test_rn13_valid_draft_passes():
    """RN-13, RN-22: a complete fictional draft is accepted."""
    schemas = _schemas_module()
    assert _validate(_valid_draft(), schemas.DRAFT_SCHEMA) == []


def test_rn13_draft_without_mana_cost_or_power_uses_empty_strings():
    """RN-17: a land has no mana cost (empty string, mana value 0); a
    non-creature has empty power and toughness."""
    schemas = _schemas_module()
    data = _valid_draft()
    data.update(name="Hollowmere Basin", mana_cost="", mana_value=0, type_line="Land",
                rules_text="{T}: Add {C}.", power="", toughness="")
    assert _validate(data, schemas.DRAFT_SCHEMA) == []


def test_rn13_draft_null_mana_cost_or_power_is_rejected():
    """RN-17, RN-10: "no mana cost" is the empty string; null is malformed."""
    schemas = _schemas_module()
    for field in ("mana_cost", "power", "toughness"):
        data = _valid_draft()
        data[field] = None
        assert _validate(data, schemas.DRAFT_SCHEMA), field


def test_rn13_draft_with_odd_characters_hybrid_symbols_and_huge_text_passes():
    """RN-13: the schema carries any text; validators judge it later."""
    schemas = _schemas_module()
    data = _valid_draft()
    data.update(
        name="Æther-Spun Wíllow «Ñ» 龍",
        mana_cost="{X}{2}{W/U}{G/P}{2/B}",
        power="*",
        toughness="1+*",
        rules_text="Reach\n" + "When this creature enters, scry 1. " * 400,
    )
    assert _validate(data, schemas.DRAFT_SCHEMA) == []


@pytest.mark.parametrize("missing", sorted(DRAFT_FIELDS))
def test_rn13_rn22_draft_missing_field_is_rejected(missing):
    """RN-13, RN-22, RN-10: a draft without any one of its fields is invalid."""
    schemas = _schemas_module()
    data = _valid_draft()
    del data[missing]
    assert _validate(data, schemas.DRAFT_SCHEMA)


@pytest.mark.parametrize(
    "field, value",
    [
        ("mana_value", "3"),
        ("mana_value", 3.5),
        ("mana_value", True),
        ("power", 2),
        ("rarity", "legendary"),
        ("rarity", "Rare"),
        ("power_indicator", "balanced"),
        ("power_indicator", "too strong"),
        ("power_indicator", ""),
        ("comparables", "Fictional Grove Keeper"),
        ("comparables", [{"name": "Fictional Grove Keeper", "role": "ramp"}]),
        ("comparables", [{"oracle_id": 1, "name": "Fictional Grove Keeper", "role": "ramp"}]),
        ("comparables", ["Fictional Grove Keeper"]),
        ("rationale", ["a", "b"]),
        ("power_justification", None),
    ],
)
def test_rn13_rn22_draft_wrong_values_are_rejected(field, value):
    """RN-13, RN-22, RN-10: malformed draft values are invalid."""
    schemas = _schemas_module()
    data = _valid_draft()
    data[field] = value
    assert _validate(data, schemas.DRAFT_SCHEMA)


@pytest.mark.parametrize("data", [None, [], "card", 0, {}])
def test_rn13_malformed_draft_responses_are_rejected(data):
    """RN-10: a draft answer that is not the expected object is invalid."""
    schemas = _schemas_module()
    assert _validate(data, schemas.DRAFT_SCHEMA)


# --- Revision (RN-15) --------------------------------------------------------


def test_rn15_revision_returns_the_whole_card():
    """RN-15: the revision returns every card field, the rationale, the
    comparables and the power indicator; the design intent stays."""
    schemas = _schemas_module()
    props = schemas.REVISION_SCHEMA["properties"]
    assert set(props) == DRAFT_FIELDS
    assert "design_intent" not in props
    assert props == schemas.DRAFT_SCHEMA["properties"]


def test_rn15_valid_revision_passes():
    """RN-15: a complete fictional revision is accepted."""
    schemas = _schemas_module()
    data = _valid_draft()
    data.update(mana_cost="{3}{G}", mana_value=4, power_indicator="too_weak",
                power_justification="Now costs more than Fictional Root Caller for less.")
    assert _validate(data, schemas.REVISION_SCHEMA) == []


@pytest.mark.parametrize("missing", sorted(DRAFT_FIELDS))
def test_rn15_partial_revision_is_rejected(missing):
    """RN-15: a revision that returns only some fields is invalid (a failed revision call)."""
    schemas = _schemas_module()
    data = _valid_draft()
    del data[missing]
    assert _validate(data, schemas.REVISION_SCHEMA)


def test_rn15_revision_with_only_changed_fields_is_rejected():
    """RN-15: a patch-style answer is not a whole card."""
    schemas = _schemas_module()
    assert _validate({"mana_cost": "{3}{G}", "mana_value": 4}, schemas.REVISION_SCHEMA)


def test_schemas_are_not_mutated_by_validation():
    """Plan 9.2: the shared schema constants stay unchanged across calls."""
    schemas = _schemas_module()
    before = copy.deepcopy(_all_schemas())
    _validate(_valid_draft(), schemas.DRAFT_SCHEMA)
    _validate(_valid_design(), schemas.DESIGN_SCHEMA)
    assert _all_schemas() == before


# --- Search plan roles come from the catalog role list (RN-12, plan 9.6) -----


def test_rn12_search_plan_roles_enum_equals_the_catalog_roles():
    """RN-12, plan 9.1 and 9.6: the roles the model may plan are exactly the
    roles the catalog tags, in the same order."""
    from catalog.ingest import ROLES

    schemas = _schemas_module()
    roles = schemas.DESIGN_SCHEMA["properties"]["search_plan"]["properties"]["roles"]
    assert roles["items"]["enum"] == list(ROLES)


@pytest.mark.parametrize("role", ["big_ramp", "Ramp", "card draw", ""])
def test_rn12_search_plan_unknown_role_is_rejected(role):
    """RN-12, RN-10: a role outside the catalog list is invalid."""
    schemas = _schemas_module()
    data = _valid_design()
    data["search_plan"]["roles"] = ["ramp", role]
    assert _validate(data, schemas.DESIGN_SCHEMA)
