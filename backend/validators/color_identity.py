"""The color identity check: colors of the cost and rules text within the request (see spec RN-16)."""

import re

from validators.result import Cause

CHECK = "color_identity"
OUTSIDE_IDENTITY = "outside_identity"

COLOR_ORDER = ("W", "U", "B", "R", "G")
COLOR_WORDS = {"W": "white", "U": "blue", "B": "black", "R": "red", "G": "green"}
WORD_COLORS = {word: color for color, word in COLOR_WORDS.items()}

SYMBOL = re.compile(r"\{([^{}]*)\}")
_WORD = r"(?:white|blue|black|red|green)"
_SUBJECT = r"this\s+(?:card|creature|spell|permanent|artifact|enchantment|land|planeswalker|battle|object)"
_COLORS = rf"(all\s+colors|{_WORD}(?:(?:\s*,\s*(?:and\s+)?|\s+and\s+){_WORD})*)"
# A color-defining ability (see spec RN-16).
COLOR_DEFINITION = re.compile(rf"(?<!\w){_SUBJECT}\s+is\s+{_COLORS}(?!\w)", re.IGNORECASE)
# Longer names are not looked for in the text, so the per-card pattern stays small.
MAX_NAME_LENGTH = 200
COLOR_WORD = re.compile(_WORD, re.IGNORECASE)


def _text(value):
    return value if isinstance(value, str) else ""


def _without_reminder_text(text):
    """`text` with each closed parenthesized span blanked; an unmatched parenthesis hides nothing."""
    depth_change = [0] * (len(text) + 1)
    opened = []
    for index, char in enumerate(text):
        if char == "(":
            opened.append(index)
        elif char == ")" and opened:
            depth_change[opened.pop()] += 1
            depth_change[index + 1] -= 1
    visible = []
    depth = 0
    for index, char in enumerate(text):
        depth += depth_change[index]
        # A space, not nothing, so the words around a blanked span stay apart.
        visible.append(" " if depth else char)
    return "".join(visible)


def _symbol_colors(text):
    """Colors of every mana symbol in `text`, hybrid and Phyrexian parts included, in any case."""
    colors = set()
    for symbol in SYMBOL.findall(text):
        colors.update(part.strip() for part in symbol.upper().split("/") if part.strip() in COLOR_WORDS)
    return colors


def _name_definition(name):
    """The pattern of "<card name> is <colors>" for this card's name, or None."""
    words = name.split() if isinstance(name, str) and len(name) <= MAX_NAME_LENGTH else []
    if not words:
        return None
    subject = r"\s+".join(re.escape(word) for word in words)
    return re.compile(rf"(?<!\w){subject}\s+is\s+{_COLORS}(?!\w)", re.IGNORECASE)


def _defined_colors(text, name):
    """Colors added by "This card is <color>", "<card name> is all colors" and their variants."""
    colors = set()
    definitions = [COLOR_DEFINITION.finditer(text)]
    by_name = _name_definition(name)
    if by_name is not None:
        definitions.append(by_name.finditer(text))
    matches = [match for found in definitions for match in found]
    for match in matches:
        phrase = match.group(1).lower()
        if phrase.startswith("all"):
            colors.update(COLOR_ORDER)
        else:
            colors.update(WORD_COLORS[word.lower()] for word in COLOR_WORD.findall(phrase))
    return colors


def card_colors(card):
    """The card's color identity from its mana cost and its rules text outside reminder text."""
    rules_text = _without_reminder_text(_text(card.get("rules_text")))
    return _symbol_colors(_text(card.get("mana_cost"))) | _symbol_colors(rules_text) | _defined_colors(rules_text, card.get("name"))


def check(card, inputs):
    """One cause for each color of the card outside the requested identity."""
    requested = inputs.request.get("requested_color_identity")
    allowed = {color for color in requested if isinstance(color, str)} if isinstance(requested, list) else set()
    outside = card_colors(card) - allowed
    return [
        Cause(CHECK, OUTSIDE_IDENTITY, f"The card uses {COLOR_WORDS[color]}, outside the requested color identity.")
        for color in COLOR_ORDER
        if color in outside
    ]
