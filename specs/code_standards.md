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

The formatter, linter and type checker are chosen in `specs/plan.md`. Run them
before every commit.

## Checking a comment cleanup

A cleanup that only touches comments must leave the code identical: in Python,
the syntax tree (without docstrings) does not change; in TS/TSX, the printed
code without comments does not change. Run `pytest -q`, `npm run test` and
`npx tsc -b` afterwards.