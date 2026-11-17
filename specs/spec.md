# Spec: Card Factory

## Goal
Let a person generate custom Magic: The Gathering cards for Commander that are
valid under the rules, have a clear role in some strategy of the format, and sit
in a reasonable power range. The person adjusts the final result. Optionally, the
system also generates the card image (art and frame), or the person uploads their
own image, and the person can start from an existing card as a base: it serves as
the template of the card image and as a design example for the new card. The
person can also make a custom art version of an existing card: the card's text
is kept exactly, and only the art is new. The person can also keep a
collection of the cards they own, build decks from existing and generated
cards, and print cards on sheets to cut.

## Context of use
Card Factory is free and open source and runs in two modes with the same
features, except where a rule says otherwise (RN-63). In local mode it runs on
the person's own computer: the person downloads a ready-to-use package from
the project's GitHub releases, or clones the repository, and starts it with a
double click. In hosted mode it is a public website on the project's domain,
used from a browser with a free account. In both modes the person sets a
language model provider (OpenAI, Anthropic or Google), a model and their own
API key on the Settings screen, optionally a separate image provider and key
for art, and pays the providers directly for usage. The project's GitHub
repository stays the download page, the user guide and the source code.

## Out of scope
- Export of generated cards to other card-design programs (saving or printing
  the card image is allowed, RN-44; deck and collection lists are exported,
  RN-83)
- Billing, paid features, advertising and telemetry
- Sign-in through other services (social login), and accounts in local mode
- Sharing cards, decks or collections with other people; see Future work
- Checking deck legality for formats other than Commander
- Buying, selling or trading cards, and price history
- Automatic updates of the application in local mode
- Ready-to-use packages for systems other than Windows
- Card languages other than English and Portuguese (Brazil)
- Generated cards with more than one face (split, adventure, double-faced, and
  Battle cards, which are double-faced); see Future work
- Custom art versions of cards with more than one face, or in Portuguese; see
  Future work

## Concepts
- Local mode: the application running on the person's computer, for one
  person, with no account.
- Hosted mode: the application running as a public website, where each person
  has an account.
- Operator: whoever runs the hosted application.
- Account: an email address and a password that identify one person in hosted
  mode. Everything a person saves belongs to their account.
- Signed-out visitor: a person using the hosted application without signing
  in.
- Settings: the provider, model and key values the person sets on the Settings
  screen (RN-71).
- Data sources: Scryfall (card data, prices and card images) and the
  Comprehensive Rules published by Wizards of the Coast. The community art
  source (MPCFill) is not a data source: nothing from it enters the reference
  database.
- Generated card: any single-faced card for a Commander deck, of any card
  type and supertype except Battle, including a commander, a legendary card, a
  planeswalker or a basic card. A planeswalker is legendary and has a starting
  loyalty; no other card has one.
- Color identity: the colors of the mana symbols in the card's mana cost and
  rules text, excluding reminder text, as defined by the Comprehensive Rules for
  Commander. A hybrid symbol counts all its colors; a Phyrexian symbol counts
  its color. An ability that defines the card's color (such as "This card is
  blue" or "is all colors") adds those colors. Generated cards have no color
  indicator. A request may ask for colorless (no color), which then has to be
  chosen explicitly.
- Reminder text: text in parentheses that explains a rule; it has no effect on
  the card.
- Exists in the game: defined in the Comprehensive Rules. Terms from un-sets,
  digital-only cards (such as Alchemy) and other non-tournament products do
  not exist for this purpose.
- Comparable: an existing card, legal in Commander, found by the text model in
  the reference database and used as a reference.
- Power level: casual, medium or strong. Chooses which comparables serve as
  the reference. Shown in the request with one line each: casual, fun and fair
  in a relaxed game, without efficient staples; medium, solid and synergistic,
  at home at a typical Commander table; strong, efficient and competitive,
  close to the best cards of its role.
- Generation effort: low, medium or high, chosen in the request. It sets how
  many related cards the text model is given and whether the result has design
  notes (RN-53).
- Design notes: an explanation of the concepts behind the card and the reasons
  for its design decisions, focused on flavor: how the name, the type line, the
  abilities and the numbers express the idea or the character.
- Advanced options: optional choices in the request that fix parts of the
  generated card: card types, supertypes, subtypes, mana value, power and
  toughness and starting loyalty.
- Rarity: common, uncommon, rare or mythic. A new card's rarity follows its
  power level: common for casual, rare for medium and mythic for strong.
- Card Factory set symbol: the project's own icon, drawn in the set symbol
  area of every generated image (beside the type line), in the color of the
  card's rarity.
- Existing character: a person, creature, place or object from any fiction or
  franchise, named in the idea.
- Design intent: the role of the card (for example ramp, removal, card draw)
  and the Commander strategy it supports.
- Power range: the expected interval of power for similar cards.
- Base card: an existing card chosen by the person. Its image is the template of
  the card image (same frame, colors and layout), and its name and rules text
  are a design example of an effect or strategy. In a custom art version, it is
  the card whose text is kept.
- Card with one face: a card the reference database holds with a single face.
  Split, adventure, flip, transform, modal double-faced, meld and Battle cards
  have more than one face.
- Custom art version: a card that keeps the name, mana cost, mana value, type
  line, rules text (the card's current Oracle text), power and toughness and
  starting loyalty of an existing card with one face, and the rarity of the
  chosen printing, with new art. They are copied once when the card is
  created; a later rebuild of the reference database does not change them.
  Copied values are kept as written, even outside the sets of RN-54, and the
  color indicator is not copied. The frame and layout are those of the
  printing unless the art description asks for others.
- Art: the image of a card. A generated image is a full card image: illustration
  and frame, with the card's name, mana cost, type line, set symbol, rules text
  and power and toughness drawn inside. An uploaded image is used as is.
- Image-capable provider: a provider that offers image generation. OpenAI and
  Google are image-capable; Anthropic is not.
- Data folder: in local mode, the folder that holds the database, the card
  images and the downloaded base card images. In hosted mode the operator's
  storage plays this role.
- Existing card: a card of the reference database. Printing: one release of an
  existing card (set and collector number).
- Custom card: a generated card or a custom art version from the person's
  library.
- Collection: the cards the person owns. Collection entry: one printing of an
  existing card, or one custom card, with a quantity.
- Deck: a named list of cards for a format. Deck entry: one copy of a card in
  a deck, with a category.
- Deck category: commander, companion, main, sideboard or maybeboard.
- Deck tag: a name and a color the person creates to group decks.
- In use and available: for a collection entry, in use is the number of deck
  entries linked to it, and available is the quantity minus in use, never
  below zero.
- Extras: tokens, emblems, planes and phenomena, dungeons, schemes,
  conspiracies, attractions and contraptions of the reference database, and a
  fixed list of markers (such as the monarch and the initiative). Extras
  appear only on the Extras screen and in the print queue: an extra is never
  a base card, a comparable or a match of an import.
- Print queue: the cards chosen for printing, each with a quantity.
- Print sheet: a page with cards at their real size (63 × 88 mm), to print and
  cut.
- Own art: an image the person uploads to show on a collection entry, a deck
  entry or a print queue item in place of the printing's image.
- Community art: an image of a card published by other people through the
  community art source (MPCFill).
- Reference refresh: replacing the reference database with a newer build from
  the data sources.
- Fast text model: an optional second model of the text provider, used for
  the steps that need less reasoning (RN-05).

## Entities
- Provider configuration: text provider, model and key; optionally, a fast
  text model, image provider, image model and image key; in local mode, the
  local port. In local mode it lives in the local configuration file; in
  hosted mode it lives in the person's browser (RN-72). Keys are never stored
  by the hosted application.
- Account (hosted mode): email address, password (never stored in a readable
  form) and creation date. In hosted mode every entity below except the
  source record and the base card image belongs to one account.
- Collection entry: the card (a printing, or a custom card), quantity, foil
  (yes or no), condition (near mint, slightly played, moderately played,
  heavily played or damaged), language, notes, own or community art (optional,
  one per face) and date added.
- Deck: name, format, description, tags, cover (a card of the deck, with
  position and zoom), creation and change dates.
- Deck entry: the deck, the card (a printing, or a custom card), category,
  foil, own or community art (optional, one per face) and the collection
  entry it uses (optional).
- Deck tag: name and color.
- Print queue item: the card (a printing, a custom card or an extra), the face
  when the card has more than one, quantity, own or community art (optional).
- An entry or item of an existing printing or extra keeps the data source's
  identifier of the printing and its last known name (RN-68).
- Source record: origin and date of each data source used in the build.
- Request: kind (new card or custom art version), idea or theme, color identity (one or more colors, or colorless),
  power level, generation effort and, optionally, advanced options, card language (English or Portuguese), base card (with the chosen printing and face), art requested (yes
  or no), art description and uploaded image. A request for a custom art
  version has only the kind, the base card (printing) and the art (RN-59).
- Card: the request it came from (kind, idea, requested color identity, power level,
  generation effort and advanced options; only the kind and the base card for
  a custom art version), name, mana cost, mana value, type
  line, rules text, power and toughness (when applicable), starting loyalty
  (planeswalkers only), rarity, language, design intent, design rationale,
  design notes (high effort only), comparables used, base card (when chosen), power indicator with its
  justification, art (when present) with its origin (generated or uploaded),
  artist credit, validation result (none for a custom art version), skipped checks (when any) and favorite
  mark. A custom art version has no design intent, rationale, design notes,
  comparables or power indicator.
- Card version: a previous state of a card, including its art, restorable.
- Base card image: the downloaded image of a chosen printing, kept for reuse.
- Usage record: one per provider call, linked to a card when one exists. For a
  text generation, provider, model, and
  input and output tokens; for an art generation, provider, model, number of
  images and image size; for both, the seconds the call took.

## Business rules

### Data and sources
- RN-01: The card and rules database is built locally from the data sources,
  and the system records, for each source used, its origin, the date the source
  published it and the date it was downloaded.
- RN-02: The project repository contains no card data, no rules text, and no
  card images or frames.
- RN-03: Building the database is all or nothing: if interrupted, the database
  is not considered ready, and a new run rebuilds it without duplicating anything.
- RN-04: Only cards legal in Commander serve as comparables. Cards banned in
  Commander serve only as counterexamples of what is too strong, never as models.

### Provider and key
- RN-05: The text provider (OpenAI, Anthropic or Google), its model and its API
  key are set in the local configuration file in v1 and, from v2, on the
  Settings screen (RN-71). Optionally, an image provider
  (OpenAI or Google), an image model and an image API key are set there too.
  The image key may be left empty when art uses the text provider, either
  because no image provider is set or because the image provider equals the
  text provider; the text key is then used. Model names are required free
  text, not checked against a list. Optionally, a fast text model is set: a
  model of the same text provider, used with the same key for the design
  intent step, including the search for related cards (RN-12), and for quick
  adjustments, including their power indicator (RN-24); the draft and the
  revision always use the main model. With no fast text model, every step
  uses the main model. In local mode the same values can also be set by
  editing the local configuration file.
- RN-06: No key (text or image) is ever written to a database, a log, an error
  message or a response, or committed to the repository. A key travels from
  the browser to the application only when the person saves it (local mode)
  or with a request that needs it (hosted mode), and never travels from the
  application to the browser. In local mode the keys are stored only in the
  local configuration file. In hosted mode the keys are stored only in the
  person's browser; the application keeps a received key in memory only until
  the job it started ends, and nowhere afterwards. A job interrupted by a
  restart of the hosted application fails as in RN-10, and its key is gone.
- RN-07: For the same request, the system offers the same text-generation flow
  and the same result format with any text provider. Art generation is available
  only with an image-capable provider: the image provider when one is set,
  otherwise the text provider when it is image-capable. Art also requires an
  image model setting. When art is not available, the art
  option is shown as unavailable, with the reason and the setting that enables
  it.
- RN-08: At startup and before generating, the system checks the configuration
  without calling any provider. If a provider value is unknown, or a required key
  or model is missing, it names the setting to fix and creates no card. Keys are
  tried only by the connection test on the Status screen and by a generation; if
  the provider rejects the key, the model name or the usage limit, the system
  states the cause, names the setting to fix when there is one (an unknown model
  names the setting of the rejected model), and creates no card. A model value that looks like
  a key (equal to a configured key, or starting the way provider keys start) is
  a setting to fix: it is never shown and never sent to a provider. In the
  configuration file, only a line that starts with # is a comment; text after a
  value on the same line is part of the value. Spaces and quotes around a value
  are ignored. A key (text or image) that still contains a whitespace character
  or the character # is a setting to fix, and the key is never shown. An
  ignored image key is not checked. The same checks apply to the image settings: a problem in
  them makes art unavailable and names the setting to fix, while text generation
  keeps working. Leaving the image settings empty only makes art unavailable,
  with the reason; it is not a setting to fix. An image setting that is set but
  invalid (an unknown provider, or one that is not image-capable such as
  Anthropic) is a setting to fix. An image key set with no image provider is
  ignored, and the Status screen says so. An image model set with no image
  provider while the text provider is not image-capable is ignored the same
  way, with a notice on the Status screen. The configuration file is read again
  each time the Status screen is opened and before each generation, so a fix
  takes effect without restarting; only the port takes effect at the next
  start, and the Status screen says so when it changed. The sentences of this
  rule about the configuration file apply to local mode. The same checks
  apply, in both modes, to the values saved on the Settings screen (RN-71)
  and to the fast text model, which follows the checks of a model. In hosted
  mode, a request that needs a provider and arrives without settings, or with
  settings that fail a check, is refused naming the setting to fix, with no
  provider call.
- RN-09: Each text generation records provider, model, and input and output
  tokens. Each art generation records provider, model, number of images and
  image size. Every provider call that consumes tokens or images is recorded,
  including failed generations and refused art, and each call is a separate
  record (a draft and its revision are two records). A refused art call is
  recorded with zero images. The person sees the usage of each card, with text
  and art shown separately. Calls not linked to a card (a failed generation,
  the connection test) are recorded but not shown. Each record also holds the
  seconds the call took, from sending the request to the end of the answer or
  of the failure, shown with the usage of the card.
- RN-10: Provider failures (outage, usage limit, invalid response) become clear
  messages and never leave a card half-created.

### Generation
- RN-11: A request contains an idea or theme, a color identity, a power level
  and a generation effort and, optionally, advanced options, a card language, a
  base card, and either a request for art with an optional art description or
  an uploaded image. The generated card may be of any card type and supertype
  allowed by Generated card, and has one face.
  The idea is at most 1,000 characters and the art description at most 500,
  counted as Unicode characters. A request for a custom art version follows
  RN-59 instead.
- RN-58: From a card's Result screen, the person can start a new request from
  that card's request: the Request screen opens with the idea, color identity,
  power level and generation effort of the card filled in, and the other fields
  at their defaults. From a custom art version, the Request screen opens as a
  custom art version request with its base card and printing filled in and the
  art fields at their defaults. Nothing is sent until the person sends it.
- RN-12: Before writing the card, the system defines the design intent. The text
  model then searches the reference database for cards related to the request (and
  to the base card, when chosen) and picks the comparables among them. The search
  returns only cards legal in Commander, plus banned cards marked as
  counterexamples (RN-04). Comparables cited by the text model that the search
  did not return as legal are discarded; a response left with no valid
  comparable is an invalid response (RN-10). The result shows the design intent.
- RN-13: Every generated card, except a custom art version (RN-60), includes a
  design rationale and the list of comparables used.
- RN-14: No card is presented as approved without passing every validation.
- RN-15: A rejected card may go through at most one automatic revision. If it is
  still rejected, it is saved and shown as rejected, with the causes. If the
  revision call fails (RN-10), the first draft is saved as rejected with its
  causes, and the cause of the failure, with its fixed message, is saved with
  that version and shown while it is the current version. A later version does
  not show it; restoring that version brings it back (RN-25). The revision
  returns every card
  field except the mana value (RN-17), the rationale, the comparables and the power indicator, which replace
  those of the draft; the design intent stays. Its comparables are checked as
  in RN-12. An invalid revision response counts as a failed revision call.
  With high effort, the revision also returns design notes, which replace those
  of the draft.
- RN-53: The generation effort sets how many related cards the text model is
  given to pick comparables from: at most 8 with low effort, 20 with medium and
  40 with high. Only high effort adds design notes to the result. Every effort
  follows RN-12 to RN-15, including the one automatic revision.
- RN-54: Each advanced option is optional. Their values:
  - card types, supertypes and subtypes that exist in the game (RN-18); Battle
    is not offered;
  - mana value: a whole number from 0 to 16;
  - power and toughness: whole numbers from 0 to 99, chosen together;
  - starting loyalty: a whole number from 1 to 99.
  Rarity is not an option: it follows the power level (Concepts).
  Power and toughness require Creature among the chosen types or a Vehicle or
  Spacecraft subtype; with no type chosen, the card must be a creature, a
  Vehicle or a Spacecraft. Starting loyalty requires Planeswalker among the
  chosen types, or no type chosen (the card must then be a planeswalker). A
  value outside these sets, or a combination that RN-17, RN-18 or Generated
  card would reject (such as an Instant with the subtype Elf, or a Land with a
  mana value above 0), is refused naming the field, before any provider call.
- RN-55: While a generation runs, the person sees which step is running:
  design intent, search for related cards, draft, validation, revision and,
  when art was requested, art.
- RN-56: A card may be based on an existing character named in the idea. A
  provider refusal of the text or of
  the art is shown as a refusal (RN-10, RN-32), with the options to edit the
  request or the art description, or to upload an image. The application sends
  the idea and the art description as the person wrote them and never rewrites
  them to get around a refusal.

- RN-50: A card generation, an art generation or a quick adjustment runs one
  at a time. While one runs, starting another is refused with a message that
  says one is already running. A running generation cannot be cancelled.
  In hosted mode the limit is per account: each account runs one at a time,
  and the running step shows again after a reload or on another device. The
  operator sets how many generations the hosted application runs at once;
  when that many are running, a new one is refused with a message that says
  the site is busy and to try again shortly. Nothing is queued.

### Validations
- RN-16: The card's color identity, considering cost and text, is within the
  requested identity. With a colorless request, any colored symbol outside
  reminder text rejects the card.
- RN-17: The mana cost is well formed. The mana value of every
  generated, revised, adjusted or edited card is computed by the application
  from the mana cost, as defined by the Comprehensive Rules (a custom art
  version keeps the copied value, RN-60); the text model is not asked for it, and a mana value
  is never a cause of rejection by itself (RN-57 compares the computed value
  with a chosen one). Symbols are
  the official mana symbols, written in the order used on printed cards: {X}
  (which may repeat), then at most one generic number, then {C}, then {S},
  then one group of colored, hybrid and Phyrexian symbols in any order among
  themselves. A card with no mana cost (such as a land) is
  accepted, has mana value 0 and is different from a cost of {0}. The cost {0}
  is written alone and never combined with other symbols, and a generic number
  has no leading zero.
- RN-51: No check compares a card's name with the names of existing cards. A
  generated, revised, adjusted or edited card may have the name of an existing
  card or of one of its faces.
- RN-57: A generated draft and its revision match every advanced option chosen
  in the request: the chosen card types and supertypes are the card's only
  ones, the chosen subtypes are among its subtypes (others may be added), and
  the chosen mana value, power, toughness and starting loyalty are the
  card's. Each difference is a cause. Manual edits, quick adjustments and
  restores are not checked against the advanced options. In every check, a
  card with the Battle type is rejected, a planeswalker that is not legendary
  or has no starting loyalty is rejected, and a card that is not a planeswalker
  and has a starting loyalty is rejected.
- RN-18: The type line uses only card types, supertypes and subtypes that exist
  in the game. Card types are limited to those a Commander deck can contain.
  Each subtype must belong to one of the card's types, as the Comprehensive
  Rules define (for example, "Instant — Elf" is rejected).
- RN-19: Every keyword ability or keyword action used exists in the game.
  Keywords are read from the rules text only, so that edited cards are checked
  the same way as generated ones, and reminder text is ignored.
  - A keyword ability is a term at the start of a line, alone or in a
    comma-separated list, with its parameter when it has one (a cost, a number,
    "from …", "for …", "with …" or an object, as in "Protection from red" or
    "Equip—Pay 3 life").
  - In the middle of a sentence, a word directly followed by a number (as in
    "scry 2") must be a keyword action or a word that existing cards use the
    same way (as in "deals 3 damage"). An invented action with no number cannot
    be told apart from ordinary words and is not checked.
  - A term before a dash at the start of a line is an ability word. An ability
    word that does not exist in the game is accepted only when the person asked
    for it: it appears in the idea of the request, or the person wrote it in a
    manual edit.
  - A loyalty ability starts a line with its cost ("+1:", "−2:", "0:"); the
    cost is not a keyword, and the rest of the line is read as any other line.
- RN-20: The text respects limits on the number of abilities and on length.
  [DECIDE the limits]
- RN-21: Removed.
- RN-22: The power indicator (too strong, in range, too weak) is assessed by the
  text model, by comparing the card with the comparables it found by role, color
  and cost, and comes with a short justification that cites them. It is an
  assessment, not a validation: it never blocks approval.

### Art
- RN-31: Art is generated only when the person asks for it, in the request or
  later for an existing card. It is generated after the card text, from the
  card (name, mana cost, type line, rules text, power and toughness or starting
  loyalty, color identity, design intent and the artist credit) and the optional art description written by the person. Without
  a base card, the image model chooses a frame that fits the card's color
  identity and type. The card text shown beside the image is the card's authoritative text;
  the text drawn inside the image is not validated.
- RN-32: Art generation is a separate step that starts after the card is saved,
  for approved and rejected cards alike. Art requested in the request (generated
  or uploaded) belongs to the card's first version, so the person receives the
  complete card (layout, text and art) as one result; art generated or uploaded
  later creates a new version. If it fails (outage, usage limit,
  content-policy refusal, invalid response, timeout), the card stays saved
  without art, the person sees the cause,
  and can retry art generation alone. No partial image is saved.
- RN-33: Generated images are received by the application and stored in the
  data folder with the card. The browser loads images of custom cards and own
  art only from the application. Images of existing printings and extras, in
  lists, decks, the collection and the print queue, are loaded by the browser
  from the data source's image service, and community art from the community
  art source's image hosts; the application copies neither into its storage,
  except the base card image of RN-39. The browser loads no font, script or
  style sheet from outside the application; fonts installed on the
  computer may be used, and links the person follows are not loads.
  Deleting a card deletes the images of all its versions.
- RN-34: Editing fields and quick adjustments keep the current art and never
  call the image provider. After such a change, the Result screen notes that the
  image may show outdated text until new art is generated. Generating new art
  for an existing card creates a new version, and restoring a version restores
  the art it had.
- RN-35: Before art is generated, the interface states that art is billed by
  the image provider, separately from text.
- RN-43: The person can upload their own image as the art of a card, in the
  request or later. Uploading needs no image provider, calls no provider and
  records no usage. Only PNG, JPEG and WebP files up to 10 MB are accepted,
  checked by content and not only by extension; any other or unreadable file is
  refused with the reason. An image chosen in the request is checked when it is
  chosen, before the request is sent. If no card is saved, the image is not kept
  and the person is told; if the card is saved but the image cannot be stored,
  the card stays without art and the person sees the cause. An uploaded image
  is used as is and is stored like generated art (RN-33); in the request it
  belongs to the first version, and later it creates a new version (RN-32).
- RN-44: Generated images are requested in the smallest portrait size the
  provider offers with at least 745 × 1040 pixels and, among those, the one
  closest to the proportions of a card (63 × 88 mm); when no size reaches
  745 × 1040, the largest portrait size. That is enough to print at card size at
  300 dpi.
  Images, generated or uploaded, are stored unchanged and shown fitted into a
  card-shaped area close to the card images on Scryfall, without distortion and
  without cropping. The person can open the image at full resolution to save or
  print it. An uploaded image smaller than 745 × 1040 pixels is accepted with a
  notice that print quality may be low.

### Base card
- RN-36: The person can choose a base card by searching the reference database by
  name, and then picks one printing. Any card in the database can be a base,
  including cards banned in Commander and legendary cards. For a card with more
  than one face, the person picks the face. Extras are not offered. Search is
  available only when the database is ready.
- RN-37: The base card is a design example: its name and rules text are given to
  the text model, and the new card may pursue a similar effect or strategy, with
  any type. The color identity comes from the request, not from the base card.
  The design rationale states what was taken from the base card.
- RN-38: When art is requested with a base card, the image of the chosen
  printing is the template: the image model produces a card image with the same
  frame, colors and layout as the base card, new art, and the new card's name,
  mana cost, type line, rules text and power and toughness inside the frame.
  When the image model does not accept a template, the art is generated
  without it and the person is told, as in RN-39.
- RN-39: The image of a base card is downloaded from the data source only when
  the person chooses that printing, and is kept in the data folder for reuse. If
  the download fails (no network, source failure), the person sees the cause,
  the base card still works as a design example, and art is generated without
  the template, as in RN-31.

### Custom art versions
- RN-59: The person can ask for a custom art version instead of a new card.
  The request has the base card, chosen as in RN-36 except that only cards
  with one face are offered, and art: generated, with an optional art
  description, or uploaded (RN-43). Art is required: a request without it is
  refused naming the field, before any provider call. The idea, color
  identity, power level, generation effort, advanced options and card
  language are not asked; the card language is English. When art cannot be
  generated (RN-07), upload stays available.
- RN-60: A custom art version copies its fields as described in Concepts and
  calls no text model: it has no design intent, comparables, rationale,
  design notes or power indicator, and records only art usage. It runs no
  validation and is shown as a custom art version of its base card, neither
  approved nor rejected. Its only step is art (RN-55), and it counts as an art
  generation for RN-50. Saving, failure and retry of its art follow RN-32 and
  RN-43: when the first art fails, the card stays saved without art, still a
  custom art version, and art can be retried. The person cannot edit its text
  fields or run quick adjustments on it; generating or uploading new art,
  restoring a version, favoriting and deleting work as for any card.
- RN-61: The generated image of a custom art version uses the image of the
  chosen printing as the template (RN-38): same frame, colors, layout and card
  text, with new art that follows the art description, the artist line
  showing "Card Factory" (RN-48) and the Card Factory set symbol in place of
  the printing's set symbol (RN-62). When the art description asks for a
  different frame or layout (for example full art or borderless), the image
  model follows it, and the card text drawn inside stays the copied text. When
  the template cannot be used (RN-38, RN-39), the art is generated without it
  from the copied fields and the art description, and the person is told.

### Set symbol
- RN-62: Every generated image, with or without a base card and for custom
  art versions too, shows the Card Factory set symbol in the set symbol area
  beside the type line, in the color of the card's rarity: black for common,
  silver for uncommon, gold for rare and orange-red for mythic. The image
  model receives the symbol as an image. When the image model does not accept
  images as input, the art is generated with the symbol described in text and
  the person is told. Uploaded images are used as is (RN-43).

### Use and editing
- RN-23: The person can edit the text fields of the card: name, mana cost, type
  line, rules text, power and toughness, and starting loyalty. The mana value is
  recomputed from the edited cost. The card is revalidated right away, without
  calling the provider. Each saved edit creates one version. The power
  indicator and the design notes are kept and marked as possibly outdated
  until the next quick adjustment, which reassesses the power indicator.
- RN-24: Quick adjustments (stronger, weaker, cheaper, more expensive, simplify
  text) create a new version, also validated. A quick adjustment is a text
  generation: it records usage and reassesses the power indicator, but gets no
  automatic revision (RN-15). If it fails, the current version stays unchanged
  and the cause is shown.
- RN-25: Every change creates a version, and earlier versions can be restored.
  Restoring a version brings back its fields, art, power indicator with its
  justification and its possibly-outdated mark, and creates a new version.
  Restoring a version of a custom art version brings back its art and runs no
  validation (RN-60). Favoriting is not a change of
  the card and creates no version.
- RN-26: Cards are saved (in the data folder in local mode, in the person's
  account in hosted mode) and can be listed, favorited and deleted. Deleting
  a custom card that collection entries, deck entries or print queue items
  use names them first and, when confirmed, removes them with the card.
  Entries and items of a custom card always show and print its current
  version.

### Installation and first run
- RN-27: Local mode only. On Windows, the application is distributed as a zip file that contains
  everything it needs to run, including Python, the built interface and the
  configuration file with a comment for each setting. The person extracts it,
  fills in the configuration file and starts the application with a double
  click, without opening a terminal or installing anything else.
- RN-45: Local mode only. A person who clones the repository on Windows finds one start file.
  Double-clicking it prepares everything the application needs (with no other
  installation by the person) and then starts it as the zip does. Only the
  configuration file needs editing, from a template in the repository.
  - The built interface is downloaded from the project's GitHub release whose
    version equals the version recorded in the repository. If no release has
    that version (for example an unreleased commit), the start file says so and
    points to the latest release and to the development commands.
  - Preparation is all or nothing: if interrupted or failed, nothing is marked
    prepared, and the next run tries again.
  - Each run prepares only what is missing or does not match the current
    version, so a run after updating the clone downloads only what changed, and
    a run with nothing changed downloads nothing.
  - Other systems run from the source code with the development commands.
- RN-46: The README has a user guide that explains, for the zip and for a clone,
  how to fill in every setting on the Settings screen and in the
  configuration file, including the fast text model, the image
  provider, the image model with an example value per image-capable provider,
  the image key and the local port.
- RN-40: Local mode only. If the application cannot start (started from inside the zip without
  extracting, folder without write permission, configuration file missing, local
  port in use by another program), it shows a window with a message that names
  the problem and the fix. Problems with the values in the configuration file do
  not block startup: the interface opens on the Status screen and names the
  setting to fix. The configuration file is read as UTF-8 or as Unicode text
  (UTF-16 with a byte-order mark, as Notepad offers); a stray character that is
  not valid UTF-8 does not discard the file. A configuration file that exists
  but cannot be read, or cannot be read as text (such as UTF-16 without a
  byte-order mark), does not block startup either: the Status screen names the
  configuration file and the fix (check its permissions, or save it as UTF-8),
  and lists no other setting to fix and no port change while it cannot be read.
- RN-47: Local mode only. The application listens on a fixed default port rarely used by other
  programs, which the configuration file can change. An invalid port value is
  replaced by the default port, and the Status screen names the port setting.
  Spaces and quotes around the value are ignored. A missing or empty port value
  means the default port and is not a setting to fix. A valid value is a whole
  number from 1 to 65535 written only with the digits 0 to 9, leading zeros
  allowed; any other value is invalid. If a Card Factory started from the same
  folder is running, RN-41 applies, even when the port setting changed since it
  started. If the port is in use by another program, the message names the port
  and the setting that changes it; when that program is a Card Factory started
  from another folder, the message says so.
- RN-41: Local mode only. Starting the application opens the interface in the default browser.
  Starting it again from the same folder while it runs opens a new tab of the
  running instance. The
  application stops on its own within four minutes after the last tab is
  closed; reloading a page or leaving a tab in the background does not stop it
  while the browser keeps the tab running. If no tab connects within two
  minutes of starting, the application stops. While the database build, a card
  generation, an art generation or a quick adjustment runs, the application
  does not stop when the last tab closes; it stops within four minutes after
  the last of them ends with no tab open. An open tab whose application has
  stopped says so and explains how to start it again. Work in progress when it stops follows
  RN-03 and RN-10.
- RN-42: Local mode only. A new version is installed by extracting the new zip and copying the
  data folder and the configuration file from the previous folder, as the user
  guide describes. A new version started with the data folder of an older one
  keeps every saved card, version and image, and upgrades the stored data
  automatically. An older version started with the data folder of a newer one
  does not start and says so. A failed upgrade leaves the stored data as it was.
  When a new version needs reference data the database does not have (such as
  a new data source), the reference database is not ready (RN-28) on every
  start until the rebuild succeeds; saved cards are kept and become available
  again after it. Until then, the earlier reference data is not used.
- RN-28: Whenever the reference database is not ready (on first start, or after
  a new version that needs new reference data, RN-42), the Setup
  screen opens first and tells the person; when settings need fixing, it also
  says so and links to Status. The other screens, except Status and, from v2, Settings, are available
  only after the database is ready. The Setup screen states the expected
  download size, as reported by the data source, and the free disk space needed
  on the drive that holds the data folder. The build starts only when the
  person starts it, and shows progress. It refuses to start when there is not
  enough free space. When the data source cannot be reached, the screen shows
  the cause and a retry. A failed download is tried again automatically up
  to three attempts in all, with a short pause between them, before the build
  fails with its cause. If the disk
  fills up during the build, the build fails as in RN-03 and the person sees
  the cause. In hosted mode there is no Setup screen: the operator builds the
  reference database. While it is not ready, every screen that needs it shows
  a notice that the site is being prepared, and the other screens keep
  working.
- RN-29: In local mode the application runs entirely on the person's computer
  and is reachable only from it. In both modes, outgoing connections from the
  application go only to the data sources (to build and refresh the reference
  database, and to download the image of a chosen base card printing), to the
  providers the person configured and, in hosted mode, to the service that
  sends account emails. The application never contacts the community art
  source, unless the open question of RN-91 is answered with a way to do it. The start file of a clone also downloads,
  when preparing, Python and the dependencies from their official distribution
  sources, and the built interface from the project's GitHub releases.

### Modes and accounts
- RN-63: The application has the same rules in local and hosted mode, and the
  same screens except Home, Sign in, Create account, Account, Privacy and
  Terms (hosted mode) and Setup (local mode). The differences are the rules and sentences marked "hosted mode" or
  "local mode". In local mode there is no sign-in and every screen is open.
- RN-64: Hosted mode. A person creates an account with an email address and a
  password of at least 10 characters, signs in, signs out, changes the
  password and asks for a password reset by email. An account is free.
  Creating an account with an email already in use is refused saying so. The
  messages for an unknown email and a wrong password at sign-in are the same,
  and asking for a reset answers the same way whether or not the email has an
  account. A reset link works once and for one hour. A password change or
  reset ends the person's other sessions. After 10 failed sign-in attempts
  for one email within 15 minutes, further attempts for it are refused for 15
  minutes. The operator sets how many accounts one network address may create
  per day.
- RN-65: Hosted mode. Everything a person saves (cards, versions, images,
  usage records, collection, decks, deck tags, print queue) belongs to their
  account. Nobody else can list, open, change or delete it; a request for
  another account's item is answered as if the item did not exist.
- RN-66: Hosted mode. A person can delete their account. Deleting asks for
  the password, removes the account and everything that belongs to it,
  including images, and cannot be undone. The Account screen offers the
  backup (RN-85) before the deletion.
- RN-67: Hosted mode. Each account has limits, shown on the Account screen
  with the current use: saved cards, stored images in megabytes, decks,
  entries per deck, collection entries and print queue items. An action that
  would pass a limit is refused naming the limit, before any provider call.
  [DECIDE the limits]
- RN-92: Hosted mode. A signed-out visitor can open Home, Privacy, Terms and
  Status, search the existing cards and extras of the reference database, and
  open Sign in and Create account. Every other screen asks to sign in and
  returns to the requested screen afterwards.
- RN-93: Hosted mode. The application stores about a person only the account
  email, the password in a non-readable form, what the person saves and, for
  a limited time, what sign-in protection and operation need (failed
  attempts, reset requests, access logs). The Privacy screen, linked from
  every screen, says what is stored and for how long, that provider keys are
  not stored, and how to delete the account.
- RN-81: Hosted mode. A new version deployed by the operator keeps every
  account's data and upgrades it automatically; a failed upgrade leaves the
  stored data as it was. While a new version needs reference data the
  reference database does not have, the notice of RN-28 is shown.

### Reference database refresh
- RN-68: The reference database can be refreshed with newer data from the
  data sources. In hosted mode a refresh runs on its own at least once a
  week, and Status shows the date of the last one and the cause of a failed
  one. In local mode the person starts it from the Status screen, which shows
  the expected download size and the free disk space needed first; it
  refuses to start without that space, and RN-41 treats it as a database
  build. During a refresh the current reference database stays in use; it is
  replaced only when the new build is complete, and a failed or interrupted
  refresh leaves it as it was (RN-03) and shows the cause. A generation that
  started before the replacement finishes with the data it started with. A
  refresh changes no saved card, collection entry, deck entry or print queue
  item. An entry or item whose printing no longer exists after a refresh
  stays listed with its last known name, marked as no longer in the reference
  database.

### Settings
- RN-71: The Settings screen has the text provider, the text model, the fast
  text model, the text key, the image provider, the image model, the image
  key and, in local mode, the local port, each with a label and one line that
  says what it is for and, for a key, where to get one. A key field never
  shows a saved key: it shows only whether a key is set, and lets the person
  replace or remove it. A key being typed is hidden unless the person asks to
  see it. Saving runs the checks of RN-08 and RN-47 on the fields that
  changed; a value with a line break or a control character, or an invalid
  port, fails the check. When a field fails, the save is refused naming the
  field and nothing is saved. The connection test is offered on this screen
  too and tests the saved values.
- RN-72: In local mode, saving the Settings screen writes the values to the
  local configuration file, keeping its comments and every other line, and a
  value edited by hand in the file shows on the screen the next time it
  opens. A missing file is created from the template. When the file cannot be
  read or written the save is refused with the cause, and a failed save
  leaves the file as it was. Only the application's own screens can save
  settings. In hosted mode the values are kept in the person's browser only,
  either until the browser is closed or remembered on that device, as the
  person chooses (until the browser is closed is the default); they are sent
  with each request that needs a provider (RN-06). Signing out, a different
  account signing in, or deleting the account removes them from the browser.
  The hosted Status screen does not show a person's settings. The Settings
  screen says where the keys are kept in the current mode.
- RN-94: When a generation is requested with no text provider, model or key
  set, the Request screen
  says so and links to the Settings screen; nothing is sent.

### Collection
- RN-73: The person adds a card to the collection by searching the reference
  database by name and picking a printing, or by picking a custom card from
  the library, with a quantity from 1 to 999 and foil yes or no. Adding a
  card that equals an existing entry (same printing or custom card, same foil
  and same art) adds to its quantity, up to 999. The person can change an
  entry's quantity, foil, condition, language, notes and art (RN-90), and
  delete entries, one or several at once. Deleting an entry that deck entries
  use keeps the deck entries, no longer linked.
- RN-74: The collection is listed as a list, a compact list or a grid, with:
  search over name, type line and rules text; a color filter with two
  readings (exactly these colors, or within this color identity), multicolor
  and colorless; an availability filter (all, available, in use); and sorting
  by name, quantity, available, mana value, set, rarity or price. Each entry
  shows its quantity, in use and available, and the decks that use it. Totals
  show the number of cards, available and in use.
- RN-95: The price of an existing printing is the US dollar price in the
  reference database (the foil price for a foil entry), shown with the date
  of the reference database. A printing without a price, and every custom
  card, shows no price and counts as zero in totals.

### Decks
- RN-75: A deck has a name (1 to 100 characters), a format (Commander, Brawl,
  Standard, Modern, Pioneer, Pauper, Legacy, Vintage or Casual), an optional
  description (up to 2,000 characters), tags and a cover. Each copy of a card
  is one deck entry with a category, so each copy can have its own printing
  and art. The person adds cards by searching the reference database (with a
  printing), from the library (custom cards) or from the collection, changes
  an entry's category, printing and art, removes entries (one or several),
  and duplicates or deletes a deck. A deck may contain cards the person does
  not own, and adding a card to a deck never adds it to the collection; the
  person can add a deck's missing cards to the collection with one action.
- RN-76: A deck entry may be linked to a collection entry of the same
  printing or custom card and the same foil; the link is what counts as in
  use. Adding a card to a deck links it to the oldest available such entry
  when one exists, and otherwise leaves it unlinked. Changing the printing or
  foil of either side drops the link. The deck shows how many of its cards
  are owned and how many are missing.
- RN-77: In a Commander or Brawl deck the commander category holds one card,
  or two when the pair is allowed by the rules for two commanders (both have
  partner; partner with each other; both have friends forever; a commander
  with "choose a background" and a Background; a Doctor and a card with
  doctor's companion). Moving a card to the commander category when it would
  break this is refused with the reason. The commanders are listed first.
- RN-78: A Commander deck shows deck checks, computed from the reference
  database and never blocking a save: the number of cards (100 with the
  commanders; companion, sideboard and maybeboard not counted); no card name
  other than a basic land, or a card whose text allows any number, appears
  more than once; every card's color identity is within the commanders'
  combined identity; no card is banned in Commander; the deck has a
  commander, and each commander can be one (a legendary creature, a card
  whose text says it can be your commander, or the second card of a pair of
  RN-77). A custom card is checked with its own fields; a generated card
  whose validation result is rejected is listed in the checks. Other formats
  show only the number of cards against 60, with no other check.
- RN-79: A deck shows statistics over its commander and main categories: the
  mana curve (lands left out), the distribution of colors (each color,
  colorless, multicolor, lands), of card types and of rarities, and the total
  price (RN-95). The collection shows the same statistics.
- RN-80: Deck tags have a name (1 to 30 characters, unique without regard to
  case) and a color from a fixed palette. The person creates, renames,
  recolors and deletes tags and puts any number on a deck; deleting a tag
  removes it from its decks. The deck list filters by tag and searches by
  deck name, commander name and description.

### Import, export and backup
- RN-82: The person imports a card list pasted as text into the collection, a
  new deck or an existing deck. Each line is an optional quantity (with or
  without "x"), a card name, and optionally a set code with or without a
  collector number in parentheses or brackets, and a foil marker ("*F*",
  "*E*", "[foil]", "(foil)" or the word foil at the end; each means foil).
  Lines that start with "//" or "#" and empty lines are skipped. A line that
  names a section (Commander, Companion, Deck or Main, Sideboard, Maybeboard)
  sets the category of the lines after it; categories are ignored when
  importing into the collection. Each line is looked up in the reference
  database only, among existing cards and never extras, in this order: set
  and collector number; the name within the set; the exact name, where the
  full name of a card with two faces and the name of its front face both
  match. A line with no printing, or whose printing is not found, gets the
  most recently released printing of the card. A name that only resembles a
  card is not found, and a line with a quantity above 999 is refused. Before
  anything is saved the person sees a report: the lines found, the lines
  whose asked printing was replaced and by which, and the lines not found or
  refused; the person then confirms or cancels. A list of more than 2,000
  lines is refused. Section names and card names in Portuguese are matched
  once the reference database holds them (RN-30).
- RN-83: The person exports a deck or the collection as a text list (with set
  and collector number, with names only, or in the form "quantity x name
  [set]"), as CSV or as JSON. A list exported with set and collector number
  and imported again yields the same cards, printings, quantities, foil marks
  and categories. Custom cards are exported by name with the marker
  "[custom]" and are skipped, and reported, by an import.
- RN-84: The person exports a picture of a deck: every card image on one
  page, smaller than print size, with choices of file type (PNG, JPEG or
  PDF), page shape (A4 upright, A4 sideways, 16:9 or square), grouping of
  equal cards with a count, the commanders highlighted, card names, the
  sideboard, and a title line. The picture is made in the browser; a card
  whose image cannot be read is drawn as a frame with its name, and the
  person is told which ones.
- RN-85: The person downloads a backup: one file with the collection, decks,
  deck tags, print queue and library (custom cards with their current version
  and its image). It contains no key and no account data. Restoring a backup
  shows the counts it holds and asks for a mode: replace (cards, versions,
  images, collection, decks, tags and queue are removed first; usage records
  stay) or merge (collection quantities of equal entries are added, decks and
  custom cards are added as new, equal tags are joined, and the screen says
  that merging the same backup twice adds its decks and cards twice). Links
  between deck entries and collection entries are kept. Restored images pass
  the checks of RN-43. A file that is not a backup, or whose backup format is
  newer than the application knows, is refused with the reason and changes
  nothing; a restore that fails midway changes nothing. In hosted mode a
  restore respects the limits of RN-67. [DECIDE the largest backup file
  accepted]

### Printing
- RN-86: The print queue receives cards from the library, the collection, a
  deck entry, a whole deck (commanders first, then the others by name) and
  the extras, each with a quantity from 1 to 99. Adding a whole deck to a
  queue that is not empty asks whether to replace or add. A card with two
  faces enters as two items, front and back. The queue is saved and can be
  reordered, changed and emptied.
- RN-87: The print sheet is A4 upright with nine cards per page (three by
  three), each exactly 63 × 88 mm, with no empty page and no card backs.
  Options: cut lines (on or off, color, thickness, style), corner crop marks,
  corner fill (black, white or none) and a header line; presets set them
  together. [DECIDE the presets and the values of each option, with the Print
  screen preview] The person prints the sheets from the browser or downloads
  them as a PDF whose cards measure 63 × 88 mm when printed at 100% scale;
  the screen says to print at 100% with no margins. The sheets and the PDF
  are made in the browser. A card whose image cannot be read prints as a
  frame with its name, and the person is told which ones.
- RN-88: Custom cards, and own art on any card, can be printed in both modes.
  Existing printings, extras and community art can be put in the print queue
  and printed in local mode only; in hosted mode those sources of the queue
  are not offered and such an item is refused, and the Print screen says
  that printing existing cards is available in the local application.
- RN-96: Every print sheet with a custom card or own art carries, outside the
  cards, the line "Custom cards. Not for sale."

### Extras and art
- RN-89: The Extras screen lists the extras by kind (tokens, emblems, planes
  and phenomena, dungeons, schemes, conspiracies, attractions and
  contraptions, markers), with search by name and type, a color filter, and a
  grid or list view. An extra can be added to the print queue (RN-88).
  [DECIDE the list of markers and how each is shown, with the Extras screen
  preview]
- RN-90: For a collection entry, a deck entry or a print queue item of an
  existing card, the person can change the art to: another printing of the
  same card, chosen from all its printings with filters and sorting (release
  date, price, set name, artist); own art, uploaded under the checks of
  RN-43; or community art (RN-91). For a card with two faces each face is
  chosen separately. Own art and community art are shown and printed as given
  and are never presented as an official printing: the entry is marked as
  custom art. [DECIDE the printing filters, with the art selection preview]
- RN-91: Community art comes from MPCFill in three ways: the person imports
  an order file exported from MPCFill (its cards go to the print queue, to a
  new deck, or both in local mode, and to a new deck only in hosted mode,
  matched to existing cards by name as in RN-82); the person pastes the link
  or identifier of one image, accepted only for MPCFill's own image hosts; or
  the person searches the community art of a card by its exact name, with a
  minimum resolution filter. The application stores only the reference to a
  community image, never the image. A notice says community art belongs to
  its authors and is not provided by Card Factory. The search is delivered
  only when the open question about MPCFill is answered with a way its
  operators allow; the order file and the pasted link do not depend on it.

### Legal notice and accessibility
- RN-69: Every screen shows, in its footer, the fan content notice with the
  exact text the maintainer provides and a link to the source code; in hosted
  mode, also links to Privacy and Terms. The hosted application asks for no
  payment, survey or subscription to use any feature.
- RN-70: Wherever the image of an existing printing is shown, it is shown
  whole and unaltered (not cropped, recolored or covered), except the cover
  of a deck, which shows part of the art with the artist's name beside it,
  and the corner fill and marks of a print sheet. A custom card is always
  marked as a custom card wherever it is listed with existing cards
  (collection, decks, print queue, deck picture).
- RN-48: The artist credit of every card is "Card Factory". Generated images
  draw it in the artist line, and the Result screen shows it with the card
  text.
- RN-49: Every screen is usable with the keyboard alone; every field has a
  label; every image has a text alternative; keyboard focus is always
  visible; text meets WCAG 2.1 AA contrast.
- RN-52: Each screen of the interface sets the browser tab title to the name
  of the screen shown, a space, a middle dot (·), a space and "Card Factory".
  Screen names: Home, Sign in, Create account, Account, Settings, Setup,
  Status, Request, Result, Library, Versions, Collection, Decks, Deck,
  Extras, Print, Import and export, Privacy, Terms. Before a
  screen is shown, the title is "Card Factory"; it does not change when the
  application stops. The tab shows the application's own icon, not a
  framework default.

### Language
- RN-30: The interface is in English. The generated card text is in English by
  default, and the person can choose Portuguese (Brazil) instead. The request
  and the art description can be written in any language. Cards in both
  languages, except custom art versions (RN-60), go through every validation, with type words and keyword names
  checked against the official terms in that language. When the official
  Portuguese term of a keyword is not known to the database, a Portuguese card
  may use the keyword's official English name; that keyword check is skipped
  and the result names it. Any other unknown term is rejected.

## Acceptance criteria
Criteria marked "manual" are checked by hand on Windows, because automated tests
never use the network or a real provider. Criteria about the configuration
file, the zip, the start file or the port apply to local mode.

- CA-01 (RN-16): Given the requested identity green, when the draft has a blue
  symbol in its text, then it is rejected and the cause is stated.
- CA-02 (RN-17): Given a draft with the cost "two generic plus one green", the
  saved card has mana value three, and the text model was not asked for a
  mana value.
- CA-03 (RN-18): Given a subtype that does not exist, then the card is rejected.
- CA-04 (RN-19): Given a keyword ability that does not exist, alone on a line or
  inside a comma-separated list ("Flying, Glorpstrike"), then the card is
  rejected; "Protection from red" and "Equip—Pay 3 life" are accepted.
- CA-05 (RN-05, RN-08): With no key configured, an unknown provider value or no
  model, the system names the setting to fix, creates no card and calls no
  provider.
- CA-06 (RN-06): Neither the text key nor the image key appears in any response,
  log or error message, not even when a provider fails, and no response sent to
  the browser contains them, in either mode.
- CA-07 (RN-03): With the download interrupted, the database is not marked ready,
  and a new run rebuilds it with no duplicated records.
- CA-08 (RN-01, RN-03): With the database ready, a new run downloads nothing
  again, and the Status screen shows the origin, the publication date and the
  download date of each source.
- CA-09: Removed.
- CA-10 (RN-14): An invalid draft never appears as approved.
- CA-11 (RN-15): A card rejected twice is saved and shown as rejected, with the
  causes, with no third attempt. When the first draft is rejected and the
  revision call fails or its response is invalid, the first draft is saved as
  rejected and the failure is shown, also when the card is opened again later,
  until a new version is made. When the revision is used, its
  comparables and power indicator are the ones shown.
- CA-12 (RN-23): When the cost of an approved card is edited to a malformed
  value, revalidation rejects it right away, without using the provider. After
  a valid cost edit, the mana value is recomputed and one new version exists.
- CA-13 (RN-25): When an earlier version is restored, the fields, the power
  indicator and its possibly-outdated mark come back, the card is revalidated,
  and the restoration appears as a new version. Restoring a version of a
  custom art version brings back its art, runs no validation and appears as a
  new version.
- CA-14 (RN-07): The same scripted card, shaped as each provider's recorded
  response (OpenAI, Anthropic and Google), yields the same saved card and the
  same validation result.
- CA-15 (RN-10): When the provider returns an invalid response to the intent or
  draft call, the person sees a clear message and no card is saved.
- CA-16 (RN-09): Each text generation records and shows the tokens used. A
  generation that fails after the provider answered still records its usage,
  with no card, and a draft with its revision produces two records.
- CA-17 (RN-40, manual): Started from inside the zip, from a folder without write
  permission, or with no configuration file, the application shows a window that
  names the problem and the fix.
- CA-18 (RN-28): Given a first start with no database, the person sees a setup
  screen with the expected download size and can open the Status screen;
  nothing is downloaded until the person starts the build; the build shows
  progress, and after it finishes the normal screens work.
- CA-19 (RN-29): After the database is built, the only outgoing connections
  from the application go to the configured providers, to the data source
  when a base card printing is chosen (for that printing's image) or a
  refresh runs, and, in hosted mode, to the service that sends account
  emails.
- CA-20 (RN-29, manual): In local mode, a request from another computer on the network is not
  served, and starting the application triggers no firewall
  prompt.
- CA-21 (RN-30): Given a request with no language chosen, the card text and the
  interface labels are in English, even if the request was written in another
  language.
- CA-22 (RN-30): Given a request with a chosen language, the card text is in that
  language and the interface labels stay in English.
- CA-23 (RN-02): The repository contains no file with card data, rules text,
  card images or frame images.
- CA-24 (RN-04, RN-12): Given a card banned in Commander that matches the
  request, the search marks it as a counterexample and it never appears among
  the comparables.
- CA-25 (RN-08): When the provider rejects the key or reports the usage limit,
  the person sees that cause and no card is saved.
- CA-26 (RN-11): Given a request without an idea or theme, a color identity or a
  power level, it is not sent and the missing field is named. Colorless counts
  as a color identity only when chosen explicitly.
- CA-27 (RN-12, RN-13): Every generated card except a custom art version shows its design intent, its design
  rationale and the list of comparables used.
- CA-28 (RN-20): Given a text over the limit of abilities or of length, the card
  is rejected and the exceeded limit is named.
- CA-29 (RN-22): Every generated card except a custom art version shows a power indicator (too strong, in
  range or too weak) with a justification that cites at least one comparable,
  and a "too strong" indicator does not make the card rejected.
- CA-30 (RN-24): A quick adjustment creates a new validated version with a
  reassessed power indicator and a usage record, and the previous version can
  still be restored. When the quick adjustment fails, the current version is
  unchanged and the cause is shown.
- CA-31 (RN-25, RN-26, RN-33): A saved card is listed in the library after a
  restart, a favorited card is listed among the favorites with no new version, and a deleted card is listed
  nowhere and none of its images remain.
- CA-32 (RN-07): With Anthropic as text provider and no image provider set, the
  art option is unavailable with the reason and the setting that enables it, and
  no image request is made.
- CA-33 (RN-07): With Anthropic as text provider and an image provider set, art
  is generated by the image provider.
- CA-34 (RN-08): Startup makes no provider call. With an invalid image key, the
  connection test or the first art generation names the image key setting, and
  text generation still works.
- CA-35 (RN-09): Each art generation records and shows provider, model, number
  of images and image size, separately from the text tokens. A refused art call
  is recorded with zero images.
- CA-36 (RN-31): Given a request without art, no image request is made. Given a
  request with art and no base card, the image provider receives the card's name,
  mana cost, type line, rules text, power and toughness, color identity and the
  artist credit.
- CA-37 (RN-32): When art generation fails or is refused by content policy, the
  card stays saved without art, no image file is left, the cause is shown, and
  retrying art alone generates it without generating the text again. A rejected
  card with art requested also receives art.
- CA-38: Replaced by CA-126.
- CA-39 (RN-34): Editing a field or applying a quick adjustment keeps the art,
  makes no image request and shows the outdated-text notice. Generating new art
  creates a version, and restoring the earlier version restores the earlier art.
- CA-40 (RN-35): Before art is generated, the person sees that art is billed by
  the image provider separately from text.
- CA-41 (RN-36): Searching by part of a name lists the matching cards from the
  reference database without network access, including cards banned in Commander,
  and for a card with more than one face the person can pick the face.
- CA-42 (RN-37): Given a blue base card and a green request, the new card's
  identity is green, the text model receives the base card's name and rules
  text, and the design rationale states what was taken from the base card.
- CA-43 (RN-38): With a base card and art requested, the image provider receives
  the chosen printing's image as template, together with the new card's name,
  mana cost, type line, rules text and power and toughness.
- CA-44 (RN-39): With no network, choosing a base card printing shows the cause,
  the text model still receives the base card's name and rules text, and art is
  generated without the template. Once a printing's image is downloaded, using
  it again downloads nothing.
- CA-45 (RN-27, manual): On a Windows computer with no Python or Node installed,
  extracting the zip, filling in the configuration file and double-clicking the
  application opens the interface, with no terminal used.
- CA-46 (RN-40): With a missing key in the configuration file, the application
  starts and the Status screen names the setting to fix.
- CA-47 (RN-41, manual): Starting the application opens the browser. Starting it
  again opens a tab of the same instance. Closing the last tab stops the
  application within four minutes; reloading a page does not stop it. Closing
  the last tab during the database build or a generation does not stop it; it
  stops within four minutes after it ends. A tab left open after the
  application stopped shows that it stopped and how to start it again.
- CA-48 (RN-42): A new version started with the data folder and configuration
  file of an older version lists every saved card, version and image. An older
  version started with the data folder of a newer one refuses to start, and the
  data is unchanged.
- CA-49 (RN-43): Uploading a PNG image as art with no image provider set saves
  it as the card's art in a new version, with no provider call and no usage
  recorded. Uploading a text file renamed to ".png", or an image over 10 MB, is
  refused with the reason.
- CA-50 (RN-44): A generated or uploaded image is shown inside the card-shaped
  area with its whole content visible and its proportions kept, and opening it
  at full resolution returns the stored file unchanged. The size requested from
  the image provider has at least 745 × 1040 pixels when the model allows it.
  An uploaded 400 × 560 image is accepted with the print-quality notice.
- CA-51 (RN-45, manual): On a Windows computer with no Python or Node installed,
  a fresh clone with a filled configuration file starts with a double click on
  the start file, with no terminal used; a second start downloads nothing. A
  clone of a commit with no matching release shows a message that points to the
  latest release and to the development commands. A preparation interrupted
  midway is redone on the next run.
- CA-52 (RN-46): The README user guide covers every setting of the configuration
  file, for the zip and for a clone, including the image model with an example
  value for OpenAI and for Google.
- CA-53 (RN-47, manual): With the default port in use by another program, or by
  a Card Factory started from another folder, the application shows a window
  that names the port and the setting that changes it (and, for another Card
  Factory, says so); after changing that setting, it starts.
- CA-54 (RN-30): Given a Portuguese card with an unknown term where a keyword
  goes, it is rejected. Given a Portuguese card that writes, with its official
  English name, a keyword whose Portuguese term is not known to the database,
  the other checks run and the result names that keyword check as skipped.
- CA-55 (RN-23): After a manual edit, the power indicator is still shown, marked
  as possibly outdated, and no provider is called; a quick adjustment removes
  the mark.
- CA-56 (RN-12): Given a text model response that cites a comparable not
  returned by the search, or a banned card, that comparable is discarded; a
  response left with no valid comparable is handled as an invalid response.
- CA-57 (RN-16): Given a green request, a {G/U} hybrid symbol in the cost or in
  the rules text is rejected; a {U} symbol inside reminder text in parentheses
  is not.
- CA-58 (RN-48): Every image request asks for "Card Factory" as the artist
  credit, and the Result screen shows "Card Factory" as the artist.
- CA-59 (RN-49): Every screen can be operated with the keyboard alone, every
  field has a label, every image has a text alternative, and focus is
  visible; contrast is checked by hand.
- CA-60 (RN-28): Given less free disk space than the build needs, the setup
  screen names the space needed and the build does not start. When the disk
  fills up during the build, the database is not marked ready and the cause is
  shown.
- CA-61 (RN-43): Given a text file renamed to ".png" chosen as the image of a
  request, it is refused before the request is sent. Given a request with a
  valid uploaded image whose generation fails, no image file is left and the
  person is told the image was not kept.
- CA-62 (RN-16): Given a colorless request, a {G} symbol in the rules text is
  rejected and a {C} symbol is accepted.
- CA-63 (RN-19): In the middle of a sentence, "then glorp 2" is rejected and
  "deals 3 damage" and "scry 2" are accepted. Reminder text is not checked.
- CA-64 (RN-19): An ability word that does not exist in the game is rejected,
  unless it appears in the idea of the request or was written in a manual edit.
- CA-65 (RN-18, RN-19): A type that a Commander deck cannot contain (such as
  Scheme), a subtype that does not belong to the card's types, and a keyword
  that exists only on un-set or digital-only cards are rejected.
- CA-66 (RN-17): The cost {X}{2/W}{G/P} has mana value 3; a land with no mana
  cost is accepted with mana value 0; the cost {G}{2} is rejected for symbol
  order; the costs {2}{C}{S}{G}, {G}{U}, {U}{G} and {1}{G}{G/W}{W} are
  accepted; the cost {1}{1}{G} is rejected; the cost {0} is accepted with mana
  value 0; the costs {0}{G}, {X}{0}, {0}{C} and {00} are rejected.
- CA-67 (RN-05): With the image provider equal to the text provider and an empty
  image key, art uses the text key.
- CA-68 (RN-07): With an image provider set and no image model, art is
  unavailable and the image model setting is named.
- CA-69 (RN-32, RN-43): Given a request with art, the saved card has one version
  that holds the text and the art; generating or uploading art later adds a
  version.
- CA-70 (RN-41): While a card generation, an art generation or a quick
  adjustment runs with no tab open, the application does not stop; it stops
  within four minutes after the job ends.
- CA-71 (RN-38): With a base card and an image model that does not accept a
  template, art is generated without the template, the card gets the art, and
  the person is told the template was not used.
- CA-72 (RN-16): Given a green request, a card whose rules text says "This card
  is blue" is rejected for color identity.
- CA-73 (RN-08): After a missing key is added to the configuration file,
  reopening the Status screen shows no setting to fix and generation works,
  without restarting the application.
- CA-74 (RN-07, RN-08): With no image settings, art is unavailable with the
  reason and no setting to fix is reported; with the image provider set to
  Anthropic, the image provider setting is named as a setting to fix; with an
  image key and no image provider, the Status screen says the key is ignored;
  with an image model, no image provider and Anthropic as text provider, the
  Status screen says the image model is ignored.
- CA-75 (RN-47): With a port value that is not a number from 1 to 65535, the
  application starts on the default port and the Status screen names the port
  setting. With a missing or empty port value, it starts on the default port and
  no setting to fix is reported.
- CA-76 (RN-08): When the provider does not know the configured model name, the
  person sees that cause with the model setting named, and no card is saved.
- CA-77 (RN-40): Given a configuration file that cannot be read, or that cannot
  be read as text (such as UTF-16 without a byte-order mark), the application
  starts, the
  Status screen names the configuration file and the fix for that cause, no
  other setting to fix is listed, and no response contains any part of the
  file's content. After the file is fixed, reopening the Status screen shows
  its settings without a restart.
- CA-78 (RN-06, RN-08): Given a text or image model value equal to a configured
  key or starting the way a provider key starts, the Status screen names the
  model setting to fix, no response contains the value, and a generation calls
  no provider and creates no card.
- CA-79: Removed.
- CA-80 (RN-11): An idea of 1,000 characters is accepted and one of 1,001 is
  refused naming the field, with no provider call; the same holds for an art
  description at 500 and 501. The Request screen also stops the request
  before it is sent.
- CA-81 (RN-42, RN-28): Given a data folder whose reference database lacks
  data the new version needs, the Setup screen opens and says a rebuild is
  needed; after the rebuild every saved card, version and image is listed.
- CA-82 (RN-52): Each screen sets its title; given the database not ready,
  opening the Request address shows "Setup · Card Factory"; while readiness
  loads, the title is "Card Factory"; the built index.html links an icon
  served by the application. Manual: the tab shows the icon.
- CA-83 (RN-53): The text model is given at most 8 related cards with low
  effort, 20 with medium and 40 with high; only a high-effort result shows
  design notes.
- CA-84 (RN-54, RN-57): Given the options Creature, subtype Elf, power 2 and
  toughness 3, a 2/2 Elf Creature is rejected with the cause and a 2/3 Elf
  Warrior Creature is accepted. A request with power and toughness and the
  type Instant, power without toughness, a mana value of 17, or a Land with a
  mana value of 2 is refused naming the field, with no provider call.
- CA-85 (RN-55): While a generation runs, the Request screen names the running
  step, and the name changes as the steps advance.
- CA-86: Removed.
- CA-87 (RN-57): A planeswalker with no starting loyalty, a non-legendary
  planeswalker, a creature with a starting loyalty and a card with the Battle
  type are rejected with the cause.
- CA-88 (RN-56): Given a provider refusal of a card about an existing
  character, the refusal is shown with the options to edit the request and,
  for art, to edit the art description or upload an image; the provider
  receives the idea and the art description unchanged.
- CA-89 (RN-08): Given a text key followed on the same line by a space and a
  comment, the Status screen names the text key setting to fix without showing
  the key, and a generation or a connection test calls no provider and creates
  no card. Given an image provider set and an image key with a #, art is
  unavailable and names the image key setting, while text generation keeps
  working.
- CA-90 (RN-58): Given a saved card made from the idea "a squirrel that hoards
  artifacts", green, medium power and low effort, starting a new request from
  it opens the Request screen with those four values, the other fields at
  their defaults, and no generation started.

- CA-91 (RN-51): Given an existing card "Lantern Warden" and a two-faced card
  "Ember // Ash", a generated card named "Lantern Warden" or "Ash" is not
  rejected because of its name, and a manual edit to either name is saved.
- CA-92 (RN-59, RN-60): Given the card with one face "Lantern Warden" and a
  printing of rarity uncommon, a custom art version with generated art saves a
  card whose name, mana cost, mana value, type line, rules text, power and
  toughness equal the database's and whose rarity is uncommon, calls the image
  model once and no text model, records art usage only, and is shown as a
  custom art version with no validation result, design intent or power
  indicator; its text fields cannot be edited and quick adjustments are not
  offered. The two-faced card "Ember // Ash" is not offered. A request with no
  art is refused naming the field, with no provider call. When the art fails,
  the card is saved without art and art can be retried.
- CA-93 (RN-61): The image request of a custom art version sends the
  printing's image as the template, the copied fields, "Card Factory" as the
  artist credit and the art description unchanged. When the printing's image
  is missing, the art is generated without the template and the Result screen
  shows the notice. Manual: with "full art" in the art description, the image
  follows it.
- CA-94 (RN-62, Concepts): A casual, medium and strong request yield the
  rarities common, rare and mythic, and each image request carries the Card
  Factory set symbol with that rarity's color; a custom art version of an
  uncommon printing carries the silver symbol. With an image model that does
  not accept images as input, the symbol is described in text and the person
  is told.
- CA-95 (RN-71, RN-06): After a text key is saved on the Settings screen, no
  response contains it, the screen shows that a key is set, and the field is
  empty when the screen is opened again. Replacing and removing the key work
  without showing the earlier one. A key being typed is hidden until the
  person asks to see it.
- CA-96 (RN-72): In local mode, saving the Settings screen writes the values
  to the configuration file and keeps its comment lines; a model changed by
  hand in the file is shown the next time the screen opens; a generation
  after saving uses the new values without a restart. With no configuration
  file, saving creates it. With a file that cannot be written, the save is
  refused with the cause and the file is unchanged. A saved port takes effect
  at the next start, and the screen says so.
- CA-97 (RN-72, RN-06): After a generation in hosted mode, the key sent with
  it is in no database row, file, log line or response. Signing out, or
  signing in with another account, removes the settings from the browser.
  With "remember on this device" not chosen, the settings are gone after the
  browser is closed; with it chosen, they are still there. A job interrupted
  by a restart of the application is shown as failed.
- CA-98 (RN-08, RN-71): Saving a model equal to the key, a key with a space,
  an unknown provider, a value with a line break or the port 70000 is
  refused naming the field, and the earlier values stay. With an invalid
  image key already in the configuration file, changing only the text model
  is saved.
- CA-99 (RN-08, RN-94): The Request screen with no settings links to Settings
  and sends nothing. In hosted mode, a generation request that arrives with
  no key is refused naming the setting, with no provider call.
- CA-100 (RN-64): An account is created with an email and a 10-character
  password; a 9-character password and an email already in use are refused.
  A wrong password and an unknown email give the same message at sign-in.
  The eleventh failed attempt within 15 minutes is refused even with the
  right password.
- CA-101 (RN-65): Given two accounts, the second cannot list, open, change or
  delete a card, image, deck or collection entry of the first; each attempt
  is answered as not found.
- CA-102 (RN-66): Deleting an account with the right password removes its
  cards, images, decks and collection, and the email can sign in no more; a
  wrong password deletes nothing. The Account screen offers the backup beside
  the deletion.
- CA-103 (RN-92): A signed-out visitor can search existing cards and open
  Status; opening Library asks to sign in and returns to Library afterwards.
- CA-104 (RN-67): With the saved-card limit reached, a generation is refused
  naming the limit, with no provider call, and the Account screen shows the
  limit and the use.
- CA-105 (RN-63): In local mode no screen asks to sign in and no account
  exists.
- CA-106 (RN-68): During a refresh, a card search answers from the current
  reference database; after a refresh that fails midway, the earlier data and
  its dates are still shown, with the cause; after a successful one, the new
  dates are shown and saved cards, decks and collection entries are
  unchanged. A deck entry whose printing disappeared is still listed with its
  name, marked. In local mode, Status shows the download size before the
  refresh starts, and a refresh with too little free space does not start.
- CA-107 (RN-73): Adding the same printing twice with the same foil yields
  one entry with quantity 2; with different foil, two entries. A quantity of
  0 or 1,000 is refused.
- CA-108 (RN-74, Concepts): An entry of quantity 3 linked from 2 deck entries
  shows 2 in use and 1 available; the "available" filter lists it; the
  "exactly green" filter leaves out a green-white card that "within green and
  white" lists; sorting by quantity orders the entries by it.
- CA-109 (RN-95): A foil entry shows the foil price and the date of the
  reference database; a custom card shows no price and the total ignores it.
- CA-110 (RN-75, RN-76): Two copies of one card in a deck are two entries
  that can have different printings. Adding to a deck a card with one
  available collection entry links it; adding it again leaves the second
  unlinked, the deck shows one missing and the collection is unchanged.
  Adding the deck's missing cards to the collection adds that one.
- CA-111 (RN-77): Two commanders that both have partner are accepted, and so
  is a commander with "choose a background" beside a Background; a second
  commander without any such ability is refused with the reason.
- CA-112 (RN-78): A Commander deck with 99 cards, two copies of a nonbasic
  card, a card outside the commander's color identity and a banned card shows
  four checks naming the cards, and is saved all the same. Ten basic Forests
  raise no check. A rejected generated card is listed. A deck with no
  commander shows that check.
- CA-113 (RN-79): Given a fictional deck, the mana curve leaves out its lands
  and the color distribution counts a two-color card as multicolor.
- CA-114 (RN-80): Deleting a tag removes it from its decks; a second tag with
  the same name in another case is refused; the deck list finds a deck by its
  commander's name.
- CA-115 (RN-82): Given the lines "2x Lantern Warden (ABC) 12 *F*",
  "// note", "Sideboard" and "1 Unknown Card", the report shows two foil
  copies of that printing, a skipped line, and one line not found under
  Sideboard; nothing is saved until confirmed. A name that only resembles a
  card is not found, and a token is never matched. A line asking for a
  printing that does not exist names the most recent printing, used instead.
  The line "1000 Lantern Warden" is refused.
- CA-116 (RN-83): Exporting a deck with set and collector numbers and
  importing the file into a new deck yields the same entries. A custom card
  is exported with "[custom]" and reported as skipped on import.
- CA-117 (RN-85): Restoring a backup with "merge" into a collection that has
  the same entry adds the quantities; with "replace" only the backup's data
  remains. A text file that is not a backup is refused and nothing changes.
  The backup file contains no key. A backup of a newer format is refused, and
  a restore that fails midway leaves every row and file as it was.
- CA-118 (RN-86): Adding a deck to the queue lists its commanders first; a
  two-faced card adds a front and a back item.
- CA-119 (RN-87): Ten queued cards produce two pages, nine and one; each card
  area of the PDF measures 63 × 88 mm. Manual: a printed sheet measures
  63 × 88 mm per card at 100% scale.
- CA-120 (RN-88): In hosted mode an existing printing, an extra and a card
  with community art cannot be added to the print queue by any request, and
  a generated card can. In local mode all of them can.
- CA-121 (RN-96): A sheet with a custom card carries the line "Custom cards.
  Not for sale."
- CA-122 (RN-89, RN-36): The Extras screen lists a fictional token under
  tokens and finds it by type; the base card search does not offer it.
- CA-123 (RN-90): Changing the printing of one deck entry leaves the other
  copy unchanged. A text file renamed ".png" is refused as own art. An entry
  with own art is marked as custom art.
- CA-124 (RN-91): Importing a fictional order file adds its cards to the
  queue with their quantities in local mode and to a new deck in hosted
  mode, and the application stores the image references only. A pasted link
  to another host is refused. Manual: a pasted image link shows the image.
- CA-125 (RN-69, RN-70): Every screen shows the fan content notice and the
  link to the source code; in hosted mode every screen links to Privacy and
  Terms. A custom card in a deck list is marked as custom.
- CA-126 (RN-33): The built interface references no outside address for
  fonts, scripts or style sheets (a small icon inlined in the page counts as
  local), and images come only from the application, the data source's
  image service and the community art source's image hosts.
- CA-127 (RN-50): In hosted mode two accounts can each run one generation at
  the same time; a second generation of one account is refused; with the
  operator's limit reached, a new one is refused with the busy message.
- CA-128 (RN-81): In hosted mode, a new version started on the data of an
  older one lists every account's cards, decks and collection; a failed
  upgrade leaves the data unchanged.
- CA-129 (RN-26): Deleting a custom card used by a deck names the deck first;
  when confirmed, the card and that deck entry are gone and the deck remains.
- CA-130 (RN-84): The deck picture of a fictional deck with grouping on shows
  one image with a count for two equal cards, and a card whose image cannot
  be read as a frame with its name. Manual: each file type opens.
- CA-131 (RN-93, RN-28): In hosted mode the Privacy screen states what is
  stored and that keys are not; with the reference database not ready, the
  Request screen shows the notice that the site is being prepared and the
  Account screen works.
- CA-132 (RN-64): A reset link sets a new password once; used again, or
  after one hour, it is refused. After a password change, a session opened
  earlier on another device is signed out. Asking for a reset of an unknown
  email gives the same answer as for a known one.
- CA-133 (RN-05): With a fast text model set, the design intent call and a
  quick adjustment use it and the draft and the revision use the main model;
  with none set, every call uses the main model.
- CA-134 (RN-09): The usage of a card shows the seconds of each call, and a
  failed call records its seconds too.
## Screens
- First-run setup: the expected download size and free disk space needed, the
  action that starts the build, the build with progress, the cause of a failure with a retry, a notice and a link
  to Status when settings need fixing
- Status: text provider, model and whether a key is configured (never the key);
  image provider, image model and whether art is available, with the reason when
  it is not; the origin, publication date and download date of each data source; a connection test; the
  settings to fix and, from v2, a link from each to Settings and the refresh of the reference
  database (the action in local mode, the last refresh in hosted mode). In
  hosted mode Status shows only the data sources and the refresh
- The screens below, down to the footer, are v2.
- Home (hosted mode): what Card Factory is, sign in and create account, the
  link to the local application
- Sign in, Create account and Account (hosted mode): the account email,
  password change, the limits with their use, the backup and the deletion
- Settings: the fields of RN-71, where the keys are kept, the connection test
- Privacy and Terms (hosted mode)
- Collection: adding cards, the list in its views with search, filters,
  sorting and totals, the statistics
- Decks: the deck list with tags, search and covers. Deck: the entries by
  category, the checks, the statistics, owned and missing, the picture export
- Extras: the kinds, search, color filter and the action to print
- Print: the queue, the sheet options and presets, print and PDF
- Import and export: the text import with its report, the exports, backup and
  restore, the community order file
- Every screen: the footer of RN-69
- Request: idea or theme, color identity (colors or colorless), power level
  (each with its one-line meaning),
  generation effort (low, medium or high), advanced options hidden until
  requested (card types, supertypes, subtypes, mana value, power and toughness,
  starting loyalty; all optional), card language (English or Portuguese), optional base card (search by name,
  printing and face), and optional art: generated, with an art description and
  the billing notice, or uploaded (checked when chosen); while a generation
  runs, the running step; a choice between a new card and a custom art version,
  which asks only for the card (search among cards with one face), the
  printing and the art (generated with art description and billing notice, or
  uploaded)
- Result: the card image, when present, beside the card text in rules format
  (name, mana cost, type line, rules text, power and toughness or starting
  loyalty), in the manner of
  a card page on Scryfall; without an image, the card text alone. Also the artist
  credit, the rarity, the validation result (approved or rejected, with the causes), the
  design intent, rationale, design notes (when present, with the
  possibly-outdated mark after an edit), comparables, base card, power indicator with its
  justification (and the possibly-outdated mark after an edit), skipped checks,
  usage (text and art separately), the outdated-text notice, the print-quality
  notice for a small uploaded image, the notice when an uploaded image was not
  kept, the notice when art was generated without the base card template, the options to generate, retry or upload art, the option to start a new request from this card (RN-58), and to open the image at
  full resolution; for a custom art version, the mark that names its base
  card, the rarity, and no validation result, design sections, power
  indicator, editing or quick adjustments
- Library: saved cards with an image thumbnail when present, custom art
  versions marked, favorites and deletion; from v2, from the Library and the Result
  screen, a card can be added to the collection, to a deck and to the print
  queue
- Adjustments and versions: editing, quick adjustments, new or uploaded art and
  restoration

## Definition of done (v1)
v1 is done when every RN of v1 has a passing automated test or a recorded manual check
in the manual checklist, every CA of those rules passes, none of them has a [DECIDE], the release
zip and a fresh clone pass the manual checks on a clean Windows machine, a card
was generated end to end with each text provider using a real key, art was
generated with each image provider (OpenAI and Google) using a real key, with
and without a base card, a custom art version was generated with a real key,
and every open question about the rules it delivers is answered or
explicitly moved to Future work. v1 is the card generator in local mode:
the rules up to RN-62, with the settings in the configuration file. In v1,
the sentences of those rules about hosted mode, the Settings screen, the
collection, decks, the print queue, extras, community art or the reference
refresh are not delivered, and the parts of criteria that test them belong
to v2.

## Definition of done (v2)
v2 comes after v1 and is done when the Settings screen, hosted mode, the
collection, decks, import, export, backup, printing, extras and art
selection (RN-63 to RN-96) have a passing automated test or a recorded
manual check for every rule, the hosted application runs on the project's
domain with accounts, a card was generated there end to end with a key kept
only in the browser, the collection, deck, import and print flows passed
their manual checks in both modes, and no [DECIDE] or open question
remains.

## Open questions
- What are the limits on abilities and text length? (RN-20)
- Which license does the project use?
- Do the data source's terms allow its card images to be sent to an image model
  as a template (RN-38)?
- The image of the Card Factory set symbol, to be delivered by the maintainer
  (RN-62).
- Does MPCFill allow its community art to be searched by another
  application, and how? It offers no public interface for it and does not
  answer requests made from the pages of other websites. (RN-91)
- The exact fan content notice, the privacy notice and the terms of use, to
  be delivered by the maintainer (RN-69, RN-93).
- The account limits (RN-67) and the largest backup file (RN-85).
- Must a new account confirm its email before use? (RN-64)
- Is printing custom art versions of existing cards on the hosted site within
  the fan content policy? (RN-88)
- Does the name "Card Factory" still fit the wider scope?
- Usage records (RN-09): is each attempt sent to a provider its own record,
  including a retry and a call that fails with no reported usage, and with
  what precision are the seconds shown? To answer before Milestone 3b.
- Does v1 ship the fan content notice and the link to the source code
  (RN-69), which are otherwise delivered in v2?
- In v1, does any screen show printing images loaded by the browser from the
  data source (the base card picker, RN-36), or only images from the
  application (RN-33, CA-126)?
- In v2 local mode, does a missing configuration file still stop the start
  (RN-40), or does the application open Settings (RN-72)?
- Does the connection test also try the fast text model (RN-05, RN-08)?
- On which screen does a signed-out visitor search existing cards and extras
  (RN-92)?
- For how long are failed attempts, reset requests and access logs kept
  (RN-93)?
- Are card names in Portuguese matched by the import (RN-82)? The reference
  database holds Portuguese terms, not card names (RN-30).
- Does a colored land count under lands or under its colors in the
  statistics (RN-79)?

## Future work
- Sharing a card or a deck by link.
- Deck legality checks for formats other than Commander.
- Letter paper and sheets with card backs.
- Price history, and settings kept across devices.
- Sign-in through other services.
- Aligning casual, medium and strong with the official Commander brackets.
- Connecting through a network proxy. In v1 proxy settings are not supported.
- Cancelling a running card generation, art generation or quick adjustment
  (RN-50).
- Generated cards with more than one face (split, adventure, transform and modal
  double-faced). Each face has its own name, mana cost, type line, rules text,
  power and toughness, and art. This changes the card and its versions, the
  validators (the color identity covers every face), the generation and art
  steps, and the Result and editing screens.
- Custom art versions of cards with more than one face, and with the printed
  Portuguese text of a card.
