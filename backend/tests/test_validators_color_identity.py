"""The color identity validator (task T29, spec RN-16, CA-01, CA-57, CA-62, CA-72).

RN-16: the card's color identity, from its mana cost and its rules text, is
within the requested identity. Hybrid, Phyrexian and colored symbols in the
text count; reminder text in parentheses does not. With a colorless request,
any colored symbol outside reminder text rejects the card. An ability that
defines the card's color ("This card is blue", "is all colors") adds those
colors.

Every card is fictional. Assertions read only the `color_identity` causes, so
the mana cost check (T28) never decides these results; each card keeps a well
formed cost and a matching mana value.
"""

import time

import pytest

from tests.validator_helpers import ALL_COLORS, NO_LEXICON, card, land, request

CHECK = "color_identity"
# The stable code of a cause for a color outside the requested identity.
OUTSIDE_CODE = "outside_identity"

COLOR_WORDS = {"W": "white", "U": "blue", "B": "black", "R": "red", "G": "green"}

GREEN = ["G"]
COLORLESS = []


def _stored(draft, identity):
    from validators import validate

    return validate(draft, NO_LEXICON, request(identity)).to_dict()


def _identity_causes(stored):
    return [cause for cause in stored["causes"] if cause["check"] == CHECK]


def _assert_accepted(draft, identity):
    stored = _stored(draft, identity)
    assert CHECK in stored["checks_run"], stored
    assert _identity_causes(stored) == [], (draft, identity)
    return stored


def _assert_rejected(draft, identity):
    stored = _stored(draft, identity)
    causes = _identity_causes(stored)
    assert CHECK in stored["checks_run"], stored
    assert stored["status"] == "rejected", (draft, identity)
    assert causes, f"no {CHECK} cause for {draft!r} with identity {identity!r}"
    for cause in causes:
        assert cause["code"] == OUTSIDE_CODE, cause
        assert isinstance(cause["message"], str) and cause["message"].strip(), cause
    return causes


def _names_color(causes, color):
    """A cause message names the offending color, as a word or as its symbol."""
    text = " ".join(cause["message"] for cause in causes).lower()
    return COLOR_WORDS[color] in text or "{" + color.lower() + "}" in text


# --- Check registration ------------------------------------------------------


def test_t29_rn16_color_identity_is_a_named_check_of_validate():
    """RN-16: validate() runs the color identity check under the stable name "color_identity"."""
    stored = _stored(card(), GREEN)

    assert CHECK in stored["checks_run"]
    assert "mana_cost" in stored["checks_run"]


def test_t29_rn16_an_in_identity_card_is_approved():
    """RN-16: a green card for a green request leaves no color identity cause and is approved."""
    stored = _assert_accepted(card(mana_cost="{2}{G}", mana_value=3), GREEN)

    assert stored["status"] == "approved", stored


# --- CA-01: colored symbol in the rules text --------------------------------


def test_t29_ca01_green_request_with_a_blue_symbol_in_the_text_is_rejected_with_the_cause():
    """CA-01 (RN-16): a green request and a {U} in the rules text is rejected; the cause names blue."""
    draft = card(rules_text="{1}{U}, {T}: Draw a card.")

    causes = _assert_rejected(draft, GREEN)

    assert _names_color(causes, "U"), causes


def test_t29_ca01_the_same_text_is_accepted_when_blue_is_requested():
    """CA-01 (RN-16): the same card is within a green and blue request."""
    _assert_accepted(card(rules_text="{1}{U}, {T}: Draw a card."), ["G", "U"])


def test_t29_rn16_requested_identity_order_does_not_matter():
    """RN-16: the requested identity is a set of colors; its order never changes the result."""
    draft = card(rules_text="{1}{U}, {T}: Draw a card.")

    _assert_accepted(draft, ["U", "G"])
    _assert_accepted(draft, ["G", "U"])


@pytest.mark.parametrize("color", ["W", "U", "B", "R"])
def test_t29_rn16_each_other_color_symbol_in_the_text_is_rejected_for_green(color):
    """RN-16: any colored symbol outside green, in the rules text, rejects a green request."""
    causes = _assert_rejected(card(rules_text=f"{{{color}}}: This creature gets +1/+1 until end of turn."), GREEN)

    assert _names_color(causes, color), causes


def test_t29_rn16_a_colored_cost_outside_the_identity_is_rejected():
    """RN-16: the mana cost is a source of colors: {G}{U} is rejected for a green request."""
    causes = _assert_rejected(card(mana_cost="{G}{U}", mana_value=2), GREEN)

    assert _names_color(causes, "U"), causes


def test_t29_rn16_two_outside_colors_are_both_named():
    """RN-16: when several colors fall outside the request, the causes name each of them."""
    draft = card(mana_cost="{1}{G}{R}", mana_value=3, rules_text="{B}: Regenerate this creature.")

    causes = _assert_rejected(draft, GREEN)

    assert _names_color(causes, "R"), causes
    assert _names_color(causes, "B"), causes


# --- CA-57: hybrid, Phyrexian and reminder text ------------------------------


def test_t29_ca57_hybrid_in_the_cost_is_rejected_for_green():
    """CA-57 (RN-16): a {G/U} hybrid in the cost counts both colors and is rejected for green."""
    causes = _assert_rejected(card(mana_cost="{1}{G/U}", mana_value=2), GREEN)

    assert _names_color(causes, "U"), causes


def test_t29_ca57_hybrid_in_the_rules_text_is_rejected_for_green():
    """CA-57 (RN-16): a {G/U} hybrid in the rules text is rejected for green."""
    causes = _assert_rejected(card(rules_text="{G/U}: Untap this creature."), GREEN)

    assert _names_color(causes, "U"), causes


def test_t29_ca57_hybrid_is_accepted_when_both_colors_are_requested():
    """CA-57 (RN-16): the {G/U} hybrid is within a green and blue request."""
    _assert_accepted(card(mana_cost="{1}{G/U}", mana_value=2, rules_text="{G/U}: Untap this creature."), ["G", "U"])


def test_t29_ca57_blue_symbol_inside_reminder_text_is_not_counted():
    """CA-57 (RN-16): a {U} inside reminder text in parentheses does not add blue."""
    draft = card(rules_text="Tidewalk 2 (You may pay {U} rather than this spell's mana cost.)")

    _assert_accepted(draft, GREEN)


def test_t29_ca57_hybrid_inside_reminder_text_is_not_counted():
    """CA-57 (RN-16): a {G/U} hybrid inside reminder text does not add blue."""
    draft = card(rules_text="Mossbind (Whenever this creature attacks, you may pay {G/U}. If you do, scry 1.)")

    _assert_accepted(draft, GREEN)


def test_t29_ca57_symbol_after_closed_reminder_text_is_counted():
    """CA-57 (RN-16): only the text inside the parentheses is reminder text; a {U} after it counts."""
    draft = card(rules_text="Trample (It can deal excess damage.) {U}: Tap target creature.")

    causes = _assert_rejected(draft, GREEN)

    assert _names_color(causes, "U"), causes


def test_t29_ca57_reminder_text_on_another_line_does_not_hide_a_symbol():
    """CA-57 (RN-16): reminder text on one line does not hide a {U} on the next line."""
    draft = card(rules_text="Reach (This creature can block creatures with flying.)\n{U}: Scry 1.")

    _assert_rejected(draft, GREEN)


@pytest.mark.parametrize(
    "symbol, color",
    [("{U/P}", "U"), ("{G/U/P}", "U"), ("{2/U}", "U"), ("{R/G}", "R"), ("{W/P}", "W")],
)
def test_t29_rn16_phyrexian_and_two_generic_hybrids_count_their_colors(symbol, color):
    """RN-16: Phyrexian symbols, hybrid Phyrexian and {2/C} hybrids add their colors."""
    causes = _assert_rejected(card(rules_text=f"{symbol}: This creature gains reach until end of turn."), GREEN)

    assert _names_color(causes, color), causes


@pytest.mark.parametrize("cost, value", [("{G/P}", 1), ("{2/G}", 2), ("{1}{G}{G/P}", 3)])
def test_t29_rn16_green_phyrexian_and_two_generic_hybrids_stay_green(cost, value):
    """RN-16: {G/P} and {2/G} add only green, so they are within a green request."""
    _assert_accepted(card(mana_cost=cost, mana_value=value), GREEN)


def test_t29_rn16_phyrexian_in_the_cost_is_rejected_outside_the_identity():
    """RN-16: a {B/P} in the cost adds black and is rejected for green."""
    causes = _assert_rejected(card(mana_cost="{1}{G}{B/P}", mana_value=3), GREEN)

    assert _names_color(causes, "B"), causes


# --- CA-62: colorless request ------------------------------------------------


def test_t29_ca62_colorless_request_rejects_a_green_symbol_in_the_text():
    """CA-62 (RN-16): with a colorless request, a {G} in the rules text is rejected."""
    draft = card(mana_cost="{3}", mana_value=3, type_line="Artifact", rules_text="{G}, {T}: Gain 1 life.")

    causes = _assert_rejected(draft, COLORLESS)

    assert _names_color(causes, "G"), causes


def test_t29_ca62_colorless_request_accepts_a_colorless_symbol_in_the_text():
    """CA-62 (RN-16): with a colorless request, a {C} in the rules text is accepted."""
    draft = card(mana_cost="{3}", mana_value=3, type_line="Artifact", rules_text="{C}, {T}: Gain 1 life.")

    _assert_accepted(draft, COLORLESS)


def test_t29_ca62_colorless_land_that_adds_colorless_mana_is_accepted():
    """CA-62 (RN-16): a land with no cost whose text adds {C} is within a colorless request."""
    _assert_accepted(land(rules_text="{T}: Add {C}."), COLORLESS)


def test_t29_rn16_colorless_request_rejects_a_colored_cost():
    """RN-16: with a colorless request, a colored mana cost is rejected."""
    causes = _assert_rejected(card(mana_cost="{2}{G}", mana_value=3), COLORLESS)

    assert _names_color(causes, "G"), causes


@pytest.mark.parametrize("symbol", ["{W/U}", "{2/B}", "{R/P}", "{G}", "{u}"])
def test_t29_rn16_colorless_request_rejects_any_colored_symbol_in_the_text(symbol):
    """RN-16: with a colorless request, any colored symbol outside reminder text rejects the card."""
    draft = card(mana_cost="{4}", mana_value=4, type_line="Artifact", rules_text=f"{symbol}: Draw a card.")

    _assert_rejected(draft, COLORLESS)


def test_t29_rn16_colorless_request_ignores_colored_symbols_in_reminder_text():
    """RN-16: with a colorless request, colored symbols inside reminder text do not reject the card."""
    draft = card(
        mana_cost="{4}",
        mana_value=4,
        type_line="Artifact",
        rules_text="Shardlink (You may pay {W}{U}{B}{R}{G} as you cast this spell.)",
    )

    _assert_accepted(draft, COLORLESS)


@pytest.mark.parametrize(
    "cost, value, text",
    [
        ("{X}{X}", 0, "This artifact enters with X charge counters on it."),
        ("{2}{C}{S}", 4, "{S}, {T}: Add {C}{C}."),
        ("{0}", 0, "{T}, Sacrifice this artifact: Scry 1."),
        ("{10}", 10, "{X}, {Q}: Draw X cards. {15}: You win the game."),
        ("", 0, "{T}: Add {C}."),
    ],
)
def test_t29_rn16_colorless_generic_snow_and_x_never_add_colors(cost, value, text):
    """RN-16: {C}, {S}, {X}, generic numbers, {T} and {Q} never add a color."""
    draft = card(mana_cost=cost, mana_value=value, type_line="Artifact", rules_text=text)

    _assert_accepted(draft, COLORLESS)


# --- CA-72: color-defining abilities -----------------------------------------


def test_t29_ca72_this_card_is_blue_is_rejected_for_green():
    """CA-72 (RN-16): "This card is blue" adds blue; a green request rejects it."""
    draft = card(rules_text="This card is blue.\nWhen this creature enters, scry 1.")

    causes = _assert_rejected(draft, GREEN)

    assert _names_color(causes, "U"), causes


def test_t29_ca72_this_card_is_blue_is_accepted_when_blue_is_requested():
    """CA-72 (RN-16): the same color-defining ability is within a green and blue request."""
    _assert_accepted(card(rules_text="This card is blue.\nWhen this creature enters, scry 1."), ["G", "U"])


def test_t29_ca72_is_all_colors_is_rejected_unless_every_color_is_requested():
    """CA-72 (RN-16): "is all colors" adds every color: rejected for four colors, accepted for five."""
    draft = card(rules_text="This card is all colors.")

    causes = _assert_rejected(draft, ["W", "U", "B", "G"])
    assert _names_color(causes, "R"), causes
    _assert_accepted(draft, ALL_COLORS)


def test_t29_ca72_is_all_colors_is_rejected_for_green():
    """CA-72 (RN-16): "is all colors" is rejected for a green request."""
    _assert_rejected(card(rules_text="This card is all colors."), GREEN)


def test_t29_ca72_color_definition_with_two_colors_adds_both():
    """CA-72 (RN-16): "This card is blue and black" adds both colors."""
    draft = card(rules_text="This card is blue and black.")

    causes = _assert_rejected(draft, ["G", "U"])

    assert _names_color(causes, "B"), causes
    _assert_accepted(draft, ["G", "U", "B"])


def test_t29_ca72_color_definition_rejects_a_colorless_request():
    """CA-72 (RN-16): with a colorless request, "This card is green" adds green and is rejected."""
    draft = card(mana_cost="{2}", mana_value=2, type_line="Artifact", rules_text="This card is green.")

    _assert_rejected(draft, COLORLESS)


@pytest.mark.parametrize("sentence", ["THIS CARD IS BLUE.", "this card is Blue.", "This Card Is All Colors."])
def test_t29_ca72_color_definition_is_read_in_any_case(sentence):
    """CA-72 (RN-16): the color-defining ability is recognized in mixed case."""
    _assert_rejected(card(rules_text=sentence), GREEN)


def test_t29_ca72_color_definition_inside_reminder_text_is_not_counted():
    """CA-72 (RN-16): a color sentence inside reminder text is not a color-defining ability."""
    draft = card(rules_text="Wildtether (This card is blue while you control an Island.)")

    _assert_accepted(draft, GREEN)


def test_t29_rn16_no_color_definition_does_not_remove_cost_colors():
    """RN-16: "This card has no color" does not remove the colors of its mana symbols."""
    draft = card(mana_cost="{1}{G}", mana_value=2, rules_text="This card has no color.")

    _assert_accepted(draft, GREEN)
    _assert_rejected(draft, COLORLESS)


def test_t29_rn16_color_words_in_ordinary_text_are_not_a_color_definition():
    """RN-16: a color word that does not define this card's color ("target blue creature") adds nothing."""
    draft = card(rules_text="When this creature enters, tap target blue creature an opponent controls.")

    _assert_accepted(draft, GREEN)


# --- Edge cases --------------------------------------------------------------


@pytest.mark.parametrize("name", ["Bluecrest Herald", "Herald of {U}", "This card is blue", "Azure {G/U} Warden"])
def test_t29_rn16_the_card_name_is_not_a_source_of_colors(name):
    """RN-16: only the cost and the rules text count; the card name never adds colors."""
    _assert_accepted(card(name=name), GREEN)


def test_t29_rn16_type_line_is_not_a_source_of_colors():
    """RN-16: the type line never adds colors, even when a subtype reads like a color word."""
    _assert_accepted(card(type_line="Creature — Elf Druid"), GREEN)


def test_t29_rn16_nested_parentheses_are_all_reminder_text():
    """RN-16: a symbol inside nested parentheses is still inside the reminder text."""
    draft = card(rules_text="Rootcall (Pay {G} (or {U} if you control an Island) to return this card.)")

    _assert_accepted(draft, GREEN)


def test_t29_rn16_symbol_after_nested_reminder_text_is_counted():
    """RN-16: after the outer parenthesis closes, a {U} counts again."""
    draft = card(rules_text="Rootcall (Pay {G} (or more).) {U}: Return this card to your hand.")

    _assert_rejected(draft, GREEN)


def test_t29_rn16_an_unclosed_parenthesis_does_not_hide_symbols():
    """RN-16: an opening parenthesis that never closes is not reminder text, so a {U} after it counts."""
    draft = card(rules_text="Flash (this note never closes {U}: Draw a card.")

    _assert_rejected(draft, GREEN)


def test_t29_rn16_a_stray_closing_parenthesis_does_not_hide_symbols():
    """RN-16: a closing parenthesis with no opening one does not make reminder text."""
    draft = card(rules_text="Reach) {U}: Draw a card.")

    _assert_rejected(draft, GREEN)


def test_t29_rn16_odd_characters_around_a_symbol_do_not_hide_it():
    """RN-16: accents, emoji and other Unicode around a {U} do not hide it."""
    draft = card(rules_text="Ação — 🌲✨ {U}​: Désenchantez ★ la carte.")

    causes = _assert_rejected(draft, GREEN)

    assert _names_color(causes, "U"), causes


def test_t29_rn16_odd_characters_without_symbols_add_no_color():
    """RN-16: text with only odd characters and no colored symbol adds no color."""
    draft = card(rules_text="🌲 Ação — «Ñandú» ✨ { } {} {{ }} ​\t\r\n ¯\\_(ツ)_/¯")

    _assert_accepted(draft, GREEN)


@pytest.mark.parametrize("text", ["", "   ", "\n\n"])
def test_t29_rn16_empty_rules_text_takes_only_the_cost(text):
    """RN-16: an empty rules text adds no color; the cost decides."""
    _assert_accepted(card(rules_text=text), GREEN)
    _assert_rejected(card(mana_cost="{1}{U}", mana_value=2, rules_text=text), GREEN)


@pytest.mark.parametrize("text", [None, 42, ["{U}"], {"text": "{U}"}])
def test_t29_rn16_malformed_rules_text_from_a_provider_does_not_crash(text):
    """RN-16: a malformed provider response (null, number, list, object) yields a result, never an exception."""
    stored = _stored(card(rules_text=text), GREEN)

    assert CHECK in stored["checks_run"]
    assert stored["status"] in ("approved", "rejected")


def test_t29_rn16_malformed_mana_cost_does_not_crash_the_identity_check():
    """RN-16: a malformed cost is the mana cost check's cause; the identity check still runs on the text."""
    stored = _stored(card(mana_cost="2G}{", mana_value=3, rules_text="{U}: Draw a card."), GREEN)

    assert CHECK in stored["checks_run"]
    assert _identity_causes(stored), stored


def test_t29_rn16_huge_text_is_checked_quickly():
    """RN-16: a huge in-identity text is accepted, and a single {U} at its end is found, in well under a second."""
    body = "{G}: This creature gets +1/+1 until end of turn. (Reminder {G}.)\n" * 5000

    started = time.perf_counter()
    _assert_accepted(card(rules_text=body), GREEN)
    _assert_rejected(card(rules_text=body + "{U}: Draw a card."), GREEN)
    assert time.perf_counter() - started < 2.0


def test_t29_rn16_huge_unclosed_parentheses_are_checked_quickly():
    """RN-16: many unclosed parentheses do not make the check slow."""
    body = "(" * 50000 + "{U}"

    started = time.perf_counter()
    _stored(card(rules_text=body), GREEN)
    assert time.perf_counter() - started < 2.0


# --- Color-defining abilities in modern wording (review additions) ------------


@pytest.mark.parametrize(
    "sentence, color",
    [
        ("This creature is blue.", "U"),
        ("This spell is red.", "R"),
        ("This permanent is green and white.", "W"),
        ("This artifact is black.", "B"),
    ],
)
def test_t29_ca72_modern_self_reference_color_definitions_add_colors(sentence, color):
    """CA-72 (RN-16): "This creature/spell/permanent/artifact is <color>" defines the card's color."""
    causes = _assert_rejected(card(rules_text=sentence), GREEN)

    assert _names_color(causes, color), causes


@pytest.mark.parametrize("written", ["Bramblegate Wayfinder", "BRAMBLEGATE WAYFINDER", "bramblegate wayfinder"])
def test_t29_ca72_card_name_is_all_colors_adds_every_color(written):
    """CA-72 (RN-16): "<card name> is all colors", with the card's own name in any case, adds every color."""
    draft = card(name="Bramblegate Wayfinder", rules_text=f"{written} is all colors.")

    _assert_rejected(draft, GREEN)
    _assert_accepted(draft, ALL_COLORS)


@pytest.mark.parametrize("sentence", ["This card is  blue.", "This card is\nblue.", "This card\tis blue"])
def test_t29_ca72_whitespace_variants_of_a_color_definition_add_the_color(sentence):
    """CA-72 (RN-16): repeated spaces, a line break or a tab inside the sentence still define the color."""
    causes = _assert_rejected(card(rules_text=sentence), GREEN)

    assert _names_color(causes, "U"), causes


@pytest.mark.parametrize("text", ["{ U }: Draw a card.", "{U }: Draw a card.", "{ U}: Draw a card."])
def test_t29_rn16_a_padded_colored_symbol_in_the_text_adds_its_color(text):
    """RN-16: spaces inside the braces do not hide a colored symbol: "{ U }" adds blue."""
    causes = _assert_rejected(card(rules_text=text), GREEN)

    assert _names_color(causes, "U"), causes
