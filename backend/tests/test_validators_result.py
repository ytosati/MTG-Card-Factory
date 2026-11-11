"""The validation result and the `validate()` composition (task T28, spec RN-14, RN-17, plan sections 5 and 7).

The stored format is `{status, checks_run: [...], causes: [{check, code,
message}], skipped: [...]}` with stable check names. Later tasks add checks
(T29 color identity, T138 name, Milestone 5 type line, keywords and limits),
so these tests require `mana_cost` among the checks run, never an exact list.
"""

import copy
import json

from tests.validator_helpers import NO_LEXICON, card, land, request

STORED_KEYS = {"status", "checks_run", "causes", "skipped"}
CAUSE_KEYS = {"check", "code", "message"}


def _validate(draft, req=None):
    from validators import validate

    return validate(draft, NO_LEXICON, req if req is not None else request())


def test_t28_rn17_validate_returns_a_validation_result():
    """RN-17 / T28: `validate(card, lexicon, request)` returns a `ValidationResult`."""
    from validators import ValidationResult

    result = _validate(card())

    assert isinstance(result, ValidationResult)


def test_t28_rn17_approved_result_in_the_stored_format():
    """RN-17 / T28 (plan section 7): a valid card gives an approved result in the stored format."""
    stored = _validate(card()).to_dict()

    assert set(stored) == STORED_KEYS
    assert stored["status"] == "approved"
    assert "mana_cost" in stored["checks_run"]
    assert stored["causes"] == []
    assert "mana_cost" not in stored["skipped"]


def test_t28_rn17_result_attributes_match_the_stored_format():
    """RN-17 / T28: the result exposes status, checks run, causes and skipped checks."""
    result = _validate(card())

    assert result.status == "approved"
    assert "mana_cost" in list(result.checks_run)
    assert list(result.causes) == []
    assert "mana_cost" not in result.skipped


def test_t28_ca02_rejected_result_names_the_cause_in_the_stored_format():
    """CA-02 / T28 (plan section 7): a rejection carries a cause with a stable check name, code and message."""
    stored = _validate(card(mana_cost="{2}{G}", mana_value=4)).to_dict()

    assert set(stored) == STORED_KEYS
    assert stored["status"] == "rejected"
    assert "mana_cost" in stored["checks_run"]
    assert stored["causes"], "a rejected result names at least one cause"
    for cause in stored["causes"]:
        assert set(cause) == CAUSE_KEYS
        assert isinstance(cause["check"], str) and cause["check"]
        assert isinstance(cause["code"], str) and cause["code"]
        assert isinstance(cause["message"], str) and cause["message"].strip()


def test_t28_ca02_cause_objects_carry_check_code_and_message():
    """CA-02 / T28: each cause of the result object has `check`, `code` and `message`."""
    result = _validate(card(mana_cost="{2}{G}", mana_value=4))

    assert result.status == "rejected"
    cause = next(c for c in result.causes if c.check == "mana_cost")
    assert cause.code == "mana_value_mismatch"
    assert cause.message.strip()


def test_t28_rn17_stored_format_survives_a_json_round_trip():
    """RN-17 / T28 (plan section 7): the stored result is plain JSON, as the version's `validation` field keeps it."""
    for draft in (card(), card(mana_value=4)):
        stored = _validate(draft).to_dict()

        assert json.loads(json.dumps(stored)) == stored


def test_t28_rn14_status_is_rejected_exactly_when_there_are_causes():
    """RN-14 / RN-17 / T28: the status agrees with the causes (cards.services refuses a mismatch)."""
    drafts = [card(), card(mana_value=4), land(), card(mana_cost="{G}{2}"), card(mana_cost="{Q}")]
    for draft in drafts:
        stored = _validate(draft).to_dict()

        expected = "rejected" if stored["causes"] else "approved"
        assert stored["status"] == expected, draft["mana_cost"]


def test_t28_rn17_causes_name_a_check_that_ran():
    """RN-17 / T28 (plan section 7): every cause names, by its stable check name, a check listed as run."""
    stored = _validate(card(mana_cost="{G}{2}", mana_value=4)).to_dict()

    assert "mana_cost" in stored["checks_run"]
    assert len(stored["checks_run"]) == len(set(stored["checks_run"])), "each check is listed once"
    assert {cause["check"] for cause in stored["causes"]} <= set(stored["checks_run"])


def test_t28_rn17_validate_does_not_change_its_inputs():
    """RN-17 / T28: validation is a pure function; the card and the request are left as given."""
    draft = card(mana_cost="{1}{G}{G/W}{W}", mana_value=4)
    req = request()
    draft_before, request_before = copy.deepcopy(draft), copy.deepcopy(req)

    _validate(draft, req)

    assert draft == draft_before
    assert req == request_before


def test_t28_rn17_validate_is_deterministic():
    """RN-17 / T28: the same card and request always give the same stored result."""
    draft = card(mana_cost="{G}{2}", mana_value=5)

    assert _validate(draft).to_dict() == _validate(draft).to_dict()


def test_t28_rn17_mana_cost_check_does_not_need_a_lexicon():
    """RN-17 / T28: the lexicon arrives in Milestone 5 (T24); the mana cost check runs without one."""
    stored = _validate(card()).to_dict()

    assert "mana_cost" in stored["checks_run"]
    assert "mana_cost" not in stored["skipped"]
