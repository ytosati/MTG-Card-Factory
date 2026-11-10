"""JSON validator for the provider schema subset (task T35, spec RN-10).

Details: specs/plan.md, section 9.2. Text responses are parsed and checked
against the schema before use; an invalid response becomes `InvalidResponse`.
The subset is: object (with `properties` and `required`), array (with
`items`), string, integer, number, boolean and enum.

API under test:

    providers.schema.validate_json(data, schema) -> list[str]
        the problems found in `data`; an empty list means the data matches.
        Pure function: no provider call, no exception for a mismatch.

Every response below is fictional and written by hand.
"""

import pytest

CARD_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "mana_value": {"type": "integer"},
        "power_score": {"type": "number"},
        "legendary": {"type": "boolean"},
        "rarity": {"type": "string", "enum": ["common", "uncommon", "rare", "mythic"]},
        "colors": {"type": "array", "items": {"type": "string", "enum": ["W", "U", "B", "R", "G"]}},
        "comparables": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"name": {"type": "string"}, "reason": {"type": "string"}},
                "required": ["name", "reason"],
            },
        },
    },
    "required": ["name", "mana_value", "power_score", "legendary", "rarity", "colors", "comparables"],
}


def _valid_card():
    return {
        "name": "Lantern Warden of Vell",
        "mana_value": 3,
        "power_score": 6.5,
        "legendary": True,
        "rarity": "rare",
        "colors": ["W", "U"],
        "comparables": [{"name": "Quiet Harbor Sentry", "reason": "Same role at a similar cost."}],
    }


def validate_json(data, schema):
    from providers.schema import validate_json as validate

    return validate(data, schema)


def assert_valid(data, schema):
    problems = validate_json(data, schema)
    assert problems == []


def assert_invalid(data, schema):
    problems = validate_json(data, schema)
    assert isinstance(problems, list)
    assert problems, "the validator accepted data that does not match the schema"
    assert all(isinstance(problem, str) and problem for problem in problems)


# Whole response


def test_rn10_accepts_a_full_fictional_card_response():
    """RN-10: a response that matches every keyword of the schema is accepted."""
    assert_valid(_valid_card(), CARD_SCHEMA)


def test_rn10_validator_does_not_change_the_data():
    """RN-10: checking a response leaves it as the provider sent it."""
    card = _valid_card()
    validate_json(card, CARD_SCHEMA)
    assert card == _valid_card()


# object


def test_rn10_object_refuses_non_object_values():
    """RN-10 (object): a list, a string, a number or null in place of an object is refused."""
    for value in ([], "card", 3, None, True):
        assert_invalid(value, CARD_SCHEMA)


def test_rn10_object_accepts_an_empty_object_with_no_properties():
    """RN-10 (object) edge case: an object schema with no properties accepts {}."""
    assert_valid({}, {"type": "object", "properties": {}, "required": []})


# required


@pytest.mark.parametrize("missing", CARD_SCHEMA["required"])
def test_rn10_required_refuses_a_missing_property(missing):
    """RN-10 (required): every property is required; a missing one is refused."""
    card = _valid_card()
    del card[missing]
    assert_invalid(card, CARD_SCHEMA)


def test_rn10_required_refuses_an_empty_object():
    """RN-10 (required) edge case: an empty object misses every property."""
    assert_invalid({}, CARD_SCHEMA)


def test_rn10_required_is_checked_inside_array_items():
    """RN-10 (required, nested): an item missing a required property is refused."""
    card = _valid_card()
    card["comparables"] = [{"name": "Quiet Harbor Sentry"}]
    assert_invalid(card, CARD_SCHEMA)


# properties


def test_rn10_properties_checks_the_type_of_each_property():
    """RN-10 (properties): a property of the wrong type is refused."""
    card = _valid_card()
    card["name"] = 42
    assert_invalid(card, CARD_SCHEMA)


def test_rn10_properties_checks_nested_objects():
    """RN-10 (properties, nested): a wrong type deep inside the response is refused."""
    card = _valid_card()
    card["comparables"][0]["reason"] = ["not", "a", "string"]
    assert_invalid(card, CARD_SCHEMA)


# string


def test_rn10_string_accepts_text():
    """RN-10 (string): text is accepted, including an empty string."""
    schema = {"type": "string"}
    assert_valid("Flying", schema)
    assert_valid("", schema)


def test_rn10_string_accepts_odd_characters_and_hybrid_symbols():
    """RN-10 (string) edge case: mana symbols, hybrid and Phyrexian symbols,
    accents, quotes and line breaks are plain text."""
    schema = {"type": "string"}
    for text in (
        "{W/U}{2/B}{G/P}",
        "Ação rápida — “Voe”.",
        "{T}: Add {C}.\nWhen this enters, scry 1.",
        "\u0000�\U0001f0a1",
    ):
        assert_valid(text, schema)


def test_rn10_string_accepts_huge_text():
    """RN-10 (string) edge case: the validator has no length limit of its own."""
    assert_valid("x" * 200_000, {"type": "string"})


def test_rn10_string_refuses_other_types():
    """RN-10 (string): numbers, booleans, null, lists and objects are refused."""
    schema = {"type": "string"}
    for value in (3, 3.5, True, None, ["Flying"], {"text": "Flying"}):
        assert_invalid(value, schema)


# integer


def test_rn10_integer_accepts_whole_numbers_including_zero_and_negative():
    """RN-10 (integer): zero, negative and very large whole numbers are accepted."""
    schema = {"type": "integer"}
    for value in (0, 7, -1, 10**30):
        assert_valid(value, schema)


def test_rn10_integer_refuses_fractions_and_text():
    """RN-10 (integer): a fraction or a number written as text is refused."""
    schema = {"type": "integer"}
    for value in (2.5, "3", None, [3]):
        assert_invalid(value, schema)


def test_rn10_integer_refuses_booleans():
    """RN-10 (integer) edge case: JSON booleans are not numbers, even though
    Python treats bool as int."""
    schema = {"type": "integer"}
    assert_invalid(True, schema)
    assert_invalid(False, schema)


# number


def test_rn10_number_accepts_integers_and_fractions():
    """RN-10 (number): integers and fractions, zero and negative, are accepted."""
    schema = {"type": "number"}
    for value in (0, 0.0, 6.5, -2, -0.25, 1e300):
        assert_valid(value, schema)


def test_rn10_number_refuses_text_null_and_booleans():
    """RN-10 (number): text, null and booleans are refused."""
    schema = {"type": "number"}
    for value in ("6.5", None, True, False, {}):
        assert_invalid(value, schema)


# boolean


def test_rn10_boolean_accepts_true_and_false():
    """RN-10 (boolean): true and false are accepted."""
    schema = {"type": "boolean"}
    assert_valid(True, schema)
    assert_valid(False, schema)


def test_rn10_boolean_refuses_look_alikes():
    """RN-10 (boolean) edge case: 0, 1, "true" and null are not booleans."""
    schema = {"type": "boolean"}
    for value in (0, 1, "true", "false", None):
        assert_invalid(value, schema)


# array and items


def test_rn10_array_accepts_lists_including_empty():
    """RN-10 (array): a list of valid items is accepted, and so is an empty list."""
    schema = {"type": "array", "items": {"type": "string"}}
    assert_valid(["W", "U"], schema)
    assert_valid([], schema)


def test_rn10_array_refuses_non_lists():
    """RN-10 (array): a string, an object or null in place of a list is refused."""
    schema = {"type": "array", "items": {"type": "string"}}
    for value in ("WU", {"0": "W"}, None, 2):
        assert_invalid(value, schema)


def test_rn10_items_refuses_a_single_wrong_item():
    """RN-10 (items): one wrong item among valid ones is refused."""
    schema = {"type": "array", "items": {"type": "integer"}}
    assert_invalid([1, 2, "3"], schema)


def test_rn10_items_checks_arrays_of_arrays():
    """RN-10 (items, nested): the item schema applies at every depth."""
    schema = {"type": "array", "items": {"type": "array", "items": {"type": "boolean"}}}
    assert_valid([[True], [], [False, True]], schema)
    assert_invalid([[True], [1]], schema)


# enum


def test_rn10_enum_accepts_a_listed_value():
    """RN-10 (enum): each listed value is accepted."""
    schema = CARD_SCHEMA["properties"]["rarity"]
    for value in ("common", "uncommon", "rare", "mythic"):
        assert_valid(value, schema)


def test_rn10_enum_refuses_an_unlisted_value():
    """RN-10 (enum): a value outside the list is refused, including a different
    case, surrounding spaces and an empty string."""
    schema = CARD_SCHEMA["properties"]["rarity"]
    for value in ("legendary", "Rare", " rare", "", None):
        assert_invalid(value, schema)


def test_rn10_enum_inside_array_items():
    """RN-10 (enum in items): one color outside the list makes the response invalid."""
    card = _valid_card()
    card["colors"] = ["W", "P"]
    assert_invalid(card, CARD_SCHEMA)


def test_rn10_enum_of_integers():
    """RN-10 (enum) with integer values: only the listed numbers are accepted."""
    schema = {"type": "integer", "enum": [1, 2, 3]}
    assert_valid(2, schema)
    assert_invalid(4, schema)
    assert_invalid(0, schema)


# malformed provider responses


@pytest.mark.parametrize(
    "response",
    [
        None,
        "",
        "{\"name\": \"Lantern Warden of Vell\"}",
        [],
        [_valid_card()],
        {"card": _valid_card()},
    ],
    ids=["null", "empty-string", "json-as-text", "empty-list", "wrapped-in-list", "wrapped-in-object"],
)
def test_rn10_malformed_provider_responses_are_refused(response):
    """RN-10: malformed responses (null, text, a wrapped card) never pass as a card."""
    assert_invalid(response, CARD_SCHEMA)
