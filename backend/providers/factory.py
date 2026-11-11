"""Provider factory: the only place that turns the configuration into an adapter.

Details: specs/plan.md, sections 8 and 9.2. Call sites look up
`factory.text_adapter()` when they run, so tests can replace it with the fake.
"""

from dataclasses import dataclass

from core.config import ENV_FILE_SETTING, get_config
from core.errors import CODE_CONFIG_INVALID, CODE_PROVIDER_NOT_AVAILABLE_YET
from providers.base import TextAdapter
from providers.openai_text import OpenAITextAdapter

NOT_AVAILABLE_YET_MESSAGE = "This text provider is not supported yet. Set LLM_PROVIDER to openai for now."

# Settings whose problems block text; image settings and APP_PORT do not (spec RN-08).
_TEXT_SETTINGS = (ENV_FILE_SETTING, "LLM_PROVIDER", "LLM_API_KEY", "LLM_MODEL")

_TEXT_ADAPTERS = {"openai": OpenAITextAdapter}


@dataclass(frozen=True)
class AdapterResult:
    """An adapter with the provider and model it was built for, or the error code, setting and
    message that explain why there is none."""

    adapter: TextAdapter | None
    code: str | None = None
    setting: str | None = None
    message: str | None = None
    provider: str | None = None
    model: str | None = None


def text_adapter() -> AdapterResult:
    """The text adapter for the current `.env`, read again on every call (spec RN-08); never calls a provider."""
    config = get_config()
    for issue in config.settings_to_fix:
        if issue.setting in _TEXT_SETTINGS:
            return AdapterResult(adapter=None, code=CODE_CONFIG_INVALID, setting=issue.setting, message=issue.message)
    adapter_class = _TEXT_ADAPTERS.get(config.llm_provider)
    if adapter_class is None:
        return AdapterResult(adapter=None, code=CODE_PROVIDER_NOT_AVAILABLE_YET, message=NOT_AVAILABLE_YET_MESSAGE)
    adapter = adapter_class(api_key=config.llm_api_key.reveal(), model=config.llm_model)
    return AdapterResult(adapter=adapter, provider=config.llm_provider, model=config.llm_model)
