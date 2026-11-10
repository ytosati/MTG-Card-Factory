"""`validate()`: every card check composed into one result.
Details: specs/plan.md, sections 5 and 7.
"""

from dataclasses import dataclass

from validators import color_identity, mana_cost, name
from validators.result import ValidationResult


@dataclass(frozen=True)
class CheckInputs:
    """What a check reads besides the card: the lexicon, the request and the existing card names."""

    lexicon: object
    request: dict
    existing_names: frozenset | None


# Each check with its stable name and the input it cannot run without; a
# check whose input is None is listed as skipped (plan section 7).
CHECKS = (
    (mana_cost.CHECK, mana_cost.check, None),
    (color_identity.CHECK, color_identity.check, None),
    (name.CHECK, name.check, "existing_names"),
)


def validate(card, lexicon, request, existing_names=None):
    """Run every check on `card` (a mapping of version fields) for `request` (requested identity and idea).

    `existing_names` holds the normalized names of existing cards and faces; None skips the name check.
    """
    names = None if existing_names is None else frozenset(existing_names)
    inputs = CheckInputs(lexicon=lexicon, request=request, existing_names=names)
    checks_run, skipped, causes = [], [], []
    for check, run, needs in CHECKS:
        if needs is not None and getattr(inputs, needs) is None:
            skipped.append(check)
            continue
        checks_run.append(check)
        causes.extend(run(card, inputs))
    return ValidationResult(checks_run=tuple(checks_run), causes=tuple(causes), skipped=tuple(skipped))
