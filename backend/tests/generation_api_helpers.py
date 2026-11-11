"""Test helpers for the generation endpoint and the card endpoint (task T49).

Details: specs/plan.md, section 6 (Endpoints, Jobs, Contract samples). Shared
by tests/test_api_generations.py and the contract samples
(tests/test_contract_samples.py).

Assumed contract, kept in one place so a shape change is edited here only:

    POST /api/generations  {"idea": str, "color_identity": [letters], "power_level": str}
        202  the job, shaped as GET /api/jobs/{id}: {id, kind: "generate", status, progress, result, error}
    GET /api/jobs/{id} of a generation that ended "done":
        result = {"card": "<card id>", "revision_failure": {"code", "message"} | null}
    GET /api/cards/{id}
        200  {"id", "current_version": {...version fields}, "usage": {"text": [record, ...]}, ...}

Every catalog row, card and request below is fictional and written by hand.
"""

import uuid
from concurrent.futures import Executor, Future

from providers.base import Usage

GENERATIONS_URL = "/api/generations"
CARDS_URL = "/api/cards"
JOBS_URL = "/api/jobs"

GENERATE_KIND = "generate"

# The generation job result (assumed shape; see the module docstring).
RESULT_CARD = "card"
RESULT_REVISION_FAILURE = "revision_failure"
GENERATION_RESULT_FIELDS = {RESULT_CARD, RESULT_REVISION_FAILURE}
REVISION_FAILURE_FIELDS = {"code", "message"}

# The current version of GET /api/cards/{id}: the fields Milestone 3 shows (task T49).
CARD_VERSION_KEY = "current_version"
CARD_VERSION_FIELDS = {
    "name",
    "mana_cost",
    "mana_value",
    "type_line",
    "rules_text",
    "power",
    "toughness",
    "rarity",
    "design_intent",
    "rationale",
    "comparables",
    "power_indicator",
    "power_justification",
    "origin",
    "status",
    "validation",
}
COMPARABLE_FIELDS = {"oracle_id", "name", "role"}
TEXT_RECORD_FIELDS = {"provider", "model", "input_tokens", "output_tokens", "outcome", "created_at"}

PROVIDER = "openai"
MODEL = "fake-text-model-1"

DESIGN_USAGE = Usage(input_tokens=812, output_tokens=143)
DRAFT_USAGE = Usage(input_tokens=2405, output_tokens=388)
REVISION_USAGE = Usage(input_tokens=2990, output_tokens=402)

DESIGN_INTENT = "Token maker for a go-wide green-white deck that rewards lanterns entering."

GREEN_WHITE_REQUEST = {
    "idea": "An elf that makes the lanterns of the forest glow and grows the army.",
    "color_identity": ["G", "W"],
    "power_level": "medium",
}

COLORLESS_REQUEST = {
    "idea": "A clockwork lantern that builds small servants.",
    "color_identity": [],
    "power_level": "casual",
}

# A rejected draft: the stated mana value does not match the cost {2}{G}{W}.
MISMATCH = {"mana_value": 5}

_CLEAR_FTS = "DELETE FROM oracle_fts"
_FILL_FTS = (
    "INSERT INTO oracle_fts(oracle_id, name, type_line, oracle_text) "
    "SELECT oracle_id, name, type_line, oracle_text FROM catalog_oraclecard"
)


def _row(name, text, *, identity=("G",), type_line="Creature — Elf Druid"):
    from catalog.models import OracleCard

    return OracleCard.objects.create(
        oracle_id=uuid.uuid4(),
        name=name,
        mana_cost="{2}{G}",
        cmc=3.0,
        type_line=type_line,
        oracle_text=text,
        colors=list(identity),
        color_identity=list(identity),
        keywords=[],
        power="2",
        toughness="2",
        layout="normal",
        faces=[],
        commander_legality="legal",
        game_changer=False,
        edhrec_rank=None,
        roles=["tokens"],
    )


def seed_catalog():
    """Fictional legal reference rows, indexed in the full-text table like a build does."""
    from django.db import connection

    rows = {
        "lanternroot": _row("Lanternroot Shaman", "Create a 1/1 green Elf Warrior creature token."),
        "glowmoss": _row(
            "Glowmoss Herder", "Whenever a token you control enters, you gain 1 life.", identity=("G", "W")
        ),
        "brightbark": _row(
            "Brightbark Elder", "Create a 1/1 white Spirit creature token with flying.", identity=("W",)
        ),
        "rustgear": _row(
            "Rustgear Automaton",
            "Create a 1/1 colorless Servo artifact creature token.",
            identity=(),
            type_line="Artifact Creature — Construct",
        ),
    }
    with connection.cursor() as cursor:
        cursor.execute(_CLEAR_FTS)
        cursor.execute(_FILL_FTS)
    return rows


def design_answer(intent=DESIGN_INTENT, keywords=("lantern", "token")):
    return {
        "design_intent": intent,
        "search_plan": {
            "keywords": list(keywords),
            "roles": ["tokens"],
            "card_types": ["Creature"],
            "mana_value_min": 1,
            "mana_value_max": 6,
        },
    }


def cite(row, role="token maker at three mana"):
    return {"oracle_id": str(row.oracle_id), "name": row.name, "role": role}


def card_answer(rows, comparables=None, **overrides):
    """A draft or revision answer that passes every check delivered so far for a G/W request."""
    if comparables is None:
        comparables = [cite(rows["lanternroot"]), cite(rows["glowmoss"], "life gain from tokens")]
    values = {
        "comparables": comparables,
        "name": "Vellwood Lanternkeeper",
        "mana_cost": "{2}{G}{W}",
        "mana_value": 4,
        "type_line": "Creature — Elf Druid",
        "rules_text": "Whenever another creature you control enters, create a 1/1 green Elf creature token.",
        "power": "2",
        "toughness": "3",
        "rarity": "rare",
        "rationale": "A four-mana token engine in line with Lanternroot Shaman, costed one higher for the trigger.",
        "power_justification": "Slightly stronger than Lanternroot Shaman, close to Glowmoss Herder in value.",
        "power_indicator": "in_range",
    }
    values.update(overrides)
    return values


def colorless_card_answer(rows):
    return card_answer(
        rows,
        [cite(rows["rustgear"], "colorless token maker")],
        name="Cogwick Lampwright",
        mana_cost="{3}",
        mana_value=3,
        type_line="Artifact Creature — Construct",
        rules_text="When this creature enters, create a 1/1 colorless Servo artifact creature token.",
    )


def script_approved(fake, rows):
    """Script an approved generation: the design call, then a draft that passes."""
    fake.add_response(design_answer(), DESIGN_USAGE)
    fake.add_response(card_answer(rows), DRAFT_USAGE)


def script_revision_failure(fake, rows, error):
    """Script a rejected draft whose revision call raises `error`."""
    fake.add_response(design_answer(), DESIGN_USAGE)
    fake.add_response(card_answer(rows, **MISMATCH), DRAFT_USAGE)
    fake.add_error(error)


def install_fake(monkeypatch):
    """A FakeTextAdapter behind `providers.factory.text_adapter()`, as the fixture of tests.provider_fixtures."""
    from providers import factory
    from providers.fake import FakeTextAdapter

    adapter = FakeTextAdapter()
    monkeypatch.setattr(factory, "text_adapter", lambda: factory.AdapterResult(adapter=adapter))
    return adapter


def result_card_id(result):
    """The card id held by a done generation job's result."""
    assert isinstance(result, dict), result
    assert set(result) == GENERATION_RESULT_FIELDS, result
    assert isinstance(result[RESULT_CARD], str) and result[RESULT_CARD], result
    return result[RESULT_CARD]


def result_revision_failure(result):
    """The revision failure notice of a done generation job's result, or None."""
    assert isinstance(result, dict), result
    assert set(result) == GENERATION_RESULT_FIELDS, result
    notice = result[RESULT_REVISION_FAILURE]
    if notice is not None:
        assert set(notice) == REVISION_FAILURE_FIELDS, notice
    return notice


def card_path(card_id):
    return f"{CARDS_URL}/{card_id}"


def job_path(job_id):
    return f"{JOBS_URL}/{job_id}"


class HeldExecutor(Executor):
    """An executor that keeps each submitted callable until `run_all()`, so a job stays queued."""

    def __init__(self):
        self.pending = []

    def submit(self, fn, /, *args, **kwargs):
        future = Future()
        self.pending.append((future, fn, args, kwargs))
        return future

    def run_all(self):
        pending, self.pending = self.pending, []
        for future, fn, args, kwargs in pending:
            try:
                future.set_result(fn(*args, **kwargs))
            except BaseException as error:
                future.set_exception(error)
