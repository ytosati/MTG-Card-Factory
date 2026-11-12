"""OpenAI text adapter (task T40, spec RN-07, RN-08, RN-10, CA-06, CA-25, CA-76).

Details: specs/plan.md, section 9.2 (one adapter protocol, direct HTTP through
the shared transport, structured JSON output checked against the schema, the
error set, 429 split into quota and rate limit, the key only in a request
header and never in an error text, usage carried by errors raised after the
provider answered).

API under test:

    providers.openai_text.OpenAITextAdapter(api_key, model, send=None)
        Implements providers.base.TextAdapter:
            complete_json(system, messages, schema) -> (data, Usage)
        `send` is passed to providers.transport.request (the same seam the
        transport tests use); None means the standard-library sender.

Request shape assumed (OpenAI Chat Completions with structured output):

    POST https://api.openai.com/v1/chat/completions
    Authorization: Bearer <key>
    {"model": <model>,
     "messages": [{"role": "system" | "developer", "content": <system>}, *messages],
     "response_format": {"type": "json_schema",
                         "json_schema": {"name": ..., "schema": <schema>, ...}}}

Response shape assumed:

    {"choices": [{"message": {"role": "assistant", "content": "<json text>",
                              "refusal": null},
                  "finish_reason": "stop"}],
     "usage": {"prompt_tokens": n, "completion_tokens": m, "total_tokens": n + m}}

    Errors: {"error": {"message", "type", "param", "code"}}; a 429 whose
    code or type is "insufficient_quota" is a quota error, any other 429 is a
    rate limit.

Every response below is fictional and written by hand; the key only looks like
a key. Nothing reaches the network (the network guard would fail the test).
"""

import copy
import json
import traceback

import pytest

# Fictional values that only look like keys.
FAKE_KEY = "sk-proj-fakeOpenAITextKey0000Zm9yVGVzdHNPbmx5Qq9"
MASKED_ECHO = "sk-proj-****************************Qq9"
BODY_SENTINEL = "openai-body-sentinel-text"
MODEL = "gpt-fictional-4"
ENDPOINT = "https://api.openai.com/v1/chat/completions"

SYSTEM = "You design custom Commander cards. Answer only with JSON."

MESSAGES = [
    {"role": "user", "content": "A red goblin who collects bells and rings them for haste."},
]

SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "mana_cost": {"type": "string"},
        "mana_value": {"type": "integer"},
        "rarity": {"type": "string", "enum": ["common", "uncommon", "rare", "mythic"]},
        "keywords": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["name", "mana_cost", "mana_value", "rarity", "keywords"],
}

DRAFT = {
    "name": "Bellkeeper Goblin",
    "mana_cost": "{1}{R/P}",
    "mana_value": 2,
    "rarity": "uncommon",
    "keywords": ["Haste"],
}


# --- Helpers -------------------------------------------------------------------


def _transport():
    import providers.transport

    return providers.transport


def _errors():
    import providers.errors

    return providers.errors


def _usage(input_tokens, output_tokens):
    from providers.base import Usage

    return Usage(input_tokens=input_tokens, output_tokens=output_tokens)


def _adapter(send, *, api_key=FAKE_KEY, model=MODEL):
    from providers.openai_text import OpenAITextAdapter

    return OpenAITextAdapter(api_key=api_key, model=model, send=send)


class FakeSend:
    """Scripted stand-in for the standard-library sender; records every call."""

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def __call__(self, method, url, headers, body, *, connect_timeout, read_timeout):
        self.calls.append(
            {
                "method": method,
                "url": url,
                "headers": dict(headers),
                "body": body,
                "connect_timeout": connect_timeout,
                "read_timeout": read_timeout,
            }
        )
        if not self.outcomes:
            raise AssertionError("the adapter sent more requests than scripted")
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def _http(status, payload, headers=None):
    """An HttpResponse whose body is `payload` (dict -> JSON, str -> UTF-8, bytes as is)."""
    if isinstance(payload, dict):
        body = json.dumps(payload).encode("utf-8")
    elif isinstance(payload, str):
        body = payload.encode("utf-8")
    else:
        body = payload
    return _transport().HttpResponse(
        status=status, headers=headers or {"Content-Type": "application/json"}, body=body
    )


def _completion(content, *, prompt_tokens=812, completion_tokens=96, refusal=None, finish_reason="stop"):
    """A recorded fictional Chat Completions answer."""
    return {
        "id": "chatcmpl-fictional0001",
        "object": "chat.completion",
        "created": 1767225600,
        "model": MODEL,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content, "refusal": refusal},
                "logprobs": None,
                "finish_reason": finish_reason,
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


def _error_body(message, error_type, code):
    """A recorded fictional OpenAI error body that echoes the key, as a rejected-key body can."""
    return {
        "error": {
            "message": f"{message} Provided: {MASKED_ECHO}. {BODY_SENTINEL}. key={FAKE_KEY}",
            "type": error_type,
            "param": None,
            "code": code,
        }
    }


REJECTED_KEY = _error_body("Incorrect API key provided.", "invalid_request_error", "invalid_api_key")
UNKNOWN_MODEL = _error_body(
    f"The model `{MODEL}` does not exist or you do not have access to it.",
    "invalid_request_error",
    "model_not_found",
)
INSUFFICIENT_QUOTA = _error_body(
    "You exceeded your current quota, please check your plan and billing details.",
    "insufficient_quota",
    "insufficient_quota",
)
RATE_LIMITED = _error_body(
    f"Rate limit reached for {MODEL} on requests per min (RPM): Limit 3, Used 3, Requested 1.",
    "requests",
    "rate_limit_exceeded",
)
SERVER_ERROR = _error_body("The server had an error while processing your request.", "server_error", None)


def _assert_error_text_is_clean(error):
    """CA-06: neither the key, the masked echo nor the response body reaches any error text."""
    texts = [str(error), repr(error), *(str(arg) for arg in error.args)]
    texts.append("".join(traceback.format_exception(error)))
    for text in texts:
        assert FAKE_KEY not in text
        assert MASKED_ECHO not in text
        assert BODY_SENTINEL not in text
        assert "Bearer" not in text
    assert str(error).strip(), "RN-10: the error carries a clear, non-empty message"


def _sent_json(call):
    return json.loads(call["body"].decode("utf-8"))


def _strip_additional_properties(schema):
    """The adapter may add `additionalProperties: false` for strict mode; ignore it when comparing."""
    if isinstance(schema, dict):
        return {
            key: _strip_additional_properties(value)
            for key, value in schema.items()
            if key != "additionalProperties"
        }
    if isinstance(schema, list):
        return [_strip_additional_properties(item) for item in schema]
    return schema


# --- Protocol and success -----------------------------------------------------


def test_rn07_the_openai_adapter_implements_the_text_adapter_protocol():
    """RN-07: the OpenAI adapter offers the same protocol as every text provider."""
    from providers.base import TextAdapter

    assert isinstance(_adapter(FakeSend()), TextAdapter)


def test_rn07_success_returns_the_parsed_json_and_the_reported_usage():
    """RN-07, RN-09 (plan 9.2): the data is the parsed JSON, the usage is read from the response."""
    send = FakeSend(_http(200, _completion(json.dumps(DRAFT), prompt_tokens=1234, completion_tokens=87)))
    data, usage = _adapter(send).complete_json(SYSTEM, MESSAGES, SCHEMA)
    assert data == DRAFT
    assert usage == _usage(1234, 87)
    assert len(send.calls) == 1


def test_rn07_success_keeps_odd_characters_and_hybrid_symbols():
    """RN-07, RN-30: non-ASCII text, quotes and hybrid or Phyrexian symbols survive the round trip."""
    draft = dict(
        DRAFT,
        name="Sineira Goblin — “Ação” Æther",
        mana_cost="{2/W}{G/U}{R/P}{C}{X}",
        keywords=["Ímpeto", "Line\nbreak", "Tab\there", 'Back\\slash "quoted"'],
    )
    send = FakeSend(_http(200, _completion(json.dumps(draft, ensure_ascii=False))))
    data, _ = _adapter(send).complete_json(SYSTEM, MESSAGES, SCHEMA)
    assert data == draft


def test_rn07_success_with_zero_reported_tokens_is_a_zero_usage():
    """RN-09 edge: a response reporting zero tokens gives a zero usage, not an error."""
    send = FakeSend(_http(200, _completion(json.dumps(DRAFT), prompt_tokens=0, completion_tokens=0)))
    _, usage = _adapter(send).complete_json(SYSTEM, MESSAGES, SCHEMA)
    assert usage == _usage(0, 0)


# --- Request shape and the key (CA-06) -----------------------------------------


def test_rn07_the_request_posts_the_model_messages_and_structured_output_schema():
    """RN-07 (plan 9.2): one POST to Chat Completions asking for JSON matching the schema."""
    send = FakeSend(_http(200, _completion(json.dumps(DRAFT))))
    _adapter(send).complete_json(SYSTEM, MESSAGES, SCHEMA)
    call = send.calls[0]
    assert call["method"] == "POST"
    assert call["url"] == ENDPOINT
    sent = _sent_json(call)
    assert sent["model"] == MODEL
    assert sent["messages"][0]["role"] in ("system", "developer")
    assert sent["messages"][0]["content"] == SYSTEM
    assert sent["messages"][1:] == MESSAGES
    response_format = sent["response_format"]
    assert response_format["type"] == "json_schema"
    assert isinstance(response_format["json_schema"]["name"], str)
    assert response_format["json_schema"]["name"].strip()
    assert _strip_additional_properties(response_format["json_schema"]["schema"]) == SCHEMA


NESTED_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "faces": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "face_name": {"type": "string"},
                    "stats": {
                        "type": "object",
                        "properties": {"power": {"type": "integer"}, "toughness": {"type": "integer"}},
                        "required": ["power", "toughness"],
                    },
                },
                "required": ["face_name", "stats"],
            },
        },
        "frame": {
            "type": "object",
            "properties": {"border": {"type": "string", "enum": ["black", "white"]}},
            "required": ["border"],
        },
    },
    "required": ["name", "faces", "frame"],
}

NESTED_DRAFT = {
    "name": "Twin Bellkeepers",
    "faces": [
        {"face_name": "Bellkeeper Dawn", "stats": {"power": 2, "toughness": 1}},
        {"face_name": "Bellkeeper Dusk", "stats": {"power": 0, "toughness": 3}},
    ],
    "frame": {"border": "black"},
}


def _objects_in(schema, path="$"):
    """Every object schema inside `schema`, with its path."""
    found = []
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            found.append((path, schema))
        for name, subschema in schema.get("properties", {}).items():
            found.extend(_objects_in(subschema, f"{path}.{name}"))
        if "items" in schema:
            found.extend(_objects_in(schema["items"], f"{path}[]"))
    return found


def _sent_schema(send):
    return _sent_json(send.calls[0])["response_format"]["json_schema"]


def test_rn10_the_structured_output_is_strict_and_requires_every_property():
    """RN-10 (plan 9.2): strict structured output, with `required` listing every property."""
    send = FakeSend(_http(200, _completion(json.dumps(DRAFT))))
    _adapter(send).complete_json(SYSTEM, MESSAGES, SCHEMA)
    json_schema = _sent_schema(send)
    assert json_schema["strict"] is True
    sent = json_schema["schema"]
    assert sent["additionalProperties"] is False
    assert sorted(sent["required"]) == sorted(sent["properties"])


def test_rn10_a_nested_schema_is_closed_and_fully_required_at_every_level():
    """RN-10 (plan 9.2): inner objects (inside arrays and objects) are closed with
    additionalProperties false and list every property as required."""
    send = FakeSend(_http(200, _completion(json.dumps(NESTED_DRAFT))))
    _adapter(send).complete_json(SYSTEM, MESSAGES, NESTED_SCHEMA)
    json_schema = _sent_schema(send)
    assert json_schema["strict"] is True
    sent = json_schema["schema"]
    assert _strip_additional_properties(sent) == NESTED_SCHEMA
    objects = _objects_in(sent)
    assert [path for path, _ in objects] == ["$", "$.faces[]", "$.faces[].stats", "$.frame"]
    for path, obj in objects:
        assert obj.get("additionalProperties") is False, path
        assert sorted(obj["required"]) == sorted(obj["properties"]), path


def test_rn10_a_nested_answer_matching_the_schema_is_returned():
    """RN-07: a nested answer that matches the caller's schema is returned as parsed."""
    send = FakeSend(_http(200, _completion(json.dumps(NESTED_DRAFT))))
    data, _ = _adapter(send).complete_json(SYSTEM, MESSAGES, NESTED_SCHEMA)
    assert data == NESTED_DRAFT


@pytest.mark.parametrize(
    "data",
    [
        dict(NESTED_DRAFT, faces=[{"face_name": "Bellkeeper Dawn", "stats": {"power": "2", "toughness": 1}}]),
        dict(NESTED_DRAFT, faces=[{"face_name": "Bellkeeper Dawn"}]),
        dict(NESTED_DRAFT, frame={"border": "gold"}),
        dict(NESTED_DRAFT, frame=[]),
    ],
    ids=["inner-type", "inner-missing", "inner-enum", "inner-not-object"],
)
def test_rn10_a_nested_answer_is_validated_against_the_callers_schema(data):
    """RN-10: a mismatch deep inside the answer is an invalid response carrying its usage."""
    errors = _errors()
    send = FakeSend(_http(200, _completion(json.dumps(data), prompt_tokens=400, completion_tokens=60)))
    with pytest.raises(errors.InvalidResponse) as caught:
        _adapter(send).complete_json(SYSTEM, MESSAGES, NESTED_SCHEMA)
    assert caught.value.usage == _usage(400, 60)
    _assert_error_text_is_clean(caught.value)


def test_rn10_the_answer_is_checked_against_the_original_schema_not_the_strict_copy():
    """RN-10 (plan 9.2): the strict copy is only for the request; the answer is checked
    against the caller's schema, which does not close objects, so an extra property passes."""
    draft = copy.deepcopy(NESTED_DRAFT)
    draft["frame"]["foil"] = "etched"
    send = FakeSend(_http(200, _completion(json.dumps(draft))))
    schema = copy.deepcopy(NESTED_SCHEMA)
    data, _ = _adapter(send).complete_json(SYSTEM, MESSAGES, schema)
    assert data == draft
    assert schema == NESTED_SCHEMA


def test_rn07_a_conversation_with_several_turns_is_sent_in_order():
    """RN-07: the revision call sends earlier turns; they keep their roles and order."""
    messages = [
        {"role": "user", "content": "First idea."},
        {"role": "assistant", "content": json.dumps(DRAFT)},
        {"role": "user", "content": "Fix: the mana value does not match the cost."},
    ]
    send = FakeSend(_http(200, _completion(json.dumps(DRAFT))))
    _adapter(send).complete_json(SYSTEM, messages, SCHEMA)
    assert _sent_json(send.calls[0])["messages"][1:] == messages


def test_rn07_huge_and_odd_text_is_sent_intact_as_json():
    """RN-07 edge: a very long prompt with odd characters reaches the provider unchanged."""
    system = "Rules: " + ("Æ “ação” \\ \" \t {W/U} " * 20000)
    messages = [{"role": "user", "content": "Ideia: um goblin — sinos\u0000 e {R/P}"}]
    send = FakeSend(_http(200, _completion(json.dumps(DRAFT))))
    _adapter(send).complete_json(system, messages, SCHEMA)
    sent = _sent_json(send.calls[0])
    assert sent["messages"][0]["content"] == system
    assert sent["messages"][1:] == messages


def test_rn07_the_callers_schema_and_messages_are_not_modified():
    """RN-07: the adapter may adapt the schema for the provider, but never in place."""
    schema = copy.deepcopy(SCHEMA)
    messages = copy.deepcopy(MESSAGES)
    send = FakeSend(_http(200, _completion(json.dumps(DRAFT))))
    _adapter(send).complete_json(SYSTEM, messages, schema)
    assert schema == SCHEMA
    assert messages == MESSAGES


def test_rn10_the_text_call_uses_the_named_text_read_timeout():
    """RN-10 (plan 9.2): the text call waits with the text read timeout and the connect timeout."""
    transport = _transport()
    send = FakeSend(_http(200, _completion(json.dumps(DRAFT))))
    _adapter(send).complete_json(SYSTEM, MESSAGES, SCHEMA)
    assert send.calls[0]["read_timeout"] == transport.TEXT_READ_TIMEOUT
    assert send.calls[0]["connect_timeout"] == transport.CONNECT_TIMEOUT


def test_ca06_the_key_travels_only_in_the_authorization_header():
    """CA-06 (plan 9.2): the key is sent as a bearer header, never in the URL, the body or another header."""
    send = FakeSend(_http(200, _completion(json.dumps(DRAFT))))
    _adapter(send).complete_json(SYSTEM, MESSAGES, SCHEMA)
    call = send.calls[0]
    headers = {name.lower(): value for name, value in call["headers"].items()}
    assert headers["authorization"] == f"Bearer {FAKE_KEY}"
    assert "application/json" in headers["content-type"]
    assert FAKE_KEY not in call["url"]
    assert FAKE_KEY not in call["body"].decode("utf-8")
    for name, value in headers.items():
        if name != "authorization":
            assert FAKE_KEY not in value


def test_ca06_the_adapter_repr_does_not_show_the_key():
    """CA-06: printing the adapter (in a log or a traceback) never shows the key."""
    adapter = _adapter(FakeSend())
    assert FAKE_KEY not in repr(adapter)
    assert FAKE_KEY not in str(adapter)


def test_rn10_a_server_error_then_success_is_retried_through_the_transport():
    """RN-10 (plan 9.2): the adapter goes through the shared transport, so one 5xx is retried."""
    send = FakeSend(_http(500, SERVER_ERROR), _http(200, _completion(json.dumps(DRAFT))))
    data, _ = _adapter(send).complete_json(SYSTEM, MESSAGES, SCHEMA)
    assert data == DRAFT
    assert len(send.calls) == 2


# --- Provider rejections (CA-25, CA-76) ------------------------------------------


@pytest.mark.parametrize("status", [401, 403])
def test_ca25_a_rejected_key_raises_auth_error(status):
    """CA-25, RN-08: a rejected key is stated as such, and the message never shows the key."""
    errors = _errors()
    send = FakeSend(_http(status, REJECTED_KEY))
    with pytest.raises(errors.AuthError) as caught:
        _adapter(send).complete_json(SYSTEM, MESSAGES, SCHEMA)
    assert len(send.calls) == 1
    _assert_error_text_is_clean(caught.value)


def test_ca76_an_unknown_model_raises_model_not_found_naming_llm_model():
    """CA-76, RN-08: the provider not knowing the model names the LLM_MODEL setting."""
    errors = _errors()
    send = FakeSend(_http(404, UNKNOWN_MODEL))
    with pytest.raises(errors.ModelNotFound) as caught:
        _adapter(send).complete_json(SYSTEM, MESSAGES, SCHEMA)
    assert caught.value.setting == "LLM_MODEL"
    assert "LLM_MODEL" in str(caught.value)
    assert len(send.calls) == 1
    _assert_error_text_is_clean(caught.value)


def test_ca25_insufficient_quota_raises_quota_error():
    """CA-25, RN-08: a 429 for insufficient quota is the usage limit, not a rate limit."""
    errors = _errors()
    send = FakeSend(_http(429, INSUFFICIENT_QUOTA))
    with pytest.raises(errors.QuotaError) as caught:
        _adapter(send).complete_json(SYSTEM, MESSAGES, SCHEMA)
    assert len(send.calls) == 1
    _assert_error_text_is_clean(caught.value)


def test_ca25_insufficient_quota_is_recognized_by_its_code_alone():
    """CA-25 edge: the quota 429 is recognized when only `code` says insufficient_quota."""
    errors = _errors()
    body = copy.deepcopy(INSUFFICIENT_QUOTA)
    body["error"]["type"] = "invalid_request_error"
    send = FakeSend(_http(429, body))
    with pytest.raises(errors.QuotaError):
        _adapter(send).complete_json(SYSTEM, MESSAGES, SCHEMA)


MODEL_NOT_FOUND_CODE = _error_body(
    f"The model `{MODEL}` does not exist or you do not have access to it.",
    "invalid_request_error",
    "model_not_found",
)
INVALID_KEY_CODE = _error_body("Incorrect API key provided.", "invalid_request_error", "invalid_api_key")
PROJECT_WITHOUT_MODEL_ACCESS = _error_body(
    f"Project `proj_fictional0001` does not have access to model `{MODEL}`.",
    "invalid_request_error",
    "model_not_found",
)


def test_ca76_a_400_with_code_model_not_found_raises_model_not_found_naming_llm_model():
    """CA-76, RN-08: OpenAI can answer an unknown model with 400 and code model_not_found;
    the cause is still the model setting."""
    errors = _errors()
    send = FakeSend(_http(400, MODEL_NOT_FOUND_CODE))
    with pytest.raises(errors.ModelNotFound) as caught:
        _adapter(send).complete_json(SYSTEM, MESSAGES, SCHEMA)
    assert caught.value.setting == "LLM_MODEL"
    assert "LLM_MODEL" in str(caught.value)
    assert len(send.calls) == 1
    _assert_error_text_is_clean(caught.value)


def test_ca25_a_400_with_code_invalid_api_key_raises_auth_error():
    """CA-25, RN-08: a 400 whose code says the key is invalid is a rejected key."""
    errors = _errors()
    send = FakeSend(_http(400, INVALID_KEY_CODE))
    with pytest.raises(errors.AuthError) as caught:
        _adapter(send).complete_json(SYSTEM, MESSAGES, SCHEMA)
    assert len(send.calls) == 1
    _assert_error_text_is_clean(caught.value)


def test_ca76_a_403_with_code_model_not_found_raises_model_not_found_naming_llm_model():
    """CA-76, RN-08: a 403 because the project has no access to the model points at the
    model setting, not at the key."""
    errors = _errors()
    send = FakeSend(_http(403, PROJECT_WITHOUT_MODEL_ACCESS))
    with pytest.raises(errors.ModelNotFound) as caught:
        _adapter(send).complete_json(SYSTEM, MESSAGES, SCHEMA)
    assert not isinstance(caught.value, errors.AuthError)
    assert caught.value.setting == "LLM_MODEL"
    assert "LLM_MODEL" in str(caught.value)
    assert len(send.calls) == 1
    _assert_error_text_is_clean(caught.value)


@pytest.mark.parametrize(
    "payload",
    [
        _error_body("You are not allowed to sample from this model.", "invalid_request_error", None),
        _error_body("Country, region, or territory not supported.", "request_forbidden", "unsupported_country_region_territory"),
        b"",
        b"<html>Forbidden</html>",
    ],
    ids=["no-code", "other-code", "empty", "html"],
)
def test_ca25_a_403_without_the_model_not_found_code_stays_auth_error(payload):
    """CA-25, RN-08: only the model_not_found code turns a 403 into a model cause."""
    errors = _errors()
    send = FakeSend(_http(403, payload))
    with pytest.raises(errors.AuthError) as caught:
        _adapter(send).complete_json(SYSTEM, MESSAGES, SCHEMA)
    _assert_error_text_is_clean(caught.value)


def test_rn08_a_rate_limit_raises_provider_unavailable_rate_limited():
    """RN-08 (plan 9.2): a 429 rate limit is not the usage limit; its code is rate_limited."""
    errors = _errors()
    send = FakeSend(_http(429, RATE_LIMITED))
    with pytest.raises(errors.ProviderUnavailable) as caught:
        _adapter(send).complete_json(SYSTEM, MESSAGES, SCHEMA)
    assert not isinstance(caught.value, errors.QuotaError)
    assert caught.value.code == "rate_limited"
    _assert_error_text_is_clean(caught.value)


@pytest.mark.parametrize(
    "payload",
    [b"", b"<html>Too Many Requests</html>", b"\xff\xfe\x00not utf-8", "[]", '{"error": null}', '{"error": "x"}'],
    ids=["empty", "html", "not-utf8", "array", "null-error", "string-error"],
)
def test_rn08_a_429_with_a_malformed_body_is_a_rate_limit_and_does_not_crash(payload):
    """RN-08, RN-10 edge: a 429 whose body cannot be read is treated as a rate limit."""
    errors = _errors()
    send = FakeSend(_http(429, payload))
    with pytest.raises(errors.ProviderUnavailable) as caught:
        _adapter(send).complete_json(SYSTEM, MESSAGES, SCHEMA)
    assert caught.value.code == "rate_limited"


def test_rn10_a_persistent_server_error_raises_provider_unavailable():
    """RN-10: an outage becomes a clear ProviderUnavailable after one retry."""
    errors = _errors()
    send = FakeSend(_http(503, SERVER_ERROR), _http(503, SERVER_ERROR))
    with pytest.raises(errors.ProviderUnavailable) as caught:
        _adapter(send).complete_json(SYSTEM, MESSAGES, SCHEMA)
    assert len(send.calls) == 2
    _assert_error_text_is_clean(caught.value)


# --- Invalid responses carry the usage (RN-10, RN-09) ----------------------------


@pytest.mark.parametrize(
    "content",
    [
        "",
        "not json at all",
        '{"name": "Bellkeeper Goblin", "mana_cost": ',
        "```json\n{}\n```",
        f"Here is the card: {BODY_SENTINEL} {FAKE_KEY}",
    ],
    ids=["empty", "prose", "truncated", "fenced-empty-object", "echoes-key"],
)
def test_rn10_content_that_is_not_json_raises_invalid_response_with_its_usage(content):
    """RN-10, RN-09: unparseable content is an invalid response carrying the reported usage."""
    errors = _errors()
    send = FakeSend(_http(200, _completion(content, prompt_tokens=700, completion_tokens=12)))
    with pytest.raises(errors.InvalidResponse) as caught:
        _adapter(send).complete_json(SYSTEM, MESSAGES, SCHEMA)
    assert caught.value.usage == _usage(700, 12)
    _assert_error_text_is_clean(caught.value)


@pytest.mark.parametrize(
    "data",
    [
        [],
        "Bellkeeper Goblin",
        None,
        {key: value for key, value in DRAFT.items() if key != "mana_value"},
        dict(DRAFT, mana_value="2"),
        dict(DRAFT, mana_value=True),
        dict(DRAFT, mana_value=-1.5),
        dict(DRAFT, rarity="legendary"),
        dict(DRAFT, keywords="Haste"),
        dict(DRAFT, keywords=["Haste", 7]),
    ],
    ids=[
        "array",
        "string",
        "null",
        "missing-property",
        "integer-as-string",
        "integer-as-boolean",
        "negative-float-for-integer",
        "outside-enum",
        "string-for-array",
        "wrong-item-type",
    ],
)
def test_rn10_json_that_does_not_match_the_schema_raises_invalid_response_with_its_usage(data):
    """RN-10 (plan 9.2): the JSON is checked against the schema before use; a mismatch carries the usage."""
    errors = _errors()
    send = FakeSend(_http(200, _completion(json.dumps(data), prompt_tokens=950, completion_tokens=40)))
    with pytest.raises(errors.InvalidResponse) as caught:
        _adapter(send).complete_json(SYSTEM, MESSAGES, SCHEMA)
    assert caught.value.usage == _usage(950, 40)
    _assert_error_text_is_clean(caught.value)


def test_rn10_a_non_finite_number_raises_invalid_response():
    """RN-10 edge: NaN is not a JSON number, even though Python's parser accepts it."""
    errors = _errors()
    schema = {"type": "object", "properties": {"power": {"type": "number"}}, "required": ["power"]}
    send = FakeSend(_http(200, _completion('{"power": NaN}', prompt_tokens=10, completion_tokens=3)))
    with pytest.raises(errors.InvalidResponse) as caught:
        _adapter(send).complete_json(SYSTEM, MESSAGES, schema)
    assert caught.value.usage == _usage(10, 3)


def test_rn10_a_truncated_answer_cut_by_the_length_limit_raises_invalid_response_with_its_usage():
    """RN-10, RN-09: an answer cut at the token limit is invalid, and its tokens are still reported."""
    errors = _errors()
    completion = _completion(
        '{"name": "Bellkeeper Goblin", "mana_co', prompt_tokens=880, completion_tokens=4096, finish_reason="length"
    )
    send = FakeSend(_http(200, completion))
    with pytest.raises(errors.InvalidResponse) as caught:
        _adapter(send).complete_json(SYSTEM, MESSAGES, SCHEMA)
    assert caught.value.usage == _usage(880, 4096)


def _without_choices():
    completion = _completion(json.dumps(DRAFT), prompt_tokens=300, completion_tokens=0)
    del completion["choices"]
    return completion


def _with_choices(value):
    completion = _completion(json.dumps(DRAFT), prompt_tokens=300, completion_tokens=0)
    completion["choices"] = value
    return completion


def _with_message(value):
    completion = _completion(json.dumps(DRAFT), prompt_tokens=300, completion_tokens=0)
    completion["choices"][0]["message"] = value
    return completion


@pytest.mark.parametrize(
    "completion",
    [
        _without_choices(),
        _with_choices([]),
        _with_choices(None),
        _with_choices("not a list"),
        _with_message(None),
        _with_message({"role": "assistant"}),
        _with_message({"role": "assistant", "content": None, "refusal": None}),
        _with_message({"role": "assistant", "content": 42, "refusal": None}),
    ],
    ids=[
        "no-choices",
        "empty-choices",
        "null-choices",
        "string-choices",
        "null-message",
        "no-content",
        "null-content",
        "numeric-content",
    ],
)
def test_rn10_a_malformed_completion_raises_invalid_response_with_its_usage(completion):
    """RN-10, RN-09: a response without readable content is invalid and still carries the reported usage."""
    errors = _errors()
    send = FakeSend(_http(200, completion))
    with pytest.raises(errors.InvalidResponse) as caught:
        _adapter(send).complete_json(SYSTEM, MESSAGES, SCHEMA)
    assert caught.value.usage == _usage(300, 0)
    _assert_error_text_is_clean(caught.value)


@pytest.mark.parametrize(
    "payload",
    [b"", b"not json", b"<html>gateway</html>", b"\xff\xfe\x00", "[]", "null", '"text"'],
    ids=["empty", "prose", "html", "not-utf8", "array", "null", "string"],
)
def test_rn10_a_success_status_with_an_unreadable_body_raises_invalid_response(payload):
    """RN-10 edge: a 200 whose body is not a JSON object is invalid; no usage was reported, so it is zero."""
    errors = _errors()
    send = FakeSend(_http(200, payload))
    with pytest.raises(errors.InvalidResponse) as caught:
        _adapter(send).complete_json(SYSTEM, MESSAGES, SCHEMA)
    assert caught.value.usage == _usage(0, 0)
    _assert_error_text_is_clean(caught.value)


@pytest.mark.parametrize(
    "usage",
    [None, "lots", {}, {"prompt_tokens": "12", "completion_tokens": 3}, {"prompt_tokens": -5, "completion_tokens": 3}],
    ids=["null", "string", "empty", "string-count", "negative-count"],
)
def test_rn09_an_unreadable_usage_never_breaks_a_valid_answer(usage):
    """RN-09 edge: a valid answer with an unreadable usage still returns the data, with non-negative integer tokens."""
    completion = _completion(json.dumps(DRAFT))
    completion["usage"] = usage
    send = FakeSend(_http(200, completion))
    data, reported = _adapter(send).complete_json(SYSTEM, MESSAGES, SCHEMA)
    assert data == DRAFT
    for count in (reported.input_tokens, reported.output_tokens):
        assert isinstance(count, int) and not isinstance(count, bool)
        assert count >= 0


# --- Refusals (plan 9.2: ContentRefused carries the usage) -----------------------


def test_rn10_a_refusal_raises_content_refused_with_its_usage():
    """RN-10, RN-09: a structured-output refusal is ContentRefused, carrying the reported usage,
    and its text never repeats the provider's words."""
    errors = _errors()
    completion = _completion(
        None,
        prompt_tokens=640,
        completion_tokens=18,
        refusal=f"I can't help with that request. {BODY_SENTINEL} {FAKE_KEY}",
    )
    send = FakeSend(_http(200, completion))
    with pytest.raises(errors.ContentRefused) as caught:
        _adapter(send).complete_json(SYSTEM, MESSAGES, SCHEMA)
    assert caught.value.usage == _usage(640, 18)
    _assert_error_text_is_clean(caught.value)


def test_rn10_an_answer_stopped_by_the_content_filter_raises_content_refused_with_its_usage():
    """RN-10, RN-09: finish_reason content_filter is a refusal, carrying the reported usage."""
    errors = _errors()
    completion = _completion(None, prompt_tokens=500, completion_tokens=0, finish_reason="content_filter")
    send = FakeSend(_http(200, completion))
    with pytest.raises(errors.ContentRefused) as caught:
        _adapter(send).complete_json(SYSTEM, MESSAGES, SCHEMA)
    assert caught.value.usage == _usage(500, 0)


# --- The key never reaches an error (CA-06) -----------------------------------------


@pytest.mark.parametrize(
    "outcomes",
    [
        [(401, REJECTED_KEY)],
        [(403, REJECTED_KEY)],
        [(404, UNKNOWN_MODEL)],
        [(429, INSUFFICIENT_QUOTA)],
        [(429, RATE_LIMITED)],
        [(400, _error_body("Invalid parameter.", "invalid_request_error", "invalid_value"))],
        [(500, SERVER_ERROR), (502, SERVER_ERROR)],
        [(200, _completion(f"{BODY_SENTINEL} {FAKE_KEY}"))],
        [(200, _completion(json.dumps({"name": f"{BODY_SENTINEL} {FAKE_KEY}"})))],
        [(200, f"{BODY_SENTINEL} {FAKE_KEY} {MASKED_ECHO}")],
    ],
    ids=[
        "401",
        "403",
        "404",
        "429-quota",
        "429-rate",
        "400",
        "5xx",
        "content-echo",
        "schema-mismatch-echo",
        "raw-body-echo",
    ],
)
def test_ca06_no_error_text_contains_the_key_or_the_response_body(outcomes):
    """CA-06, RN-06: whatever the provider answers, the error raised never contains the key,
    the masked echo or the provider's response body."""
    errors = _errors()
    send = FakeSend(*(_http(status, payload) for status, payload in outcomes))
    with pytest.raises(errors.ProviderError) as caught:
        _adapter(send).complete_json(SYSTEM, MESSAGES, SCHEMA)
    _assert_error_text_is_clean(caught.value)


# --- Unmapped 400 answers and the wire code (RN-08, RN-10, T154) ------------------

UNSUPPORTED_FORMAT = _error_body(
    "Unsupported value: 'response_format' of type 'json_schema' is not supported with this model.",
    "invalid_request_error",
    "unsupported_value",
)


def test_rn10_t154_an_unmapped_400_answer_is_provider_rejected_naming_llm_model():
    """RN-10, RN-08 (T154): a 400 the adapter does not map (here an unsupported response format) is
    `provider_rejected`, names LLM_MODEL, shows the fixed message and is not retried."""
    errors = _errors()
    send = FakeSend(_http(400, UNSUPPORTED_FORMAT))
    with pytest.raises(errors.ProviderError) as caught:
        _adapter(send).complete_json(SYSTEM, MESSAGES, SCHEMA)
    error = caught.value
    assert not isinstance(error, (errors.AuthError, errors.ModelNotFound, errors.QuotaError))
    assert error.code == "provider_rejected"
    assert getattr(error, "setting", None) == "LLM_MODEL"
    assert str(error) == errors.MESSAGES["provider_rejected"]
    assert len(send.calls) == 1
    _assert_error_text_is_clean(error)


@pytest.mark.parametrize(
    ("status", "payload"),
    [(400, MODEL_NOT_FOUND_CODE), (403, PROJECT_WITHOUT_MODEL_ACCESS)],
    ids=["400-model-not-found", "403-model-not-found"],
)
def test_rn08_t154_the_wire_code_model_not_found_maps_through_the_adapters_own_constant(
    monkeypatch, status, payload
):
    """RN-08, RN-10 (T154): the adapter compares OpenAI's wire code with its own constant, not with the
    application's CODE_MODEL_NOT_FOUND. The application constant is changed and the adapter reloaded:
    an adapter that still reads the application constant no longer recognizes `model_not_found`."""
    import importlib

    import core.errors
    import providers.openai_text as openai_text

    errors = _errors()
    monkeypatch.setattr(core.errors, "CODE_MODEL_NOT_FOUND", "application_model_code_changed")
    try:
        importlib.reload(openai_text)
        send = FakeSend(_http(status, payload))
        adapter = openai_text.OpenAITextAdapter(api_key=FAKE_KEY, model=MODEL, send=send)
        with pytest.raises(errors.ModelNotFound) as caught:
            adapter.complete_json(SYSTEM, MESSAGES, SCHEMA)
        assert caught.value.setting == "LLM_MODEL"
        assert caught.value.code == "model_not_found"
        _assert_error_text_is_clean(caught.value)
    finally:
        monkeypatch.undo()
        importlib.reload(openai_text)
