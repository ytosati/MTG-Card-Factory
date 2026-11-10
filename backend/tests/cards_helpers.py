"""Fictional cards, requests and version fields for the `cards` tests (task T37).

Every card, rule text and comparable below is fictional and written by hand.
"""

import uuid

# The request a card came from (spec "Entities", plan section 4).
REQUEST = {
    "idea": "An elf scout that rewards casting spells from the top of the library.",
    "requested_color_identity": ["G", "U"],
    "power_level": "medium",
}

# The stored validation format of plan section 7.
APPROVED_VALIDATION = {
    "status": "approved",
    "checks_run": ["mana_cost", "color_identity"],
    "causes": [],
    "skipped": [],
}

REJECTED_VALIDATION = {
    "status": "rejected",
    "checks_run": ["mana_cost", "color_identity"],
    "causes": [
        {"check": "mana_cost", "code": "mana_value_mismatch", "message": "The stated mana value 4 does not match 3."},
        {"check": "color_identity", "code": "outside_requested", "message": "The cost uses {B}, outside the request."},
    ],
    "skipped": [],
}


def comparables():
    return [
        {"oracle_id": str(uuid.uuid4()), "name": "Mossback Herald of Quill", "role": "card_draw"},
        {"oracle_id": str(uuid.uuid4()), "name": "Tidewhisper Lookout", "role": "ramp"},
    ]


def version_fields(**overrides):
    """Every field of a version that Milestone 3 stores (plan section 4)."""
    values = {
        "name": "Thornveil Courier",
        "mana_cost": "{1}{G}{G/U}",
        "mana_value": 3,
        "type_line": "Creature — Elf Scout",
        "rules_text": "You may look at the top card of your library any time.\n"
        "Whenever you cast a spell from the top of your library, draw a card.",
        "power": "2",
        "toughness": "3",
        "rarity": "uncommon",
        "design_intent": "Card advantage for a Simic top-of-library Commander deck.",
        "rationale": "A three-mana value engine that needs a deck built around it.",
        "comparables": comparables(),
        "power_indicator": "in_range",
        "power_justification": "Comparable to medium-power draw engines at the same cost.",
        "status": "approved",
        "validation": APPROVED_VALIDATION,
    }
    values.update(overrides)
    return values


def models():
    from cards import models as cards_models

    return cards_models


def new_card(**overrides):
    """A saved card holding only its request, with no version yet."""
    values = dict(REQUEST)
    values.update(overrides)
    return models().Card.objects.create(**values)


def save_version(card, **fields):
    """The single call site of the service under test (plan section 5, `cards.services`)."""
    from cards import services

    return services.save_version(card, **fields)
