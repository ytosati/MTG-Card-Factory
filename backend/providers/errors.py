"""Error set every provider adapter maps its failures to (see spec RN-10).

Details: specs/plan.md, section 9.2. Messages never include the key or the
provider's response body.
"""

from core.errors import (
    CODE_AUTH,
    CODE_CONTENT_REFUSED,
    CODE_INVALID_RESPONSE,
    CODE_MODEL_NOT_FOUND,
    CODE_PROVIDER_REJECTED,
    CODE_PROVIDER_UNAVAILABLE,
    CODE_QUOTA,
    CODE_RATE_LIMITED,
)
from providers.base import Usage


class ProviderError(Exception):
    """Base of every provider failure; `str(error)` is the message to show.

    `code` is the API error code of the failure (specs/plan.md, section 6).
    """

    code = CODE_PROVIDER_UNAVAILABLE


class AuthError(ProviderError):
    """The provider rejected the key."""

    code = CODE_AUTH


class QuotaError(ProviderError):
    """The account has no quota or credit left."""

    code = CODE_QUOTA


class ProviderUnavailable(ProviderError):
    """The provider did not answer, failed, or limited the request rate; `code` tells which."""

    def __init__(self, message: str, code: str = CODE_PROVIDER_UNAVAILABLE):
        super().__init__(message)
        self.code = code


class ProviderRejected(ProviderError):
    """The provider answered and refused the request outside the mapped set; `setting` is the model
    setting of the call when the model is the likely cause, else None."""

    code = CODE_PROVIDER_REJECTED

    def __init__(self, setting: str | None = None):
        super().__init__(MESSAGES[CODE_PROVIDER_REJECTED])
        self.setting = setting


class _AnsweredError(ProviderError):
    """A failure raised after the provider answered; keeps the usage it reported (spec RN-09)."""

    def __init__(self, message: str, usage: Usage):
        super().__init__(message)
        self.usage = usage


class InvalidResponse(_AnsweredError):
    """The response was not JSON matching the requested schema."""

    code = CODE_INVALID_RESPONSE


class ContentRefused(_AnsweredError):
    """The provider refused to produce the content."""

    code = CODE_CONTENT_REFUSED


class TemplateUnsupported(ProviderError):
    """The image model does not accept a template image."""


class ModelNotFound(ProviderError):
    """The provider does not know the configured model; `setting` is LLM_MODEL or IMAGE_MODEL."""

    code = CODE_MODEL_NOT_FOUND

    def __init__(self, message: str, setting: str):
        super().__init__(message)
        self.setting = setting


# The message shown for each error code: fixed texts, never a provider's own words (see spec RN-10).
MESSAGES = {
    CODE_AUTH: "The provider rejected the API key.",
    CODE_QUOTA: "The provider account has no quota or credit left.",
    CODE_RATE_LIMITED: "The provider is limiting requests. Wait a moment and try again.",
    CODE_MODEL_NOT_FOUND: "The provider does not know the configured model.",
    CODE_PROVIDER_UNAVAILABLE: "The provider is not answering. Try again later.",
    CODE_PROVIDER_REJECTED: (
        "The provider refused the request. Check the model setting: the model may not support this request."
    ),
    CODE_INVALID_RESPONSE: "The provider answered in a form that could not be used.",
    CODE_CONTENT_REFUSED: "The provider refused to write this content.",
}


def message_for(error: ProviderError) -> str:
    """The fixed message of the error's code."""
    return MESSAGES.get(error.code, MESSAGES[CODE_PROVIDER_UNAVAILABLE])
