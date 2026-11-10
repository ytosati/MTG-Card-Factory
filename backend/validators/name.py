"""The name check: the card's name is not the name of an existing card or face (see spec RN-51)."""

from validators.result import Cause

CHECK = "name"
EXISTING_NAME = "existing_name"
EXISTING_NAME_MESSAGE = "An existing card already has this name. Choose a name no existing card or face uses."

TYPOGRAPHIC_APOSTROPHES = str.maketrans({"’": "'", "‘": "'", "ʼ": "'"})


def normalize_name(name):
    """The form names are compared in: case folded, single spaces, no surrounding spaces, straight apostrophes."""
    # Kept equal to catalog.selectors.normalize_name: validators import nothing from the apps (plan section 3).
    return " ".join(name.translate(TYPOGRAPHIC_APOSTROPHES).casefold().split())


def check(card, inputs):
    """A cause when the normalized name is among the existing names."""
    name = card.get("name")
    if not isinstance(name, str):
        return []
    normalized = normalize_name(name)
    if normalized and normalized in inputs.existing_names:
        return [Cause(CHECK, EXISTING_NAME, EXISTING_NAME_MESSAGE)]
    return []
