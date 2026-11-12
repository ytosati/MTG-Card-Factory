"""POST /api/generations and GET /api/cards/{id} (task T49, spec RN-08, RN-11, RN-50, CA-05,
CA-25, CA-26, CA-70, CA-80).

Details: specs/plan.md, sections 6 (envelope, codes, jobs) and 7 (one generation at a time).

Assumed contract (the shapes live in tests.generation_api_helpers):

    POST /api/generations
        body {"idea": str, "color_identity": [letters], "power_level": str}
        - idea: required, not blank, at most 1,000 Unicode characters (CA-80);
        - color_identity: required list of "W", "U", "B", "R", "G"; [] is a
          colorless request chosen explicitly (CA-26); a missing or null
          value is no choice;
        - power_level: "casual", "medium" or "strong".
        An invalid request answers 400 `validation` with each invalid field
        named in `fields`; no job starts and no provider is called.
        A configuration with a text setting to fix answers the error envelope
        with that setting (code `config_invalid`), before any provider call
        and with no job and no card (RN-08, CA-05).
        Otherwise the generation starts as a job through `core.jobs.submit`
        and the answer is 202 with the job: {id, kind: "generate", status,
        progress, result, error}. While another generation job (generate,
        adjust or art) is queued or running, the answer is 409
        `generation_running` (RN-50).
    GET /api/jobs/{id} of the generation
        done:   result {"card": id, "revision_failure": {code, message} | null}
        failed: error envelope with the provider's cause (`auth`, `quota`,
                `model_not_found` with setting LLM_MODEL), no card (CA-25).
    GET /api/cards/{id}
        200 {"id", "current_version": {text fields, design_intent, rationale,
        comparables, power_indicator, power_justification, origin, status,
        validation}, "usage": {"text": [record, ...]}}; extra fields allowed.
        An unknown or malformed id answers 404 `not_found`.

Every endpoint sits behind the readiness gate, so each test stores a ready
build first. Requests go through tests.configured_api, which checks every
response for key values. Cards, catalog rows and keys are fictional.
"""

import json
import uuid

import pytest

from providers.errors import AuthError, MESSAGES, ModelNotFound, ProviderUnavailable, QuotaError
from tests.cards_helpers import REJECTED_VALIDATION, new_card, version_fields
from tests.config_files import FAKE_TEXT_KEY, full_text_settings
from tests.configured_api import assert_error_envelope, configured_api  # noqa: F401 (fixture)
from tests.generation_api_helpers import (
    CARD_VERSION_FIELDS,
    CARD_VERSION_KEY,
    COLORLESS_REQUEST,
    COMPARABLE_FIELDS,
    DESIGN_INTENT,
    DESIGN_USAGE,
    DRAFT_USAGE,
    GENERATE_KIND,
    GENERATIONS_URL,
    GREEN_WHITE_REQUEST,
    MODEL,
    PROVIDER,
    TEXT_RECORD_FIELDS,
    HeldExecutor,
    card_answer,
    card_path,
    colorless_card_answer,
    design_answer,
    install_fake,
    job_path,
    result_card_id,
    result_revision_failure,
    script_approved,
    script_revision_failure,
    seed_catalog,
)
from tests.job_helpers import JOB_FIELDS, envelope_error, inline_runner, runner_installed, watchdog_calls_counted
from tests.setup_api_helpers import mark_ready

pytestmark = pytest.mark.django_db

IDEA_LIMIT = 1000
REQUIRED_FIELDS = ("idea", "color_identity", "power_level")


# --- Fixtures ----------------------------------------------------------------


@pytest.fixture
def api(configured_api):
    """A valid text configuration, a ready database and jobs run inline."""
    configured_api.configure(full_text_settings(provider=PROVIDER, model=MODEL))
    mark_ready()
    with inline_runner():
        yield configured_api


@pytest.fixture
def rows():
    return seed_catalog()


@pytest.fixture
def fake(fake_text_adapter, rows):
    return fake_text_adapter


@pytest.fixture
def real_provider_calls(monkeypatch):
    """Every call that reaches the real OpenAI adapter; it fails the call instead of going out."""
    from providers import openai_text

    calls = []

    def refuse(self, *args, **kwargs):
        calls.append(args)
        raise AssertionError("A provider was called.")

    monkeypatch.setattr(openai_text.OpenAITextAdapter, "complete_json", refuse)
    return calls


# --- Helpers -----------------------------------------------------------------


def _models():
    from cards import models

    return models


def _jobs():
    from core.models import Job

    return Job.objects


def _post(api, body):
    return api.request("POST", GENERATIONS_URL, data=body)


def _accepted(response):
    assert response.status_code == 202, response.content[:500]
    body = response.json()
    assert set(body) == JOB_FIELDS, body
    assert body["kind"] == GENERATE_KIND
    assert body["error"] is None
    uuid.UUID(body["id"])
    return body


def _job(api, job_id):
    response = api.get(job_path(job_id))
    assert response.status_code == 200, response.content[:500]
    body = response.json()
    assert set(body) == JOB_FIELDS, body
    return body


def _generate(api, body=GREEN_WHITE_REQUEST):
    """POST the request, then read the ended job back."""
    job_id = _accepted(_post(api, body))["id"]
    return _job(api, job_id)


def _card(api, card_id):
    response = api.get(card_path(card_id))
    assert response.status_code == 200, response.content[:500]
    assert response["Content-Type"].startswith("application/json")
    return response.json()


def _nothing_started(fake=None):
    assert _jobs().count() == 0
    assert _models().Card.objects.count() == 0
    assert _models().CardVersion.objects.count() == 0
    if fake is not None:
        assert fake.calls == []


def _refused_fields(response):
    error = assert_error_envelope(response, 400, "validation")
    assert isinstance(error["fields"], dict) and error["fields"], error
    for name, messages in error["fields"].items():
        assert isinstance(messages, list) and messages, (name, messages)
        assert all(isinstance(message, str) and message.strip() for message in messages)
    return error["fields"]


def _without(field):
    return {name: value for name, value in GREEN_WHITE_REQUEST.items() if name != field}


# --- Request validation (RN-11, CA-26) ------------------------------------------------------------


@pytest.mark.parametrize("field", REQUIRED_FIELDS)
def test_t49_ca26_each_missing_field_is_named_and_nothing_starts(api, fake, field):
    """CA-26 / RN-11: a request without one required field is refused with that field named,
    with no job, no card and no provider call."""
    fields = _refused_fields(_post(api, _without(field)))

    assert set(fields) == {field}
    _nothing_started(fake)


def test_t49_ca26_empty_request_names_every_missing_field(api, fake):
    """CA-26 / RN-11: an empty request names the idea, the color identity and the power level."""
    fields = _refused_fields(_post(api, {}))

    assert set(fields) == set(REQUIRED_FIELDS)
    _nothing_started(fake)


@pytest.mark.parametrize("idea", ["", "   ", "\n\t "])
def test_t49_ca26_blank_idea_is_a_missing_idea(api, fake, idea):
    """CA-26 / RN-11: an empty or whitespace-only idea counts as no idea, and the field is named."""
    fields = _refused_fields(_post(api, {**GREEN_WHITE_REQUEST, "idea": idea}))

    assert set(fields) == {"idea"}
    _nothing_started(fake)


@pytest.mark.parametrize("idea", [None, ["An elf"], {"text": "An elf"}])
def test_t49_rn11_idea_that_is_not_text_is_refused(api, fake, idea):
    """RN-11: a null, list or object idea is refused naming the idea."""
    fields = _refused_fields(_post(api, {**GREEN_WHITE_REQUEST, "idea": idea}))

    assert set(fields) == {"idea"}
    _nothing_started(fake)


def test_t49_ca26_null_color_identity_is_not_colorless(api, fake):
    """CA-26: colorless counts only when chosen explicitly; a null identity is no choice and is named."""
    fields = _refused_fields(_post(api, {**GREEN_WHITE_REQUEST, "color_identity": None}))

    assert set(fields) == {"color_identity"}
    _nothing_started(fake)


@pytest.mark.parametrize(
    "identity",
    [
        "GW",
        "G",
        ["X"],
        ["C"],
        ["G/W"],
        ["{G}"],
        ["G", "Purple"],
        [1],
        [None],
        [["G"]],
        {"G": True},
    ],
    ids=[
        "text",
        "one-letter-text",
        "unknown-letter",
        "colorless-symbol",
        "hybrid-symbol",
        "braced-symbol",
        "word",
        "number",
        "null-item",
        "nested-list",
        "object",
    ],
)
def test_t49_rn11_malformed_color_identity_is_refused(api, fake, identity):
    """RN-11: the identity is a list of the letters W, U, B, R and G; any other value,
    hybrid or braced symbols included, is refused naming the field."""
    fields = _refused_fields(_post(api, {**GREEN_WHITE_REQUEST, "color_identity": identity}))

    assert set(fields) == {"color_identity"}
    _nothing_started(fake)


@pytest.mark.parametrize("level", ["", "extreme", "Strong", "CASUAL", 2, None, ["casual"]])
def test_t49_rn11_unknown_power_level_is_refused(api, fake, level):
    """RN-11: the power level is one of casual, medium or strong; any other value is refused naming it."""
    fields = _refused_fields(_post(api, {**GREEN_WHITE_REQUEST, "power_level": level}))

    assert set(fields) == {"power_level"}
    _nothing_started(fake)


@pytest.mark.parametrize("level", ["casual", "medium", "strong"])
def test_t49_rn11_each_power_level_is_accepted_and_stored(api, fake, rows, level):
    """RN-11: each power level starts a generation and is stored with the card's request."""
    script_approved(fake, rows)

    job = _generate(api, {**GREEN_WHITE_REQUEST, "power_level": level})

    assert job["status"] == "done", job
    card = _models().Card.objects.get(pk=result_card_id(job["result"]))
    assert card.power_level == level


def test_t49_ca26_explicit_colorless_request_is_accepted(api, fake, rows):
    """CA-26 / RN-11: an empty identity list is a colorless request chosen explicitly; it starts the
    generation and is stored as [] with the card."""
    fake.add_response(design_answer(intent="A colorless token maker for any deck.", keywords=("servo",)), DESIGN_USAGE)
    fake.add_response(colorless_card_answer(rows), DRAFT_USAGE)

    job = _generate(api, COLORLESS_REQUEST)

    assert job["status"] == "done", job
    card = _models().Card.objects.get(pk=result_card_id(job["result"]))
    assert card.requested_color_identity == []
    assert card.power_level == "casual"
    assert card.idea == COLORLESS_REQUEST["idea"]


def test_t49_rn11_request_is_stored_with_the_card_as_sent(api, fake, rows):
    """RN-11: the card keeps the request it came from: idea, requested identity and power level."""
    script_approved(fake, rows)

    job = _generate(api)

    card = _models().Card.objects.get(pk=result_card_id(job["result"]))
    assert card.idea == GREEN_WHITE_REQUEST["idea"]
    assert sorted(card.requested_color_identity) == sorted(GREEN_WHITE_REQUEST["color_identity"])
    assert card.power_level == GREEN_WHITE_REQUEST["power_level"]


def test_t49_rn11_unknown_extra_fields_do_not_block_a_valid_request(api, fake, rows):
    """RN-11: the optional fields of later milestones are not required; an unrecognized field does
    not refuse a request whose required fields are valid."""
    script_approved(fake, rows)

    job = _generate(api, {**GREEN_WHITE_REQUEST, "unrelated": "ignored"})

    assert job["status"] == "done", job


# --- The idea limit (CA-80) --------------------------------------------------------------------------


def test_t49_ca80_idea_of_1000_characters_is_accepted(api, fake, rows):
    """CA-80: an idea of exactly 1,000 characters starts the generation and is stored unchanged."""
    idea = ("</idea> Lanterns ✦ Æther «lanterne» {G/W} 灯 " * 40)[:IDEA_LIMIT]
    assert len(idea) == IDEA_LIMIT
    script_approved(fake, rows)

    job = _generate(api, {**GREEN_WHITE_REQUEST, "idea": idea})

    assert job["status"] == "done", job
    assert _models().Card.objects.get(pk=result_card_id(job["result"])).idea == idea


def test_t49_ca80_idea_of_1001_characters_is_refused_with_no_provider_call(api, fake):
    """CA-80: an idea of 1,001 characters is refused naming the idea, with no job and no provider call;
    the field message does not quote the submitted text."""
    idea = "Q" * (IDEA_LIMIT + 1)

    response = _post(api, {**GREEN_WHITE_REQUEST, "idea": idea})

    fields = _refused_fields(response)
    assert set(fields) == {"idea"}
    assert idea not in response.content.decode("utf-8")
    _nothing_started(fake)


def test_t49_ca80_idea_length_counts_unicode_characters_not_bytes_or_utf16_units(api, fake, rows):
    """CA-80 / RN-11: the limit counts Unicode characters: 1,000 characters outside the
    basic plane (two UTF-16 units and four UTF-8 bytes each) are accepted."""
    idea = "\U0001F409" * IDEA_LIMIT
    script_approved(fake, rows)

    job = _generate(api, {**GREEN_WHITE_REQUEST, "idea": idea})

    assert job["status"] == "done", job
    assert _models().Card.objects.get(pk=result_card_id(job["result"])).idea == idea


def test_t49_ca80_1001_characters_outside_the_basic_plane_are_refused(api, fake):
    """CA-80: 1,001 characters outside the basic plane are over the limit."""
    fields = _refused_fields(_post(api, {**GREEN_WHITE_REQUEST, "idea": "\U0001F409" * (IDEA_LIMIT + 1)}))

    assert set(fields) == {"idea"}
    _nothing_started(fake)


def test_t49_ca80_huge_idea_is_refused_naming_the_field(api, fake):
    """CA-80: a very long idea (100,000 characters) is refused like any idea over the limit."""
    fields = _refused_fields(_post(api, {**GREEN_WHITE_REQUEST, "idea": "lantern " * 12_500}))

    assert set(fields) == {"idea"}
    _nothing_started(fake)


# --- Configuration checked before any provider call (RN-08, CA-05) ------------------------------------


@pytest.mark.parametrize(
    ("settings", "setting"),
    [
        (full_text_settings(key=""), "LLM_API_KEY"),
        ({"LLM_PROVIDER": "openai", "LLM_MODEL": MODEL}, "LLM_API_KEY"),
        (full_text_settings(provider="fictional-ai"), "LLM_PROVIDER"),
        (full_text_settings(model=""), "LLM_MODEL"),
        (full_text_settings(model=FAKE_TEXT_KEY), "LLM_MODEL"),
    ],
    ids=["empty-key", "no-key", "unknown-provider", "no-model", "model-equal-to-key"],
)
def test_t49_ca05_invalid_configuration_names_the_setting_with_no_provider_call_and_no_card(
    api, rows, real_provider_calls, settings, setting
):
    """CA-05 / RN-08: with no key, an unknown provider, no model or a model that is the key, the
    answer is the error envelope naming the setting to fix; no job starts, no provider is called
    and no card is created."""
    api.configure(settings)

    response = _post(api, GREEN_WHITE_REQUEST)

    assert 400 <= response.status_code < 600 and response.status_code != 500, response.content[:500]
    error = assert_error_envelope(response, response.status_code, "config_invalid")
    assert error["setting"] == setting
    assert real_provider_calls == []
    _nothing_started()


def test_t49_rn08_configuration_is_read_again_before_each_generation(api, rows, real_provider_calls, monkeypatch):
    """RN-08 / CA-73: after a missing key is added to `.env`, the next generation starts without a restart."""
    api.configure(full_text_settings(key=""))
    refused = _post(api, GREEN_WHITE_REQUEST)
    assert assert_error_envelope(refused, refused.status_code, "config_invalid")["setting"] == "LLM_API_KEY"
    _nothing_started()

    api.configure(full_text_settings(provider=PROVIDER, model=MODEL))
    # The fixed configuration passes the check; the fake answers in place of the provider.
    fake = install_fake(monkeypatch)
    script_approved(fake, rows)
    job = _generate(api)

    assert job["status"] == "done", job
    assert real_provider_calls == []


def test_t49_rn08_text_provider_not_available_yet_is_refused_before_any_call(api, rows, real_provider_calls):
    """RN-08 (Milestone 3 state, plan section 6): a valid provider with no adapter yet answers
    `provider_not_available_yet`, with no job, no call and no card."""
    api.configure(full_text_settings(provider="anthropic"))

    response = _post(api, GREEN_WHITE_REQUEST)

    assert 400 <= response.status_code < 600 and response.status_code != 500, response.content[:500]
    assert_error_envelope(response, response.status_code, "provider_not_available_yet")
    assert real_provider_calls == []
    _nothing_started()


def test_t49_rn08_image_setting_to_fix_does_not_block_text_generation(api, fake, rows):
    """RN-08: a problem in the image settings makes art unavailable but text generation keeps working."""
    api.configure(full_text_settings(provider=PROVIDER, model=MODEL) | {"IMAGE_PROVIDER": "anthropic"})
    script_approved(fake, rows)

    job = _generate(api)

    assert job["status"] == "done", job


# --- Provider failures in the job (RN-08, CA-25) ----------------------------------------------------


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (AuthError(f"Incorrect API key provided: {FAKE_TEXT_KEY}"), "auth"),
        (QuotaError(f"You exceeded your current quota for key {FAKE_TEXT_KEY}"), "quota"),
    ],
    ids=["rejected-key", "usage-limit"],
)
def test_t49_ca25_rejected_key_or_usage_limit_fails_the_job_with_the_cause_and_no_card(
    api, fake, rows, error, code
):
    """CA-25 / RN-08: when the provider rejects the key or reports the usage limit, the job fails with
    that cause in the error envelope, its fixed message (never the provider's text) and no card."""
    fake.add_error(error)

    job = _generate(api)

    assert job["status"] == "failed", job
    assert job["result"] is None
    inner = envelope_error(job["error"])
    assert inner["code"] == code
    assert inner["message"] == MESSAGES[code]
    assert inner["setting"] in (None, "LLM_API_KEY")
    assert "exceeded" not in json.dumps(job) and "Incorrect" not in json.dumps(job)
    assert _models().Card.objects.count() == 0
    assert _models().CardVersion.objects.count() == 0


def test_t49_rn08_unknown_model_fails_the_job_naming_the_model_setting(api, fake, rows):
    """RN-08 / CA-76: an unknown model name fails the job with `model_not_found`, names LLM_MODEL
    and saves no card."""
    fake.add_error(ModelNotFound("The model `fictional-model` does not exist.", setting="LLM_MODEL"))

    job = _generate(api)

    assert job["status"] == "failed", job
    inner = envelope_error(job["error"])
    assert inner["code"] == "model_not_found"
    assert inner["setting"] == "LLM_MODEL"
    assert "fictional-model" not in json.dumps(job)
    assert _models().Card.objects.count() == 0


# --- The job and its runner (CA-70, RN-50) ----------------------------------------------------------


def test_t49_ca70_generation_runs_as_a_job_through_the_runner(api, fake, rows):
    """CA-70 / RN-41: the generation is a `generate` job of the runner: the request answers 202 before
    any provider call, and the job holds the watchdog while it runs and releases it when it ends."""
    script_approved(fake, rows)
    executor = HeldExecutor()

    with runner_installed(executor), watchdog_calls_counted() as counts:
        accepted = _accepted(_post(api, GREEN_WHITE_REQUEST))
        assert fake.calls == []
        assert len(executor.pending) == 1
        assert _jobs().get(pk=accepted["id"]).kind == GENERATE_KIND
        assert counts == {"hold": 1, "release": 0}

        executor.run_all()

        assert counts == {"hold": 1, "release": 1}
        job = _job(api, accepted["id"])

    assert job["status"] == "done", job
    assert len(fake.calls) == 2
    assert _models().Card.objects.filter(pk=result_card_id(job["result"])).exists()


def test_t49_ca70_submit_is_called_with_the_generate_kind(api, fake, rows, monkeypatch):
    """CA-70: the endpoint starts the generation through `core.jobs.submit`."""
    from core import jobs

    script_approved(fake, rows)
    kinds = []
    original = jobs.submit

    def recording_submit(kind, fn):
        kinds.append(kind)
        return original(kind, fn)

    monkeypatch.setattr(jobs, "submit", recording_submit)

    _generate(api)

    assert kinds == [GENERATE_KIND]


def test_t49_rn50_generation_started_while_another_runs_is_refused(api, fake, rows):
    """RN-50: while a generation is queued or running, starting another answers 409
    `generation_running`; no second job starts and no provider is called for it."""
    executor = HeldExecutor()

    with runner_installed(executor):
        _accepted(_post(api, GREEN_WHITE_REQUEST))

        response = _post(api, COLORLESS_REQUEST)

        assert_error_envelope(response, 409, "generation_running")
        assert _jobs().count() == 1
        assert len(executor.pending) == 1
    assert fake.calls == []


@pytest.mark.parametrize("kind", ["adjust", "art"])
def test_t49_rn50_art_generation_or_quick_adjustment_running_blocks_a_card_generation(api, fake, kind):
    """RN-50: an art generation or a quick adjustment shares the slot; a card generation started
    meanwhile answers `generation_running`."""
    from core.jobs import submit

    with runner_installed(HeldExecutor()):
        submit(kind, lambda report: None)

        response = _post(api, GREEN_WHITE_REQUEST)

        assert_error_envelope(response, 409, "generation_running")
        assert _jobs().filter(kind=GENERATE_KIND).count() == 0
    assert fake.calls == []


def test_t49_rn50_generation_is_accepted_again_after_the_running_one_ends(api, fake, rows):
    """RN-50: once the running generation ends, a new one is accepted."""
    executor = HeldExecutor()
    script_approved(fake, rows)

    with runner_installed(executor):
        first = _accepted(_post(api, GREEN_WHITE_REQUEST))
        executor.run_all()
        assert _job(api, first["id"])["status"] == "done"

        script_approved(fake, rows)
        second = _accepted(_post(api, GREEN_WHITE_REQUEST))

    assert second["id"] != first["id"]


def test_t49_rn50_failed_generation_frees_the_slot(api, fake, rows):
    """RN-50: a generation that failed does not keep refusing new ones."""
    fake.add_error(AuthError("fictional rejection"))
    assert _generate(api)["status"] == "failed"

    script_approved(fake, rows)

    assert _generate(api)["status"] == "done"


def test_t49_rn50_refused_generation_message_says_one_is_running(api, fake):
    """RN-50: the refusal says that a generation is already running, with no setting to fix."""
    with runner_installed(HeldExecutor()):
        _accepted(_post(api, GREEN_WHITE_REQUEST))
        error = assert_error_envelope(_post(api, GREEN_WHITE_REQUEST), 409, "generation_running")

    assert error["setting"] is None
    assert "running" in error["message"].lower()


# --- The job result --------------------------------------------------------------------------------


def test_t49_rn15_done_job_result_holds_the_card_and_no_revision_failure(api, fake, rows):
    """RN-14 / RN-15: a done generation's result names the saved card and carries no revision failure."""
    script_approved(fake, rows)

    job = _generate(api)

    assert (job["kind"], job["status"], job["error"]) == (GENERATE_KIND, "done", None)
    card_id = result_card_id(job["result"])
    assert _models().Card.objects.filter(pk=card_id).exists()
    assert result_revision_failure(job["result"]) is None


def test_t49_rn15_failed_revision_call_is_reported_in_the_job_result(api, fake, rows):
    """RN-15 / CA-11: when the revision call fails, the rejected draft is saved and the job result
    carries the failure's code and fixed message, never the provider's text."""
    script_revision_failure(fake, rows, ProviderUnavailable("fictional upstream outage detail"))

    job = _generate(api)

    assert job["status"] == "done", job
    notice = result_revision_failure(job["result"])
    assert notice == {"code": "provider_unavailable", "message": MESSAGES["provider_unavailable"]}
    assert "fictional upstream outage detail" not in json.dumps(job)
    card = _card(api, result_card_id(job["result"]))
    assert card[CARD_VERSION_KEY]["status"] == "rejected"
    assert card[CARD_VERSION_KEY]["origin"] == "generated"


# --- GET /api/cards/{id} -----------------------------------------------------------------------------


def test_t49_rn13_generated_card_is_read_back_with_its_current_version(api, fake, rows):
    """RN-12 / RN-13 / RN-22 / CA-27: the saved card is read back with its current version: text
    fields, validation result, design intent, rationale, comparables, power indicator with its
    justification, origin and status."""
    script_approved(fake, rows)
    answer = card_answer(rows)

    card_id = result_card_id(_generate(api)["result"])
    body = _card(api, card_id)

    assert body["id"] == card_id
    version = body[CARD_VERSION_KEY]
    assert CARD_VERSION_FIELDS <= set(version), version
    for field in ("name", "mana_cost", "mana_value", "type_line", "rules_text", "power", "toughness", "rarity"):
        assert version[field] == answer[field], field
    assert version["design_intent"] == DESIGN_INTENT
    assert version["rationale"] == answer["rationale"]
    assert version["power_indicator"] == "in_range"
    assert version["power_justification"] == answer["power_justification"]
    assert (version["origin"], version["status"]) == ("generated", "approved")
    assert version["validation"]["status"] == "approved"
    assert version["validation"]["causes"] == []
    assert [comparable["name"] for comparable in version["comparables"]] == [
        "Lanternroot Shaman",
        "Glowmoss Herder",
    ]
    for comparable in version["comparables"]:
        assert set(comparable) == COMPARABLE_FIELDS


def test_t49_rn09_card_shows_its_text_usage(api, fake, rows):
    """RN-09 / CA-16: the card shows the text usage of its generation, one record per call, oldest first."""
    script_approved(fake, rows)

    card_id = result_card_id(_generate(api)["result"])
    records = _card(api, card_id)["usage"]["text"]

    assert [set(record) for record in records] == [TEXT_RECORD_FIELDS, TEXT_RECORD_FIELDS]
    assert [(r["input_tokens"], r["output_tokens"]) for r in records] == [
        (DESIGN_USAGE.input_tokens, DESIGN_USAGE.output_tokens),
        (DRAFT_USAGE.input_tokens, DRAFT_USAGE.output_tokens),
    ]
    assert {(r["provider"], r["model"], r["outcome"]) for r in records} == {(PROVIDER, MODEL, "ok")}


def test_t49_rn14_rejected_card_shows_its_causes_and_only_its_own_usage(api):
    """RN-14 / RN-09: a rejected card shows its validation causes; usage of other cards and of calls
    with no card is not shown."""
    from cards import services

    card = new_card()
    services.save_version(card, **version_fields(status="rejected", validation=REJECTED_VALIDATION))
    other = new_card(idea="Another fictional idea about lighthouse spirits.")
    services.save_version(other, **version_fields(name="Harborlight Wisp"))
    services.record_usage(provider=PROVIDER, model=MODEL, input_tokens=11, output_tokens=7, outcome="ok", card=card)
    services.record_usage(provider=PROVIDER, model=MODEL, input_tokens=99, output_tokens=9, outcome="ok", card=other)
    services.record_usage(provider=PROVIDER, model=MODEL, input_tokens=55, output_tokens=5, outcome="failed")

    body = _card(api, card.pk)

    version = body[CARD_VERSION_KEY]
    assert version["status"] == "rejected"
    assert version["validation"]["causes"] == REJECTED_VALIDATION["causes"]
    assert version["name"] == "Thornveil Courier"
    assert [(r["input_tokens"], r["output_tokens"]) for r in body["usage"]["text"]] == [(11, 7)]


def test_t49_rn13_card_shows_the_latest_version_as_current(api):
    """RN-25: the card endpoint shows the current version, the latest one saved."""
    from cards import services

    card = new_card()
    services.save_version(card, **version_fields(name="Thornveil Courier"))
    services.save_version(card, **version_fields(name="Thornveil Messenger"))

    assert _card(api, card.pk)[CARD_VERSION_KEY]["name"] == "Thornveil Messenger"


def test_t49_unknown_card_answers_not_found(api):
    """Plan section 6: an unknown card id answers 404 `not_found` in the envelope."""
    assert_error_envelope(api.get(card_path(uuid.uuid4())), 404, "not_found")


@pytest.mark.parametrize("card_id", ["not-a-uuid", "12345", "%27%20OR%201%3D1", "0" * 300])
def test_t49_malformed_card_id_answers_not_found(api, card_id):
    """Plan section 6: a malformed card id answers 404 `not_found`, never an HTML page."""
    assert_error_envelope(api.get(card_path(card_id)), 404, "not_found")


def test_t49_generations_answers_only_post(api, fake):
    """Plan section 6: GET on the generation endpoint is not allowed and starts nothing."""
    assert_error_envelope(api.get(GENERATIONS_URL), 405, "method_not_allowed")
    _nothing_started(fake)


# --- An unmapped 4xx answer to the draft (RN-08, RN-10, T154) ---------------------


def _unmapped_error(status):
    """The error the transport raises for an unmapped 4xx answer; the fictional body echoes the key."""
    from providers import transport

    body = json.dumps(
        {
            "error": {
                "message": f"Unsupported value: 'response_format' is not supported. key={FAKE_TEXT_KEY}",
                "type": "invalid_request_error",
                "param": "response_format",
                "code": "unsupported_value",
            }
        }
    ).encode("utf-8")

    def send(method, url, headers, request_body, *, connect_timeout, read_timeout):
        return transport.HttpResponse(status=status, headers={}, body=body)

    try:
        transport.request(
            "POST",
            "https://api.provider.invalid/v1/fictional",
            headers={"Authorization": f"Bearer {FAKE_TEXT_KEY}"},
            body=b"{}",
            read_timeout=transport.TEXT_READ_TIMEOUT,
            model_setting="LLM_MODEL",
            is_quota_error=lambda response: False,
            send=send,
        )
    except transport.ProviderError as error:
        return error
    raise AssertionError("the transport accepted an answer with status %d" % status)


@pytest.mark.parametrize(
    ("status", "setting"),
    [(400, "LLM_MODEL"), (409, None)],
    ids=["400-names-model-setting", "409-names-no-setting"],
)
def test_t154_rn10_an_unmapped_draft_answer_fails_the_job_as_provider_rejected_with_no_card(
    api, fake, rows, status, setting
):
    """RN-08 / RN-10 (T154): an unmapped 4xx answer to the draft fails the job with `provider_rejected`,
    the fixed message, the model setting only for a 400, and no card; the provider's text never appears."""
    fake.add_response(design_answer(), DESIGN_USAGE)
    fake.add_error(_unmapped_error(status))

    job = _generate(api)

    assert job["status"] == "failed", job
    assert job["result"] is None
    inner = envelope_error(job["error"])
    assert inner["code"] == "provider_rejected"
    assert inner["setting"] == setting
    assert inner["message"] == MESSAGES["provider_rejected"]
    assert "unsupported_value" not in json.dumps(job)
    assert "Unsupported value" not in json.dumps(job)
    assert FAKE_TEXT_KEY not in json.dumps(job)
    assert _models().Card.objects.count() == 0
    assert _models().CardVersion.objects.count() == 0
