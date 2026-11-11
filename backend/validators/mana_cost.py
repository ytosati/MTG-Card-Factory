"""The mana cost check: official symbols in printed order and a matching mana value (see spec RN-17)."""

import re

from validators.result import Cause

CHECK = "mana_cost"

COLORS = ("W", "U", "B", "R", "G")
# Two-color hybrids as printed, in the official order of each pair.
HYBRID_PAIRS = ("W/U", "U/B", "B/R", "R/G", "G/W", "W/B", "U/R", "B/G", "R/W", "G/U")

# Printed order of the symbol groups; the colored group is one run in any order.
RANK_X, RANK_GENERIC, RANK_COLORLESS, RANK_SNOW, RANK_COLORED = range(5)

COLORED_SYMBOLS = {
    **{color: 1 for color in COLORS},
    **{pair: 1 for pair in HYBRID_PAIRS},
    **{f"2/{color}": 2 for color in COLORS},
    **{f"{color}/P": 1 for color in COLORS},
    **{f"{pair}/P": 1 for pair in HYBRID_PAIRS},
}
# A generic number has no leading zero; six digits bound the integer conversion.
GENERIC = re.compile(r"0|[1-9][0-9]{0,5}")
WELL_FORMED = re.compile(r"(?:\{[^{}]+\})+")
SYMBOL = re.compile(r"\{([^{}]+)\}")

MALFORMED_MESSAGE = "The mana cost is not written as a sequence of mana symbols in braces, such as {2}{G}."
UNKNOWN_SYMBOL_MESSAGE = "The mana cost uses a symbol that is not an official mana symbol."
ORDER_MESSAGE = (
    "The mana cost symbols are not in printed order: {X}, then one generic number, then {C}, then {S}, "
    "then the colored, hybrid and Phyrexian symbols."
)
REPEATED_GENERIC_MESSAGE = "The mana cost has more than one generic number; write them as a single number."
INVALID_VALUE_MESSAGE = "The stated mana value is missing or is not a whole number."


def _symbol(symbol):
    """The (rank, mana value) of an official mana symbol, or None."""
    if symbol == "X":
        return RANK_X, 0
    if GENERIC.fullmatch(symbol):
        return RANK_GENERIC, int(symbol)
    if symbol == "C":
        return RANK_COLORLESS, 1
    if symbol == "S":
        return RANK_SNOW, 1
    if symbol in COLORED_SYMBOLS:
        return RANK_COLORED, COLORED_SYMBOLS[symbol]
    return None


def _parse(cost):
    """The (rank, value) of each symbol, or the code and message of why the cost is not well formed."""
    if not isinstance(cost, str):
        return None, Cause(CHECK, "malformed_cost", MALFORMED_MESSAGE)
    if cost == "":
        return [], None
    if not WELL_FORMED.fullmatch(cost):
        return None, Cause(CHECK, "malformed_cost", MALFORMED_MESSAGE)
    symbols = [_symbol(symbol) for symbol in SYMBOL.findall(cost)]
    if None in symbols:
        return None, Cause(CHECK, "unknown_symbol", UNKNOWN_SYMBOL_MESSAGE)
    return symbols, None


def mana_value(cost):
    """The mana value of a well formed cost; no cost at all is 0 (see spec RN-17)."""
    symbols, cause = _parse(cost)
    if cause is not None:
        raise ValueError(cause.message)
    return sum(value for _rank, value in symbols)


def check(card, inputs):
    """The causes that reject the card's mana cost or its stated mana value."""
    symbols, cause = _parse(card.get("mana_cost"))
    if cause is not None:
        return [cause]
    causes = []
    ranks = [rank for rank, _value in symbols]
    if any(later < earlier for earlier, later in zip(ranks, ranks[1:])):
        causes.append(Cause(CHECK, "symbol_order", ORDER_MESSAGE))
    if ranks.count(RANK_GENERIC) > 1:
        causes.append(Cause(CHECK, "repeated_generic", REPEATED_GENERIC_MESSAGE))

    computed = sum(value for _rank, value in symbols)
    stated = card.get("mana_value")
    # bool is an int in Python, but True is never a stated mana value.
    if not isinstance(stated, int) or isinstance(stated, bool):
        causes.append(Cause(CHECK, "mana_value_invalid", INVALID_VALUE_MESSAGE))
    elif stated != computed:
        causes.append(
            Cause(
                CHECK,
                "mana_value_mismatch",
                f"The stated mana value {stated} does not match the mana value of the cost, {computed}.",
            )
        )
    return causes
