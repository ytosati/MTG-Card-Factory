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
  src/hooks/            heartbeat, job polling
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
| core | config loader, `Secret` type, data paths, Django secret key, `Job` model and runner, status service | none |
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
- `BuildRun`: status (running, ready, failed), started_at, finished_at, error,
  progress (RN-03, RN-28).
- `OracleCard`: `oracle_id` (Scryfall, primary key), name, mana_cost, cmc,
  type_line, oracle_text, colors, color_identity, keywords, power, toughness,
  layout, faces (JSON), commander_legality (legal, banned, not_legal),
  game_changer, edhrec_rank, roles (JSON list, section 9.6).
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
- `Card`: `id` (UUID4), created_at, favorite, language, current_version.
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
| core.config | `load_config()`, `get_config()`; `Secret.reveal()` used only by providers.factory |
| core.jobs | `submit(kind, fn)`, `get_job(id)`, `fail_orphan_jobs()` |
| core.status | `status_snapshot()` (no key values) |
| catalog.ingest | `run_build()`, `download_sources()`, `import_oracle()`, `import_printings()`, `import_rules()`, `import_pt_terms()`, `tag_roles()` |
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
`{"error": {"code": str, "message": str, "setting": str | null}}`, where
`setting` names the configuration setting to fix when there is one (RN-08).

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
| GET `usage?card=` | usage records | 09 |
| POST `heartbeat` / GET `instance` | tab liveness / identifies Card Factory on the port | 41, 47 |

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

**Concurrency.** SQLite runs in WAL mode with a busy timeout, because job
threads write while waitress threads read. Job and build progress is kept in
memory by the runner and persisted only at state changes (queued, running,
done, failed), so the long import transaction never blocks progress reads.

**All-or-nothing build (RN-03).** Two phases.
1. Download each source to `data/downloads/` and check size and checksum. A
   download can resume; it does not mark anything ready.
2. Import in a single SQLite transaction: delete reference rows, insert the new
   ones, rebuild the FTS tables, tag roles, mark the `BuildRun` ready, commit.
   An interruption rolls the transaction back; user tables are never touched.

*Alternative considered:* build into a second database file and swap it in.
Rejected: the user tables live in the same file (CLAUDE.md: a single SQLite
file), so a swap would need copying user data across.

**Stable identifiers.** Reference cards use the Scryfall `oracle_id`, printings
the Scryfall `id`; both survive a rebuild. User cards and images use UUID4.
Versions are numbered per card. A version stores a snapshot of its base card and
comparables, so a rebuild never breaks a saved card.

**Upgrades (RN-42).** On start, when migrations are pending, the launcher
copies the database to `data/backups/` (replacing the previous backup) and runs
them. If the database is newer than the
application (unknown migrations), it stops with a message instead of migrating.

## 8. Configuration, secret and status (topic 3)

- **Loading `.env`.** `core.config` is the only reader. It takes the file path as
  a parameter (the default is `.env` in the application home), so tests use
  temporary files with a cleared environment and never read the repository
  `.env`. A small parser in the standard library reads `KEY=VALUE` lines, ignores comments and blank lines,
  strips quotes, spaces and the UTF-8 byte-order mark that Notepad may add, and
  lets process environment variables override only when `CARDFACTORY_DEBUG=1`.
  It returns a frozen config object; keys are `Secret` objects whose text form
  is `***`. `get_config()` reads the file again when its modification time
  changed, so the Status screen and each generation see a fix without a restart
  (RN-08). The port is read once at startup; a changed port is reported as
  taking effect at the next start. An invalid `APP_PORT` falls back to 47821
  and is reported as a setting to fix (RN-47). Empty image settings only make
  art unavailable; set but invalid ones are settings to fix; `IMAGE_API_KEY`
  with no `IMAGE_PROVIDER` is ignored with a notice.
  *Alternative:* the `python-dotenv` package. Rejected to avoid a dependency for
  about forty lines.
- **Defaults and checks (RN-05, RN-07, RN-08).** No provider call at startup.
  The loader reports missing or unknown values as a list of "settings to fix".
  `IMAGE_API_KEY` falls back to `LLM_API_KEY` when art uses the text provider.
  `APP_PORT` defaults to 47821.
- **Django secret key.** On first start, `core` writes `data/secret_key` with a
  random value from the standard library and reads it on later starts. It is not
  the API key and is never shown. No action from the person.
- **Key protection (RN-06).** Only `providers.factory` calls `reveal()`.
  Adapters never put the key in exception text. A logging filter redacts the key
  values as a second line of defense. Serializers list fields explicitly; the
  status serializer has booleans only. A test sends every endpoint through a
  fake configuration and asserts the key never appears.
- **Settings.** `DEBUG` is on only when the environment variable
  `CARDFACTORY_DEBUG=1` is set (development; it is not in `.env.example`).
  `ALLOWED_HOSTS` is limited to `127.0.0.1` and `localhost`. The server always
  binds to `127.0.0.1`; there is no setting to change it in v1 (RN-29). Until
  the secret key task exists, settings use a development placeholder secret.
- **Cross-site requests.** Any web page open in the browser can send requests
  to `127.0.0.1`. Non-GET requests are refused unless `Origin` (or, when absent,
  `Referer`) is the application's own origin. DRF parsers are JSON only, except
  multipart on the upload endpoint, so a form post from another site is refused
  before it reaches a provider.
- **Logs.** With `pythonw.exe` there is no console, so the application logs to
  `data/logs/app.log` with size-based rotation. The key redaction filter applies
  to every handler. Logs record events, causes and identifiers, never card
  contents, prompts or keys.

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
Milestone 0 review confirms it in the embeddable Python planned for the zip. If
it is missing, the fallback is a `LIKE` search with the same filters. Base card
search by part of a name (RN-36) uses a case-insensitive `LIKE`, not FTS.

### 9.2 Provider factory and adapters (topic 2)

**Chosen: one adapter protocol, direct HTTP with the standard library.**
- Protocol: `complete_json(system, messages, schema) -> (data, usage)`;
  `generate_image(prompt, template_image | None, size) -> (bytes, mime, usage)`;
  `capabilities` (text, image, image_template).
- `providers.factory` is the only place that reads `LLM_PROVIDER` and
  `IMAGE_PROVIDER`, which accept only `openai`, `anthropic` and `google`
  (`IMAGE_PROVIDER`: `openai` and `google`). Tests replace the factory
  functions with a pytest fixture that returns the fake adapter; the fake is
  never selectable from `.env`.
- Keys travel only in request headers, never in URLs (for Google, the
  `x-goog-api-key` header), because URLs appear in exception text.
- Each adapter maps its errors to one set: `AuthError`, `QuotaError`,
  `ProviderUnavailable`, `InvalidResponse`, `ContentRefused`,
  `TemplateUnsupported`. Messages never include the key.
- Text calls request structured JSON output; the response is parsed and checked
  against the schema before use (invalid → `InvalidResponse`, RN-10).
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
  first start), `README.md`.
- **Start file:** a `.cmd` that runs `start "" python\pythonw.exe
  launcher\start.pyw` and exits; the console flashes for under a second. A
  Windows shortcut needs absolute paths, and Windows Script Host is being
  deprecated, so both were set aside.
- **Launcher (`start.pyw`):**
  1. Checks that it is not running from inside a zip (path under the temporary
     folder of the Explorer zip view), that the folder is writable, and that
     `.env` exists; failures open a Windows message box through `ctypes`
     (tkinter is not part of the embeddable package) (RN-40).
  2. Probes `127.0.0.1:APP_PORT/api/instance`: Card Factory answers → opens a
     tab and exits (RN-41); another program holds the port → message naming
     `APP_PORT` (RN-47).
  3. Backs up the database and migrates (RN-42), marks orphan jobs failed.
  4. Starts waitress on `127.0.0.1` in a thread, opens the default browser.
  5. A watchdog stops the process when no heartbeat arrived for 180 seconds
     after the last one, or when no first heartbeat arrived within 120 seconds
     of startup (RN-41). The margin tolerates the timer throttling browsers
     apply to background tabs. Every running job (build, generation, art,
     quick adjustment) holds it; holds are counted. The frontend sends a
     heartbeat every 15 seconds, when the tab becomes visible again and on
     `pagehide`; when heartbeats fail, it shows that the application stopped
     and how to start it again.
- **Serving the frontend:** a catch-all Django view returns `index.html`; assets
  are served by Django's static file view mapped explicitly to the built folder,
  which works with `DEBUG` off. No extra package.
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
  (streamed, keeping only Portuguese printings for terms). Bulk files are large JSON arrays, so they are read as a stream, one
  record at a time, with the standard library, never loaded whole (the exact
  layout is verified against a real file in T16).
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
| 40, 47 | launcher checks and messages | manual check |
| 41 | heartbeat endpoint, launcher watchdog, job runner hold, frontend hook | watchdog unit test; runner hold test |
| 42 | launcher backup and migrate | migration from older fixture database |
| 43 | cards.services.upload_image with header checks | renamed text file |
| 44 | generation.art size request; frontend fitted display; images endpoint | size and display tests |
| 45 | start.cmd, `runtime/prepared.json` | manual check |
| 46 | README user guide | review |
| 48 | art prompt artist credit; Result screen | fake adapter receives the credit; component test |
| 49 | frontend components and screens | component tests, manual check |

Cross-site requests are refused by an origin check (section 8), tested on
every non-GET endpoint. Tests block outgoing connections globally (a fixture that fails any socket
connection), so CA-19 and the "tests never touch the network" rule hold.

## 12. Agents and folders they may change

| Agent | May change | Never changes |
|---|---|---|
| backend-dev | `backend/**` except `providers/` and `generation/`; `.env.example` | `frontend/`, `specs/`, `launcher/`, `release/`, tests |
| llm-engineer | `backend/providers/**`, `backend/generation/**` (adapters, factory, prompts, retrieval for the text model, generation pipelines, the search evaluation script) | models, catalog, validators, cards, api, tests |
| qa | test files: `backend/**/tests/**`, `backend/**/conftest.py`, `backend/pytest.ini`, `frontend/**/*.test.ts(x)`, `launcher/tests/**`, `release/tests/**`, test fixtures and helpers | production code |
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
  jsdom and @testing-library/react (frontend, approved for T9). Further testing
  helpers need approval in the task that first needs them.
- Versions: Python 3.12 (development and the embeddable package); Django 5.2
  LTS.
- Not added: SDKs of the providers, `python-dotenv`, an image library, a router
  library (the frontend uses a small hash-based switch), a task queue (jobs run
  in a thread pool inside the process).

### Tooling

- Type check: `npx tsc -b` (frontend).
- Tests: `pytest -q` (backend), `pytest launcher release` (launcher and release
  scripts, from the repository root), `npm run test` (frontend).
- Python formatter and linter: none in v1 until one is approved (ruff is the
  proposed option). No ESLint in v1.

## 14. Suggested task order

Milestones for `specs/tasks.md`, which assigns the final IDs.

1. Foundations: backend skeleton, config and secret, network guard for tests,
   origin check, logging, CI for the test suites, frontend skeleton.
2. Reference data: catalog models and ingest, roles, search, T26 evaluation,
   Portuguese terms.
3. Validation: validators and lexicon.
4. Generation: provider protocol and fake, adapters, text pipeline, jobs,
   endpoints, usage.
5. Cards: library, editing, versions, quick adjustments.
6. Art: image adapters, art pipeline, uploads, base card images.
7. Frontend screens.
8. Distribution: launcher, release build, clone start file, README guide.

## 15. Verification

- Backend: `pytest -q` with the fake provider and the network guard; every test
  names the RN or CA it covers.
- Frontend: `npm run test` and `npx tsc -b`.
- Manual checks on a clean Windows machine: the CAs marked manual (zip start,
  clone start, port in use, firewall prompt, browser close), listed in
  `specs/manual-checks.md`, plus one end-to-end generation with a real key per
  text provider.
- T26 counts recorded in the Milestone A review (T27) before generation work relies on the search.
