"""Milestone 3 end-to-end flow: a request becomes a validated card (task T117).

Spec: RN-10, RN-11, RN-14, RN-15, CA-10, CA-11, CA-15, CA-27. Details: specs/plan.md,
sections 6 (generations, jobs, cards, usage) and 14 (end-to-end suite).

The demo path runs through the API: the reference database is built from the Setup
screen (as in the Milestone 2 flow, on the same temporary home and fake data source),
fictional comparable cards join the catalog and its full-text index, a request is sent
with `POST /api/generations`, the job is followed to its end and the card, its validation
and its usage are read back with `GET /api/cards/{id}` and `GET /api/usage?card=`. The
fake text adapter answers in place of a provider, scripted per scenario. The jobs run on
the real thread pool, so the database is a file shared by the request and job threads.
"""

import json
import uuid
from urllib.parse import urlencode

import pytest

from tests.config_files import full_text_settings
from tests.e2e.helpers import E2EApp
from tests.generation_api_helpers import (
    CARD_VERSION_FIELDS,
    CARD_VERSION_KEY,
    COMPARABLE_FIELDS,
    DESIGN_INTENT,
    DESIGN_USAGE,
    DRAFT_USAGE,
    GENERATIONS_URL,
    GREEN_WHITE_REQUEST,
    MISMATCH,
    MODEL,
    PROVIDER,
    REVISION_USAGE,
    card_answer,
    card_path,
    cite,
    design_answer,
    result_card_id,
    result_revision_failure,
    script_approved,
    seed_catalog,
)
from tests.job_helpers import envelope_error
from providers.errors import MESSAGES

pytestmark = pytest.mark.django_db(transaction=True)

USAGE_URL = "/api/usage"
TOKENS = {
    "design": (DESIGN_USAGE.input_tokens, DESIGN_USAGE.output_tokens),
    "draft": (DRAFT_USAGE.input_tokens, DRAFT_USAGE.output_tokens),
    "revision": (REVISION_USAGE.input_tokens, REVISION_USAGE.output_tokens),
}


# ---------------------------------------------------------------- the demo's setting


@pytest.fixture
def rows(app):
    """The database built from the Setup screen, then fictional comparables indexed in the full-text table."""
    job = app.start_build()
    ended, _ = app.follow_job(job["id"])
    assert ended["status"] == "done", ended
    app.api.configure(full_text_settings(provider=PROVIDER, model=MODEL))
    return seed_catalog()


@pytest.fixture
def fake(fake_text_adapter, rows):
    return fake_text_adapter


def _revision_answer(rows, **overrides):
    """A revision that replaces the comparables and the power indicator of the draft."""
    values = {
        "comparables": [cite(rows["brightbark"], "white token maker"), cite(rows["glowmoss"], "life from tokens")],
        "name": "Vellwood Lanternwarden",
        "power_indicator": "too_strong",
        "power_justification": "Stronger than Brightbark Elder and above Glowmoss Herder in output.",
    }
    values.update(overrides)
    return card_answer(rows, **values)


def _invented_comparables():
    return [{"oracle_id": str(uuid.uuid4()), "name": "Imaginary Lantern Titan", "role": "token maker"}]


def _generate(app, body=GREEN_WHITE_REQUEST):
    """POST the request and follow the job to its end; returns (ended job, bodies seen)."""
    response = app.api.request("POST", GENERATIONS_URL, data=body, **app.origin)
    assert response.status_code == 202, response.content[:500]
    accepted = response.json()
    assert accepted["kind"] == "generate"
    assert accepted["status"] in ("queued", "running", "done")
    return app.follow_job(accepted["id"])


def _card(app, card_id):
    return app.json(card_path(card_id))


def _usage(app, card_id):
    return app.json(f"{USAGE_URL}?{urlencode({'card': card_id})}")


def _pairs(records):
    return [(r["input_tokens"], r["output_tokens"]) for r in records]


def _assert_nothing_saved():
    from cards import models

    assert models.Card.objects.count() == 0
    assert models.CardVersion.objects.count() == 0


def _assert_read_back(app, card_id):
    """The card and its usage endpoints agree, and the card shows what RN-12/RN-13 require (CA-27)."""
    card = _card(app, card_id)
    assert card["id"] == card_id
    version = card[CARD_VERSION_KEY]
    assert CARD_VERSION_FIELDS <= set(version), version
    assert version["design_intent"] == DESIGN_INTENT
    assert version["rationale"].strip()
    assert version["comparables"], "A generated card lists the comparables it used."
    assert all(set(c) == COMPARABLE_FIELDS for c in version["comparables"])
    usage = _usage(app, card_id)
    assert usage["card"] == card_id
    assert usage["text"] == card["usage"]["text"]
    return card, version, usage["text"]


# ---------------------------------------------------------------- the scenarios


def test_m3_rn14_ca10_ca27_approved_draft_is_saved_approved_and_read_back(app, fake, rows):
    """RN-14, CA-10, CA-27: an approved draft is saved with origin generated, shows its design intent,
    rationale and comparables, passes validation, and records the design and draft usage."""
    script_approved(fake, rows)

    ended, _ = _generate(app)

    assert (ended["status"], ended["error"]) == ("done", None)
    card_id = result_card_id(ended["result"])
    assert result_revision_failure(ended["result"]) is None
    card, version, text = _assert_read_back(app, card_id)
    assert (version["origin"], version["status"]) == ("generated", "approved")
    assert version["validation"]["status"] == "approved"
    assert version["validation"]["causes"] == []
    assert [c["name"] for c in version["comparables"]] == ["Lanternroot Shaman", "Glowmoss Herder"]
    assert len(fake.calls) == 2
    assert _pairs(text) == [TOKENS["design"], TOKENS["draft"]]
    assert {(r["provider"], r["model"], r["outcome"]) for r in text} == {(PROVIDER, MODEL, "ok")}


def test_m3_ca11_rn15_rejected_draft_fixed_by_the_revision_shows_the_revision(app, fake, rows):
    """CA-11, RN-15, CA-10: a rejected draft gets one revision; when it passes, the card is approved,
    its origin is revised and its comparables and power indicator are the revision's."""
    fake.add_response(design_answer(), DESIGN_USAGE)
    fake.add_response(card_answer(rows, **MISMATCH), DRAFT_USAGE)
    fake.add_response(_revision_answer(rows), REVISION_USAGE)

    ended, _ = _generate(app)

    assert (ended["status"], ended["error"]) == ("done", None)
    assert result_revision_failure(ended["result"]) is None
    card, version, text = _assert_read_back(app, result_card_id(ended["result"]))
    assert (version["origin"], version["status"]) == ("revised", "approved")
    assert version["validation"]["status"] == "approved"
    assert version["name"] == "Vellwood Lanternwarden"
    assert version["mana_value"] == 4
    assert [c["name"] for c in version["comparables"]] == ["Brightbark Elder", "Glowmoss Herder"]
    assert version["power_indicator"] == "too_strong"
    assert version["design_intent"] == DESIGN_INTENT
    assert len(fake.calls) == 3
    assert _pairs(text) == [TOKENS["design"], TOKENS["draft"], TOKENS["revision"]]


def test_m3_ca11_ca10_rn14_draft_rejected_twice_is_saved_rejected_with_causes_and_no_third_attempt(
    app, fake, rows
):
    """CA-11, CA-10, RN-14, RN-15: a card rejected twice is saved and shown as rejected with its causes
    and no third call; the usage keeps the three calls."""
    fake.add_response(design_answer(), DESIGN_USAGE)
    fake.add_response(card_answer(rows, **MISMATCH), DRAFT_USAGE)
    fake.add_response(_revision_answer(rows, **MISMATCH), REVISION_USAGE)

    ended, _ = _generate(app)

    assert (ended["status"], ended["error"]) == ("done", None)
    assert result_revision_failure(ended["result"]) is None
    card, version, text = _assert_read_back(app, result_card_id(ended["result"]))
    assert version["status"] == "rejected"
    assert version["status"] != "approved" and version["validation"]["status"] == "rejected"
    assert version["validation"]["causes"], "A rejected card shows its causes."
    assert len(fake.calls) == 3, "A card rejected twice gets no third attempt."
    assert _pairs(text) == [TOKENS["design"], TOKENS["draft"], TOKENS["revision"]]


def test_m3_ca15_rn10_invalid_draft_response_fails_the_job_and_saves_no_card(app, fake, rows):
    """CA-15, RN-10: an invalid draft response (no valid comparable) fails the job with a clear
    `invalid_response` message and saves no card or version."""
    fake.add_response(design_answer(), DESIGN_USAGE)
    fake.add_response(card_answer(rows, _invented_comparables()), DRAFT_USAGE)

    ended, _ = _generate(app)

    assert ended["status"] == "failed", ended
    assert ended["result"] is None
    inner = envelope_error(ended["error"])
    assert inner["code"] == "invalid_response"
    assert inner["message"] == MESSAGES["invalid_response"]
    assert "Imaginary Lantern Titan" not in json.dumps(ended)
    assert len(fake.calls) == 2
    _assert_nothing_saved()


def test_m3_rn15_ca11_invalid_revision_response_saves_the_rejected_draft_and_reports_the_failure(
    app, fake, rows
):
    """RN-15, CA-11, RN-10: an invalid revision response counts as a failed revision call; the first
    draft is saved rejected with its causes, origin generated, and the job result carries the failure."""
    fake.add_response(design_answer(), DESIGN_USAGE)
    fake.add_response(card_answer(rows, **MISMATCH), DRAFT_USAGE)
    fake.add_response(_revision_answer(rows, comparables=_invented_comparables()), REVISION_USAGE)

    ended, _ = _generate(app)

    assert (ended["status"], ended["error"]) == ("done", None)
    notice = result_revision_failure(ended["result"])
    assert notice == {"code": "invalid_response", "message": MESSAGES["invalid_response"]}
    assert "Imaginary Lantern Titan" not in json.dumps(ended)
    card, version, text = _assert_read_back(app, result_card_id(ended["result"]))
    assert (version["origin"], version["status"]) == ("generated", "rejected")
    assert version["validation"]["status"] == "rejected"
    assert version["validation"]["causes"]
    assert version["name"] == "Vellwood Lanternkeeper"
    assert [c["name"] for c in version["comparables"]] == ["Lanternroot Shaman", "Glowmoss Herder"]
    assert len(fake.calls) == 3
    assert _pairs(text) == [TOKENS["design"], TOKENS["draft"], TOKENS["revision"]]


def test_m3_flow_a_failed_generation_leaves_the_slot_free_for_the_next_request(app, fake, rows):
    """RN-10, RN-14: after an invalid draft response, the next request in the same session is accepted
    and ends with an approved card (no half-created card is left behind)."""
    fake.add_response(design_answer(), DESIGN_USAGE)
    fake.add_response(card_answer(rows, _invented_comparables()), DRAFT_USAGE)
    failed, _ = _generate(app)
    assert failed["status"] == "failed"
    _assert_nothing_saved()

    script_approved(fake, rows)
    ended, _ = _generate(app)

    assert ended["status"] == "done", ended
    _, version, _ = _assert_read_back(app, result_card_id(ended["result"]))
    assert version["status"] == "approved"
    from cards import models

    assert models.Card.objects.count() == 1


def test_m3_rn11_a_refused_request_starts_no_job_and_calls_no_provider(app, fake, rows):
    """RN-11: a request with no idea is refused naming the idea; no job starts and the fake is not called."""
    from core.models import Job

    before = Job.objects.filter(kind="generate").count()
    response = app.api.request("POST", GENERATIONS_URL, data={**GREEN_WHITE_REQUEST, "idea": ""}, **app.origin)

    assert response.status_code == 400, response.content[:500]
    assert response.json()["error"]["code"] == "validation"
    assert Job.objects.filter(kind="generate").count() == before
    assert fake.calls == []
    _assert_nothing_saved()


def test_m3_the_flow_uses_the_e2e_app_fixture(app):
    """The Milestone 3 flow shares the Milestone 2 application fixture (same home and data source)."""
    assert isinstance(app, E2EApp)
