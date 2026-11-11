"""JSON schemas of the generation calls: design intent, card draft and revision.

Details: specs/plan.md, sections 9.1 and 9.2. Only the keyword subset every
provider accepts in strict structured output; every property is required.
"""

from cards.models import CardVersion
from catalog.ingest import ROLES

POWER_INDICATORS = list(CardVersion.PowerIndicator.values)
RARITIES = ["common", "uncommon", "rare", "mythic"]

_STRING = {"type": "string"}
_STRING_LIST = {"type": "array", "items": {"type": "string"}}


def _object(properties: dict) -> dict:
    return {"type": "object", "properties": properties, "required": list(properties)}


DESIGN_SCHEMA = _object(
    {
        "design_intent": _STRING,
        "search_plan": _object(
            {
                "keywords": _STRING_LIST,
                # The roles the catalog tags cards with, so the search can filter on them.
                "roles": {"type": "array", "items": {"type": "string", "enum": list(ROLES)}},
                "card_types": _STRING_LIST,
                "mana_value_min": {"type": "integer"},
                "mana_value_max": {"type": "integer"},
            }
        ),
    }
)

# Property order is the order the model writes in: comparables first, so the
# card is built from them, and the justification before the indicator it supports.
_CARD_PROPERTIES = {
    "comparables": {
        "type": "array",
        "items": _object({"oracle_id": _STRING, "name": _STRING, "role": _STRING}),
    },
    "name": _STRING,
    "mana_cost": _STRING,
    "mana_value": {"type": "integer"},
    "type_line": _STRING,
    "rules_text": _STRING,
    "power": _STRING,
    "toughness": _STRING,
    "rarity": {"type": "string", "enum": RARITIES},
    "rationale": _STRING,
    "power_justification": _STRING,
    "power_indicator": {"type": "string", "enum": POWER_INDICATORS},
}

DRAFT_SCHEMA = _object(_CARD_PROPERTIES)

# The revision returns the whole card again; the design intent stays (spec RN-15).
REVISION_SCHEMA = _object(_CARD_PROPERTIES)
