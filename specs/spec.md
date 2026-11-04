# Spec: Card Factory

## Goal
Let a person generate custom Magic: The Gathering cards for Commander that are
valid under the rules, have a clear role in some strategy of the format, and sit
in a reasonable power range. The person adjusts the final result.

## Context of use
Card Factory is a free, open-source application that runs on the person's own
computer. The person downloads it, sets a language model provider (OpenAI,
Anthropic or Google), a model and their own API key in a local configuration
file, and starts it. The person pays the provider directly for usage.

## Out of scope
- Art generation, commanders, "a card for my deck", export to other programs
- User accounts, login, billing, hosting on a network
- Automatic updates of the card database

## Concepts
- Support card: an ordinary card of a deck that is not the commander.
- Color identity: the set of colors of the mana symbols in a card's cost and
  text, as defined by the game rules for Commander.
- Comparable: an existing card, legal in Commander, used as a reference.
- Power level: casual, medium or strong. Chooses which comparables serve as
  the reference.
- Design intent: the role of the card (for example ramp, removal, card draw)
  and the Commander strategy it supports.
- Power range: the expected interval of power for similar cards.

## Entities
- Provider configuration: provider, model and key, read from the local
  configuration file at startup. The key is never stored by the application.
- Request: idea or theme, color identity, power level and, optionally, card language.
- Card: name, mana cost, mana value, type line, rules text, power and toughness
  (when applicable), rarity, design rationale, comparables used, power
  indicator and validation result.
- Card version: a previous state of a card, restorable.
- Usage record: provider, model, and input and output tokens of one generation.

## Business rules

### Data and sources
- RN-01: The card and rules database is built locally from the official sources,
  and the system records the date and origin of each source used.
- RN-02: The project repository contains no card data and no rules text.
- RN-03: Building the database is all or nothing: if interrupted, the database
  is not considered ready, and a new run rebuilds it without duplicating anything.
- RN-04: Only cards legal in Commander serve as comparables. Cards banned in
  Commander serve only as counterexamples of what is too strong, never as models.

### Provider and key
- RN-05: The provider (OpenAI, Anthropic or Google), the model and the API key are
  set in a local configuration file before the application starts. The
  interface has no field for the key.
- RN-06: The key is never written to a database, log, error message or response,
  is never sent to the browser, and is never committed to the repository.
- RN-07: For the same request, the system offers the same flow and the same
  result format with any provider.
- RN-08: At startup and before generating, the system checks the configuration.
  If the provider value is unknown, or the key or the model is missing, it names
  the setting to fix and creates no card. If the provider rejects the key or the
  usage limit, it states the cause and creates no card.
- RN-09: Each generation records provider, model, and input and output tokens,
  and the person can see this usage.
- RN-10: Provider failures (outage, usage limit, invalid response) become clear
  messages and never leave a card half-created.

### Generation
- RN-11: A request contains an idea or theme, a color identity, a power level and,
  optionally, a card language. The type is always a support card.
- RN-12: Before writing the card, the system defines the design intent and looks
  up relevant cards and rules.
- RN-13: Every generated card includes a design rationale and the list of
  comparables used.
- RN-14: No card is presented as approved without passing every validation.
- RN-15: A rejected card may go through at most one automatic revision. If it is
  still rejected, it is shown as rejected, with the causes.

### Validations
- RN-16: The card's color identity, considering cost and text, is within the
  requested identity.
- RN-17: The mana cost is well formed and the stated mana value matches it.
- RN-18: The type line uses only card types, supertypes and subtypes that exist
  in the game.
- RN-19: Every keyword ability or keyword action used exists in the game.
- RN-20: The text respects limits on the number of abilities and on length.
  [DECIDE the limits]
- RN-21: The card is not a copy of an existing card. [DECIDE the criterion]
- RN-22: The power indicator (too strong, in range, too weak) compares the card
  with similar cards by role, color and cost. [DECIDE what "in range" means]

### Use and editing
- RN-23: The person can edit any field of the card, and it is revalidated right
  away, without calling the provider.
- RN-24: Quick adjustments (stronger, weaker, cheaper, more expensive, simplify
  text) create a new version, also validated.
- RN-25: Every change creates a version, and earlier versions can be restored.
- RN-26: Cards are saved locally and can be listed, favorited and deleted.

### Installation and first run
- RN-27: The application starts with a single command. If a prerequisite is
  missing (for example the required Python version) or the configuration file
  does not exist, the command stops and says what is missing and how to fix it.
  [DECIDE which operating systems are supported]
- RN-28: On first start, if the reference database is not ready, the application
  tells the person and builds it, showing progress. The other screens are
  available only after it is ready.
- RN-29: The application runs entirely on the person's computer and is reachable
  only from it by default. Outgoing connections go only to the official data
  sources (during the build) and to the configured provider.

### Language
- RN-30: The interface is in English. The generated card text is in English by
  default, and the person can choose any language available in Scryfall. The
  request can be written in any language.
  [DECIDE how rules validation and keyword names work in non-English cards]

## Acceptance criteria
- CA-01 (RN-16): Given the requested identity green, when the draft has a blue
  symbol in its text, then it is rejected and the cause is stated.
- CA-02 (RN-17): Given the cost "two generic plus one green" (mana value three),
  when the stated value is four, then it is rejected.
- CA-03 (RN-18): Given a subtype that does not exist, then the card is rejected.
- CA-04 (RN-19): Given a keyword ability that does not exist, then the card is
  rejected.
- CA-05 (RN-05, RN-08): With no key configured, an unknown provider value or no
  model, the system names the setting to fix, creates no card and calls no
  provider.
- CA-06 (RN-06): The key does not appear in any response, log or error message,
  not even when the provider fails, and no response sent to the browser contains
  it.
- CA-07 (RN-03): With the download interrupted, the database is not marked ready,
  and a new run completes it.
- CA-08 (RN-01, RN-03): With the database ready, a new run downloads nothing again.
- CA-09 (RN-21): Given a card identical to an existing one, then it is rejected
  as a copy.
- CA-10 (RN-14): An invalid draft never appears as approved.
- CA-11 (RN-15): A card rejected twice is shown as rejected, with the causes,
  with no third attempt.
- CA-12 (RN-23): When the cost of an approved card is edited to an inconsistent
  value, revalidation rejects it right away, without using the provider.
- CA-13 (RN-25): When an earlier version is restored, the fields come back and
  the card is revalidated.
- CA-14 (RN-07): The same card returned by three test providers produces the same
  validation result.
- CA-15 (RN-10): When the provider returns an invalid response, the person sees a
  clear message and no card is saved.
- CA-16 (RN-09): Each generation records and shows the tokens used.
- CA-17 (RN-27): Given a missing prerequisite or a missing configuration file, the
  start command stops with a message that names the problem and the fix.
- CA-18 (RN-28): Given a first start with no database, the person sees a setup
  screen with progress, and after it finishes the normal screens work.
- CA-19 (RN-29): After the database is built, the only outgoing connections go to
  the configured provider.
- CA-20 (RN-29): By default, a request from another computer on the network is
  not served.
- CA-21 (RN-30): Given a request with no language chosen, the card text and the
  interface labels are in English, even if the request was written in another
  language.
- CA-22 (RN-30): Given a request with a chosen language, the card text is in that
  language and the interface labels stay in English.

## Screens
- First-run setup: database build with progress
- Status: provider, model and whether a key is configured (never the key), with
  a connection test
- Request: theme, color, power level and card language
- Result: card, rationale, comparables, power indicator and usage
- Library: saved cards, favorites and deletion
- Adjustments and versions: editing, quick adjustments and restoration

## Open questions
- What are the limits on abilities and text length? (RN-20)
- What is the criterion for considering a card a copy? (RN-21)
- What does "in range" mean for the power indicator? (RN-22)
- How does the system discover the role of existing cards in order to compare them?
- Which operating systems are supported? (RN-27)
- Is the model name required, or does each provider have a default? Is it free
  text, or checked against a list?
- If the source download fails, how many times does it retry?
- Can the person refresh the database later, and how?
- How are rules validated for cards in languages other than English (keyword
  names, type words), and which data does that need?
- Which license does the project use?