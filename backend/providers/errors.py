"""Error set every provider adapter maps its failures to (see spec RN-10).

Details: specs/plan.md, section 9.2. Messages never include the key or the
provider's response body.
"""

from providers.base import Usage


class ProviderError(Exception):
    """Base of every provider failure; `str(error)` is the message to show.

    `code` is the API error code of the failure (specs/plan.md, section 6).
    """

    code = "provider_unavailable"


class AuthError(ProviderError):
    """The provider rejected the key."""

    code = "auth"


class QuotaError(ProviderError):
    """The account has no quota or credit left."""

    code = "quota"


class ProviderUnavailable(ProviderError):
    """The provider did not answer, failed, or limited the request rate; `code` tells which."""

    def __init__(self, message: str, code: str = "provider_unavailable"):
        super().__init__(message)
        self.code = code


class _AnsweredError(ProviderError):
    """A failure raised after the provider answered; keeps the usage it reported (spec RN-09)."""

    def __init__(self, message: str, usage: Usage):
        super().__init__(message)
        self.usage = usage


class InvalidResponse(_AnsweredError):
    """The response was not JSON matching the requested schema."""

    code = "invalid_response"


class ContentRefused(_AnsweredError):
    """The provider refused to produce the content."""

    code = "content_refused"


class TemplateUnsupported(ProviderError):
    """The image model does not accept a template image."""


class ModelNotFound(ProviderError):
    """The provider does not know the configured model; `setting` is LLM_MODEL or IMAGE_MODEL."""

    code = "model_not_found"

    def __init__(self, message: str, setting: str):
        super().__init__(message)
        self.setting = setting


# The message shown for each error code: fixed texts, never a provider's own words (see spec RN-10).
MESSAGES = {
    "auth": "The provider rejected the API key.",
    "quota": "The provider account has no quota or credit left.",
    "rate_limited": "The provider is limiting requests. Wait a moment and try again.",
    "model_not_found": "The provider does not know the configured model.",
    "provider_unavailable": "The provider is not answering. Try again later.",
    "invalid_response": "The provider answered in a form that could not be used.",
    "content_refused": "The provider refused to write this content.",
}


def message_for(error: ProviderError) -> str:
    """The fixed message of the error's code."""
    return MESSAGES.get(error.code, MESSAGES["provider_unavailable"])
