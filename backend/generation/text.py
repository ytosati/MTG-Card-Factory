"""Text generation: design intent and search plan, retrieval of candidates, the card draft, one
revision when the draft is rejected, and saving the card with the usage of every answered call.

Details: specs/plan.md, sections 5, 9.1 and 11 (RN-09, RN-10, RN-14, RN-15).
"""

from collections.abc import Mapping
from dataclasses import asdict, dataclass, replace
from typing import Any


# Modules, not functions, are imported where a test replaces the function.
from catalog import selectors
from cards import services
from cards.models import Card, CardVersion
from core.config import get_config
from generation.prompts import draft_message, load_prompt, request_message, revision_message
from generation.schemas import DESIGN_SCHEMA, DRAFT_SCHEMA, REVISION_SCHEMA
from providers import factory
from providers.base import TextAdapter, Usage
from providers.errors import ContentRefused, InvalidResponse, ProviderError, message_for
from providers.schema import validate_json
from validators import validate


@dataclass(frozen=True)
class DesignStep:
    """The design intent and search plan of the first call, the candidates found and the call's usage."""

    design_intent: str
    search_plan: dict[str, Any]
    candidates: list[dict[str, Any]]
    usage: Usage


def plan_card(request: Mapping[str, Any], adapter: TextAdapter) -> DesignStep:
    """Ask for the design intent and search plan, then search the catalog with it (see spec RN-12).

    `request` holds `idea`, `color_identity` and `power_level`. Provider errors,
    including InvalidResponse for an answer off DESIGN_SCHEMA, propagate before any search.
    """
    data, usage = design_call(request, adapter)
    return search_candidates(request, data, usage)


def design_call(request: Mapping[str, Any], adapter: TextAdapter) -> tuple[dict[str, Any], Usage]:
    """The design call alone: its answer, checked against DESIGN_SCHEMA, and its usage."""
    message = request_message(request["idea"], request["color_identity"], request["power_level"])
    data, usage = adapter.complete_json(
        load_prompt("design"), [{"role": "user", "content": message}], DESIGN_SCHEMA
    )
    _check_schema(data, DESIGN_SCHEMA, usage)
    return data, usage


def search_candidates(request: Mapping[str, Any], data: dict[str, Any], usage: Usage) -> DesignStep:
    """The design step built from a design answer, with the candidates its search plan finds."""
    plan = data["search_plan"]
    # The identity and power level come from the request, never from the model.
    filters = {
        "color_identity": list(request["color_identity"]),
        "power_level": request["power_level"],
        "roles": list(plan["roles"]),
        "card_types": list(plan["card_types"]),
        "mana_value_min": plan["mana_value_min"],
        "mana_value_max": plan["mana_value_max"],
    }
    candidates = list(selectors.search_cards(" ".join(plan["keywords"]), filters))
    return DesignStep(design_intent=data["design_intent"], search_plan=plan, candidates=candidates, usage=usage)


@dataclass(frozen=True)
class Draft:
    """The card of the draft call, its comparables left after the discard, the design intent and the call's usage."""

    name: str
    mana_cost: str
    mana_value: int
    type_line: str
    rules_text: str
    power: str
    toughness: str
    rarity: str
    rationale: str
    comparables: list[dict[str, str]]
    power_indicator: str
    power_justification: str
    design_intent: str
    usage: Usage


_CARD_FIELDS = (
    "name",
    "mana_cost",
    "mana_value",
    "type_line",
    "rules_text",
    "power",
    "toughness",
    "rarity",
    "rationale",
    "power_indicator",
    "power_justification",
)


def draft_card(request: Mapping[str, Any], design: DesignStep, adapter: TextAdapter) -> Draft:
    """Write the card from the request, the design intent and the candidates (see spec RN-12, RN-13, RN-22).

    Cited comparables not among the legal candidates are discarded; none left
    raises InvalidResponse with the draft usage. The power indicator is kept as the model gave it.
    """
    message = draft_message(request, design.design_intent, design.candidates)
    return _card_call(adapter, "draft", DRAFT_SCHEMA, message, design)


def revise_card(
    request: Mapping[str, Any], design: DesignStep, draft: Draft, causes: list[str], adapter: TextAdapter
) -> Draft:
    """Rewrite a rejected draft as a whole card, the design intent kept (see spec RN-15).

    Its comparables are checked as the draft's are; none left raises InvalidResponse with the revision usage.
    """
    rejected = {field: getattr(draft, field) for field in ("comparables", *_CARD_FIELDS)}
    message = revision_message(request, design.design_intent, design.candidates, rejected, causes)
    return _card_call(adapter, "revision", REVISION_SCHEMA, message, design)


def _card_call(adapter: TextAdapter, prompt: str, schema: dict[str, Any], message: str, design: DesignStep) -> Draft:
    data, usage = adapter.complete_json(load_prompt(prompt), [{"role": "user", "content": message}], schema)
    _check_schema(data, schema, usage)
    comparables = kept_comparables(data["comparables"], design.candidates)
    if not comparables:
        # No ids or names in the text: they are the provider's output.
        raise InvalidResponse("The provider answer cited no comparable from the search results.", usage=usage)
    fields = {field: data[field] for field in _CARD_FIELDS}
    return Draft(**fields, comparables=comparables, design_intent=design.design_intent, usage=usage)


def kept_comparables(cited: list[dict[str, str]], candidates: list[dict[str, Any]]) -> list[dict[str, str]]:
    """The cited comparables that the search returned as legal, in the cited order (see spec RN-12, CA-56)."""
    legal = {str(candidate["oracle_id"]): candidate for candidate in candidates if not candidate["counterexample"]}
    kept = []
    seen = set()
    for comparable in cited:
        candidate = legal.get(comparable["oracle_id"])
        if candidate is None or comparable["oracle_id"] in seen:
            continue
        seen.add(comparable["oracle_id"])
        # The name comes from the database, not from the model.
        kept.append({"oracle_id": comparable["oracle_id"], "name": candidate["name"], "role": comparable["role"]})
    return kept


def _check_schema(data: Any, schema: dict[str, Any], usage: Usage) -> None:
    # Adapters already check the schema; checked again so no adapter bug lets bad data through.
    if validate_json(data, schema):
        raise InvalidResponse("The provider answer did not match the requested format.", usage=usage)


@dataclass(frozen=True)
class RevisionFailure:
    """Why the automatic revision call failed: an error code of plan section 6 and its fixed message."""

    code: str
    message: str


@dataclass(frozen=True)
class GenerationOutcome:
    """The saved card and, when its automatic revision failed, that failure (spec RN-15)."""

    card: Card
    revision_failure: RevisionFailure | None = None


# Bounds a stated mana value to what a version stores (plan section 4).
MAX_MANA_VALUE = 1_000_000


def generate_card(request: Mapping[str, Any]) -> Card:
    """The card saved by run_generation()."""
    return run_generation(request).card


def run_generation(request: Mapping[str, Any]) -> GenerationOutcome:
    """Design, draft, validate, revise once when rejected, and save one card (see spec RN-14, RN-15).

    A failure of the design or the draft call saves no card and is raised again.
    Every call the provider answered is recorded, whatever happens after it (see spec RN-09).
    """
    result = factory.text_adapter()
    if result.adapter is None:
        raise RuntimeError("run_generation needs a text adapter; the configuration is checked before it runs.")
    provider, model = result.provider, result.model
    if provider is None:
        # An adapter result with no provider (the test fake) falls back to the configuration.
        config = get_config()
        provider, model = config.llm_provider, config.llm_model
    usage = _UsageLog(provider=provider, model=model)
    outcome = None
    try:
        outcome = _generate(request, result.adapter, usage)
        return outcome
    finally:
        usage.write(card=outcome.card if outcome is not None else None)


def _generate(request: Mapping[str, Any], adapter: TextAdapter, usage: "_UsageLog") -> GenerationOutcome:
    validator_request = {"requested_color_identity": list(request["color_identity"]), "idea": request["idea"]}
    existing_names = selectors.existing_card_names()

    # The design usage is noted before the search runs, so a search failure still records it.
    data, design_usage = usage.answered(lambda: design_call(request, adapter), usage_of=lambda answer: answer[1])
    design = search_candidates(request, data, design_usage)
    draft = _bounded(usage.answered(lambda: draft_card(request, design, adapter)))

    origin = CardVersion.Origin.GENERATED
    revision_failure = None
    checked = validate(_validated_fields(draft), None, validator_request, existing_names)
    if checked.causes:
        causes = [cause.message for cause in checked.causes]
        try:
            revision = _bounded(usage.answered(lambda: revise_card(request, design, draft, causes, adapter)))
        except ProviderError as error:
            # A failed revision call, with or without an answer, keeps the rejected draft (spec RN-15).
            revision_failure = RevisionFailure(code=error.code, message=message_for(error))
        else:
            draft, origin = revision, CardVersion.Origin.REVISED
            checked = validate(_validated_fields(draft), None, validator_request, existing_names)

    return GenerationOutcome(card=_save_card(request, draft, origin, checked), revision_failure=revision_failure)


_VALIDATED_FIELDS = ("name", "mana_cost", "mana_value", "type_line", "rules_text", "power", "toughness", "rarity")


def _bounded(draft: Draft) -> Draft:
    """The draft with its mana value in the stored range, before it is validated and saved."""
    return replace(draft, mana_value=min(max(draft.mana_value, 0), MAX_MANA_VALUE))


def _validated_fields(draft: Draft) -> dict[str, Any]:
    return {field: getattr(draft, field) for field in _VALIDATED_FIELDS}


def _save_card(request: Mapping[str, Any], draft: Draft, origin: str, checked) -> Card:
    """The card with the request and its first version, written together."""
    fields = asdict(draft)
    del fields["usage"]
    return services.create_card(
        idea=request["idea"],
        requested_color_identity=request["color_identity"],
        power_level=request["power_level"],
        origin=origin,
        status=checked.status,
        validation=checked.to_dict(),
        **fields,
    )


class _UsageLog:
    """The usage of every answered call of one generation, written once the card is known (see spec RN-09)."""

    def __init__(self, provider: str, model: str):
        self.provider = provider
        self.model = model
        self.entries: list[tuple[Usage, str]] = []

    def answered(self, step, usage_of=lambda answer: answer.usage):
        """Run one provider step and note its usage; an error that carries usage is noted as failed."""
        try:
            answer = step()
        except (InvalidResponse, ContentRefused) as error:
            self.entries.append((error.usage, "failed"))
            raise
        self.entries.append((usage_of(answer), "ok"))
        return answer

    def write(self, card: Card | None) -> None:
        entries, self.entries = self.entries, []
        for usage, outcome in entries:
            services.record_usage(
                provider=self.provider,
                model=self.model,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                outcome=outcome,
                card=card,
            )
