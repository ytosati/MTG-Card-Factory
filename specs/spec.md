# Spec: Card Factory

## Goal
Let a person generate custom Magic: The Gathering cards for Commander that are
valid under the rules, have a clear role in some strategy of the format, and sit
in a reasonable power range. The person adjusts the final result. Optionally, the
system also generates the card image (art and frame), or the person uploads their
own image, and the person can start from an existing card as a base: it serves as
the template of the card image and as a design example for the new card.

## Context of use
Card Factory is a free, open-source application that runs on the person's own
computer. The project's GitHub repository is its home: download page, user guide
and source code. The person downloads a ready-to-use package from its releases,
or clones the repository, sets a language model provider (OpenAI, Anthropic or
Google), a model and their own API key in a local configuration file, and starts
it with a double click. Optionally, the same file sets a separate image provider
and key for art. The person pays the providers directly for usage.

## Out of scope
- Export to other programs (saving or printing the card image is allowed, RN-44)
- User accounts, login, billing, hosting on a network
- Automatic updates of the card database or of the application
- Ready-to-use packages for systems other than Windows

## Concepts
- Data sources: Scryfall (card data and card images) and the Comprehensive
  Rules published by Wizards of the Coast.
- Support card: an ordinary card of a deck that is not the commander.
- Color identity: the colors of the mana symbols in the card's mana cost and
  rules text, excluding reminder text, as defined by the Comprehensive Rules for
  Commander. A hybrid symbol counts all its colors; a Phyrexian symbol counts
  its color.
- Comparable: an existing card, legal in Commander, found by the text model in
  the local database and used as a reference.
- Power level: casual, medium or strong. Chooses which comparables serve as
  the reference.
- Design intent: the role of the card (for example ramp, removal, card draw)
  and the Commander strategy it supports.
- Power range: the expected interval of power for similar cards.
- Base card: an existing card chosen by the person. Its image is the template of
  the card image (same frame, colors and layout), and its name and rules text
  are a design example of an effect or strategy.
- Art: the image of a card. A generated image is a full card image: illustration
  and frame, with the card's name, mana cost, type line, set symbol, rules text
  and power and toughness drawn inside. An uploaded image is used as is.
- Image-capable provider: a provider that offers image generation. OpenAI and
  Google are image-capable; Anthropic is not.
- Data folder: the folder that holds the database, the card images and the
  downloaded base card images.

## Entities
- Provider configuration: text provider, model and key; optionally, image
  provider, image model and image key; the local port. Read from the local
  configuration file at startup. Keys are never stored by the application.
- Source record: origin and date of each data source used in the build.
- Request: idea or theme, color identity, power level and, optionally, card
  language, base card (with the chosen printing and face), art requested (yes
  or no), art description and uploaded image.
- Card: name, mana cost, mana value, type line, rules text, power and toughness
  (when applicable), rarity, language, design intent, design rationale,
  comparables used, base card (when chosen), power indicator with its
  justification, art (when present) with its origin (generated or uploaded),
  validation result, skipped checks (when any) and favorite mark.
- Card version: a previous state of a card, including its art, restorable.
- Base card image: the downloaded image of a chosen printing, kept for reuse.
- Usage record: one per provider call, linked to a card when one exists. For a
  text generation, provider, model, and
  input and output tokens; for an art generation, provider, model, number of
  images and image size.

## Business rules

### Data and sources
- RN-01: The card and rules database is built locally from the data sources,
  and the system records the date and origin of each source used.
- RN-02: The project repository contains no card data, no rules text, and no
  card images or frames.
- RN-03: Building the database is all or nothing: if interrupted, the database
  is not considered ready, and a new run rebuilds it without duplicating anything.
- RN-04: Only cards legal in Commander serve as comparables. Cards banned in
  Commander serve only as counterexamples of what is too strong, never as models.

### Provider and key
- RN-05: The text provider (OpenAI, Anthropic or Google), its model and its API
  key are set in a local configuration file before the application starts.
  Optionally, the same file sets an image provider (OpenAI or Google), an image
  model and an image API key. The image key may be left empty when art uses the
  text provider, either because no image provider is set or because the image
  provider equals the text provider; the text key is then used. Model names are required free text,
  not checked against a list. The interface has no field for any key.
- RN-06: No key (text or image) is ever written to a database, log, error message
  or response, sent to the browser, or committed to the repository.
- RN-07: For the same request, the system offers the same text-generation flow
  and the same result format with any text provider. Art generation is available
  only with an image-capable provider: the image provider when one is set,
  otherwise the text provider when it is image-capable. Art also requires an
  image model in the configuration file. When art is not available, the art
  option is shown as unavailable, with the reason and the setting that enables
  it.
- RN-08: At startup and before generating, the system checks the configuration
  without calling any provider. If a provider value is unknown, or a required key
  or model is missing, it names the setting to fix and creates no card. Keys are
  tried only by the connection test on the Status screen and by a generation; if
  the provider rejects the key or the usage limit, the system states the cause
  and creates no card. The same checks apply to the image settings: a problem in
  them makes art unavailable and names the setting to fix, while text generation
  keeps working.
- RN-09: Each text generation records provider, model, and input and output
  tokens. Each art generation records provider, model, number of images and
  image size. Every provider call that consumes tokens or images is recorded,
  including failed generations and refused art, and each call is a separate
  record (a draft and its revision are two records). A refused art call is
  recorded with zero images. The person can see this
  usage, with text and art shown separately.
- RN-10: Provider failures (outage, usage limit, invalid response) become clear
  messages and never leave a card half-created.

### Generation
- RN-11: A request contains an idea or theme, a color identity and a power level
  and, optionally, a card language, a base card, and either a request for art
  with an optional art description or an uploaded image. The type is always a
  support card. [DECIDE whether a support card may be legendary (for example
  "Legendary Creature") or basic]
- RN-12: Before writing the card, the system defines the design intent. The text
  model then searches the local database for cards related to the request (and
  to the base card, when chosen) and picks the comparables among them. The search
  returns only cards legal in Commander, plus banned cards marked as
  counterexamples (RN-04). Comparables cited by the text model that the search
  did not return as legal are discarded; a response left with no valid
  comparable is an invalid response (RN-10). The result shows the design intent.
- RN-13: Every generated card includes a design rationale and the list of
  comparables used.
- RN-14: No card is presented as approved without passing every validation.
- RN-15: A rejected card may go through at most one automatic revision. If it is
  still rejected, it is saved and shown as rejected, with the causes. If the
  revision call fails (RN-10), the first draft is saved as rejected with its
  causes, and the provider failure is shown.

### Validations
- RN-16: The card's color identity, considering cost and text, is within the
  requested identity.
- RN-17: The mana cost is well formed and the stated mana value matches it.
  [DECIDE whether the canonical symbol order is required; whether an empty cost
  (a land) is accepted; how {X}, {C}, {S}, two-generic hybrid ({2/W}) and
  Phyrexian ({G/P}) symbols count toward the mana value]
- RN-18: The type line uses only card types, supertypes and subtypes that exist
  in the game. [DECIDE whether each subtype must belong to one of the card's
  types (for example, "Instant — Elf" rejected)]
- RN-19: Every keyword ability or keyword action used exists in the game.
  Keywords are read from the card's structured list of keywords returned by the
  text model and from lines of rules text that start with a capitalized term
  followed by a cost, a number or the end of the line. Ability words (such as
  the italic word before a dash) and reminder text in parentheses are not
  keywords.
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
  card (name, mana cost, type line, rules text, power and toughness, colors and
  design intent) and the optional art description written by the person. Without
  a base card, the image model chooses a frame that fits the card's colors and
  type. The card text shown beside the image is the card's authoritative text;
  the text drawn inside the image is not validated.
- RN-32: Art generation is a separate step that starts after the card is saved,
  for approved and rejected cards alike. If it fails (outage, usage limit,
  content-policy refusal, invalid response, timeout, model that does not accept
  the template), the card stays saved without art, the person sees the cause,
  and can retry art generation alone. No partial image is saved.
- RN-33: Generated images are received by the application and stored in the
  data folder with the card. The browser loads images only from the local
  application. Deleting a card deletes the images of all its versions.
- RN-34: Editing fields and quick adjustments keep the current art and never
  call the image provider. After such a change, the Result screen notes that the
  image may show outdated text until new art is generated. Generating new art
  creates a new version, and restoring a version restores the art it had.
- RN-35: Before art is generated, the interface states that art is billed by
  the image provider, separately from text.
- RN-43: The person can upload their own image as the art of a card, in the
  request or later. Uploading needs no image provider, calls no provider and
  records no usage. An image chosen in the request is uploaded after the card
  is saved; if the generation fails, the image is discarded and the person is
  told. Only PNG, JPEG and WebP files up to 10 MB are accepted,
  checked by content and not only by extension; any other or unreadable file is
  refused with the reason. An uploaded image is used as is, is stored like
  generated art (RN-33) and creates a new version like new art (RN-34).
- RN-44: Generated images are requested in the provider's portrait size closest
  to the proportions of a card (63 × 88 mm), with at least 745 × 1040 pixels
  when the model allows it, which is enough to print at card size at 300 dpi.
  Images, generated or uploaded, are stored unchanged and shown fitted into a
  card-shaped area close to the card images on Scryfall, without distortion and
  without cropping. The person can open the image at full resolution to save or
  print it. An uploaded image smaller than 745 × 1040 pixels is accepted with a
  notice that print quality may be low.

### Base card
- RN-36: The person can choose a base card by searching the local database by
  name, and then picks one printing. Any card in the database can be a base,
  including cards banned in Commander and legendary cards. For a card with more
  than one face, the person picks the face. Search is available only when the
  database is ready.
- RN-37: The base card is a design example: its name and rules text are given to
  the text model, and the new card may pursue a similar effect or strategy, with
  any type. The color identity comes from the request, not from the base card.
  The design rationale states what was taken from the base card.
- RN-38: When art is requested with a base card, the image of the chosen
  printing is the template: the image model produces a card image with the same
  frame, colors and layout as the base card, new art, and the new card's name,
  mana cost, type line, rules text and power and toughness inside the frame.
- RN-39: The image of a base card is downloaded from the data source only when
  the person chooses that printing, and is kept in the data folder for reuse. If
  the download fails (no network, source failure), the person sees the cause,
  the base card still works as a design example, and art is generated without
  the template, as in RN-31.

### Use and editing
- RN-23: The person can edit any field of the card, and it is revalidated right
  away, without calling the provider. [DECIDE the list of editable fields: in
  particular whether the mana value, the language, the comparables and the
  power indicator are editable] The power indicator is kept and marked as
  possibly outdated until the next quick adjustment or generation.
- RN-24: Quick adjustments (stronger, weaker, cheaper, more expensive, simplify
  text) create a new version, also validated. A quick adjustment is a text
  generation: it records usage and reassesses the power indicator, but gets no
  automatic revision (RN-15). If it fails, the current version stays unchanged
  and the cause is shown.
- RN-25: Every change creates a version, and earlier versions can be restored.
  Restoring a version also creates a new version. Favoriting is not a change of
  the card and creates no version.
- RN-26: Cards are saved locally and can be listed, favorited and deleted.

### Installation and first run
- RN-27: On Windows, the application is distributed as a zip file that contains
  everything it needs to run, including Python, the built interface and the
  configuration file with a comment for each setting. The person extracts it,
  fills in the configuration file and starts the application with a double
  click, without opening a terminal or installing anything else.
- RN-45: A person who clones the repository on Windows finds one start file.
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
  how to fill in every setting of the configuration file, including the image
  provider, the image model with an example value per image-capable provider,
  the image key and the local port.
- RN-40: If the application cannot start (started from inside the zip without
  extracting, folder without write permission, configuration file missing, local
  port in use by another program), it shows a window with a message that names
  the problem and the fix. Problems with the values in the configuration file do
  not block startup: the interface opens on the Status screen and names the
  setting to fix.
- RN-47: The application listens on a fixed default port rarely used by other
  programs, which the configuration file can change. If the port is in use by a
  running Card Factory, RN-41 applies. If it is in use by another program, the
  message names the port and the setting that changes it.
- RN-41: Starting the application opens the interface in the default browser.
  Starting it again while it runs opens a new tab of the running instance. The
  application stops on its own within one minute after the last tab is closed;
  reloading a page does not stop it. While the database build runs, the
  application does not stop when the last tab closes; it stops within one
  minute after the build ends with no tab open. Work in progress when it stops follows
  RN-03 and RN-10.
- RN-42: A new version is installed by extracting the new zip and copying the
  data folder and the configuration file from the previous folder, as the user
  guide describes. A new version started with the data folder of an older one
  keeps every saved card, version and image, and upgrades the stored data
  automatically.
- RN-28: On first start, if the reference database is not ready, the application
  tells the person and builds it, showing progress. The other screens, except
  Status, are available only after it is ready. Before building, the setup
  screen states the expected download size and the free disk space needed, and
  refuses to start the build when there is not enough free space. If the disk
  fills up during the build, the build fails as in RN-03 and the person sees
  the cause.
- RN-29: The application runs entirely on the person's computer and is reachable
  only from it. Outgoing connections go only to the data sources
  (during the build, and to download the image of a chosen base card printing)
  and to the configured providers. The start file of a clone also downloads,
  when preparing, Python and the dependencies from their official distribution
  sources, and the built interface from the project's GitHub releases.

### Legal notice and accessibility
- RN-48: The README and the interface footer show the unofficial fan content
  notice, with the exact text provided by the maintainer. [DECIDE the notice
  text]
- RN-49: Every screen is usable with the keyboard alone; every field has a
  label; keyboard focus is always visible; text meets WCAG 2.1 AA contrast.

### Language
- RN-30: The interface is in English. The generated card text is in English by
  default, and the person can choose any language available in Scryfall. The
  request and the art description can be written in any language.
  - English and Portuguese cards go through every validation, with type words
    and keyword names checked against the official terms in that language.
  - For other languages, the validations that do not depend on words (color
    identity, mana cost and mana value, limits) still run; the type and keyword
    checks are skipped, and the result names the skipped checks.

## Acceptance criteria
Criteria marked "manual" are checked by hand on Windows, because automated tests
never use the network or a real provider.

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
- CA-06 (RN-06): Neither the text key nor the image key appears in any response,
  log or error message, not even when a provider fails, and no response sent to
  the browser contains them.
- CA-07 (RN-03): With the download interrupted, the database is not marked ready,
  and a new run rebuilds it with no duplicated records.
- CA-08 (RN-01, RN-03): With the database ready, a new run downloads nothing
  again, and the Status screen shows the date and origin of each source.
- CA-09: Removed.
- CA-10 (RN-14): An invalid draft never appears as approved.
- CA-11 (RN-15): A card rejected twice is saved and shown as rejected, with the
  causes, with no third attempt. When the first draft is rejected and the
  revision call fails, the first draft is saved as rejected and the provider
  failure is shown.
- CA-12 (RN-23): When the cost of an approved card is edited to an inconsistent
  value, revalidation rejects it right away, without using the provider.
- CA-13 (RN-25): When an earlier version is restored, the fields come back, the
  card is revalidated, and the restoration appears as a new version.
- CA-14 (RN-07): The same scripted card, shaped as each provider's recorded
  response (OpenAI, Anthropic and Google), yields the same saved card and the
  same validation result.
- CA-15 (RN-10): When the provider returns an invalid response, the person sees a
  clear message and no card is saved.
- CA-16 (RN-09): Each text generation records and shows the tokens used. A
  generation that fails after the provider answered still records its usage,
  with no card, and a draft with its revision produces two records.
- CA-17 (RN-40, manual): Started from inside the zip, from a folder without write
  permission, or with no configuration file, the application shows a window that
  names the problem and the fix.
- CA-18 (RN-28): Given a first start with no database, the person sees a setup
  screen with progress and can open the Status screen, and after the build
  finishes the normal screens work.
- CA-19 (RN-29): After the database is built, the only outgoing connections go to
  the configured providers and, when a base card printing is chosen, to the
  data source for that printing's image.
- CA-20 (RN-29, manual): A request from another computer on the network is not
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
  power level, it is not sent and the missing field is named.
- CA-27 (RN-12, RN-13): Every generated card shows its design intent, its design
  rationale and the list of comparables used.
- CA-28 (RN-20): Given a text over the limit of abilities or of length, the card
  is rejected and the exceeded limit is named.
- CA-29 (RN-22): Every generated card shows a power indicator (too strong, in
  range or too weak) with a justification that cites at least one comparable,
  and a "too strong" indicator does not make the card rejected.
- CA-30 (RN-24): A quick adjustment creates a new validated version with a
  reassessed power indicator and a usage record, and the previous version can
  still be restored. When the quick adjustment fails, the current version is
  unchanged and the cause is shown.
- CA-31 (RN-26, RN-33): A saved card is listed in the library after a restart, a
  favorited card is listed among the favorites, and a deleted card is listed
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
  of images and image size, separately from the text tokens.
- CA-36 (RN-31): Given a request without art, no image request is made. Given a
  request with art and no base card, the image provider receives the card's name,
  mana cost, type line, rules text, power and toughness and colors.
- CA-37 (RN-32): When art generation fails or is refused by content policy, the
  card stays saved without art, no image file is left, the cause is shown, and
  retrying art alone generates it without generating the text again. A rejected
  card with art requested also receives art.
- CA-38 (RN-33): The browser loads no image from an address outside the local
  application.
- CA-39 (RN-34): Editing a field or applying a quick adjustment keeps the art,
  makes no image request and shows the outdated-text notice. Generating new art
  creates a version, and restoring the earlier version restores the earlier art.
- CA-40 (RN-35): Before art is generated, the person sees that art is billed by
  the image provider separately from text.
- CA-41 (RN-36): Searching by part of a name lists the matching cards from the
  local database without network access, including cards banned in Commander,
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
  application within one minute; reloading a page does not stop it. Closing the
  last tab during the database build does not stop it; it stops within one
  minute after the build ends.
- CA-48 (RN-42): A new version started with the data folder and configuration
  file of an older version lists every saved card, version and image.
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
- CA-53 (RN-47, manual): With the default port in use by another program, the
  application shows a window that names the port and the setting that changes
  it; after changing that setting, it starts.
- CA-54 (RN-30): Given a Portuguese card with a keyword that does not exist in
  Portuguese, it is rejected. Given a Japanese card, color identity and mana
  checks run, and the result names the type and keyword checks as skipped.
- CA-55 (RN-23): After a manual edit, the power indicator is still shown, marked
  as possibly outdated, and no provider is called; a quick adjustment removes
  the mark.
- CA-56 (RN-12): Given a text model response that cites a comparable not
  returned by the search, or a banned card, that comparable is discarded; a
  response left with no valid comparable is handled as an invalid response.
- CA-57 (RN-16): Given a green request, a {G/U} hybrid symbol in the cost or in
  the rules text is rejected; a {U} symbol inside reminder text in parentheses
  is not.
- CA-58 (RN-48): The README and the footer of every screen show the fan content
  notice.
- CA-59 (RN-49): Every screen can be operated with the keyboard alone, every
  field has a label, and focus is visible; automated component tests check the
  labels and focus, and contrast is checked by hand.
- CA-60 (RN-28): Given less free disk space than the build needs, the setup
  screen names the space needed and the build does not start.
- CA-61 (RN-43): Given a request with an uploaded image whose generation fails,
  no image file is left and the person is told the image was discarded.

## Screens
- First-run setup: database build with progress
- Status: text provider, model and whether a key is configured (never the key);
  image provider, image model and whether art is available, with the reason when
  it is not; the date and origin of each data source; a connection test; the
  settings to fix
- Request: theme, color, power level, card language, optional base card (search
  by name, printing and face), and optional art: generated, with an art
  description and the billing notice, or uploaded
- Result: the card image, when present, beside the card text in rules format
  (name, mana cost, type line, rules text, power and toughness), in the manner of
  a card page on Scryfall; without an image, the card text alone. Also the design
  intent, rationale, comparables, base card, power indicator with its
  justification (and the possibly-outdated mark after an edit), skipped checks, usage (text and art separately), the
  outdated-text notice, the options to generate, retry or upload art, and to open
  the image at full resolution
- Library: saved cards with an image thumbnail when present, favorites and
  deletion
- Adjustments and versions: editing, quick adjustments, new or uploaded art and
  restoration

## Definition of done (v1)
v1 is done when every RN has a passing automated test or a recorded manual check
in `specs/manual-checks.md`, every CA passes, no [DECIDE] remains, the release
zip and a fresh clone pass the manual checks on a clean Windows machine, and a
card was generated end to end with each text provider using a real key.

## Open questions
- What are the limits on abilities and text length? (RN-20)
- If the source download fails, how many times does it retry?
- Can the person refresh the database later, and how (for example a button on
  the Status screen)? Does a new application version require a rebuild (RN-42)?
- Which license does the project use?
- What is the exact fan content notice text (RN-48), and do the data source's
  terms allow its card images to be sent to an image model as a template
  (RN-38)?
- Does full Portuguese validation stay in v1, given the size of the extra
  download it needs (RN-30)?
- Which languages does the card language selector list: every Scryfall language
  or a fixed list?
- Should casual, medium and strong align with the official Commander brackets?
- What happens when a generated card has the same name as an existing card?
- Are simultaneous generations allowed, and can a running generation be
  cancelled?
- What are the maximum lengths of the idea and of the art description?
