"""Error set every provider adapter maps its failures to (see spec RN-10).

Details: specs/plan.md, section 9.2. Messages never include the key or the
provider's response body.
"""

from providers.base import Usage


class ProviderError(Exception):
    """Base of every provider failure; `str(error)` is the message to show."""


class AuthError(ProviderError):
    """The provider rejected the key."""


class QuotaError(ProviderError):
    """The account has no quota or credit left."""


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


class ContentRefused(_AnsweredError):
    """The provider refused to produce the content."""


class TemplateUnsupported(ProviderError):
    """The image model does not accept a template image."""


class ModelNotFound(ProviderError):
    """The provider does not know the configured model; `setting` is LLM_MODEL or IMAGE_MODEL."""

    def __init__(self, message: str, setting: str):
        super().__init__(message)
        self.setting = setting
