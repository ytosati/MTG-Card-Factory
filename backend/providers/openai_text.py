"""OpenAI text adapter: Chat Completions with Structured Outputs.

Details: specs/plan.md, section 9.2.
"""

import copy
import json
from typing import Any

from providers import transport
from providers.base import Usage
from providers.errors import (
    AuthError,
    ContentRefused,
    InvalidResponse,
    ModelNotFound,
    ProviderError,
)
from providers.schema import validate_json

ENDPOINT = "https://api.openai.com/v1/chat/completions"
SCHEMA_NAME = "card_factory_response"
MODEL_SETTING = "LLM_MODEL"


class OpenAITextAdapter:
    """Text adapter for OpenAI; the key is held privately and sent only as a bearer header."""

    def __init__(self, api_key: str, model: str, send: transport.Sender | None = None):
        self._api_key = api_key
        self._model = model
        self._send = send

    def __repr__(self) -> str:
        return f"OpenAITextAdapter(model={self._model!r})"

    __str__ = __repr__

    def complete_json(
        self, system: str, messages: list[dict[str, str]], schema: dict[str, Any]
    ) -> tuple[Any, Usage]:
        payload = {
            "model": self._model,
            # "system" rather than "developer": every chat model accepts it, and
            # newer models treat it as a developer message.
            "messages": [{"role": "system", "content": system}, *copy.deepcopy(messages)],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": SCHEMA_NAME, "schema": _strict_schema(schema), "strict": True},
            },
        }
        response = transport.request(
            "POST",
            ENDPOINT,
            headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
            body=json.dumps(payload).encode("utf-8"),
            read_timeout=transport.TEXT_READ_TIMEOUT,
            model_setting=MODEL_SETTING,
            is_quota_error=_is_quota_error,
            send=self._send,
            classify_error=_classify_error,
        )
        return _read_completion(response.body, schema)


def _strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """A copy of `schema` as strict mode demands: every object closed and every property required."""
    strict = copy.deepcopy(schema)
    _close_objects(strict)
    return strict


def _close_objects(node: Any) -> None:
    if isinstance(node, dict):
        if node.get("type") == "object":
            properties = node.setdefault("properties", {})
            node["required"] = list(properties)
            node["additionalProperties"] = False
        for value in node.values():
            _close_objects(value)
    elif isinstance(node, list):
        for item in node:
            _close_objects(item)


def _read_completion(body: bytes, schema: dict[str, Any]) -> tuple[Any, Usage]:
    # Error messages are fixed texts: the response can echo the key or the user's text.
    completion = _parse_json(body)
    if not isinstance(completion, dict):
        raise InvalidResponse("The provider answer could not be read.", usage=Usage(0, 0))
    usage = _read_usage(completion.get("usage"))

    choices = completion.get("choices")
    choice = choices[0] if isinstance(choices, list) and choices else None
    if not isinstance(choice, dict):
        raise InvalidResponse("The provider answer had no content.", usage=usage)
    message = choice.get("message")
    finish_reason = choice.get("finish_reason")
    refusal = message.get("refusal") if isinstance(message, dict) else None
    if (isinstance(refusal, str) and refusal.strip()) or finish_reason == "content_filter":
        raise ContentRefused("The provider refused to write this card.", usage=usage)
    if finish_reason == "length":
        raise InvalidResponse("The provider answer was cut off before it was complete.", usage=usage)
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str):
        raise InvalidResponse("The provider answer had no content.", usage=usage)

    data = _parse_json(content)
    if data is _UNREADABLE or validate_json(data, schema):
        raise InvalidResponse("The provider answer did not match the requested format.", usage=usage)
    return data, usage


_UNREADABLE = object()


def _parse_json(text: bytes | str) -> Any:
    """The parsed JSON, or _UNREADABLE; the parser's own error is not kept, as it can quote the text."""
    try:
        return json.loads(text)
    except (ValueError, RecursionError):
        return _UNREADABLE


def _read_usage(raw: Any) -> Usage:
    if not isinstance(raw, dict):
        return Usage(0, 0)
    return Usage(
        input_tokens=_token_count(raw.get("prompt_tokens")),
        output_tokens=_token_count(raw.get("completion_tokens")),
    )


def _token_count(value: Any) -> int:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return 0


def _error_fields(response: transport.HttpResponse) -> tuple[Any, Any]:
    """The `code` and `type` of an OpenAI error body, or (None, None) when unreadable."""
    body = _parse_json(response.body)
    error = body.get("error") if isinstance(body, dict) else None
    if not isinstance(error, dict):
        return None, None
    return error.get("code"), error.get("type")


def _is_quota_error(response: transport.HttpResponse) -> bool:
    return "insufficient_quota" in _error_fields(response)


def _classify_error(response: transport.HttpResponse) -> ProviderError | None:
    """Errors OpenAI reports with a status other than the usual one; None keeps the default mapping."""
    if response.status not in (400, 403):
        return None
    code, _ = _error_fields(response)
    # A 403 with this code means the project has no access to the model, not a rejected key.
    if code == "model_not_found":
        return ModelNotFound(
            f"The provider does not know the model set in {MODEL_SETTING}.", setting=MODEL_SETTING
        )
    if response.status == 400 and code == "invalid_api_key":
        return AuthError("The provider rejected the API key.")
    return None
