"""Role tagging of reference cards (task T20, spec RN-12).

Details: specs/plan.md, sections 5 (catalog.ingest) and 9.6 (deterministic role
patterns at build time). The roles let the comparables search (RN-12) filter
the local database by what a card does.

API under test:

    catalog.ingest.ROLES
        Tuple of the role identifiers, in the order of plan section 9.6:
        ramp, card_draw, removal, board_wipe, counterspell, tutor, recursion,
        tokens, life_gain, protection, combat_boost, mana_fixing,
        sacrifice_outlet, graveyard_fill, evasion. Identifiers are the plan
        names in snake_case, the form already stored in `OracleCard.roles`.

    catalog.ingest.tag_roles(type_line, oracle_text, name="") -> list[str]
        Pure function: applies fixed patterns over the rules text and the type
        line and returns every matching role once, in the order of `ROLES`.
        A card with no match gets an empty list. `oracle_text` may hold the
        text of several faces joined by "\\n//\\n" (as `oracle_row` builds it);
        every face counts. `name` is the card's name: where the rules text
        refers to the card by its name (or by "~"), the name is not read as
        rules text, so a name that looks like an effect creates no role.

Out of scope here (later tasks): storing the roles during the build (T21) and
filtering by role in the search (T23).

Reminder text in parentheses creates no role on its own. The one exception
tested is a land whose subtypes give it mana of several colors: its type line
alone makes it mana fixing, even when its only text is the reminder.

Every card below is fictional and written by hand.
"""

import time

import pytest

# Plan section 9.6, in order, as snake_case identifiers.
PLAN_ROLES = (
    "ramp",
    "card_draw",
    "removal",
    "board_wipe",
    "counterspell",
    "tutor",
    "recursion",
    "tokens",
    "life_gain",
    "protection",
    "combat_boost",
    "mana_fixing",
    "sacrifice_outlet",
    "graveyard_fill",
    "evasion",
)


def _tag(type_line, oracle_text, name=""):
    from catalog import ingest

    return ingest.tag_roles(type_line=type_line, oracle_text=oracle_text, name=name)


# --- Fictional cards per role ------------------------------------------------------------
# Each entry: (role, name, type_line, oracle_text). Positives must carry the role;
# negatives must not. Negatives are chosen close to the role's wording.

POSITIVES = [
    # ramp
    ("ramp", "Brassbound Idol", "Artifact", "{T}: Add {C}{C}."),
    ("ramp", "Mossling Tender", "Creature — Elf Druid", "{T}: Add {G}."),
    (
        "ramp",
        "Rootward Call",
        "Sorcery",
        "Search your library for a basic land card, put it onto the battlefield tapped, then shuffle.",
    ),
    # card_draw
    ("card_draw", "Inkwell Insight", "Instant", "Draw two cards."),
    ("card_draw", "Pagewing Owl", "Creature — Bird", "Flying\nWhen Pagewing Owl enters, draw a card."),
    (
        "card_draw",
        "Mournful Scholar",
        "Creature — Human Wizard",
        "Whenever another creature you control dies, you may draw a card.",
    ),
    # removal
    ("removal", "Sudden Verdict", "Instant", "Destroy target creature."),
    ("removal", "Fade Into Mist", "Instant", "Exile target nonland permanent an opponent controls."),
    (
        "removal",
        "Cinder Spitter",
        "Creature — Goblin Shaman",
        "When Cinder Spitter enters, it deals 3 damage to target creature or planeswalker.",
    ),
    ("removal", "Rustbreaker Rite", "Instant", "Destroy target artifact or enchantment."),
    # board_wipe
    ("board_wipe", "Ashen Reckoning", "Sorcery", "Destroy all creatures. They can't be regenerated."),
    ("board_wipe", "Tide of Forgetting", "Sorcery", "Exile all nonland permanents."),
    ("board_wipe", "Emberstorm", "Sorcery", "Emberstorm deals 4 damage to each creature."),
    # counterspell
    ("counterspell", "Quiet Refusal", "Instant", "Counter target spell."),
    (
        "counterspell",
        "Tax the Weaver",
        "Instant",
        "Counter target noncreature spell unless its controller pays {3}.",
    ),
    # tutor
    (
        "tutor",
        "Whispered Errand",
        "Sorcery",
        "Search your library for a card, put it into your hand, then shuffle.",
    ),
    (
        "tutor",
        "Archive Seeker",
        "Creature — Human Wizard",
        "When Archive Seeker enters, you may search your library for an instant or sorcery card, "
        "reveal it, put it into your hand, then shuffle.",
    ),
    # recursion
    (
        "recursion",
        "Gravebloom Rite",
        "Sorcery",
        "Return target creature card from your graveyard to your hand.",
    ),
    (
        "recursion",
        "Second Dawn",
        "Sorcery",
        "Return target permanent card from your graveyard to the battlefield.",
    ),
    # tokens
    ("tokens", "Muster the Ranks", "Sorcery", "Create two 1/1 white Soldier creature tokens."),
    (
        "tokens",
        "Gilded Cutpurse",
        "Creature — Human Rogue",
        "Whenever Gilded Cutpurse deals combat damage to a player, create a Treasure token.",
    ),
    (
        "tokens",
        "Mirror Pool Ritual",
        "Instant",
        "Create a token that's a copy of target creature you control.",
    ),
    # life_gain
    ("life_gain", "Dawnmeadow Balm", "Instant", "You gain 3 life."),
    (
        "life_gain",
        "Lantern Keeper",
        "Creature — Human Cleric",
        "Whenever another creature you control enters, you gain 1 life.",
    ),
    ("life_gain", "Sunfang Lion", "Creature — Cat", "Lifelink"),
    # protection
    (
        "protection",
        "Bulwark Charm",
        "Instant",
        "Target creature you control gains hexproof and indestructible until end of turn.",
    ),
    (
        "protection",
        "Prismatic Veil",
        "Instant",
        "Target creature you control gains protection from the color of your choice until end of turn.",
    ),
    (
        "protection",
        "Steadfast Banner",
        "Artifact",
        "{2}, {T}: Permanents you control gain indestructible until end of turn.",
    ),
    # combat_boost
    (
        "combat_boost",
        "Rallying Horn",
        "Instant",
        "Creatures you control get +1/+1 until end of turn.",
    ),
    ("combat_boost", "Feral Surge", "Instant", "Target creature gets +3/+3 until end of turn."),
    (
        "combat_boost",
        "Banner Captain",
        "Creature — Human Soldier",
        "Other Soldier creatures you control get +1/+1.",
    ),
    # mana_fixing
    ("mana_fixing", "Prism Sapling", "Creature — Plant", "{T}: Add one mana of any color."),
    ("mana_fixing", "Harbor Cliffs", "Land", "{T}: Add {W} or {U}."),
    # sacrifice_outlet
    ("sacrifice_outlet", "Altar of Embers", "Artifact", "Sacrifice a creature: Scry 1."),
    (
        "sacrifice_outlet",
        "Hungering Ghoul",
        "Creature — Zombie",
        "Sacrifice another creature: Hungering Ghoul gets +2/+2 until end of turn.",
    ),
    ("sacrifice_outlet", "Scrap Furnace", "Artifact", "{1}, Sacrifice an artifact: Draw a card."),
    # graveyard_fill
    ("graveyard_fill", "Grave Tide", "Sorcery", "Mill three cards."),
    ("graveyard_fill", "Rotting Deluge", "Sorcery", "Each player mills four cards."),
    (
        "graveyard_fill",
        "Bone Sifter",
        "Creature — Zombie",
        "When Bone Sifter enters, put the top five cards of your library into your graveyard.",
    ),
    # evasion
    ("evasion", "Cloudrunner Kite", "Creature — Bird", "Flying"),
    ("evasion", "Alley Shade", "Creature — Shade", "Alley Shade can't be blocked."),
    ("evasion", "Snarling Brute", "Creature — Ogre", "Menace"),
    (
        "evasion",
        "Wings of Ash",
        "Enchantment — Aura",
        "Enchant creature\nEnchanted creature gets +1/+0 and has flying.",
    ),
]

NEGATIVES = [
    # ramp: lands that tap for mana are not ramp; pump spells are not ramp.
    ("ramp", "Quiet Glade", "Land", "{T}: Add {G}."),
    ("ramp", "Feral Surge", "Instant", "Target creature gets +3/+3 until end of turn."),
    # card_draw: looking at cards is not drawing them.
    (
        "card_draw",
        "Seer's Glance",
        "Sorcery",
        "Look at the top three cards of your library, then put them back in any order.",
    ),
    ("card_draw", "Grave Tide", "Sorcery", "Mill three cards."),
    # removal: targeting a card in a graveyard or a pump is not removal.
    (
        "removal",
        "Gravebloom Rite",
        "Sorcery",
        "Return target creature card from your graveyard to your hand.",
    ),
    ("removal", "Feral Surge", "Instant", "Target creature gets +3/+3 until end of turn."),
    # board_wipe: single target, or "all creatures" that is not a wipe.
    ("board_wipe", "Sudden Verdict", "Instant", "Destroy target creature."),
    ("board_wipe", "Second Wind Horn", "Instant", "Untap all creatures you control."),
    # counterspell: a +1/+1 counter is not a counterspell.
    ("counterspell", "Mentor's Blessing", "Sorcery", "Put a +1/+1 counter on target creature."),
    ("counterspell", "Inkwell Insight", "Instant", "Draw two cards."),
    # tutor: looking at the library is not searching it.
    (
        "tutor",
        "Seer's Glance",
        "Sorcery",
        "Look at the top three cards of your library, then put them back in any order.",
    ),
    ("tutor", "Quiet Refusal", "Instant", "Counter target spell."),
    # recursion: returning a creature to its owner's hand is a bounce, not recursion.
    ("recursion", "Riptide Shove", "Instant", "Return target creature to its owner's hand."),
    ("recursion", "Graveyard Sweep", "Instant", "Exile target player's graveyard."),
    # tokens: copying a spell creates no token.
    ("tokens", "Echo Spell", "Instant", "Copy target instant or sorcery spell. You may choose new targets for the copy."),
    ("tokens", "Sudden Verdict", "Instant", "Destroy target creature."),
    # life_gain: losing life, or forbidding life gain, is not life gain.
    ("life_gain", "Bitter Tithe", "Sorcery", "Each opponent loses 2 life."),
    ("life_gain", "Withering Curse", "Enchantment", "Players can't gain life."),
    # protection: a restriction on a creature is not protection.
    ("protection", "Hobbling Snare", "Instant", "Target creature can't block this turn."),
    ("protection", "Sudden Verdict", "Instant", "Destroy target creature."),
    # combat_boost: a shrinking effect is not a boost.
    ("combat_boost", "Wilting Touch", "Instant", "Target creature gets -2/-2 until end of turn."),
    ("combat_boost", "Inkwell Insight", "Instant", "Draw two cards."),
    # mana_fixing: a single color or colorless mana fixes nothing.
    ("mana_fixing", "Brassbound Idol", "Artifact", "{T}: Add {C}{C}."),
    ("mana_fixing", "Mossling Tender", "Creature — Elf Druid", "{T}: Add {G}."),
    # sacrifice_outlet: an opponent's sacrifice or the card sacrificing itself is not an outlet.
    ("sacrifice_outlet", "Grim Decree", "Sorcery", "Each opponent sacrifices a creature."),
    (
        "sacrifice_outlet",
        "Spark Lantern",
        "Artifact",
        "{T}, Sacrifice Spark Lantern: Add one mana of any color.",
    ),
    # graveyard_fill: exiling from the library or a graveyard fills nothing.
    ("graveyard_fill", "Void Glimpse", "Sorcery", "Exile the top three cards of your library."),
    ("graveyard_fill", "Graveyard Sweep", "Instant", "Exile target player's graveyard."),
    # evasion: reach, vigilance and "can't block" are not evasion.
    ("evasion", "Thornback Spider", "Creature — Spider", "Reach"),
    ("evasion", "Steadfast Sentry", "Creature — Human Soldier", "Vigilance"),
    ("evasion", "Reckless Brute", "Creature — Ogre", "Reckless Brute can't block."),
    ("evasion", "Stampeding Auroch", "Creature — Ox", "Trample"),
    # A basic-type land search onto the battlefield is ramp, not a tutor.
    (
        "tutor",
        "Wildpath Survey",
        "Sorcery",
        "Search your library for a Forest or Island card, put it onto the battlefield tapped, then shuffle.",
    ),
    # A land that fetches a land is mana fixing, not ramp.
    (
        "ramp",
        "Misty Hollow",
        "Land",
        "{T}, Pay 1 life, Sacrifice Misty Hollow: Search your library for a Forest or Island card, "
        "put it onto the battlefield, then shuffle.",
    ),
    # Blinking your own creature, graveyard hate and bounce are not removal.
    (
        "removal",
        "Flicker Ward",
        "Instant",
        "Exile target creature you control, then return it to the battlefield under its owner's control.",
    ),
    ("removal", "Ashen Broom", "Instant", "Exile target creature card from a graveyard."),
    ("removal", "Riptide Shove", "Instant", "Return target creature to its owner's hand."),
    # A legendary card granting itself indestructible by its short name is not protection.
    (
        "protection",
        "Varn, the Quiet Warden",
        "Legendary Creature — Human Monk",
        "{2}: Varn gains indestructible until end of turn.",
    ),
    ("protection", "Mossback Sentinel", "Creature — Treefolk", "Mossback Sentinel has hexproof."),
    # Making opponents discard fills their graveyard, not yours.
    ("graveyard_fill", "Mind Rot Wisp", "Sorcery", "Target opponent discards two cards."),
    ("graveyard_fill", "Gnawing Doubt", "Enchantment", "At the beginning of your upkeep, each opponent discards a card."),
    # Effects that benefit an opponent do not give you the role.
    (
        "card_draw",
        "Spiteful Scribe",
        "Creature — Human Wizard",
        "Whenever an opponent draws a card, Spiteful Scribe deals 1 damage to that player.",
    ),
    ("life_gain", "Merciful End", "Instant", "Destroy target creature. Its controller gains 3 life."),
    (
        "tokens",
        "Beastly Exchange",
        "Instant",
        "Destroy target creature. Its controller creates a 3/3 green Beast creature token.",
    ),
    # Sacrificing a Food for mana is not a sacrifice outlet.
    ("sacrifice_outlet", "Pantry Golem", "Artifact Creature — Golem", "{T}, Sacrifice a Food: Add one mana of any color."),
]

EXTRA_POSITIVES = [
    (
        "ramp",
        "Wildpath Survey",
        "Sorcery",
        "Search your library for a Forest or Island card, put it onto the battlefield tapped, then shuffle.",
    ),
    (
        "mana_fixing",
        "Misty Hollow",
        "Land",
        "{T}, Pay 1 life, Sacrifice Misty Hollow: Search your library for a Forest or Island card, "
        "put it onto the battlefield, then shuffle.",
    ),
    (
        "removal",
        "Phase Warden",
        "Creature — Spirit",
        "When Phase Warden enters, exile another target nonland permanent.",
    ),
    ("removal", "Twin Verdict", "Sorcery", "Destroy two target creatures."),
    (
        "counterspell",
        "Spellward Denial",
        "Instant",
        "Counter target enchantment, instant, or sorcery spell.",
    ),
    (
        "sacrifice_outlet",
        "Ice",
        "Creature — Elemental",
        "Sacrifice a creature: Ice gets +1/+1 until end of turn.",
    ),
    ("mana_fixing", "Verdant Shoals", "Land — Forest Island", "({T}: Add {G} or {U}.)"),
    ("graveyard_fill", "Restless Hoarder", "Sorcery", "Discard two cards, then draw two cards."),
    ("graveyard_fill", "Murk Diviner", "Creature — Zombie Wizard", "When Murk Diviner enters, surveil 2."),
    ("graveyard_fill", "Shoreline Dredge", "Instant", "Mill two cards, then draw a card."),
]
POSITIVES = POSITIVES + EXTRA_POSITIVES


def _case_id(case):
    role, name, _type_line, _text = case
    return f"{role}-{name}"


# --- The role list ------------------------------------------------------------------------


def test_rn12_roles_are_the_plan_list_in_order():
    """RN-12: the role identifiers are exactly the roles of plan section 9.6, in order."""
    from catalog import ingest

    assert tuple(ingest.ROLES) == PLAN_ROLES


def test_rn12_every_role_has_a_positive_and_a_negative_example():
    """RN-12 (T20 Done when): each role is covered by at least one positive and one negative card."""
    assert {case[0] for case in POSITIVES} == set(PLAN_ROLES)
    assert {case[0] for case in NEGATIVES} == set(PLAN_ROLES)


# --- Per role -----------------------------------------------------------------------------


@pytest.mark.parametrize("case", POSITIVES, ids=_case_id)
def test_rn12_positive_card_gets_the_role(case):
    """RN-12: a fictional card whose rules text does the role is tagged with it."""
    role, name, type_line, text = case
    assert role in _tag(type_line, text, name=name)


@pytest.mark.parametrize("case", NEGATIVES, ids=_case_id)
def test_rn12_negative_card_does_not_get_the_role(case):
    """RN-12: a fictional card with close but different wording is not tagged with the role."""
    role, name, type_line, text = case
    assert role not in _tag(type_line, text, name=name)


@pytest.mark.parametrize("case", POSITIVES + NEGATIVES, ids=_case_id)
def test_rn12_result_is_a_list_of_known_roles_in_order_without_duplicates(case):
    """RN-12: the result is a JSON-ready list of known roles, each once, in the order of ROLES."""
    _role, name, type_line, text = case
    roles = _tag(type_line, text, name=name)
    assert isinstance(roles, list)
    assert all(isinstance(role, str) for role in roles)
    assert set(roles) <= set(PLAN_ROLES)
    assert len(roles) == len(set(roles))
    assert roles == sorted(roles, key=PLAN_ROLES.index)


# --- No match -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("type_line", "text"),
    [
        ("", ""),
        ("Creature — Bear", ""),
        ("Basic Land — Forest", ""),
        ("Creature — Human Peasant", "Gentle Farmhand's power is equal to the number of cards in your hand."),
        ("Instant", "Ünïcödé “curly” ‘quotes’ ✦ — · … ½ ∞ 漢字 🜁"),
    ],
    ids=["empty", "vanilla-creature", "basic-land-no-text", "plain-ability", "odd-characters"],
)
def test_rn12_card_with_no_match_gets_an_empty_list(type_line, text):
    """RN-12: a card that matches no pattern keeps an empty list (and odd characters do not break tagging)."""
    assert _tag(type_line, text, name="Gentle Farmhand") == []


# --- Several roles, order, duplicates, case -----------------------------------------------


def test_rn12_card_with_several_roles_gets_all_in_the_order_of_roles():
    """RN-12: a card matching several roles gets all of them, in the stable order of ROLES."""
    text = (
        "Flying\n"
        "When Storm Herald enters, destroy target creature an opponent controls and draw a card. "
        "You gain 2 life."
    )
    roles = _tag("Creature — Angel", text, name="Storm Herald")
    assert roles == ["card_draw", "removal", "life_gain", "evasion"]


def test_rn12_the_same_card_always_gets_the_same_roles():
    """RN-12: tagging is deterministic; the same input gives the same list every time."""
    text = "Create two 1/1 white Soldier creature tokens. You gain 2 life."
    first = _tag("Sorcery", text, name="Muster and Mend")
    assert first == ["tokens", "life_gain"]
    for _ in range(5):
        assert _tag("Sorcery", text, name="Muster and Mend") == first


def test_rn12_a_role_matched_several_times_appears_once():
    """RN-12: a role whose pattern matches several times is listed once."""
    text = "Draw a card.\nAt the beginning of your upkeep, draw a card.\nWhen this enchantment leaves, draw two cards."
    assert _tag("Enchantment", text, name="Endless Study") == ["card_draw"]


def test_rn12_patterns_ignore_letter_case():
    """RN-12: patterns match regardless of letter case."""
    assert "card_draw" in _tag("INSTANT", "DRAW TWO CARDS.", name="Loud Insight")
    assert "counterspell" in _tag("instant", "counter target spell.", name="quiet refusal")


# --- Faces --------------------------------------------------------------------------------


def test_rn12_text_of_every_face_counts():
    """RN-12: on a card with several faces (text joined by "\\n//\\n"), every face's text is tagged."""
    roles = _tag(
        "Creature — Faerie // Sorcery",
        "Flying\n//\nDestroy target creature.",
        name="Duskwing Sprite // Midnight Sting",
    )
    assert roles == ["removal", "evasion"]


def test_rn12_back_face_alone_can_carry_the_role():
    """RN-12: a role found only on the back face is still tagged."""
    roles = _tag(
        "Creature — Human // Creature — Werewolf",
        "Vigilance\n//\nCreatures you control get +1/+1 until end of turn.",
        name="Village Watcher // Howling Watcher",
    )
    assert "combat_boost" in roles


# --- Card name in the text ----------------------------------------------------------------


def test_rn12_tilde_as_card_name_works_like_the_name():
    """RN-12: "~" standing for the card's name is matched like the name itself."""
    with_name = _tag("Creature — Bird", "Flying\nWhen Pagewing Owl enters, draw a card.", name="Pagewing Owl")
    with_tilde = _tag("Creature — Bird", "Flying\nWhen ~ enters, draw a card.", name="Pagewing Owl")
    assert with_name == with_tilde == ["card_draw", "evasion"]


def test_rn12_card_name_that_looks_like_an_effect_creates_no_role():
    """RN-12: a card's own name inside its rules text is not read as an effect."""
    roles = _tag(
        "Creature — Spirit",
        "When Draw a Card, the Wanderer dies, you gain 3 life.",
        name="Draw a Card, the Wanderer",
    )
    assert roles == ["life_gain"]


def test_rn12_card_name_that_reads_like_a_board_wipe_creates_no_role():
    """RN-12: a name such as "Destroy All Creatures Golem" in its own text creates no board wipe."""
    roles = _tag(
        "Artifact Creature — Golem",
        "Destroy All Creatures Golem can't block.",
        name="Destroy All Creatures Golem",
    )
    assert roles == []


# --- Reminder text ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("type_line", "text"),
    [
        ("Creature — Spirit", "(Whenever you cast a spell, draw a card.)"),
        ("Instant", "(Destroy target creature. You gain 3 life.)"),
        ("Artifact", "({T}: Add one mana of any color.)"),
        ("Creature — Bird", "(This creature can't be blocked.)"),
    ],
    ids=["draw", "removal-and-life", "any-color-mana", "unblockable"],
)
def test_rn12_reminder_text_alone_creates_no_role(type_line, text):
    """RN-12: text inside parentheses (reminder text) on a non-land card creates no role."""
    assert _tag(type_line, text, name="Glimmer Wisp") == []


# --- Size ---------------------------------------------------------------------------------


def test_rn12_long_search_text_is_tagged_quickly():
    """RN-12: a search clause followed by a huge repeated word is tagged in bounded time."""
    text = "Search your library for " + "land " * 20000
    start = time.perf_counter()
    roles = _tag("Sorcery", text, name="Endless Survey")
    assert time.perf_counter() - start < 2.0
    assert isinstance(roles, list)


def test_rn12_huge_text_is_tagged_quickly():
    """RN-12: a very long rules text is tagged in bounded time, and a match at its end still counts."""
    filler = "Nothing of note happens here, and the story goes on. " * 2000  # about 100,000 characters
    start = time.perf_counter()
    assert _tag("Legendary Enchantment", filler, name="Endless Saga") == []
    assert _tag("Legendary Enchantment", filler + "\nDraw a card.", name="Endless Saga") == ["card_draw"]
    assert time.perf_counter() - start < 2.0
