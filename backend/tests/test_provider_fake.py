"""Scriptable fake text adapter (task T35, spec RN-07, RN-10; RN-09 for the usage).

Details: specs/plan.md, section 9.2. The fake stands in for every text
provider in tests; later tasks install it through a pytest fixture that
replaces the factory functions. It is never selectable from `.env`.

API under test:

    providers.base.TextAdapter      runtime-checkable Protocol with
        complete_json(system, messages, schema) -> (data, usage)
    providers.base.Usage(input_tokens, output_tokens)
    providers.fake.FakeTextAdapter(script=None)
        `script` is a list consumed in order, one entry per call:
          - a (data, Usage) tuple: the call returns it;
          - an exception instance: the call raises it.
        .add_response(data, usage)   appends a response to the script
        .add_error(error)            appends an error to the script
        .calls                       list of recorded calls, in order, each with
                                     .system, .messages and .schema as received
        A call made after the script is exhausted fails loudly with an error
        outside the provider error set, so a test never mistakes it for a
        provider failure.

Every response below is fictional and written by hand.
"""

import pytest

SCHEMA = {
    "type": "object",
    "properties": {"name": {"type": "string"}, "mana_value": {"type": "integer"}},
    "required": ["name", "mana_value"],
}

SYSTEM = "You design custom Commander cards."

MESSAGES = [{"role": "user", "content": "A white-blue lighthouse keeper that protects artifacts."}]

DRAFT = {"name": "Lantern Warden of Vell", "mana_value": 3}

REVISION = {"name": "Lantern Warden of Vell", "mana_value": 4}


def _usage(input_tokens, output_tokens):
    from providers.base import Usage

    return Usage(input_tokens=input_tokens, output_tokens=output_tokens)


def _fake(script=None):
    from providers.fake import FakeTextAdapter

    return FakeTextAdapter(script)


# Protocol


def test_rn07_fake_follows_the_text_adapter_protocol():
    """RN-07: the fake offers the same `complete_json` call as every real adapter."""
    from providers.base import TextAdapter

    fake = _fake([(DRAFT, _usage(10, 5))])
    assert isinstance(fake, TextAdapter)
    assert callable(fake.complete_json)


def test_rn07_fake_is_not_a_configurable_provider():
    """RN-07 (plan 9.2): the fake is never selectable from `.env`."""
    from core.config import IMAGE_PROVIDERS, TEXT_PROVIDERS

    assert "fake" not in TEXT_PROVIDERS
    assert "fake" not in IMAGE_PROVIDERS


# Scripted responses


def test_rn07_fake_returns_the_scripted_response_and_usage():
    """RN-07 with RN-09: a call returns the scripted data and the scripted usage."""
    fake = _fake([(DRAFT, _usage(812, 95))])
    data, usage = fake.complete_json(SYSTEM, MESSAGES, SCHEMA)
    assert data == DRAFT
    assert usage == _usage(812, 95)


def test_rn07_fake_returns_scripted_responses_in_order():
    """RN-07: a draft and its revision are two calls with their own responses."""
    fake = _fake([(DRAFT, _usage(800, 90)), (REVISION, _usage(900, 100))])
    first = fake.complete_json(SYSTEM, MESSAGES, SCHEMA)
    second = fake.complete_json(SYSTEM, MESSAGES, SCHEMA)
    assert first == (DRAFT, _usage(800, 90))
    assert second == (REVISION, _usage(900, 100))


def test_rn07_fake_script_can_be_built_after_creation():
    """RN-07: responses and errors can be appended to the script one by one."""
    from providers.errors import ProviderUnavailable

    fake = _fake()
    fake.add_response(DRAFT, _usage(1, 2))
    fake.add_error(ProviderUnavailable("The provider is not answering."))
    assert fake.complete_json(SYSTEM, MESSAGES, SCHEMA) == (DRAFT, _usage(1, 2))
    with pytest.raises(ProviderUnavailable):
        fake.complete_json(SYSTEM, MESSAGES, SCHEMA)


def test_rn07_fake_returns_responses_with_odd_characters_unchanged():
    """RN-07 edge case: hybrid symbols, accents and huge text come back as scripted."""
    data = {"name": "Ação {W/U} — “Farol”", "mana_value": 0, "text": "{2/B}" * 20_000}
    fake = _fake([(data, _usage(0, 0))])
    returned, usage = fake.complete_json(SYSTEM, MESSAGES, SCHEMA)
    assert returned == data
    assert usage == _usage(0, 0)


# Scripted errors


@pytest.mark.parametrize(
    "name",
    ["AuthError", "QuotaError", "ProviderUnavailable", "TemplateUnsupported", "ModelNotFound"],
)
def test_rn10_fake_raises_scripted_errors_before_an_answer(name):
    """RN-10: each error of the set can be scripted and is raised as is."""
    import providers.errors

    error_class = getattr(providers.errors, name)
    if name == "ModelNotFound":
        error = error_class("The provider does not know this model.", setting="LLM_MODEL")
    else:
        error = error_class("Scripted failure.")
    fake = _fake([error])
    with pytest.raises(error_class) as caught:
        fake.complete_json(SYSTEM, MESSAGES, SCHEMA)
    assert caught.value is error


@pytest.mark.parametrize("name", ["InvalidResponse", "ContentRefused"])
def test_rn09_rn10_fake_raises_errors_after_an_answer_with_their_usage(name):
    """RN-10 with RN-09: an error raised after the provider answered reaches the
    caller with the usage the provider reported."""
    import providers.errors

    error_class = getattr(providers.errors, name)
    fake = _fake([error_class("Scripted failure after an answer.", usage=_usage(640, 72))])
    with pytest.raises(error_class) as caught:
        fake.complete_json(SYSTEM, MESSAGES, SCHEMA)
    assert caught.value.usage == _usage(640, 72)


def test_rn10_fake_mixes_errors_and_responses_in_script_order():
    """RN-10: a draft that answers followed by a revision that fails (RN-15 path)."""
    from providers.errors import InvalidResponse

    fake = _fake([(DRAFT, _usage(800, 90)), InvalidResponse("Not a card.", usage=_usage(900, 3))])
    assert fake.complete_json(SYSTEM, MESSAGES, SCHEMA) == (DRAFT, _usage(800, 90))
    with pytest.raises(InvalidResponse) as caught:
        fake.complete_json(SYSTEM, MESSAGES, SCHEMA)
    assert caught.value.usage == _usage(900, 3)


def test_rn10_fake_fails_loudly_when_the_script_is_exhausted():
    """RN-10 guard: an unscripted call is a test mistake, not a provider failure,
    so it raises an error outside the provider error set."""
    from providers.errors import ProviderError

    fake = _fake([(DRAFT, _usage(1, 1))])
    fake.complete_json(SYSTEM, MESSAGES, SCHEMA)
    with pytest.raises(Exception) as caught:
        fake.complete_json(SYSTEM, MESSAGES, SCHEMA)
    assert not isinstance(caught.value, ProviderError)


def test_rn10_fake_with_an_empty_script_fails_loudly():
    """RN-10 guard, edge case: a fake with no script refuses the first call."""
    from providers.errors import ProviderError

    fake = _fake([])
    with pytest.raises(Exception) as caught:
        fake.complete_json(SYSTEM, MESSAGES, SCHEMA)
    assert not isinstance(caught.value, ProviderError)


# Recorded calls


def test_rn07_fake_starts_with_no_recorded_calls():
    """RN-07: before any call, nothing is recorded."""
    assert list(_fake([(DRAFT, _usage(1, 1))]).calls) == []


def test_rn07_fake_records_each_call_with_its_arguments():
    """RN-07: the fake records the system text, the messages and the schema it received."""
    fake = _fake([(DRAFT, _usage(1, 1)), (REVISION, _usage(2, 2))])
    second_messages = MESSAGES + [{"role": "user", "content": "Fix the mana cost."}]
    fake.complete_json(SYSTEM, MESSAGES, SCHEMA)
    fake.complete_json("Revise the draft.", second_messages, {"type": "object", "properties": {}, "required": []})

    assert len(fake.calls) == 2
    first, second = fake.calls
    assert first.system == SYSTEM
    assert first.messages == MESSAGES
    assert first.schema == SCHEMA
    assert second.system == "Revise the draft."
    assert second.messages == second_messages
    assert second.schema == {"type": "object", "properties": {}, "required": []}


def test_rn10_fake_records_calls_that_raise():
    """RN-10: a call that ends in a scripted error is recorded too, so a test can
    tell that the provider was called."""
    from providers.errors import AuthError, ContentRefused

    fake = _fake([AuthError("Rejected key."), ContentRefused("Refused.", usage=_usage(5, 0))])
    with pytest.raises(AuthError):
        fake.complete_json(SYSTEM, MESSAGES, SCHEMA)
    with pytest.raises(ContentRefused):
        fake.complete_json("Second system text.", MESSAGES, SCHEMA)
    assert [call.system for call in fake.calls] == [SYSTEM, "Second system text."]


def test_rn07_fake_records_odd_and_empty_arguments_unchanged():
    """RN-07 edge case: an empty system text and odd characters in messages are
    recorded exactly as received."""
    fake = _fake([(DRAFT, _usage(1, 1))])
    messages = [{"role": "user", "content": "{W/U}{G/P} — ção \u0000 " + "z" * 50_000}]
    fake.complete_json("", messages, SCHEMA)
    call = fake.calls[0]
    assert call.system == ""
    assert call.messages == messages
