"""Write services of the cards app.
Details: specs/plan.md, sections 5 and 7.
"""

from django.db import transaction
from django.db.models import Max

from cards.models import Card, CardVersion, UsageRecord
from core import jobs


def save_version(card: Card, **fields) -> CardVersion:
    """Create the next version of `card` and make it the current one, in one transaction (see spec RN-25)."""
    _check_version_fields(fields)
    # The IMMEDIATE transaction holds the write lock from its start, so the
    # number read here cannot be taken by another thread before the insert.
    with transaction.atomic():
        last = CardVersion.objects.filter(card_id=card.pk).aggregate(last=Max("number"))["last"]
        version = CardVersion.objects.create(card_id=card.pk, number=(last or 0) + 1, **fields)
        Card.objects.filter(pk=card.pk).update(current_version=version)
    card.current_version = version
    return version



def create_card(*, idea, requested_color_identity, power_level, **version_fields) -> Card:
    """Create a card with the request it came from and its first version, in one transaction (see spec RN-26)."""
    _check_version_fields(version_fields)
    with transaction.atomic():
        card = Card.objects.create(
            idea=idea,
            requested_color_identity=list(requested_color_identity),
            power_level=power_level,
        )
        save_version(card, **version_fields)
    return card

def _check_version_fields(fields):
    """Refuse values outside their choices and a status that disagrees with its validation (see spec RN-14)."""
    # create() does not enforce choices, so an unchecked value would be stored as is.
    status = fields.get("status")
    if status not in CardVersion.Status.values:
        raise ValueError(f"Unknown version status: {status!r}.")
    validation = fields.get("validation")
    if not isinstance(validation, dict) or validation.get("status") != status:
        raise ValueError("The version status does not match its validation status.")
    if fields.get("origin", CardVersion.Origin.GENERATED) not in CardVersion.Origin.values:
        raise ValueError(f"Unknown version origin: {fields['origin']!r}.")
    if fields.get("power_indicator") not in CardVersion.PowerIndicator.values:
        raise ValueError(f"Unknown power indicator: {fields.get('power_indicator')!r}.")


def record_usage(*, provider, model, input_tokens, output_tokens, outcome, card=None):
    """Record one text provider call, with its card or none (see spec RN-09)."""
    if outcome not in UsageRecord.Outcome.values:
        raise ValueError(f"Unknown usage outcome: {outcome!r}.")
    for name, value in (("input_tokens", input_tokens), ("output_tokens", output_tokens)):
        # bool is an int in Python, but True is never a token count.
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"{name} must be a non-negative integer.")

    def write():
        UsageRecord.objects.create(
            card=card,
            kind=UsageRecord.Kind.TEXT,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            outcome=outcome,
        )

    # Through the jobs queue: a write during a build waits for it to end (plan section 7).
    jobs.enqueue_usage(write)
