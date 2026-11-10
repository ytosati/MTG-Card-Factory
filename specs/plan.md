# Plan: Card Factory

Technical plan for `specs/spec.md`. The spec is the source of truth; this plan
says how each rule is met. Where a choice had alternatives, the chosen option is
stated first and the trade-offs follow. Dependencies named here are the approved
ones (CLAUDE.md); anything else needs approval before a task adds it.

## 1. Context

The repository holds only the specification, the standards and an empty
`backend/` and `frontend/`. This plan defines the Django apps, models, services,
selectors, endpoints, the data directory, the distribution, and the folders each
agent may change, so that `specs/tasks.md` can be cut into reviewable tasks.

## 2. Repository layout

```
backend/
  cardfactory/          Django project: settings, urls, wsgi
  core/                 configuration (.env), paths, secret key, jobs, status
  catalog/              reference data: ingest, search, rules lexicon
  providers/            provider adapters, factory, fake provider
  validators/           pure validation functions (no models)
  generation/           text and art generation pipelines, retrieval of
                        comparables and rules for the text model
  generation/prompts/   prompt text files
  cards/                cards, versions, images, usage, library, editing
  api/                  DRF views, serializers, urls
  tests/                pytest suites, fictional fixtures
  pytest.ini            pytest configuration (DJANGO_SETTINGS_MODULE)
  requirements.txt      runtime dependencies (pinned)
  requirements-dev.txt  test dependencies (pinned)
frontend/
  src/api/              typed API client
  src/screens/          Setup, Status, Request, Result, Library, Versions
  src/components/       shared components
  src/styles/           design tokens (single source)
  src/assets/           favicon and any approved local font or icon files
  src/hooks/            heartbeat, job polling
  index.html            document shell; links the favicon from src/assets/
launcher/               start.pyw (zip and clone), Windows message boxes, tests
release/                release build script, pinned versions and hashes,
                        repository content check, tests
.github/workflows/      CI: test suites on push and pull request; release artifacts
start.cmd               clone start file (RN-45)
VERSION                 application version, matches the GitHub release tag
data/                   runtime only, never committed (see section 7)
```

## 3. Django apps

| App | Owns | Depends on |
|---|---|---|
| core | config loader, `Secret` type, data paths, Django secret key, key redaction log filter, `Job` model and runner, status service | none |
| catalog | `OracleCard`, `Printing`, `RuleSection`, `Term`, `SourceRecord`, `BuildRun`; ingest services; search selectors; lexicon selector | core |
| providers | adapter protocol, OpenAI/Anthropic/Google adapters, fake adapter, factory | core |
| validators | pure functions over a card and a lexicon | none |
| generation | request pipeline, revision, quick adjustments, art pipeline, prompts | catalog, providers, validators, cards |
| cards | `Card`, `CardVersion`, `CardImage`, `BaseCardImage`, `UsageRecord`; write services; library selectors | core, validators |
| api | views, serializers, urls, frontend view | all, through services and selectors only |

Rule: views call one service or selector; serializers validate and shape;
business rules live in services and selectors; validators never import Django
models.

## 4. Models

Fields listed are the ones the spec needs; types are left to the tasks.

**catalog**
- `SourceRecord`: source (scryfall_oracle, scryfall_default, scryfall_all,
  comprehensive_rules), url, published_at, downloaded_at, sha256, size (RN-01).
- `BuildRun`: one row per completed build, written as ready inside the import
  transaction: catalog_version, started_at, finished_at (RN-03). The live state
  of a build (queued, running, failed, progress, error) is its `Job`, so a
  crash never leaves a build "running".
- `OracleCard`: `oracle_id` (Scryfall, primary key), name, mana_cost, cmc,
  type_line, oracle_text, colors, color_identity, keywords, power, toughness,
  layout, faces (JSON), commander_legality (legal, banned, not_legal),
  game_changer, edhrec_rank, roles (JSON list, section 9.6).
  Import mapping (T16): Commander `restricted` is stored as legal and any other
  or missing value as not_legal; non-card layouts (token, double_faced_token,
  emblem, art_series, vanguard, scheme, planar) are not imported; a card
  without top-level mana_cost, oracle_text, colors, type_line or cmc takes
  them from its faces (front face mana cost and cmc, face texts joined with
  `//`, union of face colors, face type lines joined with ` // `); a record
  without a top-level oracle_id takes the first face's; a repeated oracle_id
  is stored once.
- `Printing`: `scryfall_id` (primary key), oracle_card, set_code,
  collector_number, lang, frame, border_color, frame_effects, released_at,
  image URLs per face (png 745 × 1040).
- `RuleSection`: number (primary key, for example "702.19b"), text.
- `Term`: lang (en, pt), kind (card_type, supertype, subtype, keyword_ability,
  keyword_action, ability_word, number_word), english, localized, parent card
  types (JSON list, for a subtype; a subtype may belong to several types),
  allowed in Commander (for a card type or supertype) (RN-18, RN-19, RN-30).
  The Commander list is fixed in code: card types Artifact, Battle, Creature,
  Enchantment, Instant, Kindred, Land, Planeswalker and Sorcery; supertypes
  Basic, Legendary, Snow and World. Every other card type and supertype in the
  Comprehensive Rules (such as Scheme, Plane, Conspiracy or Ongoing) is not
  allowed. `number_word` rows are the words that existing cards follow with a
  number (as in "deals 3"), derived at build time from English oracle text and
  Portuguese printed text.
- Full-text tables `oracle_fts` and `rules_fts` (SQLite FTS5), created by a
  migration with fixed SQL and queried only with parameters.

**cards**
- `Card`: `id` (UUID4), created_at, favorite, language, current_version, and
  the request it came from: idea, requested color identity (possibly
  colorless), power level. Revalidation after an edit, an adjustment or a
  restore uses it (RN-16, RN-19).
- `CardVersion`: card, number (1, 2, …), origin (generated, revised, edited,
  adjusted, restored, art_generated, art_uploaded), name, mana_cost, mana_value,
  type_line, rules_text, power, toughness, rarity, design_intent, rationale,
  comparables (JSON: oracle_id, name, role), base_card (JSON snapshot: oracle_id,
  printing id, face, name, rules text), power_indicator, power_justification,
  power_outdated, status (approved, rejected), validation (JSON causes),
  skipped_checks, image (nullable). Versions are immutable, with one exception:
  art requested in the request is attached to version 1 by the generation job
  that created it (RN-32). The artist credit "Card Factory" is a constant, not
  a stored field (RN-48).
- `CardImage`: `id` (UUID4), card, origin (generated, uploaded), relative file
  path, mime, width, height, created_at.
- `BaseCardImage`: printing id (primary key), face, relative file path,
  downloaded_at (RN-39).
- `UsageRecord`: card (nullable), kind (text, image), provider, model,
  input_tokens, output_tokens, images, image_size, outcome (ok, failed),
  created_at (RN-09).

**core**
- `Job`: `id` (UUID4), kind (build, generate, adjust, art), status (queued,
  running, done, failed), progress, result (card id), error message,
  created_at. Jobs left running at startup are marked failed (RN-03, RN-10).

## 5. Services and selectors

| Module | Functions (names indicative) |
|---|---|
| core.config | `load_config()`, `get_config()`; `Secret.reveal()` used only by providers.factory and core.log_redaction |
| core.jobs | `submit(kind, fn)`, `get_job(id)`, `fail_orphan_jobs()` |
| core.status | `status_snapshot()` (no key values) |
| catalog.build, catalog.ingest | `run_build()` and `start_build()` (catalog.build); `download_sources()`, `import_oracle()`, `import_printings()`, `import_rules()`, `import_pt_terms()`, `tag_roles()` |
| catalog.selectors | `is_ready()`, `search_cards(query, filters)`, `search_rules(keywords)`, `get_lexicon(lang)`, `find_base_cards(name)`, `list_printings(oracle_id)` |
| providers.factory | `text_adapter()`, `image_adapter()`, `art_availability()` |
| validators | `validate(card, lexicon, request) -> ValidationResult` composed of color identity, mana cost, type line, keywords, limits; `request` gives the requested identity (possibly colorless) and the idea text |
| generation.text | `generate_card(request)`, `revise(draft, causes)`, `quick_adjust(card, kind)` |
| generation.art | `generate_art(card, description)`, `fetch_base_image(printing, face)` |
| cards.services | `save_version()`, `edit_fields()`, `restore_version()`, `set_favorite()`, `delete_card()`, `attach_image()`, `upload_image()`, `record_usage()` |
| cards.selectors | `list_cards(favorite)`, `get_card()`, `list_versions()`, `usage_for(card)` |

## 6. Endpoints

All under `/api/`, JSON, local only. Long operations return `202` with a job id.
Response shapes are the serializers in `backend/api/serializers.py`; the
frontend client types mirror them. Every error response uses one envelope:
`{"error": {"code": str, "message": str, "setting": str | null, "fields": {name: [str]} | null}}`,
where `setting` names the configuration setting to fix when there is one
(RN-08) and `fields` names each invalid request field (CA-26). An unknown
`/api/` path answers 404 in the envelope, never the built `index.html`.

**Error codes.** Stable, added per milestone, never renamed; the frontend
branches on `code`, never on `message`: `config_invalid`, `origin_refused`,
`not_found`, `method_not_allowed`, `validation`, `database_not_ready`,
`database_busy`, `insufficient_space`, `source_unreachable`, `auth`, `quota`,
`rate_limited`, `model_not_found`, `provider_unavailable`,
`provider_not_available_yet`
(development state of Milestone 3 only), `invalid_response`,
`content_refused`, `art_unavailable`, `card_changed`, `generation_running`,
`bad_request`, `internal`.
`bad_request` answers a malformed JSON body (400), an unsupported media type
(415) and an unacceptable `Accept` header (406), with a fixed message and the
original status. `origin_refused` answers 403. `database_not_ready` answers 503,
`insufficient_space` 507, `source_unreachable` 502, `generation_running` 409 and `validation` 400. The messages in `fields` are fixed texts chosen by the error kind; they never quote the submitted value. A settings
list (status, generation, setup) uses the same objects, `{setting, code,
message}`, with codes as stable as the error codes: `config_invalid` for a
setting to fix and `ignored` for a setting ignored with a notice (RN-08). A
configuration file that cannot be read is the single item `config_invalid`
with `setting` equal to `.env` and a message for its cause (RN-40, CA-77).

**Jobs.** `GET /api/jobs/{id}` returns `{id, kind, status, progress, result,
error}`, where `error` is the envelope above. A job never stores the text of an
exception: an exception outside the mapped set becomes `internal` with a fixed
message, and its detail goes only to the redacted log.

**Readiness gate.** A default DRF permission requires a ready catalog; the
views that work without it (status, connection test, setup, jobs, instance,
heartbeat) opt out explicitly, and a test walks the URL configuration.

**Contract samples.** A backend test helper calls the endpoints with a fake
configuration, normalizes what varies (UUIDs, dates, elapsed time) and writes
`frontend/src/api/contract/samples.ts`, one `export const <name> = {...}
satisfies <ClientType>;` per sample. The test fails when the generated text
differs from the committed file (`CARDFACTORY_UPDATE_CONTRACT=1` rewrites it),
and `npx tsc -b` checks every sample against the client types. Frontend tests
build their mocks from these samples. This catches drift between the
serializers and the client types with no new dependency.

| Method and path | Purpose | RN |
|---|---|---|
| GET `status` | providers, models, key configured (bool), art availability and reason, settings to fix, sources, database readiness | 08, 01, 07 |
| POST `status/connection-test` | tries the text key and, when set, the image key | 08 |
| GET `setup` / POST `setup/build` | build progress / start build | 28, 03 |
| GET `catalog/cards?q=` | base card search by name | 36 |
| GET `catalog/cards/{oracle_id}/printings` | printings and faces | 36 |
| POST `catalog/printings/{scryfall_id}/image` | downloads the printing image, or returns the cached one; a failure returns the cause | 39 |
| POST `generations` | request → job | 11–15 |
| GET `jobs/{id}` | job progress, result, error | 10 |
| GET `cards?favorite=` / GET `cards/{id}` | library / card with current version | 26 |
| PATCH `cards/{id}` | edit fields (new version) or favorite (no version) | 23, 25, 26 |
| DELETE `cards/{id}` | delete card and image files | 26, 33 |
| POST `cards/{id}/adjustments` | quick adjustment → job | 24 |
| GET `cards/{id}/versions` / POST `…/versions/{n}/restore` | versions / restore | 25 |
| POST `cards/{id}/art` | generate art → job | 31–32, 38 |
| POST `cards/{id}/art/upload` | multipart upload; an image chosen in the request is uploaded here after the generation job saves the card | 43 |
| GET `images/{id}` | serves the stored file unchanged | 33, 44 |
| GET `usage?card=` | `{card, text: [{provider, model, input_tokens, output_tokens, outcome, created_at}]}`, oldest first, only records linked to the card; a missing or malformed `card` answers `validation`, an unknown card `not_found` | 09 |
| POST `heartbeat` / GET `instance` | tab liveness / identifies Card Factory on the port | 41, 47 |

**Instance contract.** `GET /api/instance` returns `{app: "card-factory",
version, home}` and is a contract between versions (a newer launcher probes an
older instance): these fields never change meaning, and readers ignore extra
fields. `version` comes from the `VERSION` file in the home, or
`0.0.0+unknown` when it is missing. `POST /api/heartbeat` takes a JSON body
(`{}`) and answers 204 with no body.

Every non-API path returns the built `index.html`; `/assets/*` is served from
the built frontend (section 9.5).

## 7. Database and data directory (topic 4)

```
data/
  cardfactory.sqlite3      reference tables and user tables
  secret_key               Django secret key, generated on first start
  images/cards/{card_id}/{image_id}.{png|jpg|webp}
  images/base/{printing_id}-{face}.png
  downloads/               source files during a build, deleted after import
  backups/                 copy of the database before pending migrations
                           (only the last backup is kept)
  logs/app.log             application log, rotated (section 8)
```

**Application home.** The application home is the folder that holds `.env` and
`data/`. The launcher sets the environment variable `CARDFACTORY_HOME`; in
development it defaults to the repository root. `core.paths` is the only place
that resolves it, and every other path (`data/`, `.env`, images, logs) is
derived from it. In the zip the home is the extracted folder; in a clone it is
the repository root.

**Concurrency.** SQLite runs in WAL mode with a busy timeout and IMMEDIATE
transactions, because job threads write while waitress threads read. Job and
build progress is kept in memory by the runner and persisted only at state
changes (queued, running, done, failed), so the import transaction never blocks
progress reads. Rules:
- While a build runs, no other writing job starts; the readiness gate already
  blocks generation, adjustments and art.
- One generation job (card generation, art generation or quick adjustment)
  runs at a time (RN-50); submitting another while one runs is refused with
  `generation_running`. There is no cancellation in v1.
- The only write possible during a build is the usage record of a connection
  test; it waits in a small in-memory queue in `core` that the build job flushes
  when it ends, whatever the outcome.
- Selectors never open `transaction.atomic()`: with IMMEDIATE transactions it
  would take the write lock.
- `database is locked` maps to the error code `database_busy`.
- Orphans are detected by the runner: a job persisted as queued or running
  whose id the runner of this process does not know is reported and stored as
  failed by `get_job`; the startup cleanup is only housekeeping. This works
  under the launcher, `runserver` and tests.

**Catalog version (RN-03, RN-42).** `catalog` keeps a source registry (one
entry per source: name, how to read its size, how to download it, its
importer) and an integer `CATALOG_VERSION`. A milestone that adds a source adds
its entry and increments the constant. `is_ready()` means a ready `BuildRun`
with `catalog_version == CATALOG_VERSION`; when the constant changes, the Setup
screen opens again and the build reruns every source, leaving user tables
untouched. The setup download size is the sum over the registry.

**All-or-nothing build (RN-03).** Two phases.
1. Outside any transaction, and resumable: download each source to
   `data/downloads/` and check size and checksum, then stream it once and
   extract only the needed fields, with the roles already tagged, into a
   compact JSON-lines file next to it. A
   download resumes with `If-Range` (ETag or Last-Modified), so a source that
   changed since the partial download starts over. Nothing is marked ready.
2. Import in a single short SQLite transaction: delete reference rows, insert
   the extracted rows, rebuild the FTS tables, write the
   `SourceRecord` rows and the ready `BuildRun`, commit. An interruption rolls
   the transaction back; user tables are never touched. The review of each
   milestone that adds a source records how long the write lock was held.
   A failed build keeps the complete downloads for the next run, except
   after a disk-full failure; the JSON-lines file is always deleted.

*Alternative considered:* build into a second database file and swap it in.
Rejected: the user tables live in the same file (CLAUDE.md: a single SQLite
file), so a swap would need copying user data across.

**Stable identifiers.** Reference cards use the Scryfall `oracle_id`, printings
the Scryfall `id`; both survive a rebuild. User cards and images use UUID4.
Versions are numbered per card, inside the IMMEDIATE transaction of
`save_version()`, with a unique `(card, number)` constraint. A version stores a
snapshot of its base card and comparables, so a rebuild never breaks a saved
card. User tables never hold a foreign key to a catalog table (only ids inside
snapshots), because a rebuild deletes the reference rows. The JSON fields of a
version (`comparables`, `base_card`, `validation`) may gain keys but never
rename or remove one; readers default missing keys. `validation` is
`{status, checks_run: [...], causes: [{check, code, message}], skipped: [...]}`,
with stable check names (`mana_cost`, `color_identity`, `type_line`,
`keywords`, `limits`), so a card approved before every validator existed shows
which checks ran. Inputs that cannot be rebuilt later (the request of a card)
are stored by the first milestone that receives them.

**Upgrades (RN-42).** On start, when migrations are pending, the launcher
copies the database to `data/backups/` with the SQLite backup API of the
standard library (a plain file copy can miss pages still in the write-ahead
log), replacing the previous backup, and runs them. If the database is newer than the
application (unknown migrations), it stops with a message instead of migrating.

## 8. Configuration, secret and status (topic 3)

- **Loading `.env`.** `core.config` is the only reader. It takes the file path as
  a parameter (the default is `.env` in the application home), so tests use
  temporary files with a cleared environment and never read the repository
  `.env`. A small parser in the standard library reads `KEY=VALUE` lines, ignores comments and blank lines,
  strips quotes, spaces and the UTF-8 byte-order mark that Notepad may add, and
  lets process environment variables override only when `CARDFACTORY_DEBUG=1`.
  It returns a frozen config object; keys are `Secret` objects whose text form
  is `***`. `get_config()` reads the file again when its modification time or
  its size changed, so the Status screen and each generation see a fix without
  a restart (RN-08); the size catches most saves made within the 2-second
  timestamp precision of FAT32. A read that fails is never cached: the next
  call tries the file again, so a permission fixed without editing the file is
  seen. The parser reads UTF-8, with or without a byte-order mark, and UTF-16
  with a byte-order mark (Notepad "Unicode"); an invalid UTF-8 byte is
  replaced, so one stray character in a comment does not discard the file. A
  file that exists but cannot be opened, or holds NUL bytes after decoding
  (UTF-16 with no byte-order mark), reads as empty and is reported as the
  single item for `.env` (section 6): no other setting to fix and no port
  change are reported while it cannot be read (RN-40, CA-77). `core.config`
  imports nothing from Django, so the launcher can use it before the settings
  load. A model value (`LLM_MODEL`, `IMAGE_MODEL`) equal to a configured key
  value or starting with a known key prefix (`sk-`, `AIza`) is a setting to
  fix; it is not kept in the config, like an unknown provider value, so it is
  never shown, logged or sent to a provider (RN-06, RN-08, CA-78). The port is read once at startup; a changed port is reported as
  taking effect at the next start. An invalid `APP_PORT` falls back to 47821
  and is reported as a setting to fix (RN-47). Empty image settings only make
  art unavailable; set but invalid ones are settings to fix; `IMAGE_API_KEY`
  with no `IMAGE_PROVIDER` is ignored with a notice. Setting names are
  case-sensitive, the first `=` separates the name from the value, and the last
  repeated line wins. There are no inline comments (an unquoted key may contain
  `#`) and no `export` prefix. An empty process variable never overrides the
  file. A missing or unreadable file reads as empty and never raises; at
  startup, a missing file is the launcher's case (RN-40). An unrecognized
  provider value is not kept in the config, since it may be a pasted key
  (RN-06). A `Secret` is false when empty.
  *Alternative:* the `python-dotenv` package. Rejected to avoid a dependency for
  about forty lines.
- **Defaults and checks (RN-05, RN-07, RN-08).** No provider call at startup.
  The loader reports missing or unknown values as a list of "settings to fix".
  `IMAGE_API_KEY` falls back to `LLM_API_KEY` when art uses the text provider.
  `APP_PORT` defaults to 47821.
- **Django secret key.** When settings first load, `core` writes
  `data/secret_key` with a random value from the standard library (`secrets`,
  at least 50 characters, so Django's key check passes) and reads it on later
  loads, without surrounding whitespace. A file that is empty or holds only
  whitespace, or whose content is not UTF-8, is replaced by a new value: in v1
  the key signs nothing that persists (no sessions, no accounts), so replacing
  it is harmless. A readable file with valid content is never rewritten. A file
  that cannot be read or written (no permission, a folder in its place) raises
  `core.startup.StartupError` naming `data/secret_key`, with the fix "check its
  permissions, or delete it"; the launcher shows it in a message box (RN-40).
  It is not the API key and is never shown. No action from the person.
- **Key protection (RN-06).** In application code, only `providers.factory`
  and the log filter (`core.log_redaction`, which needs the values to remove
  them) call `reveal()`. Adapters never put the key in exception text. As a
  second line of defense, the log filter replaces with `***` every key value
  of the current configuration (`get_config()` on each record): the text key,
  the image key held in the config (the effective one after the fallback, or
  the one set with an invalid `IMAGE_PROVIDER`), and an `IMAGE_API_KEY` ignored
  for lack of `IMAGE_PROVIDER`, kept in the config as a `Secret` for this
  purpose. Every key value seen since the process started stays redacted
  until the process stops, so a call made with a key replaced in `.env`
  cannot log the old value; these values are kept in memory only. A value
  under 8 characters is left alone, since replacing it would garble ordinary
  text. This is an accepted risk: real provider keys are far longer, and a key
  that short is not valid. The filter covers the formatted message, its arguments
  when they do not match the message, the exception text and `stack_info`; it
  never drops a record. Serializers list fields explicitly; the
  status serializer has booleans only. A test sends every endpoint through a
  fake configuration and asserts the key never appears.
- **Settings.** `DEBUG` is on only when the environment variable
  `CARDFACTORY_DEBUG=1` is set (development; it is not in `.env.example`).
  `ALLOWED_HOSTS` is limited to `127.0.0.1` and `localhost`. The server always
  binds to `127.0.0.1`; there is no setting to change it in v1 (RN-29).
- **Cross-site requests.** Any web page open in the browser can send requests
  to `127.0.0.1`. Non-GET requests are refused unless `Origin` (or, when absent,
  `Referer`) is the application's own origin. DRF parsers are JSON only, except
  multipart on the upload endpoint, so a form post from another site is refused
  before it reaches a provider.
- **Logs.** With `pythonw.exe` there is no console, so the application logs to
  `data/logs/app.log` with size-based rotation. The key redaction filter applies
  to every handler. The log format uses only the message, the standard record
  fields, the exception and the stack, so `extra` fields, which the filter
  does not cover, never reach the file. Logs record events, causes and
  identifiers, never card contents, prompts or keys.

## 9. Topics with alternatives

### 9.1 Search for comparables and rules without embeddings (topic 1)

**Chosen: model-generated keywords, then database filters plus FTS5.**
1. The text model returns the design intent and a search plan: keywords,
   candidate roles, card types and a mana value range (JSON).
2. `catalog.selectors.search_cards` filters by color identity (within the
   request), commander legality (legal; banned returned only as
   counterexamples), roles, types and mana value, then ranks with FTS5 BM25 over
   name, type line and rules text. Power level shapes the candidate set: strong
   includes Game Changer cards and ranks by EDHREC rank; casual excludes Game
   Changer cards; medium allows Game Changer cards without prioritizing them
   and ranks by BM25 alone. User text passed to `MATCH` is quoted per token.
3. If fewer than a minimum number of results come back (a named constant,
   10), the selector widens the filters deterministically (drop mana value,
   then types). No second model call.
4. The model writes the card and cites comparables from the candidates; cited
   cards not returned as legal are discarded (RN-12).
5. `search_rules` uses FTS5 over `RuleSection` with the same keywords and adds
   the sections of every keyword the draft uses.

| Option | For | Against |
|---|---|---|
| Database filters only | deterministic, instant | misses cards phrased differently |
| FTS5 over rules text | built into SQLite, no dependency, good on mechanics words | literal matching; needs good keywords |
| Keywords generated by the model | bridges the person's wording and card wording | one more model output to check |
| Embeddings | semantic matches | needs a vector store or extension (dependency), an embedding provider (Anthropic has none, which breaks RN-07), a heavier build |

**T26: search quality evaluation.** The task that decides on embeddings. Twenty
written requests covering the main roles, every color and the three power
levels, run against a real local database (a manual script outside the test
suite, since tests never use real data). For each request a person marks the
relevant cards in the top ten. Pass: at least 16 of 20 requests have five or
more relevant cards. On pass, embeddings stay out. On fail, the task records
which requests failed and why, and proposes either better role patterns and
keywords or an embeddings option for approval. Only the request texts and the
counts are committed, never card data (RN-02).

FTS5 availability is checked early: T14 tests it in the running Python, and the
Milestone 1 review (T88) confirms it in the embeddable Python of the zip. If
it is missing, the fallback is a `LIKE` search with the same filters. Base card
search by part of a name (RN-36) uses a case-insensitive `LIKE`, not FTS.

### 9.2 Provider factory and adapters (topic 2)

**Chosen: one adapter protocol, direct HTTP with the standard library.**
- Two protocols: `TextAdapter.complete_json(system, messages, schema) -> (data,
  usage)`, and `ImageAdapter.generate_image(prompt, template_image | None,
  size) -> (bytes, mime, usage)` with `capabilities` (image_template). The text
  side and its fake come first (Milestone 3); the image side and its fake come
  with art (Milestone 7). Anthropic has no image adapter.
- `providers.factory` is the only place that reads `LLM_PROVIDER` and
  `IMAGE_PROVIDER`, which accept only `openai`, `anthropic` and `google`
  (`IMAGE_PROVIDER`: `openai` and `google`). Tests replace the factory
  functions with a pytest fixture that returns the fake adapter; the fake is
  never selectable from `.env`.
- Keys travel only in request headers, never in URLs (for Google, the
  `x-goog-api-key` header), because URLs appear in exception text.
- Each adapter maps its errors to one set: `AuthError`, `QuotaError`,
  `ProviderUnavailable`, `InvalidResponse`, `ContentRefused`,
  `TemplateUnsupported`, `ModelNotFound` (names `LLM_MODEL` or `IMAGE_MODEL`).
  Messages never include the key. An error raised after the provider answered
  (`InvalidResponse`, `ContentRefused`) carries the usage the provider
  reported, so it is recorded (RN-09).
- Text calls request structured JSON output; the response is parsed and checked
  against the schema before use (invalid → `InvalidResponse`, RN-10), by a small
  validator in `providers/` (no `jsonschema` dependency).
- Schemas use only the subset the three providers accept in structured output:
  object, array, string, integer, number, boolean and enum, every property
  required, no `oneOf`, `anyOf`, `pattern` or `format`. A test walks every
  schema and refuses other keywords, so a schema that one provider rejects is
  caught before its adapter exists.
- Error texts never include the provider's response body: a rejected-key body
  can echo a masked part of the key that the log filter does not recognize.
- HTTP 429 is split: a quota or billing error maps to `QuotaError`, a rate limit
  to `ProviderUnavailable` with the code `rate_limited`, so the cause shown is
  the right one (RN-08).
- Images: OpenAI image generation and edit (template); Google image models that
  accept an input image for the template, and Imagen without template. A model
  without template support raises `TemplateUnsupported`. The art pipeline skips
  the template when the adapter's capabilities exclude `image_template`, and
  retries once without it on `TemplateUnsupported`; either way the result
  carries a notice (RN-38).

| Option | For | Against |
|---|---|---|
| Official SDKs | maintained by vendors, retries and typing included | three packages with their own trees (HTTP client, validation library, auth libraries for Google), tens of MB in the zip, version conflicts |
| Direct HTTP, standard library | no dependency, a handful of endpoints per provider, full control of errors and of key redaction | own multipart and retry code; API changes are ours to follow |
| Direct HTTP with one HTTP client package | nicer timeouts and multipart | one more dependency |

Direct HTTP fits the small surface (one text endpoint and one or two image
endpoints per provider) and the install weight goal. Timeouts are named
constants: connect 10 s, text read 180 s, image read 300 s; one retry on 5xx and
network errors. While a provider call runs, the job reports "waiting for the
provider" with the elapsed time.

### 9.3 Configuration, secret and status
Covered in section 8.

### 9.4 Data layout and build
Covered in section 7.

### 9.5 Installation and serving (topic 5)

**Chosen: zip with portable Python for releases, start file for clones,
waitress as server, Django serves the built frontend.**

| Option | For | Against |
|---|---|---|
| Zip with embeddable Python (chosen) | nothing to install, double click, small | Windows only; release script to maintain |
| Docker Compose | same everywhere | needs Docker Desktop and WSL2 (gigabytes), a terminal, admin rights; contradicts RN-27 |
| Single executable (freezer) | one file | antivirus false positives, a new build dependency, slow start |

- **Zip layout:** `python/` (embeddable Python with the dependencies in its
  site-packages), `app/backend/`, `app/frontend/` (built), `launcher/`,
  `Start Card Factory.cmd`, `.env` (from `.env.example`), `data/` (created on
  first start), `README.md`, `VERSION`. The zip is assembled from tracked files
  only, through an explicit include list (no tests, `conftest.py`,
  `__pycache__`, `data/` or local `.env`); its `.env` is a byte copy of
  `.env.example`. `python312._pth` lists the standard library,
  `Lib\site-packages` and `import site`; the pinned requirements are installed
  with `pip install --target` as binary wheels for win_amd64 and Python 3.12.
  After assembly, a smoke test runs the zip's own `python.exe`: it imports
  Django, Django REST Framework and waitress and creates an FTS5 table, so FTS5
  and the embeddable package are checked on every build.
- **Start file:** a `.cmd` (source under `launcher/`) that first checks that
  `python\pythonw.exe` and `launcher\start.pyw` exist next to it (`%~dp0`). When
  they do not (started from inside the zip, where Explorer extracts only the
  clicked file, or a partial extraction), it shows the problem and the fix in
  its console and waits for a key (RN-40, CA-17). Otherwise it runs
  `start "" python\pythonw.exe launcher\start.pyw` and exits; the console
  flashes for under a second. A Windows shortcut needs absolute paths, and
  Windows Script Host is being deprecated, so both were set aside.
- **Boundary with the backend.** The launcher imports only `core.config` and
  `core.startup`, which holds `StartupError(problem, fix)`, the running port,
  the upgrade service and `serve()`. Every `StartupError` becomes a message box;
  any other exception shows a fixed message box that points to
  `data/logs/app.log` (never the exception text, which could hold a key), and
  its traceback goes to the redacted log when logging is configured.
- **Launcher (`start.pyw`):**
  1. Bootstrap, before any other import: resolve the home from its own
     `__file__` (the parent of `launcher/`), put the code folder (`app/backend`
     in the zip, `backend` in a clone) and `launcher/` on `sys.path` (the
     embeddable package ignores the script folder and `PYTHONPATH`), set
     `CARDFACTORY_HOME`, and replace `sys.stdout` and `sys.stderr` with
     `os.devnull` handles when they are None (`pythonw.exe` has neither).
  2. Checks, with no Django and no network: the home and `data/` are writable
     and `.env` exists as a file; failures open a Windows message box through
     `ctypes` (tkinter is not part of the embeddable package) (RN-40).
  3. Takes the single-instance lock `data/launcher.lock` (`msvcrt.locking`) and
     keeps it for the life of the process. When the lock is held, a Card
     Factory from this folder is starting or running: the launcher waits up to
     30 seconds for `data/instance.json` (written by the running process with
     its port and process id), probes that port and opens a tab of it (RN-41,
     even when `APP_PORT` changed since it started), then exits.
  4. Loads the Django settings inside the `StartupError` handling; the port is
     `settings.RUNNING_PORT`, the single source for the probe, the bind and the
     status.
  5. Probes `http://127.0.0.1:<port>/api/instance` with `http.client` (never
     `urllib`, which applies the system proxy) and a 2-second timeout. Nothing
     answers → continue. A Card Factory whose home equals this one (compared
     after `os.path.realpath` and `os.path.normcase`) → opens a tab and exits; a
     Card Factory with another home → message naming `APP_PORT` that says
     another Card Factory uses it; any other answer, a timeout or a body that
     is not the instance JSON → message naming `APP_PORT` (RN-47). The bind
     stays the authority: a program that does not speak HTTP is caught there.
     An exclusive bind on `127.0.0.1:<port>`, closed at once and never
     listening, comes first: when it succeeds, the port is free and the probe
     is skipped. A timeout while connecting counts as nothing answering
     (Windows retries a refused loopback connection for about two seconds);
     a timeout waiting for the response gives the port message.
  6. Backs up the database and migrates (RN-42), marks orphan jobs failed.
  7. Binds waitress to `127.0.0.1` in a thread (exclusive address use, so no
     other program shares the port; a bind failure is a `StartupError` naming
     `APP_PORT`), writes `data/instance.json`, opens the default browser on
     `http://127.0.0.1:<port>/` (not `localhost`, which may try `::1` first).
  8. A watchdog stops the process when no heartbeat arrived for 180 seconds
     after the last one, or when no first heartbeat arrived within 120 seconds
     of the browser being opened, so a long upgrade does not use up the window
     (RN-41). It checks every 5 seconds and calls its stop callback at most
     once. The margin tolerates the timer throttling browsers
     apply to background tabs. Every running job (build, generation, art,
     quick adjustment) holds it; holds are counted (added with jobs, T13). Only
     the launcher creates the watchdog, never the app configuration or the
     settings, so `runserver` and the tests never stop on their own; a
     heartbeat with no watchdog does nothing. The frontend sends a
     heartbeat when it mounts, every 15 seconds, when the tab becomes visible
     again and on `pagehide`; when a heartbeat fails, it shows that the
     application stopped and how to start it again, and a later heartbeat that
     succeeds clears the notice. Accepted risks: a probe that reaches an
     instance in the moment its watchdog stops opens a tab that says the
     application stopped; a computer that sleeps for more than 180 seconds
     with no tab awake finds the application stopped.
- **Serving the frontend:** a catch-all Django view returns `index.html`; an
  explicit asset view serves `/assets/*` from the built folder, which works
  with `DEBUG` off. It sets the content types of `.js`, `.mjs` and `.css`
  itself, because Django's static file view guesses them through the Windows
  registry, which can map `.js` to `text/plain` and block the module script.
  `core.paths` resolves the built folder and keeps every asset inside it
  (no `..`, no NTFS stream names). No extra package.
- **Interface files:** the frontend has no `public/` folder. Only `index.html`
  and `/assets/*` are served, so a root file such as `/favicon.ico` would get
  `index.html` back. The favicon (SVG) lives in `frontend/src/assets/` and is
  linked from `index.html`, so Vite emits it under `/assets/` (or inlines it);
  fonts and icons follow the same path. SVG takes its type from the standard
  table (`image/svg+xml`). Nothing is loaded from a CDN or font service.
- **Clone (`start.cmd`, RN-45):** prepares `runtime/` and then calls the same
  launcher.
  - Downloads the embeddable Python (pinned version and SHA-256 in
    `release/versions.json`) from python.org, installs pip from PyPI's bootstrap
    and the pinned `backend/requirements.txt` from PyPI.
  - Downloads `frontend-dist-v{VERSION}.zip` from the GitHub release whose tag
    equals `VERSION`; no such release → message pointing to the latest release
    and to the development commands.
  - Works in `runtime/.staging/` and renames into place only when everything
    succeeded, then writes `runtime/prepared.json` (versions and hashes). Each
    run compares that file with `VERSION` and the pinned versions and redoes
    only what differs.
  - Uses `curl.exe` and `tar.exe`, shipped with Windows 10 and later. A console
    window shows progress during preparation; the person types nothing.
- **Release build (`release/build_release.py`, maintainer machine or CI):**
  builds the frontend, assembles the zip and the `frontend-dist` asset, and
  writes the version into both.

### 9.6 Role of existing cards (topic 6)

**Chosen: deterministic role patterns at build time plus model keywords at
request time.** During the import, `tag_roles()` applies a fixed list of
patterns over oracle text and type line and stores a multi-label `roles` list:
ramp, card draw, removal, board wipe, counterspell, tutor, recursion, tokens,
life gain, protection, combat boost, mana fixing, sacrifice outlet, graveyard
fill, evasion. Patterns are plain code, tested with fictional cards. Cards with
no match keep an empty list and are still found by FTS.

Classification rules (T20): reminder text in parentheses is ignored, and the
card's name and face names (and the short name of a legendary card) count as
the card itself. A mana ability is ramp only on a nonland face; a land or basic
land type card searched for and put onto the battlefield is ramp, or mana
fixing when the searching card is a land; any other library search is a tutor.
A land with two or more basic land types is mana fixing. Returning a permanent
to its owner's hand is not removal; exiling your own creature or a card in a
graveyard is not removal; an edict on opponents is removal, not a sacrifice
outlet, which needs a cost of sacrificing a creature, artifact or other
permanent. Lifelink is life gain. Trample is not evasion. Discard, milling and
surveil count as graveyard fill only for your own cards. A keyword the card
gives only itself (hexproof, indestructible) is not protection. Effects for an
opponent or a spell's target controller (draws, life, tokens) give no role.

| Option | For | Against |
|---|---|---|
| Patterns at build (chosen) | deterministic, fast, free, testable | misses unusual wordings |
| Model classification of every card at build | rich labels | tens of thousands of calls, cost and a key before first use, not repeatable |
| Community tags from Scryfall | curated | not in the bulk files; would need many API calls |
| No roles, FTS only | simplest | weak filtering by role |

The T26 evaluation measures whether the patterns plus keywords are good enough.

## 10. Data sources and Portuguese terms

- Scryfall bulk files: Oracle Cards (one record per card), Default Cards
  (printings in English, for base card printings and images), All Cards
  (streamed, keeping only Portuguese printings for terms). The bulk-data
  listing gives each file as gzip-compressed JSON Lines
  (`jsonl_download_uri`, `compressed_size`, one record per line); the older
  uncompressed JSON array (`download_uri`, `size`) is still accepted. Files are
  read as a stream, one record at a time, with the standard library, never
  loaded whole. Because the listed size is compressed, the free space needed
  is the download size times `BUILD_SPACE_FACTOR` = 10 (download, extract,
  database and the write-ahead log of the import); the Milestone 2 review
  checks it against a real build. Tests use hand-written fictional files.
  Requests send a descriptive User-Agent and Accept header, as Scryfall asks.
- Comprehensive Rules: the text file linked from the Wizards rules page; the
  importer finds the link and stores the sections. Keyword abilities (702),
  keyword actions (701), type lists (205) and the ability word list (207.2c)
  feed `Term` in English.
- Portuguese terms: type words come from aligning `printed_type_line` with
  `type_line` on Portuguese printings; keyword names from Portuguese printed text
  of cards whose English text starts with that keyword, by majority. A keyword
  with no Portuguese term found is reported as a skipped check instead of a
  rejection. Card languages are English and Portuguese (Brazil) only.
- *Trade-off:* All Cards is the largest file (gigabytes). It is downloaded once
  during the build and deleted after import. *Alternative:* paged API search of
  Portuguese printings; smaller download, but Scryfall asks for bulk files when
  many cards are needed.

## 11. Where each rule is guaranteed

| RN | Where | Main test |
|---|---|---|
| 01 | catalog.ingest writes `SourceRecord`; status shows it | ingest with fixture files |
| 02 | `.gitignore` for `data/`, `runtime/`; repository check script | CA-23 check |
| 03 | catalog.ingest single transaction; `BuildRun` | interrupted import |
| 04 | catalog.selectors.search_cards legality filter | banned card fixture |
| 05 | core.config | parser tests |
| 06 | core.config `Secret`, providers adapters, logging filter, explicit serializers | key-leak test across endpoints |
| 07 | providers.factory capabilities; generation pipeline provider-agnostic | three fake providers |
| 08 | core.config checks; status connection test | missing settings |
| 09 | cards.services.record_usage called by every adapter call site | usage on failure |
| 10 | generation services: no save before validation; error mapping | invalid response |
| 11 | api serializer for the request | missing fields |
| 12 | generation.text search plan; discard of invalid comparables | fake response with bad comparable |
| 13 | generation.text output schema | fields present |
| 14 | generation.text; cards.services status | invalid draft |
| 15 | generation.text one revision; save rejected; revision failure | two rejections |
| 16–20 | validators | one suite per validator |
| 22 | generation.text output schema; not part of `validate()` | indicator does not block |
| 23 | cards.services.edit_fields → validators, power_outdated | edit without provider |
| 24 | generation.text.quick_adjust | failed adjustment keeps version |
| 25 | cards.services.restore_version | restore creates version |
| 26 | cards.services and selectors | library after restart |
| 27 | release build; launcher | manual check |
| 28 | setup endpoint; frontend gate; disk errors mapped | first start |
| 29 | settings bind and hosts; only adapters, ingest and base image fetch open connections | network guard in tests |
| 30 | generation prompt language (en, pt); validators with `get_lexicon(lang)`; skipped checks for unknown Portuguese keyword terms | en and pt fixtures |
| 31–32 | generation.art; save after card; failure leaves no file | art failure |
| 33 | cards.services image storage; `images` endpoint; delete removes files | delete card |
| 34 | cards.services keeps image on edit; art creates version | edit keeps art |
| 35 | frontend Request and Result screens | component test |
| 36 | catalog.selectors.find_base_cards, list_printings | search fixture |
| 37 | generation.text prompt includes base snapshot | fake receives base |
| 38–39 | generation.art template; fetch_base_image cache and fallback | no-network fallback |
| 40, 47 | launcher checks and messages; `core.startup` errors; `core.config` unreadable file | launcher unit tests with a message recorder; CA-77 backend test; manual check |
| 41 | heartbeat endpoint, launcher watchdog, job runner hold, frontend hook | watchdog unit test; runner hold test |
| 42 | launcher backup and migrate | migration from older fixture database |
| 43 | cards.services.upload_image with header checks | renamed text file |
| 44 | generation.art size request; frontend fitted display; images endpoint | size and display tests |
| 45 | start.cmd, `runtime/prepared.json` | manual check |
| 46 | README user guide | review |
| 48 | art prompt artist credit; Result screen | fake adapter receives the credit; component test |
| 49 | frontend components and screens; Interface rules of `specs/code-standards.md` | component tests, manual check |
| 52 | screen switch sets the tab title; icon in `src/assets/` linked from `index.html` | title tests; built-file check; manual check of the icon |

Cross-site requests are refused by an origin check (section 8), tested on
every non-GET endpoint. Tests block outgoing connections globally (a fixture that fails any socket
connection), so CA-19 and the "tests never touch the network" rule hold.

## 12. Agents and folders they may change

| Agent | May change | Never changes |
|---|---|---|
| backend-dev | `backend/**` except `providers/` and `generation/`; `.env.example` | `frontend/`, `specs/`, `launcher/`, `release/`, tests |
| llm-engineer | `backend/providers/**`, `backend/generation/**` (adapters, factory, prompts, retrieval for the text model, generation pipelines, the search evaluation script) | models, catalog, validators, cards, api, tests |
| qa | test files: `backend/**/tests/**`, `backend/**/conftest.py`, `backend/pytest.ini`, `frontend/**/*.test.ts(x)`, `frontend/src/api/contract/**` (generated contract samples), `launcher/tests/**`, `release/tests/**`, test fixtures and helpers | production code |
| frontend-dev | `frontend/**` except tests | `backend/`, `specs/` |
| release-dev | `launcher/**`, `release/**` (except tests), `start.cmd`, `VERSION`, `.github/workflows/**`, `.gitignore`, `.gitattributes` | `backend/`, `frontend/` |
| docs-writer | `README.md`, `docs/**`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `.github/ISSUE_TEMPLATE/**`, `specs/manual-checks.md` | code, other `specs/` files |
| reviewer, spec-reviewer, architect | nothing (read only) | everything |

`specs/` (except `specs/manual-checks.md`) and `CLAUDE.md` change only with the
maintainer's approval. Any implementing agent may append rows to
`docs/DECISIONS.md`. Each agent reads `CLAUDE.md`, the spec and this plan; a
task names exactly one agent.

## 13. Dependencies

- Runtime (approved): Django, Django REST Framework, waitress; embeddable Python
  for the zip.
- Development: pytest, pytest-django (backend); Vite, TypeScript, React, Vitest,
  jsdom, @testing-library/react, @types/react and @types/react-dom (frontend,
  approved for T9). JSX is compiled by Vite's own esbuild, with no React
  plugin. Further testing helpers need approval in the task that first needs them.
- Versions: Python 3.12 (development and the embeddable package); Django 5.2
  LTS; Node 22.22.2 or later for frontend development, tests and the release
  build (required by jsdom), declared in `engines` of `frontend/package.json`.
- Not added: SDKs of the providers, `python-dotenv`, an image library, a router
  library (the frontend uses a small hash-based switch), a task queue (jobs run
  in a thread pool inside the process), an animation library, a component or
  icon library, and fonts from a CDN (the interface uses CSS transitions and
  local files; specs/code-standards.md, Interface).

### Tooling

- Type check: `npx tsc -b` (frontend).
- Tests: `pytest -q` (backend), `pytest launcher release` (launcher and release
  scripts, from the repository root), `npm run test` (frontend).
- Python formatter and linter: none in v1 until one is approved (ruff is the
  proposed option). No ESLint in v1.

## 14. Delivery in vertical slices

Milestones are vertical slices (`specs/tasks.md`, "Delivery method"): each one
ends with a capability demonstrated in the running application, across every
layer it needs. The structure in sections 2 to 13 is the target; each
milestone builds the part of it that its demo needs, and later milestones
extend models, endpoints, the API client, prompts, screens and the build
sources.

| Milestone | Demonstrable capability | Layers it adds |
|---|---|---|
| M0 Foundation | Status screen shows the configuration and the settings to fix | config, status endpoint, log, frontend skeleton served by Django, CI |
| M1 Double-click start | the locally built zip starts with a double click and stops after the last tab closes | server entry point, instance and heartbeat, watchdog, upgrade service, launcher, release zip, manual checklist |
| M2 Reference database | Setup screen builds the database from Oracle Cards; Status lists the source | jobs, catalog models, downloader, Oracle import, roles, build, setup endpoints and gate, Setup screen |
| M3 First card | a request becomes a validated, saved card shown on the Result screen, with OpenAI | provider protocol, OpenAI text adapter, factory, card models, usage, mana cost and color identity validators, comparables search, generation pipeline, Request and Result screens, key-leak sweep |
| M4 Text providers | the same request works with OpenAI, Anthropic and Google; Status tests the text key | Anthropic and Google text adapters, cross-provider test, connection test |
| M5 Rules validation | type line, keyword and limits validators with terms from the Comprehensive Rules | rules import, terms, lexicon, rules search in the draft call |
| M6 Library and versions | library, favorites, deletion, editing, quick adjustments, restore | library, edit, versions and adjustment endpoints and screens |
| M7 Art | generated and uploaded art, shown beside the card text | image adapters, art availability, image storage and serving, art pipeline, upload, art screens |
| M8 Base card | a chosen printing guides the design and is the art template | printings import, base card search, base image cache, template |
| M9 Portuguese cards | cards in Portuguese with every validation | Portuguese terms and lexicon, card language |
| M10 Public release | release zip and clone start for the public | release assets, clone start file, CI release, README, license, community files |

**Build sources by milestone.** M2 builds from Oracle Cards; M5 adds the
Comprehensive Rules, M8 Default Cards and M9 All Cards. During development, a
milestone that adds a source rebuilds the database by hand; whether a new
application version requires a rebuild (spec, open questions) is answered
in the Milestone 2 review (T89), before any milestone adds a source.

**Decisions that are expensive to change late** are exercised early: the
embeddable Python and FTS5 in M1, the SQLite concurrency between jobs and the
server in M2, the generation pipeline and the search quality evaluation in M3,
the provider protocol across the three text providers in M4, and the upgrade of
a data folder from an earlier zip in M6.

**End-to-end suite.** `backend/tests/e2e/` runs the demo path of every
milestone from M2 on through the API, with the fake provider, fictional source
files behind a fake transport and a temporary data folder. Each milestone adds
its flow; earlier flows keep passing.

**Migrations.** Development data folders are disposable. Before the first
public release, the migrations are replaced by one initial migration per app
(T125); the upgrade path of section 7 applies from that release on.

## 15. Verification

- Backend: `pytest -q` with the fake provider and the network guard; every test
  names the RN or CA it covers. It includes the end-to-end suite of section 14.
- Frontend: `npm run test` and `npx tsc -b`. Screen tests check the document
  title (`<Screen> · Card Factory`, CA-82) and a single `h1`; a check of the
  built files finds no external address (CA-38); the reviewer checks the
  rest of the Interface section of `specs/code-standards.md` (no gradients or
  pill shapes outside the tokens, no emojis in UI text, motion off
  under reduced motion, alt text on images).
- Manual checks on a Windows machine: the CAs marked manual (zip start,
  clone start, port in use, firewall prompt, browser close), listed in
  `specs/manual-checks.md` from Milestone 1 on and extended by later
  milestones, plus one end-to-end generation with a real key per text provider.
- Each milestone review runs its demo from the locally built zip (from
  Milestone 1 on): on a Windows computer with no Python or Node for Milestones
  1 and 10, on the development machine for the others.
- T26 counts recorded in the Milestone 3 review (T94), with the first generated cards.
