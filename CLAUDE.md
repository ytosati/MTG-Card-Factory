# Card Factory

Open-source generator of custom Magic: The Gathering cards for Commander. It runs
locally on the user's computer; each person brings their own API key (OpenAI,
Anthropic or Google).

## Language and tone
- Write everything in English: code, identifiers, comments, tests, documentation, specs (spec,
  plan, tasks), commit messages, UI text, error messages, LLM prompts, and agent
  and skill files.
- Generated cards are in any language available in ScryFall (English Default).
- Repository content is public and professional. It describes the project only:
  no first person, no personal context, no references to how the work was
  organized (specs/code_standards.md).

## Stack (decisions already made)
- Backend (folder backend/): Python 3.12, Django, Django REST Framework.
  Model-view-serializer pattern plus services (business rules and writes) and
  selectors (read queries). Thin views; serializers only validate and shape data.
- Database: a single SQLite file under data/. No other database.
- Frontend (folder frontend/): React, TypeScript, Vite. The built frontend is
  served by the backend, so users do not need Node.
- LLM: LLM_PROVIDER (openai, anthropic or google), LLM_API_KEY and LLM_MODEL are
  set in .env. One factory returns the adapter for the chosen provider; call
  sites never branch on the provider.
- Tests: pytest with pytest-django (backend), Vitest (frontend). A fake provider
  stands in for the LLM.
- Distribution: free and open source, local only. No hosting, accounts, billing
  or telemetry.

## Commands
- Backend: python manage.py runserver  |  pytest -q
- Frontend: npm run dev  |  npm run test
- Build the database: management command defined in the plan

## How we work
- The source of truth is specs/spec.md. Code and tests follow the spec.
- If the spec is ambiguous, ask before deciding.
- One task at a time, from specs/tasks.md. Nothing outside the current task.
- Tests never touch the network or a real provider. They use the fake provider
  and fictional cards written by hand.

## Standards
- Code and comments: specs/code_standards.md
- Commits, branches and Git safety: specs/git_standards.md
- Never commit, push, merge or switch branches unless the maintainer asks.

## Non-negotiable rules
- The user's API key is read from .env in one place. It is never written to the
  database, a file, a log, an error message or a response, and it is never sent
  to the browser.
- The server listens only on the local machine by default.
- The repository contains no Scryfall data and no Comprehensive Rules text.
- Card validators are deterministic code and never call a provider.
- All data access goes through the ORM or parameters. Never SQL built from text.
- The application contacts only the official data sources and the configured
  provider.
- No new dependency without approval: every dependency weighs on the install.