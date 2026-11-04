# Tasks: Card Factory

Tasks derived from `specs/spec.md` (source of truth) and `specs/plan.md`.
Branches and commits cite the task ID (for example `feat/t29-color-identity-validator`
and `Refs: T29`), as described in `specs/git-standards.md`.

## Process

- One task at a time. Nothing outside the current task.
- A milestone starts only when the previous milestone is complete, with every
  test suite passing (`pytest -q` and `npm run test`).
- Each milestone has its own branch, created from `main` (`milestone/m0-foundation`,
  `milestone/ma-data`, `milestone/mb-validators`, `milestone/mc-generation`,
  `milestone/md-api-interface`, `milestone/me-release`). Each task of the
  milestone has its own branch, created from the milestone branch, and merges
  back into it. The milestone branch merges into `main` after its review task
  (`specs/git-standards.md`, section 2).
- Each milestone ends with a review task: run the test suites, check that every
  RN and CA listed for the milestone is covered by a passing test or a recorded
  manual check, and record the findings as new tasks or spec questions.
- Each task names exactly one agent and stays within the folders that agent may
  change (`specs/plan.md`, section 12). Review tasks are run by the maintainer.
- Tests never touch the network or a real provider. They use the fake provider
  and fictional cards written by hand, and cite the RN or CA they protect.
- No new dependency without approval.

## Milestone 0 — Foundation

### T1: Backend project skeleton
Create the Django project `cardfactory` and the empty apps `core`, `catalog`,
`providers`, `validators`, `generation`, `cards` and `api`, with pinned
`requirements.txt` (Django, Django REST Framework, waitress) and
`requirements-dev.txt` (pytest, pytest-django). Settings: `DEBUG` off unless a
development flag is set, `ALLOWED_HOSTS` limited to `127.0.0.1` and `localhost`,
and the SQLite database at `data/cardfactory.sqlite3`.
Covers: RN-29
Agent: backend-dev
Depends on: none
Done when: `pytest -q` passes, with a smoke test that checks the settings for allowed hosts, `DEBUG` and the database path.

### T2: Runtime folders ignored and repository content check
Make sure `.gitignore` covers `data/`, `runtime/`, `.env` and the built frontend.
Add a check script under `release/` that fails when the repository tracks card
data, rules text, card images or frame images (file types, sizes, known source
file names).
Covers: RN-02, CA-23
Agent: release-dev
Depends on: none
Done when: the check script exits with 0 on the repository and with an error on a test fixture folder that contains a fake bulk card file.

### T3: Test network guard
Add a global pytest fixture that fails any outgoing socket connection, so that
no test can reach the network or a provider.
Covers: RN-29, CA-19
Agent: backend-dev
Depends on: T1
Done when: `pytest -q` passes, and a test proves that an attempted connection fails with a clear error.

### T4: Configuration loader and settings to fix
Implement `core.config`, the only module that reads `.env`. It uses a
standard-library parser (comments, blank lines, quotes, spaces, UTF-8 byte-order
mark, environment override) and returns a frozen config. Keys are `Secret`
values that print as `***`. It reports a list of settings to fix: unknown
provider, missing key or model, and image settings checked separately, with the
image key falling back to the text key. `APP_PORT` defaults to 47821. Update
`.env.example` with a comment for each setting.
Covers: RN-05, RN-06, RN-07, RN-08, RN-27, RN-47, CA-05
Agent: backend-dev
Depends on: T1
Done when: parser and check tests pass for every case in RN-05 and RN-08, including the image key fallback and a `Secret` whose `str` and `repr` never reveal the value.

### T5: Django secret key and key redaction in logs
On first start, generate `data/secret_key` from the standard library and read it
on later starts. Add a logging filter that redacts the configured text and image
key values from every log record.
Covers: RN-06, CA-06
Agent: backend-dev
Depends on: T4
Done when: tests show that the secret key is created once and reused, and that a log record containing a key value is written with the value redacted.

### T6: Status endpoint (configuration part)
Add `GET /api/status` with the text provider, the model, whether a key is
configured (boolean), the image provider and image model, and the settings to
fix. Invalid configuration values never block startup. Add a reusable test
helper that calls endpoints with a fake configuration and asserts that no key
value appears in a response.
Covers: RN-06, RN-08, RN-40, CA-06, CA-46
Agent: backend-dev
Depends on: T4, T5
Done when: tests pass for a missing key (the setting is named, the response contains no key) and for a full configuration (the response contains booleans only, never the key).

### T7: Local server entry point
Provide a backend function that starts waitress on `127.0.0.1` and `APP_PORT`,
so the launcher calls it later. The host is fixed to the local machine unless a
documented override is set.
Covers: RN-29, RN-47, CA-20
Agent: backend-dev
Depends on: T4
Done when: a test checks that the entry point binds to `127.0.0.1` on the configured port without starting a real listener on another interface.

### T8: Instance and heartbeat endpoints with watchdog
Add `GET /api/instance`, which identifies Card Factory on the port, and
`POST /api/heartbeat`. Add a watchdog that calls a stop callback when no
heartbeat has arrived for 45 seconds after the first one.
Covers: RN-41, RN-47, CA-47
Agent: backend-dev
Depends on: T1
Done when: watchdog tests with a fake clock pass: no stop before the first heartbeat, no stop while heartbeats arrive, and a stop 45 seconds after the last one.

### T9: Frontend skeleton
Create the Vite, React and TypeScript app with Vitest, a single design-tokens
file, a small hash-based screen switch, a typed API client base, and a
placeholder Status screen that reads `/api/status`. All interface labels are in
English.
Covers: RN-30
Agent: frontend-dev
Depends on: T6
Done when: `npm run test` passes, with a test that renders the placeholder Status screen from a mocked API response, and `npm run build` produces the built files.

### T10: Django serves the built frontend
Every non-API path returns the built `index.html`, and `/assets/*` is served
from the built folder through an explicit static view that works with `DEBUG`
off. When no build is present, the response is a clear message that names the
build step.
Covers: RN-27, RN-33, CA-38
Agent: backend-dev
Depends on: T1, T9
Done when: tests with a fixture build folder pass for `index.html` on an unknown path, for an asset with the right content type, and for the message when no build is present.

### T11: Frontend heartbeat hook
Add a hook that sends a heartbeat every 15 seconds and on `pagehide`, mounted
once in the application root.
Covers: RN-41, CA-47
Agent: frontend-dev
Depends on: T8, T9
Done when: a Vitest test with fake timers shows the heartbeat calls at the right interval and on `pagehide`.

### T12: Milestone 0 review
Run both test suites. Check the coverage of RN-02, RN-05 to RN-08, RN-27,
RN-29, RN-30, RN-33, RN-40, RN-41 and RN-47 so far. Confirm that `runserver` and
the built frontend work together on `127.0.0.1`. Record the findings.
Covers: none (review)
Agent: maintainer
Depends on: T1–T11
Done when: both suites pass, and the findings are recorded as new tasks or as spec questions.

## Milestone A — Data

### T13: Job model and in-process runner
Add the `Job` model and the runner: a thread pool with `submit`, `get_job`, and
`fail_orphan_jobs`, which marks jobs left running as failed. Add
`GET /api/jobs/{id}` with progress, result and error message.
Covers: RN-03, RN-10, RN-41
Agent: backend-dev
Depends on: T12
Done when: tests pass for a successful job, a failing job (clear message, no partial result) and the orphan cleanup.

### T14: Catalog models and full-text tables
Add `SourceRecord`, `BuildRun`, `OracleCard`, `Printing`, `RuleSection` and
`Term`. Add the FTS5 tables `oracle_fts` and `rules_fts` through a migration
with fixed SQL. Add the `is_ready()` selector.
Covers: RN-01, RN-03, RN-04
Agent: backend-dev
Depends on: T12
Done when: migrations apply on an empty database, and tests show that the FTS5 tables accept parameterized queries and that `is_ready()` is false until a `BuildRun` is ready.

### T15: Source downloader
Download each source to `data/downloads/` with the standard library, a
descriptive User-Agent and an Accept header. Downloads can resume, and size and
checksum are checked. Errors map to clear causes (no network, source failure,
disk full). The retry count is a named parameter until the spec decides it.
Covers: RN-01, RN-03, RN-28, RN-29
Agent: backend-dev
Depends on: T14
Done when: tests with a fake transport pass for success, resume, checksum mismatch, network failure and disk full, and assert the User-Agent header.

### T16: Oracle cards import with Commander legality
Import the Oracle Cards bulk file line by line into `OracleCard`, including
faces, Commander legality (legal, banned, not legal), the Game Changer flag and
EDHREC rank.
Covers: RN-01, RN-04
Agent: backend-dev
Depends on: T14
Done when: an import test with a hand-written fictional bulk file stores the expected rows and legality values.

### T17: Printings import
Import the Default Cards bulk file into `Printing`: set, collector number,
frame, border, frame effects, release date and the image URL of each face.
Covers: RN-36, RN-38
Agent: backend-dev
Depends on: T16
Done when: an import test with a fictional bulk file stores the printings, including a two-faced card with one image URL per face.

### T18: Comprehensive Rules import and English terms
Find the rules text link on the official rules page, store the sections in
`RuleSection`, and derive the English `Term` rows for card types, supertypes,
subtypes, keyword abilities and keyword actions (sections 205, 701 and 702).
Covers: RN-01, RN-18, RN-19
Agent: backend-dev
Depends on: T14
Done when: tests with a fictional rules page and a fictional rules text extract the link, the sections and the expected terms.

### T19: Portuguese terms
Stream the All Cards bulk file and keep only Portuguese printings. Derive
Portuguese type words by aligning the printed type line with the type line, and
keyword names by majority from the printed text. Keywords without a Portuguese
term are recorded as missing.
Covers: RN-30
Agent: backend-dev
Depends on: T18
Done when: tests with fictional Portuguese printings produce the expected type and keyword terms, and the missing keywords are listed.

### T20: Role tagging
Implement `tag_roles()` with fixed patterns over rules text and type line for
the roles listed in plan section 9.6. Cards with no match keep an empty list.
Covers: RN-12
Agent: backend-dev
Depends on: T16
Done when: tests with fictional cards pass, with at least one positive and one negative example for each role.

### T21: All-or-nothing build and management command
Implement `run_build()` and the `build_catalog` management command. Downloads
come first. The imports, the FTS rebuild, the role tagging, the `SourceRecord`
rows and the ready mark run in one transaction that never touches user tables.
When the database is ready, a new run downloads nothing.
Covers: RN-01, RN-03, RN-28, CA-07, CA-08
Agent: backend-dev
Depends on: T13, T15, T16, T17, T18, T19, T20
Done when: tests pass for an interrupted import (not ready, no duplicates after a rerun), a rerun on a ready database (no download), and a disk-full failure (the cause is reported).

### T22: Setup endpoints and readiness gate
Add `GET /api/setup` (build progress) and `POST /api/setup/build`, which starts
the build as a job. Extend `/api/status` with readiness and the date and origin
of each source. Every endpoint except status, setup, jobs, instance and
heartbeat answers with a clear "database not ready" error until the build is
ready.
Covers: RN-01, RN-28, CA-08, CA-18
Agent: backend-dev
Depends on: T21
Done when: tests pass for the gate before and after a ready build, for progress reporting, and for the sources listed in status.

### T23: Comparables search
Implement `search_cards(query, filters)`. It filters by color identity within
the request, Commander legality, roles, types and mana value. Banned cards come
back only marked as counterexamples. The power level shapes the candidates.
Results are ranked with FTS5 BM25 and widened deterministically when there are
too few.
Covers: RN-04, RN-12, CA-24
Agent: backend-dev
Depends on: T21
Done when: tests with fictional cards pass for the identity filter, the banned counterexample marking, the power level shaping and the widening order.

### T24: Rules search and lexicon selectors
Implement `search_rules(keywords)` over `rules_fts`, plus the sections of the
keywords a draft uses. Implement `get_lexicon(lang)` for English and Portuguese
terms, including the missing Portuguese keywords.
Covers: RN-12, RN-18, RN-19, RN-30
Agent: backend-dev
Depends on: T21
Done when: tests with fictional rules and terms pass for both selectors, including a language with no lexicon.

### T25: Base card search selectors
Implement `find_base_cards(name)`, a search by part of the name over every
card (banned cards included), and `list_printings(oracle_id)`, which returns
the printings with their faces.
Covers: RN-36, CA-41
Agent: backend-dev
Depends on: T21
Done when: tests pass for a partial name that matches a banned card, and for a two-faced card that lists both faces.

### T26: Search quality evaluation
The evaluation that decides on embeddings (plan section 9.1). Write twenty
requests that cover the main roles, every color and the three power levels,
plus a manual script outside the test suite that prints the top ten candidates
against a real local database. Check that the Python build planned for the zip
has FTS5 enabled. Commit only the request texts and the counts.
Covers: RN-04, RN-12
Agent: backend-dev
Depends on: T23
Done when: the counts are recorded and the pass rule is applied (at least 16 of 20 requests with five or more relevant cards). On a fail, the failed requests are listed with a proposal for approval.

### T27: Milestone A review
Run both test suites. Check the coverage of RN-01, RN-03, RN-04, RN-12, RN-28,
RN-30, RN-36, CA-07, CA-08, CA-18, CA-24 and CA-41 so far. Run `build_catalog`
once on a real machine. Confirm the outcome of T26. Record the findings.
Covers: none (review)
Agent: maintainer
Depends on: T13–T26
Done when: both suites pass, a real build reaches ready, and the findings are recorded.

## Milestone B — Validators

### T28: Validation result and mana cost validator
Define the `ValidationResult` (status, causes, skipped checks) and the
`validate(card, lexicon)` composition with no Django imports. Add the mana cost
validator: a well-formed cost and a stated mana value that matches it.
Covers: RN-17, CA-02
Agent: backend-dev
Depends on: T27
Done when: tests pass, including CA-02: the cost {2}{G} with a stated value of 4 is rejected and the cause is named.

### T29: Color identity validator
Compute the color identity from the cost and the rules text (hybrid, Phyrexian
and colored symbols in text) and reject anything outside the requested
identity.
Covers: RN-16, CA-01
Agent: backend-dev
Depends on: T28
Done when: tests pass, including CA-01: a green request with a blue symbol in the text is rejected with the cause.

### T30: Type line validator
Check every card type, supertype and subtype against the lexicon.
Covers: RN-18, CA-03
Agent: backend-dev
Depends on: T28
Done when: tests pass for valid English and Portuguese type lines and for an unknown subtype (CA-03).

### T31: Keyword validator
Check every keyword ability and keyword action used in the text against the
lexicon.
Covers: RN-19, CA-04, CA-54
Agent: backend-dev
Depends on: T28
Done when: tests pass for an unknown English keyword (CA-04) and an unknown Portuguese keyword (CA-54, first part).

### T32: Text limits validator
Check the number of abilities and the text length against named parameters.
The values stay [DECIDE] in RN-20, and CA-28 can only be finished once the spec
sets them.
Covers: RN-20, CA-28
Agent: backend-dev
Depends on: T28
Done when: tests with parameter values pass, rejecting a text over each limit and naming the exceeded limit. The final values are applied once the spec decides them.

### T33: Language-aware validation and skipped checks
`validate()` runs every check for English and Portuguese. For other languages
it runs color identity, mana cost and limits, and lists the type and keyword
checks as skipped. A Portuguese keyword with no known term is listed as skipped
instead of rejected.
Covers: RN-30, CA-54
Agent: backend-dev
Depends on: T29, T30, T31, T32
Done when: tests pass for a Japanese card (CA-54, second part) and for a Portuguese keyword with no term.

### T34: Milestone B review
Run both test suites. Check the coverage of RN-16 to RN-20, RN-30, CA-01 to
CA-04, CA-28 and CA-54. Confirm that validators import no Django models and make
no network or provider call. Record the findings.
Covers: none (review)
Agent: maintainer
Depends on: T28–T33
Done when: both suites pass, and the findings are recorded.

## Milestone C — Providers and generation

### T35: Provider protocol, error set and fake adapter
Define the adapter protocol (`complete_json`, `generate_image`,
`capabilities`) and the error set (`AuthError`, `QuotaError`,
`ProviderUnavailable`, `InvalidResponse`, `ContentRefused`,
`TemplateUnsupported`). Add a scriptable fake adapter for text and images that
records the calls it receives.
Covers: RN-07, RN-10
Agent: backend-dev
Depends on: T34
Done when: tests show that the fake adapter returns scripted responses, raises scripted errors and records the calls.

### T36: Provider factory and art availability
Implement `providers.factory`, the only reader of `LLM_PROVIDER` and
`IMAGE_PROVIDER` and the only caller of `Secret.reveal()`. It provides
`text_adapter()`, `image_adapter()` and `art_availability()` (reason and
setting that enables art). Extend `/api/status` with art availability.
Covers: RN-05, RN-06, RN-07, RN-08, CA-32, CA-33, CA-34
Agent: backend-dev
Depends on: T35
Done when: tests pass for Anthropic with no image provider (art unavailable, setting named), Anthropic with an image provider (image adapter returned), and invalid image settings (text still available).

### T37: Card models and version service
Add `Card`, `CardVersion` (immutable, numbered per card), `CardImage`,
`BaseCardImage` and `UsageRecord`. Add `save_version()`, which creates a version
and moves `current_version` in one transaction.
Covers: RN-14, RN-25, RN-26
Agent: backend-dev
Depends on: T34
Done when: tests pass for version numbering, immutability and an atomic save that leaves nothing behind on error.

### T38: Usage recording and usage endpoint
Implement `record_usage()` (text: tokens; image: number of images and size;
outcome ok or failed; card optional), `usage_for(card)`, and `GET /api/usage`
with text and art kept separate.
Covers: RN-09, CA-16, CA-35
Agent: backend-dev
Depends on: T37
Done when: tests pass for a text record, an image record, a failed record with no card, and the separated endpoint output.

### T39: Shared HTTP transport for adapters
A standard-library HTTP helper with fixed timeouts, one retry on 5xx and
network errors, multipart support, and mapping of status codes to the error
set. Error messages never contain the key or the authorization header.
Covers: RN-06, RN-10, RN-29
Agent: backend-dev
Depends on: T35
Done when: tests with a fake transport pass for the timeout, the retry and the mapping, and assert that the key is absent from every error text.

### T40: OpenAI text adapter
JSON-structured completion for OpenAI. Usage is read from the response, and the
JSON is checked against the schema (invalid means `InvalidResponse`).
Covers: RN-07, RN-08, RN-10, CA-06, CA-25
Agent: backend-dev
Depends on: T39
Done when: tests with recorded fictional responses pass for success, rejected key, usage limit and invalid JSON.

### T41: Anthropic text adapter
The same contract as T40, for Anthropic.
Covers: RN-07, RN-08, RN-10, CA-06, CA-25
Agent: backend-dev
Depends on: T39
Done when: the T40 test set passes against the Anthropic adapter with its own recorded fictional responses.

### T42: Google text adapter
The same contract as T40, for Google.
Covers: RN-07, RN-08, RN-10, CA-06, CA-25
Agent: backend-dev
Depends on: T39
Done when: the T40 test set passes against the Google adapter with its own recorded fictional responses.

### T43: OpenAI image adapter
Image generation without a template and image edit with a template. It requests
the portrait size closest to the card proportions, at least 745 × 1040 when the
model allows it. Content-policy refusals and unsupported templates map to the
error set.
Covers: RN-31, RN-32, RN-38, RN-44, CA-50
Agent: backend-dev
Depends on: T39
Done when: tests pass for the size choice, the template request, a refusal and a model without template support.

### T44: Google image adapter
Image models that accept an input image (template) and Imagen without a
template. Size choice and error mapping are the same as in T43.
Covers: RN-31, RN-32, RN-38, RN-44, CA-50
Agent: backend-dev
Depends on: T39
Done when: the T43 test set passes against the Google adapter.

### T45: Connection test endpoint
`POST /api/status/connection-test` tries the text key and, when set, the image
key. Each result is reported separately and names the setting to fix.
Covers: RN-08, CA-25, CA-34
Agent: backend-dev
Depends on: T36, T40, T41, T42, T43, T44
Done when: tests with the fake adapter pass for a valid text key with an invalid image key (the image key setting is named, text is reported working) and for a rejected text key.

### T46: Generation prompts and output schemas
Prompts and JSON schemas for the design intent and search plan, the card draft
(fields, rationale, comparables, power indicator with justification), the
revision and the quick adjustments. They include the card language (English by
default) and the base card snapshot.
Covers: RN-12, RN-13, RN-22, RN-30, RN-37, CA-21, CA-22, CA-42
Agent: backend-dev
Depends on: T35
Done when: tests pass for the prompt content (language, base card name and rules text) and for schema checks on valid and invalid fictional responses.

### T47: Draft pipeline
Steps: the design intent and search plan, `search_cards`, `search_rules`, the
draft, and the discard of comparables that were not returned as legal (none
left means `InvalidResponse`). The power indicator comes from the model and is
not a validation.
Covers: RN-12, RN-13, RN-22, RN-37, CA-24, CA-27, CA-29, CA-42, CA-56
Agent: backend-dev
Depends on: T23, T24, T36, T46
Done when: tests with the fake adapter pass for a discarded and a banned comparable (CA-56), no valid comparable left, the base card snapshot sent (CA-42) and a "too strong" indicator kept.

### T48: Validation, one automatic revision and saving
Validate the draft. Allow at most one revision. Save the result as approved or
rejected with its causes, and save the first draft as rejected when the
revision call fails. Record usage for every call, including failures. Invalid
responses save no card.
Covers: RN-09, RN-10, RN-14, RN-15, CA-10, CA-11, CA-14, CA-15, CA-16
Agent: backend-dev
Depends on: T33, T38, T47
Done when: tests pass for CA-10, CA-11 (both cases), CA-14 (three fake providers, same validation result), CA-15 and CA-16 (two records for a draft and its revision, a record for a failure with no card).

### T49: Generation endpoint and request serializer
`POST /api/generations` validates the request (idea, color identity and power
level required; language, base card with printing and face, art option) and
checks the configuration before any provider call. It then starts the
generation as a job.
Covers: RN-08, RN-11, CA-05, CA-25, CA-26
Agent: backend-dev
Depends on: T13, T22, T48
Done when: tests pass for each missing field being named (CA-26), invalid configuration with no provider call and no card (CA-05), and a rejected key with no card (CA-25).

### T50: Image storage service
`attach_image()` stores image bytes under `data/images/cards/{card_id}/` and
creates a new version that keeps the text fields. A failure leaves no file.
Deleting a card removes the image files of every version.
Covers: RN-33, RN-34
Agent: backend-dev
Depends on: T37
Done when: tests in a temporary data folder pass for the stored file, the new version, cleanup after a failed write, and deletion of every image.

### T51: Art pipeline
`generate_art(card, description)` runs after the card is saved, for approved and
rejected cards alike. It builds the prompt from the card fields, uses the base
printing image as template when it is cached, and falls back to no template
otherwise. It records usage, and on failure keeps the card unchanged with the
cause. A generation job with art requested chains this step.
Covers: RN-09, RN-31, RN-32, RN-38, RN-39, RN-44, CA-33, CA-35, CA-36, CA-37, CA-43, CA-44
Agent: backend-dev
Depends on: T43, T44, T49, T50
Done when: tests with the fake adapter pass for CA-36 (no image request without art; card fields sent), CA-37, CA-43, the template fallback from CA-44, and image usage recorded (CA-35).

### T52: Quick adjustment service
`quick_adjust(card, kind)` (stronger, weaker, cheaper, more expensive, simplify
text) is a text generation with no automatic revision. It validates the result,
reassesses the power indicator, clears the outdated mark, keeps the art and
records usage. On failure the current version is unchanged.
Covers: RN-09, RN-23, RN-24, RN-34, CA-30, CA-39, CA-55
Agent: backend-dev
Depends on: T48, T50
Done when: tests pass for CA-30 (both cases), no image request and art kept (CA-39), and the outdated mark removed (CA-55).

### T53: Milestone C review
Run both test suites. Check the coverage of RN-05 to RN-15, RN-22, RN-24,
RN-31 to RN-39 and RN-44, and their CAs so far. Confirm that call sites never
branch on the provider and that only the factory reveals keys. Record the
findings.
Covers: none (review)
Agent: maintainer
Depends on: T35–T52
Done when: both suites pass, and the findings are recorded.

## Milestone D — API and interface

### T54: Library API
`GET /api/cards?favorite=`, `GET /api/cards/{id}` (current version, image
reference and usage), favorite through `PATCH`, and `DELETE`, which removes the
card, its versions and every image file.
Covers: RN-26, RN-33, CA-31
Agent: backend-dev
Depends on: T53
Done when: tests pass for CA-31: listed after a new test client session, listed among the favorites, and gone with no image files left after deletion.

### T55: Edit with revalidation
`PATCH /api/cards/{id}` with card fields calls `edit_fields()`. It creates a
new version, revalidates it with no provider call, keeps the art and the power
indicator, and marks the indicator as possibly outdated.
Covers: RN-23, RN-25, RN-34, CA-12, CA-39, CA-55
Agent: backend-dev
Depends on: T54
Done when: tests pass for CA-12, the art kept on edit (CA-39) and the outdated mark set with no provider call (CA-55).

### T56: Versions and restore API
`GET /api/cards/{id}/versions` and `POST .../versions/{n}/restore`. A restore
creates a new version with the fields and the art of version n, revalidated.
Covers: RN-25, RN-34, CA-13, CA-39
Agent: backend-dev
Depends on: T54
Done when: tests pass for CA-13 and for restoring the earlier art after new art was added (CA-39).

### T57: Quick adjustment endpoint
`POST /api/cards/{id}/adjustments` starts `quick_adjust` as a job.
Covers: RN-24, CA-30
Agent: backend-dev
Depends on: T54
Done when: endpoint tests with the fake adapter pass for success and for failure (current version unchanged, cause in the job error).

### T58: Art generation endpoint and image serving
`POST /api/cards/{id}/art` starts art generation as a job when art is
available, or refuses with the reason and the setting. `GET /api/images/{id}`
returns the stored file unchanged, with its content type.
Covers: RN-07, RN-31, RN-32, RN-33, RN-44, CA-32, CA-37, CA-38, CA-50
Agent: backend-dev
Depends on: T54
Done when: tests pass for an unavailable art option with no image request (CA-32), retrying art alone (CA-37), and byte-identical image serving (CA-50).

### T59: Image upload
`POST /api/cards/{id}/art/upload` accepts PNG, JPEG and WebP up to 10 MB,
checked by content. It reads the dimensions from the file headers with the
standard library, adds the low print-quality notice below 745 × 1040, and makes
no provider call and no usage record.
Covers: RN-43, RN-44, CA-49, CA-50
Agent: backend-dev
Depends on: T54
Done when: tests pass for CA-49 (PNG accepted as a new version; a renamed text file and an oversized file refused with the reason) and for a 400 × 560 image accepted with the notice (CA-50).

### T60: Base card endpoints and base image cache
`GET /api/catalog/cards?q=` and `GET /api/catalog/cards/{oracle_id}/printings`.
Choosing a printing fetches its image once through `fetch_base_image()` into
`data/images/base/`. A download failure is reported with its cause, and the
base card stays usable as a design example.
Covers: RN-29, RN-36, RN-39, CA-19, CA-41, CA-44
Agent: backend-dev
Depends on: T54
Done when: tests pass for the search with no network (CA-41), a download failure with the cause reported (CA-44), and a second choice with no download.

### T61: Key-leak and outgoing connection sweep
One test sends every endpoint, including failures and provider errors, through
a fake configuration and asserts that no key value appears. A second test
checks that connections are only attempted by the adapters, the ingest
downloader and the base image fetch.
Covers: RN-06, RN-29, CA-06, CA-19
Agent: backend-dev
Depends on: T55, T56, T57, T58, T59, T60
Done when: both sweep tests pass over the full endpoint list from plan section 6.

### T62: App shell, API client, job polling and readiness gate
Extend the typed API client to the full endpoint list. Add a job polling hook.
The app shell opens the Setup screen while the database is not ready and allows
only Status during the build.
Covers: RN-28, CA-18
Agent: frontend-dev
Depends on: T61
Done when: Vitest tests pass for the gate (not ready: Setup and Status only; ready: every screen) and for job polling until done or failed.

### T63: Setup screen
Shows the build progress, starts the build when needed, shows the cause of a
failure with a retry, and links to Status.
Covers: RN-28, CA-18
Agent: frontend-dev
Depends on: T62
Done when: Vitest tests pass for progress, failure with its cause, and the move to the normal screens when ready.

### T64: Status screen
Text provider, model and key configured (yes or no); image provider, image
model and art availability with its reason; date and origin of each source;
the settings to fix; and a connection test button.
Covers: RN-01, RN-07, RN-08, RN-40, CA-08, CA-32, CA-34, CA-46
Agent: frontend-dev
Depends on: T62
Done when: Vitest tests pass for a missing key setting named (CA-46), unavailable art with its reason (CA-32), the listed sources, and connection test results.

### T65: Request screen
Theme, color identity, power level and card language (English by default).
Optional art: generated (with a description and the billing notice) or
uploaded, shown as unavailable with the reason when art is not available.
Missing required fields are named and the request is not sent.
Covers: RN-07, RN-11, RN-30, RN-35, RN-43, CA-21, CA-26, CA-32, CA-40
Agent: frontend-dev
Depends on: T62
Done when: Vitest tests pass for CA-26, the billing notice before sending (CA-40), unavailable art (CA-32) and English as the default language.

### T66: Base card picker
Search by part of the name, then choose the printing and, for cards with more
than one face, the face. A failed image download shows its cause.
Covers: RN-36, RN-39, CA-41, CA-44
Agent: frontend-dev
Depends on: T65
Done when: Vitest tests pass for picking a face of a two-faced card and for the download failure message.

### T67: Result screen: card display
The card image fitted into a card-shaped area (whole image, proportions kept,
loaded only from the local application) beside the card text in rules format,
or the text alone. Also the design intent, rationale, comparables, base card,
power indicator with its justification and outdated mark, skipped checks, and
the approved or rejected status with its causes.
Covers: RN-12, RN-13, RN-14, RN-15, RN-22, RN-30, RN-33, RN-44, CA-21, CA-22, CA-27, CA-29, CA-38, CA-50
Agent: frontend-dev
Depends on: T62
Done when: Vitest tests pass for a card with and without an image, a rejected card with its causes, a "too strong" indicator on an approved card, and image sources limited to local paths.

### T68: Result screen: art actions, notices and usage
Generate, retry or upload art (with the billing notice); open the image at full
resolution; the outdated-text notice after an edit or adjustment; and usage
with text and art shown separately.
Covers: RN-09, RN-23, RN-32, RN-34, RN-35, RN-43, RN-44, CA-16, CA-35, CA-37, CA-39, CA-40, CA-55
Agent: frontend-dev
Depends on: T67
Done when: Vitest tests pass for the art failure cause with retry, the outdated-text notice, the separate usage lists and the full-resolution link.

### T69: Adjustments and versions screen
Edit fields with the revalidation result shown right away, the quick
adjustments, new or uploaded art, and the version list with restore.
Covers: RN-23, RN-24, RN-25, RN-34, RN-43, CA-12, CA-13, CA-30, CA-39, CA-49
Agent: frontend-dev
Depends on: T67
Done when: Vitest tests pass for an edit that ends rejected (CA-12), a restore that appears as a new version (CA-13), a failed adjustment with its cause (CA-30), and a refused upload with its reason (CA-49).

### T70: Library screen
Saved cards with an image thumbnail when present, a favorites filter, and
deletion with confirmation.
Covers: RN-26, RN-33, CA-31
Agent: frontend-dev
Depends on: T62
Done when: Vitest tests pass for the list, the favorites filter and the removal after deletion.

### T71: Milestone D review
Run both test suites. Check the coverage of every RN and CA in the screens and
API sections. Run the built frontend served by Django against a real build with
a real provider by hand. Record the findings.
Covers: none (review)
Agent: maintainer
Depends on: T54–T70
Done when: both suites pass, a full manual flow (request, result, art, edit, adjustment, restore, library) works, and the findings are recorded.

## Milestone E — Open-source release

### T72: Database upgrade service
A backend function, called by the launcher, that copies the database to
`data/backups/`, runs pending migrations, marks orphan jobs failed, and stops
with a clear message when the database is newer than the application.
Covers: RN-42, CA-48
Agent: backend-dev
Depends on: T71
Done when: tests pass for an upgrade from an older fixture database that keeps every card, version and image record (CA-48), and for the refusal of a newer database.

### T73: VERSION file and launcher prerequisite checks
Add `VERSION` and `launcher/start.pyw` checks: not started from inside a zip,
folder writable, `.env` present, and the port free or held by Card Factory.
Each failure shows a Windows message box (through `ctypes`) that names the
problem and the fix.
Covers: RN-40, RN-47, CA-17, CA-53
Agent: release-dev
Depends on: T71
Done when: unit tests for each check pass with the message box replaced by a recorder, including the message that names `APP_PORT`.

### T74: Launcher startup sequence
When a running Card Factory answers on the port, open a new tab and exit.
Otherwise run the upgrade service, start the local server entry point, open the
default browser, and wire the watchdog to stop the process.
Covers: RN-29, RN-41, RN-42, CA-20, CA-47, CA-48
Agent: release-dev
Depends on: T72, T73
Done when: unit tests with fakes pass for the order of steps, the second-start path (new tab, no second server) and the stop on watchdog.

### T75: Release build script
`release/build_release.py` and `release/versions.json` (pinned embeddable
Python and hashes). It builds the frontend and assembles the Windows zip
(`python/`, `app/`, `launcher/`, `Start Card Factory.cmd`, `.env` from
`.env.example`, `README.md`) and the `frontend-dist-v{VERSION}.zip` asset. The
repository content check runs first.
Covers: RN-02, RN-27, CA-23, CA-45
Agent: release-dev
Depends on: T2, T74
Done when: running the script on a Windows machine produces both archives with the expected layout and the version written into both.

### T76: Clone start file: runtime preparation
`start.cmd` prepares `runtime/` in `runtime/.staging/`: the pinned embeddable
Python from python.org, pip and the pinned requirements from PyPI. It renames
into place only on success, writes `runtime/prepared.json`, and redoes only what
differs.
Covers: RN-29, RN-45, CA-51
Agent: release-dev
Depends on: T75
Done when: a manual run on Windows prepares the runtime, a second run downloads nothing, and an interrupted run is redone on the next start.

### T77: Clone start file: built interface by version
Download `frontend-dist-v{VERSION}.zip` from the GitHub release whose tag
equals `VERSION`. When no such release exists, show a message that points to
the latest release and to the development commands. Then call the launcher.
Covers: RN-45, CA-51
Agent: release-dev
Depends on: T76
Done when: a manual run on a released version starts the application, and a run with an unreleased `VERSION` shows the message.

### T78: CI workflow
A workflow that runs both test suites on every push and pull request, and on a
version tag builds the frontend, the release zip and the `frontend-dist` asset
as release artifacts. Publishing a release stays a maintainer action.
Covers: RN-27, RN-45
Agent: release-dev
Depends on: T75
Done when: the workflow file passes a syntax check, and a run on a branch (authorized by the maintainer) executes the test jobs.

### T79: README user guide
A user guide for the zip and for a clone: every setting of the configuration
file (text provider, model, key, image provider, image model with an example
value for OpenAI and for Google, image key, local port), the first-run build,
upgrading by copying `data/` and `.env`, and the development commands for other
systems.
Covers: RN-27, RN-42, RN-45, RN-46, CA-52
Agent: docs-writer
Depends on: T77
Done when: every setting in `.env.example` appears in the guide for both install paths, checked line by line.

### T80: License
Add the license file chosen by the maintainer and reference it in the README.
Covers: none (open question in the spec)
Agent: docs-writer
Depends on: T79, the maintainer's license decision
Done when: the license file is present and the README names it.

### T81: Community files
Contributing guide (spec-first workflow, tests with the fake provider, git
standards), code of conduct, and issue templates for bug reports and feature
requests.
Covers: none (project files)
Agent: docs-writer
Depends on: T80
Done when: the files exist and the README links to them.

### T82: Manual acceptance checklist
`docs/manual-checks.md` with step-by-step checks on a clean Windows machine for
CA-17, CA-20, CA-45, CA-47, CA-51 and CA-53, each with the expected result.
Covers: CA-17, CA-20, CA-45, CA-47, CA-51, CA-53
Agent: docs-writer
Depends on: T77
Done when: each listed CA has steps and an expected result.

### T83: Clean-machine installation test
Run `docs/manual-checks.md` on a Windows computer with no Python or Node, once
from the release zip and once from a fresh clone.
Covers: RN-27, RN-29, RN-40, RN-41, RN-45, RN-47, CA-17, CA-20, CA-45, CA-47, CA-51, CA-53
Agent: maintainer
Depends on: T78, T81, T82
Done when: every check in the checklist is recorded as passed, or failures are recorded as new tasks.

### T84: Milestone E review
Run both test suites and the repository content check. Confirm that every RN and
CA in the coverage table has a passing test or a recorded manual check. Record
the findings.
Covers: none (review)
Agent: maintainer
Depends on: T72–T83
Done when: both suites and the content check pass, and the coverage table has no open entry.

## Reserved

Interface quality tasks (design guidelines, accessibility, the generation wait
experience, screen review passes, a final consistency pass) will be appended
with the next free IDs, starting at T85. Design guidelines and accessibility
fit after T62. The wait experience, review passes and consistency pass fit
before T71 (Milestone D review) or before T84 (Milestone E review); those review
tasks then add the new IDs to their dependencies.

## Coverage

| RN / CA | Tasks |
|---|---|
| RN-01 | T14, T15, T16, T18, T21, T22, T64 |
| RN-02 | T2, T75 |
| RN-03 | T13, T14, T15, T21 |
| RN-04 | T14, T16, T23, T26 |
| RN-05 | T4, T36 |
| RN-06 | T4, T5, T6, T36, T39, T61 |
| RN-07 | T4, T35, T36, T40, T41, T42, T58, T64, T65 |
| RN-08 | T4, T6, T36, T40, T41, T42, T45, T49, T64 |
| RN-09 | T38, T48, T51, T52, T68 |
| RN-10 | T13, T35, T39, T40, T41, T42, T48 |
| RN-11 | T49, T65 |
| RN-12 | T20, T23, T24, T26, T46, T47, T67 |
| RN-13 | T46, T47, T67 |
| RN-14 | T37, T48, T67 |
| RN-15 | T48, T67 |
| RN-16 | T29 |
| RN-17 | T28 |
| RN-18 | T18, T24, T30 |
| RN-19 | T18, T24, T31 |
| RN-20 | T32 |
| RN-22 | T46, T47, T67 |
| RN-23 | T52, T55, T68, T69 |
| RN-24 | T52, T57, T69 |
| RN-25 | T37, T55, T56, T69 |
| RN-26 | T37, T54, T70 |
| RN-27 | T4, T10, T75, T78, T79, T83 |
| RN-28 | T15, T21, T22, T62, T63 |
| RN-29 | T1, T3, T7, T15, T39, T60, T61, T74, T76, T83 |
| RN-30 | T9, T19, T24, T33, T46, T65, T67 |
| RN-31 | T43, T44, T51, T58 |
| RN-32 | T43, T44, T51, T58, T68 |
| RN-33 | T10, T50, T54, T58, T67, T70 |
| RN-34 | T50, T52, T55, T56, T68, T69 |
| RN-35 | T65, T68 |
| RN-36 | T17, T25, T60, T66 |
| RN-37 | T46, T47 |
| RN-38 | T17, T43, T44, T51 |
| RN-39 | T51, T60, T66 |
| RN-40 | T6, T64, T73, T83 |
| RN-41 | T8, T11, T13, T74, T83 |
| RN-42 | T72, T74, T79 |
| RN-43 | T59, T65, T68, T69 |
| RN-44 | T43, T44, T51, T58, T59, T67, T68 |
| RN-45 | T76, T77, T78, T79, T83 |
| RN-46 | T79 |
| RN-47 | T4, T7, T8, T73, T83 |
| CA-01 | T29 |
| CA-02 | T28 |
| CA-03 | T30 |
| CA-04 | T31 |
| CA-05 | T4, T49 |
| CA-06 | T5, T6, T40, T41, T42, T61 |
| CA-07 | T21 |
| CA-08 | T21, T22, T64 |
| CA-10 | T48 |
| CA-11 | T48 |
| CA-12 | T55, T69 |
| CA-13 | T56, T69 |
| CA-14 | T48 |
| CA-15 | T48 |
| CA-16 | T38, T48, T68 |
| CA-17 | T73, T82, T83 |
| CA-18 | T22, T62, T63 |
| CA-19 | T3, T60, T61 |
| CA-20 | T7, T74, T82, T83 |
| CA-21 | T46, T65, T67 |
| CA-22 | T46, T67 |
| CA-23 | T2, T75 |
| CA-24 | T23, T47 |
| CA-25 | T40, T41, T42, T45, T49 |
| CA-26 | T49, T65 |
| CA-27 | T47, T67 |
| CA-28 | T32 |
| CA-29 | T47, T67 |
| CA-30 | T52, T57, T69 |
| CA-31 | T54, T70 |
| CA-32 | T36, T58, T64, T65 |
| CA-33 | T36, T51 |
| CA-34 | T36, T45, T64 |
| CA-35 | T38, T51, T68 |
| CA-36 | T51 |
| CA-37 | T51, T58, T68 |
| CA-38 | T10, T58, T67 |
| CA-39 | T52, T55, T56, T68, T69 |
| CA-40 | T65, T68 |
| CA-41 | T25, T60, T66 |
| CA-42 | T46, T47 |
| CA-43 | T51 |
| CA-44 | T51, T60, T66 |
| CA-45 | T75, T82, T83 |
| CA-46 | T6, T64 |
| CA-47 | T8, T11, T74, T82, T83 |
| CA-48 | T72, T74 |
| CA-49 | T59, T69 |
| CA-50 | T43, T44, T58, T59, T67 |
| CA-51 | T76, T77, T82, T83 |
| CA-52 | T79 |
| CA-53 | T73, T82, T83 |
| CA-54 | T31, T33 |
| CA-55 | T52, T55, T68 |
| CA-56 | T47 |
