# Code standards

Applies to all new or changed code in this repository, whether written by a
person or by an AI agent. Agents follow the same rules.

## Comments

Code is read by people. A comment is the last resort, not the documentation.

| Where | What to write | Size |
|---|---|---|
| Top of a file | what the module is + `Details: <doc>` when there is one | 1-3 lines |
| Function, class, component | a label for what it is; parameters only when not obvious | 1-2 lines |
| Inside the code | only the non-obvious why, especially why a line was NOT written the "simplest" way | 1-2 lines |

**Never goes in a comment:**

- what a line does or how (the code says it);
- history: dates, "used to be", "fixed in", version numbers;
- who decided (people's names) or incidents told at length;
- business rules explained: they live in `specs/spec.md`, and the comment only
  points to them: `see spec RN-16`;
- commented-out code: delete it, Git remembers.

**Where the content that left the code goes:**

| Content | Document |
|---|---|
| Business rule, behavior, screens | `specs/spec.md` |
| Architecture, data model, API contract | `specs/plan.md` |
| Why a protection exists (the trap it avoids) | `docs/DECISIONS.md` |
| History of what changed | `git log` and the commit message |

Create `docs/DECISIONS.md` the first time it is needed. Add rows to this table
when new documents appear (for example `docs/ARCHITECTURE.md`).

**Example**

    # before
    # On 2026-11-10 the key leaked into a traceback. The serializer used to
    # return the whole provider config object, so ... (6 more lines)

    # after
    # Never serialize the provider config as-is: it carries the key
    # (see docs/DECISIONS.md).

## Structure

- High cohesion, low coupling: each module does one thing.
- Business rules live in services (writes and orchestration) and selectors
  (read queries), never in views, serializers or components.
- Validators are pure functions: no network, no provider calls, no writes.
- Provider differences (formats, parameter names, errors) stay inside each
  adapter. Only the factory looks at the configured provider.
- The frontend talks to the backend only through the API contract in
  `specs/plan.md`. It never receives an API key.
- The API keys (text and image) are read from configuration in one place. They
  are never stored or logged.
- A change to a business rule changes `specs/spec.md` first, then the tests,
  then the code, in the same branch.

## Tests

- Each test cites the RN or CA it protects, in its name or docstring.
- Tests use fictional cards written by hand and the fake provider, which stands
  in for text and image generation. They never use the network.

## Interface

Card Factory is a local tool served on 127.0.0.1, not a public website. Search
engine and marketing concerns (sitemap, robots, canonical URLs, meta
descriptions, structured data, Open Graph, HTTPS, custom domain, search
consoles, `llms.txt`) do not apply. The rules below aim at an interface that
looks made for this tool, not assembled from a generic template.

**Document structure**

- Each screen sets the document title as `<Screen> · Card Factory`.
- Exactly one `<h1>` per screen; headings descend without skipping levels
  (`h1`, `h2`, `h3`).
- Every image has an `alt` that says what it shows (for card art: the card
  name and that it is the art); purely decorative images use `alt=""`.
- Every internal link and navigation target leads to an existing screen.
- Images reserve their space (width and height, or an aspect ratio) so the
  layout does not shift while they load.
- Layout works from a narrow window (about 360px) to a wide desktop without
  horizontal scrolling or overlapping text; side-by-side parts (such as card
  art beside its text) stack on a narrow window. Desktop is the main target.

**Identity**

- The application has its own favicon, served locally with the built frontend.
- No branding from tools or templates (framework logos, "built with" marks,
  starter-template leftovers).
- The accent color is the purple in `frontend/src/styles/tokens.css`, used as
  a solid color. No purple or neon gradients, glows, glass effects or
  decorative blurs. A gradient is allowed only when it draws information
  (for example the quarter marks on a progress bar).
- Interface fonts and icons are either installed on the computer (system font
  stacks) or part of the built frontend; card images come from the
  application (spec RN-33). Nothing is loaded from a CDN or font service; a
  new font or icon set is a dependency and needs approval.

**Shapes and motion**

- Corner radii come from the tokens. No pill-shaped buttons or fields
  (`border-radius: 9999px`) unless a token defines that shape for a specific
  component, such as a tag.
- Motion only explains a change of state (progress, an item appearing, a
  pressed button). No scroll-triggered animation, no animation libraries,
  nothing that delays reaching the content.
- Every animation and transition is turned off under
  `prefers-reduced-motion: reduce`.

**Content**

- The application opens on work, not on a hero: no taglines, slogans or
  marketing copy on any screen.
- No placeholder testimonials, invented statistics, sample users or fake
  activity. Empty states say what is missing and how to fill it.
- Generated images appear only as card art. The interface itself uses no
  generated illustrations or stock imagery.
- UI text is short, specific and plain: name the thing and the action ("Build
  database", not "Get started"). No emojis. Inside a sentence, prefer a
  period, colon or comma to an em dash; this is a style preference, not a
  blocking rule.

## Writing for a public repository

- Everything committed describes the project only: no first person, no
  references to the author's personal context (studies, goals, private notes),
  no references to conversations or to how the work was organized.
- Tone: professional, neutral and friendly.
- Applies to code comments, documentation, commit messages, pull request text,
  and agent and skill files.
- Personal preferences live outside the repository (`CLAUDE.local.md`, which is
  not committed).

## Tooling

The tests, the type checker and, once approved, the formatter and linter are
listed in `specs/plan.md` (section 13, Tooling). Run them before every commit.

## Checking a comment cleanup

A cleanup that only touches comments must leave the code identical: in Python,
the syntax tree (without docstrings) does not change; in TS/TSX, the printed
code without comments does not change. Run `pytest -q`, `npm run test` and
`npx tsc -b` afterwards.