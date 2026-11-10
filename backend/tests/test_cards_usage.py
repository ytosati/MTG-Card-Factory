"""Usage recording for text generations (task T38, spec RN-09, CA-16).

Details: specs/plan.md, sections 4 (`UsageRecord`), 5 (`cards.services`,
`cards.selectors`) and 7 (Concurrency: the usage queue of `core.jobs`).

API under test:

    cards.services.record_usage(*, provider, model, input_tokens, output_tokens, outcome, card=None)
        Records one text provider call as a `UsageRecord` of kind "text".
        `outcome` is "ok" or "failed"; `card` is a saved Card or None (a failed
        generation, the connection test). The write goes through
        `core.jobs.enqueue_usage`, so while a build runs it waits in the
        in-memory queue and is written when the build ends. An outcome outside
        ok/failed or a negative token count raises ValueError and stores
        nothing. Image usage (kind "image") is added by T50.

    cards.selectors.usage_for(card) -> iterable of UsageRecord
        The usage records linked to `card`, oldest first. Records of other
        cards and records with no card are never included.

Every card, provider answer and model name below is fictional.
"""

import pytest

from tests.cards_helpers import models, new_card
from tests.job_helpers import BUILD_KIND, inline_runner

PROVIDER = "openai"
MODEL = "gpt-fictional-mini"


def record_usage(**values):
    """The single call site of the service under test (plan section 5, `cards.services`)."""
    from cards import services

    return services.record_usage(**values)


def usage_for(card):
    """The single call site of the selector under test (plan section 5, `cards.selectors`)."""
    from cards import selectors

    return list(selectors.usage_for(card))


def text_usage(**overrides):
    values = {
        "provider": PROVIDER,
        "model": MODEL,
        "input_tokens": 1234,
        "output_tokens": 567,
        "outcome": "ok",
    }
    values.update(overrides)
    return values


def stored():
    return list(models().UsageRecord.objects.order_by("pk"))


@pytest.fixture
def inline():
    with inline_runner() as runner:
        yield runner


# --- A text record ---------------------------------------------------------------------------------


@pytest.mark.django_db
def test_t38_rn09_ca16_text_record_stores_provider_model_tokens_and_outcome(inline):
    """RN-09 / CA-16 / T38: a text generation records provider, model, input and output tokens and its
    outcome, linked to its card, with kind text and a creation time."""
    card = new_card()

    record_usage(card=card, **text_usage())

    [record] = stored()
    assert record.card_id == card.pk
    assert record.kind == "text"
    assert record.provider == PROVIDER
    assert record.model == MODEL
    assert record.input_tokens == 1234
    assert record.output_tokens == 567
    assert record.outcome == "ok"
    assert record.created_at is not None


@pytest.mark.django_db
def test_t38_rn09_ca16_failed_record_with_no_card(inline):
    """RN-09 / CA-16 / T38: a generation that fails after the provider answered records its usage with
    outcome failed and no card."""
    record_usage(**text_usage(input_tokens=800, output_tokens=42, outcome="failed"))

    [record] = stored()
    assert record.card_id is None
    assert record.kind == "text"
    assert record.outcome == "failed"
    assert record.input_tokens == 800
    assert record.output_tokens == 42


@pytest.mark.django_db
def test_t38_rn09_card_is_optional_and_defaults_to_none(inline):
    """RN-09 / T38: `card` may be left out; the record is then not linked to a card."""
    record_usage(**text_usage())

    [record] = stored()
    assert record.card_id is None


@pytest.mark.django_db
def test_t38_rn09_ca16_each_call_is_a_separate_record(inline):
    """RN-09 / CA-16 / T38: a draft and its revision are two records, never merged."""
    card = new_card()

    record_usage(card=card, **text_usage(input_tokens=1000, output_tokens=300))
    record_usage(card=card, **text_usage(input_tokens=1500, output_tokens=280))

    records = stored()
    assert len(records) == 2
    assert [(r.input_tokens, r.output_tokens) for r in records] == [(1000, 300), (1500, 280)]


@pytest.mark.django_db
def test_t38_rn09_zero_tokens_are_recorded(inline):
    """RN-09 / T38: a call that reports zero tokens is still a record (edge case: zero)."""
    record_usage(**text_usage(input_tokens=0, output_tokens=0, outcome="failed"))

    [record] = stored()
    assert (record.input_tokens, record.output_tokens) == (0, 0)


@pytest.mark.django_db
def test_t38_rn09_huge_token_counts_are_kept_exactly(inline):
    """RN-09 / T38: large token counts are stored without loss (edge case: huge values)."""
    record_usage(**text_usage(input_tokens=1_999_999_999, output_tokens=2_000_000_000))

    [record] = stored()
    assert record.input_tokens == 1_999_999_999
    assert record.output_tokens == 2_000_000_000


@pytest.mark.django_db
def test_t38_rn09_model_name_with_odd_characters_is_kept_as_given(inline):
    """RN-09 / T38: the model name is stored as the configuration gave it (edge case: odd characters)."""
    model = "fictional/model-é_ß:2025.01 «β»"

    record_usage(**text_usage(model=model))

    [record] = stored()
    assert record.model == model


@pytest.mark.django_db
@pytest.mark.parametrize("field", ["input_tokens", "output_tokens"])
def test_t38_rn09_negative_token_count_is_refused_and_stores_nothing(inline, field):
    """RN-09 / T38: a negative token count is not a usage; it raises ValueError and stores nothing
    (edge case: negative)."""
    with pytest.raises(ValueError):
        record_usage(**text_usage(**{field: -1}))

    assert stored() == []


@pytest.mark.django_db
@pytest.mark.parametrize("outcome", ["", "OK", "refused", "partial"])
def test_t38_rn09_unknown_outcome_is_refused_and_stores_nothing(inline, outcome):
    """RN-09 / T38: the outcome is ok or failed; anything else raises ValueError and stores nothing."""
    with pytest.raises(ValueError):
        record_usage(**text_usage(outcome=outcome))

    assert stored() == []


# --- usage_for(card) -------------------------------------------------------------------------------


@pytest.mark.django_db
def test_t38_rn09_usage_for_returns_the_card_records_oldest_first(inline):
    """RN-09 / T38: `usage_for(card)` returns the records of that card, in the order they were made."""
    card = new_card()
    record_usage(card=card, **text_usage(input_tokens=10, output_tokens=1))
    record_usage(card=card, **text_usage(input_tokens=20, output_tokens=2, outcome="failed"))

    records = usage_for(card)

    assert [(r.input_tokens, r.outcome) for r in records] == [(10, "ok"), (20, "failed")]
    assert all(r.card_id == card.pk for r in records)


@pytest.mark.django_db
def test_t38_rn09_usage_for_leaves_out_other_cards_and_records_with_no_card(inline):
    """RN-09 / T38: records not linked to the card (another card, a failed generation, the connection
    test) are never part of its usage."""
    card = new_card()
    other = new_card(idea="A fictional goblin that sacrifices artifacts for treasure.")
    record_usage(card=card, **text_usage(input_tokens=111))
    record_usage(card=other, **text_usage(input_tokens=222))
    record_usage(**text_usage(input_tokens=333, outcome="failed"))

    records = usage_for(card)

    assert [r.input_tokens for r in records] == [111]


@pytest.mark.django_db
def test_t38_rn09_usage_for_a_card_with_no_records_is_empty(inline):
    """RN-09 / T38: a card with no usage has an empty list (edge case: empty)."""
    assert usage_for(new_card()) == []


# --- Writes during a build go through the queue of T13 (plan section 7) ---------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("ending", ["done", "failed"])
def test_t38_rn09_usage_recorded_during_a_build_waits_for_the_build_to_end(inline, ending):
    """RN-09 / T38 (plan section 7, Concurrency): a usage record made while a build runs is not written
    during the build; it is written when the build ends, whatever the outcome."""
    from core import jobs

    during = {}

    def build(report):
        record_usage(**text_usage(input_tokens=77, output_tokens=7))
        during["count"] = models().UsageRecord.objects.count()
        if ending == "failed":
            raise RuntimeError("fictional build failure")

    jobs.submit(BUILD_KIND, build)

    assert during["count"] == 0
    [record] = stored()
    assert (record.input_tokens, record.output_tokens) == (77, 7)


@pytest.mark.django_db
def test_t38_rn09_usage_is_written_through_the_jobs_usage_queue(inline, monkeypatch):
    """RN-09 / T38 (plan section 7): `record_usage` hands its write to `core.jobs.enqueue_usage`, so a
    held write is not stored until the queue runs it."""
    from core import jobs

    held = []
    monkeypatch.setattr(jobs, "enqueue_usage", held.append)
    monkeypatch.setattr(jobs.JobRunner, "enqueue_usage", lambda self, write: held.append(write))

    record_usage(**text_usage())

    assert len(held) == 1
    assert stored() == []
    held[0]()
    assert len(stored()) == 1


@pytest.mark.django_db
def test_t38_rn09_usage_outside_a_build_is_written_at_once(inline):
    """RN-09 / T38: with no build running, the record is stored before `record_usage` returns."""
    record_usage(**text_usage())

    assert len(stored()) == 1


@pytest.mark.django_db
@pytest.mark.parametrize("field, value", [("input_tokens", True), ("output_tokens", False)])
def test_t38_rn09_boolean_token_count_is_refused_and_stores_nothing(inline, field, value):
    """RN-09 / T38: a boolean is not a token count, although Python treats it as an integer; it raises
    ValueError and stores nothing (edge case: malformed provider response)."""
    with pytest.raises(ValueError):
        record_usage(**text_usage(**{field: value}))

    assert stored() == []
