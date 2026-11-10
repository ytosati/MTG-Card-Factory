"""Fictional cards and requests for the validator suites (tasks T28, T29, T138).

Every card, name and rules text below is fictional and written by hand. A card
is the plain mapping of the fields a draft carries (plan section 4); a request
gives the requested color identity and the idea text (plan section 5).
"""

ALL_COLORS = ["W", "U", "B", "R", "G"]


def card(**overrides):
    """A fictional draft with a well formed cost and a matching mana value."""
    values = {
        "name": "Bramblegate Wayfinder",
        "mana_cost": "{2}{G}",
        "mana_value": 3,
        "type_line": "Creature — Elf Scout",
        "rules_text": "When this creature enters, look at the top two cards of your library.",
        "power": "2",
        "toughness": "2",
        "rarity": "common",
    }
    values.update(overrides)
    return values


def land(**overrides):
    """A fictional land: no mana cost at all."""
    values = {
        "name": "Hollowmere Crossing",
        "mana_cost": "",
        "mana_value": 0,
        "type_line": "Land",
        "rules_text": "This land enters tapped.",
        "power": "",
        "toughness": "",
        "rarity": "common",
    }
    values.update(overrides)
    return values


def request(identity=None, idea="A scout that finds paths through the forest."):
    """A request; by default every color, so only the mana cost decides."""
    return {
        "requested_color_identity": list(ALL_COLORS if identity is None else identity),
        "idea": idea,
    }


# The lexicon is built from the Comprehensive Rules in Milestone 5 (T24); the
# mana cost check does not read it.
NO_LEXICON = None
