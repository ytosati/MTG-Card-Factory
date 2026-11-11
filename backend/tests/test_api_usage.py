"""GET /api/usage?card= (task T38, spec RN-09, CA-16; plan section 6).

Assumed contract (plan section 6 names the endpoint and "usage records"):

    GET /api/usage?card=<card id>
        200 {"card": "<card id>", "text": [record, ...]}
        Each text record holds provider, model, input_tokens, output_tokens,
        outcome ("ok" or "failed") and created_at, oldest first. Only records
        linked to that card appear; records with no card (a failed generation,
        the connection test) are recorded but never shown (RN-09). Art usage is
        added by T50 as a separate list, so this file does not pin the full set
        of top-level fields.
        A missing, empty or malformed `card` answers 400 `validation` with
        `fields` naming `card`; an unknown card answers 404 `not_found`; both
        in the error envelope. Only GET is allowed.

The endpoint sits behind the readiness gate (plan section 6), so each test
stores a ready build first. Requests go through tests.configured_api, which
checks every response for key values. Every card and model is fictional.
"""

import uuid
from datetime import datetime
from urllib.parse import urlencode

import pytest

from tests.cards_helpers import new_card
from tests.config_files import full_text_settings
from tests.configured_api import assert_error_envelope, configured_api  # noqa: F401 (fixture)
from tests.job_helpers import inline_runner
from tests.setup_api_helpers import mark_ready

USAGE_URL = "/api/usage"
TEXT_RECORD_FIELDS = {"provider", "model", "input_tokens", "output_tokens", "outcome", "created_at"}

pytestmark = pytest.mark.django_db


def record_usage(**values):
    from cards import services

    return services.record_usage(**values)


def _text(provider="openai", model="gpt-fictional-mini", input_tokens=900, output_tokens=300, outcome="ok", card=None):
    record_usage(
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        outcome=outcome,
        card=card,
    )


@pytest.fixture
def api(configured_api):
    configured_api.configure(full_text_settings())
    mark_ready()
    with inline_runner():
        yield configured_api


def _usage(api, **query):
    path = f"{USAGE_URL}?{urlencode(query)}" if query else USAGE_URL
    return api.get(path)


def _ok_json(response):
    assert response.status_code == 200, response.content[:500]
    assert response["Content-Type"].startswith("application/json")
    return response.json()


# --- The output for a card -------------------------------------------------------------------------


def test_t38_rn09_ca16_endpoint_shows_the_text_usage_of_a_card(api):
    """RN-09 / CA-16 / T38: the endpoint shows the tokens of each text call of the card: provider,
    model, input and output tokens and outcome."""
    card = new_card()
    _text(card=card, input_tokens=1234, output_tokens=567)

    body = _ok_json(_usage(api, card=card.pk))

    assert body["card"] == str(card.pk)
    [record] = body["text"]
    assert TEXT_RECORD_FIELDS <= set(record)
    assert record["provider"] == "openai"
    assert record["model"] == "gpt-fictional-mini"
    assert record["input_tokens"] == 1234
    assert record["output_tokens"] == 567
    assert record["outcome"] == "ok"
    datetime.fromisoformat(record["created_at"].replace("Z", "+00:00"))


def test_t38_rn09_ca16_draft_and_revision_are_two_records_oldest_first(api):
    """RN-09 / CA-16 / T38: a draft and its revision appear as two records, in the order they were made;
    a failed revision keeps its outcome."""
    card = new_card()
    _text(card=card, input_tokens=1000, output_tokens=310)
    _text(card=card, input_tokens=1600, output_tokens=12, outcome="failed")

    body = _ok_json(_usage(api, card=card.pk))

    assert [(r["input_tokens"], r["output_tokens"], r["outcome"]) for r in body["text"]] == [
        (1000, 310, "ok"),
        (1600, 12, "failed"),
    ]


def test_t38_rn09_records_with_no_card_or_another_card_are_not_shown(api):
    """RN-09 / T38: calls not linked to the card (a failed generation, the connection test, another card)
    are recorded but never shown with it."""
    card = new_card()
    other = new_card(idea="A fictional merfolk that taps creatures at end of turn.")
    _text(card=card, input_tokens=111)
    _text(card=other, input_tokens=222)
    _text(card=None, input_tokens=333, outcome="failed")

    body = _ok_json(_usage(api, card=card.pk))

    assert [r["input_tokens"] for r in body["text"]] == [111]


def test_t38_rn09_card_with_no_usage_has_an_empty_text_list(api):
    """RN-09 / T38: a card with no records answers an empty text list (edge case: empty)."""
    card = new_card()
    _text(card=None, outcome="failed")

    body = _ok_json(_usage(api, card=card.pk))

    assert body["card"] == str(card.pk)
    assert body["text"] == []


def test_t38_rn09_zero_and_huge_token_counts_are_shown_exactly(api):
    """RN-09 / T38: zero and large token counts come back unchanged (edge cases)."""
    card = new_card()
    _text(card=card, input_tokens=0, output_tokens=0, outcome="failed")
    _text(card=card, input_tokens=1_999_999_999, output_tokens=2_000_000_000)

    body = _ok_json(_usage(api, card=card.pk))

    assert [(r["input_tokens"], r["output_tokens"]) for r in body["text"]] == [
        (0, 0),
        (1_999_999_999, 2_000_000_000),
    ]


def test_t38_rn09_model_name_with_odd_characters_is_shown_as_stored(api):
    """RN-09 / T38: a model name with odd characters is returned as it was recorded."""
    card = new_card()
    model = 'fictional/model-é_ß:2025 "β" <tag>'
    _text(card=card, model=model)

    body = _ok_json(_usage(api, card=card.pk))

    assert body["text"][0]["model"] == model


def test_t38_rn09_card_id_in_upper_case_is_accepted(api):
    """RN-09 / T38: the card id is a UUID; its upper-case spelling names the same card."""
    card = new_card()
    _text(card=card, input_tokens=55)

    body = _ok_json(_usage(api, card=str(card.pk).upper()))

    assert body["card"] == str(card.pk)
    assert [r["input_tokens"] for r in body["text"]] == [55]


# --- Invalid requests ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "query",
    [
        {},
        {"card": ""},
        {"card": "not-a-card-id"},
        {"card": "1; DROP TABLE cards_usagerecord"},
        {"card": "0" * 5000},
        {"card": "\u0000‮🃏"},
    ],
    ids=["missing", "empty", "malformed", "sql-text", "huge", "odd-characters"],
)
def test_t38_rn09_missing_or_malformed_card_answers_validation_naming_card(api, query):
    """RN-09 / T38 (plan section 6, error envelope): without a valid card id the endpoint answers 400
    `validation` and names the `card` field."""
    error = assert_error_envelope(_usage(api, **query), 400, "validation")

    assert error["fields"] is not None and "card" in error["fields"]
    assert all(isinstance(text, str) and text.strip() for text in error["fields"]["card"])


def test_t38_rn09_unknown_card_answers_not_found(api):
    """RN-09 / T38 (plan section 6): a well-formed id with no card answers 404 `not_found`, even when
    records with no card exist."""
    _text(card=None, outcome="failed")

    assert_error_envelope(_usage(api, card=uuid.uuid4()), 404, "not_found")


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_t38_rn09_usage_endpoint_only_answers_get(api, method):
    """RN-09 / T38 (plan section 6): usage is read only; other methods answer `method_not_allowed`."""
    card = new_card()

    response = api.request(method, f"{USAGE_URL}?card={card.pk}", data={})

    assert_error_envelope(response, 405, "method_not_allowed")


# --- Error texts never echo the input (plan section 6) -----------------------------------------------


@pytest.mark.parametrize(
    "value",
    ["<script>alert(1)</script>", "fictional-not-a-uuid-QX7", "‮🃏<b>bold</b>"],
    ids=["markup", "plain-text", "odd-characters"],
)
def test_t38_rn09_validation_messages_never_echo_the_submitted_card(api, value):
    """RN-09 / T38 (plan section 6): the `card` field messages are fixed texts that never quote the
    submitted value."""
    error = assert_error_envelope(_usage(api, card=value), 400, "validation")

    texts = error["fields"]["card"]
    assert texts and all(isinstance(text, str) and text.strip() for text in texts)
    assert all(value not in text for text in texts), texts
    assert value not in error["message"]


def test_t38_rn09_validation_messages_are_the_same_for_any_malformed_card(api):
    """RN-09 / T38 (plan section 6): two different malformed values get the same fixed message."""
    first = assert_error_envelope(_usage(api, card="<script>alert(1)</script>"), 400, "validation")
    second = assert_error_envelope(_usage(api, card="another-bad-value"), 400, "validation")

    assert first["fields"]["card"] == second["fields"]["card"]


def test_t38_rn09_unknown_card_message_names_the_card_not_the_api_path(api):
    """RN-09 / T38 (plan section 6): an unknown card answers "The card does not exist.", not the message
    of an unknown API path."""
    error = assert_error_envelope(_usage(api, card=uuid.uuid4()), 404, "not_found")

    assert error["message"] == "The card does not exist."
    assert "path" not in error["message"].lower()


def _handled_validation(serializer_class, data):
    """The response of the API exception handler for the validation error of `serializer_class`."""
    from rest_framework import exceptions

    from api.exceptions import exception_handler

    serializer = serializer_class(data=data)
    with pytest.raises(exceptions.ValidationError) as raised:
        serializer.is_valid(raise_exception=True)
    return exception_handler(raised.value, {})


def _evil_serializers():
    from rest_framework import serializers

    class Inner(serializers.Serializer):
        rarity = serializers.ChoiceField(choices=["common", "rare"])

    class Outer(serializers.Serializer):
        kind = serializers.ChoiceField(choices=["text", "image"])
        details = Inner()

    return Outer


@pytest.mark.parametrize("evil", ["<evil>", "<script>alert(1)</script>", "fictional\u0000value"])
def test_t38_handler_validation_fields_are_fixed_texts_with_dotted_names(evil):
    """Plan section 6 / T38: the handler answers `fields` as {name: [str]}, with dotted names for nested
    fields, and never quotes the submitted value (ChoiceField texts do quote it in DRF)."""
    response = _handled_validation(_evil_serializers(), {"kind": evil, "details": {"rarity": evil}})

    assert response.status_code == 400
    error = response.data["error"]
    assert error["code"] == "validation"
    fields = error["fields"]
    assert set(fields) == {"kind", "details.rarity"}, fields
    for name, texts in fields.items():
        assert isinstance(texts, list) and texts, (name, texts)
        for text in texts:
            assert isinstance(text, str) and text.strip()
            assert evil not in text and "evil" not in text, (name, text)
    assert evil not in error["message"]


def test_t38_handler_validation_texts_do_not_depend_on_the_value():
    """Plan section 6 / T38: the field texts are fixed: two different bad values give the same texts."""
    serializer_class = _evil_serializers()

    first = _handled_validation(serializer_class, {"kind": "<evil>", "details": {"rarity": "<evil>"}})
    second = _handled_validation(serializer_class, {"kind": "other", "details": {"rarity": "other"}})

    assert first.data["error"]["fields"] == second.data["error"]["fields"]
