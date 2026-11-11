"""Provider error set and usage (task T35, spec RN-07, RN-10; RN-09 for the usage).

Details: specs/plan.md, section 9.2 (error set, usage carried by errors raised
after the provider answered).

API under test:

    providers.base.Usage(input_tokens, output_tokens)
        immutable value with equality (a dataclass)
    providers.errors
        ProviderError                       base of the whole set
        AuthError, QuotaError, ProviderUnavailable, InvalidResponse,
        ContentRefused, TemplateUnsupported, ModelNotFound
        InvalidResponse(message, usage=Usage)   .usage is the reported usage
        ContentRefused(message, usage=Usage)    .usage is the reported usage
        ModelNotFound(message, setting="LLM_MODEL")   .setting names the model setting
"""

import pytest

ERROR_NAMES = (
    "AuthError",
    "QuotaError",
    "ProviderUnavailable",
    "InvalidResponse",
    "ContentRefused",
    "TemplateUnsupported",
    "ModelNotFound",
)

ANSWERED_ERROR_NAMES = ("InvalidResponse", "ContentRefused")


def _errors():
    import providers.errors

    return providers.errors


@pytest.mark.parametrize("name", ERROR_NAMES)
def test_rn10_error_set_is_defined_under_one_base(name):
    """RN-10: every provider failure maps to one known error set, so call sites
    catch a single base and turn it into a clear message."""
    errors = _errors()
    error_class = getattr(errors, name)
    assert issubclass(error_class, errors.ProviderError)
    assert issubclass(errors.ProviderError, Exception)


def test_rn10_error_set_members_are_distinct():
    """RN-10: each cause is its own class, so the message shown names the right cause."""
    errors = _errors()
    classes = {getattr(errors, name) for name in ERROR_NAMES}
    assert len(classes) == len(ERROR_NAMES)
    for first in classes:
        for second in classes:
            if first is not second:
                assert not issubclass(first, second)


@pytest.mark.parametrize("name", ANSWERED_ERROR_NAMES)
def test_rn09_rn10_error_after_answer_carries_reported_usage(name):
    """RN-10 with RN-09: an error raised after the provider answered keeps the
    usage the provider reported, so the failed call is still recorded."""
    from providers.base import Usage

    errors = _errors()
    usage = Usage(input_tokens=812, output_tokens=95)
    error = getattr(errors, name)("The provider answered with an unusable card.", usage=usage)
    assert error.usage == usage
    assert error.usage.input_tokens == 812
    assert error.usage.output_tokens == 95


@pytest.mark.parametrize("name", ANSWERED_ERROR_NAMES)
def test_rn09_error_after_answer_keeps_zero_usage(name):
    """RN-09 edge case: a reported usage of zero tokens is kept as zero, not lost."""
    from providers.base import Usage

    errors = _errors()
    error = getattr(errors, name)("Empty answer.", usage=Usage(input_tokens=0, output_tokens=0))
    assert error.usage == Usage(input_tokens=0, output_tokens=0)


@pytest.mark.parametrize("name", ANSWERED_ERROR_NAMES)
def test_rn10_error_after_answer_can_be_raised_and_caught_with_its_usage(name):
    """RN-10: the usage survives raising and catching through the common base."""
    from providers.base import Usage

    errors = _errors()
    usage = Usage(input_tokens=1, output_tokens=2)
    with pytest.raises(errors.ProviderError) as caught:
        raise getattr(errors, name)("Refused.", usage=usage)
    assert caught.value.usage == usage


def test_rn10_error_message_is_kept():
    """RN-10: the message given to an error is its text, so it can be shown as is."""
    errors = _errors()
    error = errors.ProviderUnavailable("The provider is not answering. Try again later.")
    assert str(error) == "The provider is not answering. Try again later."


@pytest.mark.parametrize("setting", ["LLM_MODEL", "IMAGE_MODEL"])
def test_rn10_model_not_found_names_the_model_setting(setting):
    """RN-10 (plan 9.2): ModelNotFound names `LLM_MODEL` or `IMAGE_MODEL`."""
    errors = _errors()
    error = errors.ModelNotFound("The provider does not know this model.", setting=setting)
    assert error.setting == setting


def test_rn09_usage_is_a_value_with_equality():
    """RN-09: usage is a plain value with input and output tokens."""
    from providers.base import Usage

    assert Usage(input_tokens=10, output_tokens=3) == Usage(input_tokens=10, output_tokens=3)
    assert Usage(input_tokens=10, output_tokens=3) != Usage(input_tokens=3, output_tokens=10)


def test_rn09_usage_is_immutable():
    """RN-09: a reported usage cannot be changed after the call returned it."""
    from providers.base import Usage

    usage = Usage(input_tokens=10, output_tokens=3)
    with pytest.raises(AttributeError):
        usage.input_tokens = 0


def test_rn10_t154_provider_rejected_has_a_fixed_message_that_asks_to_check_the_model():
    """RN-10, RN-08 (T154): the fixed message of `provider_rejected` points to the model setting and
    is not a quotation of a provider's answer (no status number, no braces)."""
    errors = _errors()
    message = errors.MESSAGES[errors.CODE_PROVIDER_REJECTED]
    assert message.strip()
    assert "model" in message.lower()
    assert "check" in message.lower()
    assert "HTTP" not in message
    assert "{" not in message and "}" not in message
