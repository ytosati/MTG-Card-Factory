# Card Factory

Open-source generator of custom Magic: The Gathering cards for Commander, with
a collection, decks and print sheets. It runs in two modes from one code base
(spec RN-63): local, on the user's computer, and hosted, as a public website
with free accounts. Each person brings their own API key (OpenAI, Anthropic or
Google).

## Language and tone
- Write everything in English: code, identifiers, comments, tests, documentation, specs (spec,
  plan, tasks), commit messages, UI text, error messages, LLM prompts, and agent
  and skill files.
- Generated cards are in English (default) or Portuguese (Brazil), both with
  full rules validation (spec RN-30).
- Repository content is public and professional. It describes the project only:
  no first person, no personal context, no references to how the work was
  organized (specs/code-standards.md).

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
- Images (optional): IMAGE_PROVIDER (openai or google), IMAGE_API_KEY and
  IMAGE_MODEL in .env. Without IMAGE_PROVIDER, art uses the LLM provider when it
  is image-capable. IMAGE_API_KEY may be empty when no image provider is set or
  it equals the text provider; LLM_API_KEY is then used. The same factory rule applies to image adapters.
- Port: APP_PORT in .env, default 47821. In local mode the server binds to
  127.0.0.1 and no setting changes the bind address. Hosted mode
  (CARDFACTORY_MODE=hosted, plan section 16) takes its address and hosts
  from the environment.
- Settings screen: in local mode it writes .env; in hosted mode the values
  stay in the person's browser and travel with each request that needs a
  provider (spec RN-71, RN-72).
- Saved data has an owner in both modes; local mode has one implicit user
  (plan section 16.2). Accounts use Django's own auth.
- Startup never calls a provider; keys are tried by the Status connection test
  and by generation.
- Images are stored as local files under data/; the SQLite database keeps their
  references.
- Tests: pytest with pytest-django (backend), Vitest (frontend). A fake provider
  stands in for text and image generation.
- Distribution: free and open source. No billing, advertising or telemetry.
  The hosted site runs the same code (plan section 16.7). The Windows release is a zip with a portable Python, the built
  frontend, a .env with a comment for each setting, and a double-click launcher
  that opens the browser. Building the release requires Node; running it does
  not. The GitHub repository is the download page (releases), the user guide
  (README) and the source code. A clone has a Windows start file that prepares
  everything on the first run, downloading the built frontend from the matching
  GitHub release (spec RN-45).
- Approved for distribution: the official embeddable Python package, waitress as
  the server, and a launcher run with pythonw.exe (no console window). Django
  serves the built frontend's static files. No image library: providers
  generate images and the browser displays them.

## Commands
Development commands. End users start the application with the launcher
(spec RN-27).
- Backend (from backend/, with the virtual environment active):
  python manage.py runserver 127.0.0.1:47821  |  pytest -q
  (the Vite development server proxies /api to this port)
- Launcher and release scripts (from the repository root): pytest launcher release
- Frontend (from frontend/): npm run dev  |  npm run test  |  npx tsc -b
- Build the database (from backend/): python manage.py build_catalog

## Workflow
- The source of truth is specs/spec.md. Code and tests follow the spec.
- If the spec is ambiguous, ask before deciding.
- Milestones are vertical slices: each ends with a capability demonstrated in
  the running application, across frontend, backend and database, and builds
  only what its demo needs (specs/tasks.md, "Delivery method").
- One task at a time, from specs/tasks.md. Nothing outside the current task.
- Tests never touch the network or a real provider. They use the fake provider
  and fictional cards written by hand.

## Standards
- Code and comments: specs/code-standards.md
- Commits, branches and Git safety: specs/git-standards.md
- Never commit, push, merge or switch branches unless the maintainer asks.

## Non-negotiable rules
- The user's API keys (text and image) are never written to the database, a
  log, an error message or a response, and are never sent from the
  application to the browser. In local mode they live only in .env, read in
  one place and written only by the Settings service. In hosted mode they
  live only in the person's browser; the server holds a received key in
  memory until its job ends and stores it nowhere.
- In local mode the server listens only on the local machine.
- In hosted mode every saved item belongs to one account, and no account
  can read or change another's.
- The hosted site is free: no payment, survey or subscription for any
  feature, and it shows the fan content notice on every screen.
- The repository contains no Scryfall data, no Comprehensive Rules text, and no
  card images or frames.
- Card validators are deterministic code and never call a provider. The power
  indicator is an assessment by the text model, not a validator.
- All data access goes through the ORM or parameters. Never SQL built from text.
- The application contacts only the data sources (Scryfall and the
  Comprehensive Rules), the configured providers and, in hosted mode, the
  service that sends account emails. After the database build, Scryfall is
  contacted only to refresh the database and to download the image of a
  chosen base card. The
  start file of a clone also downloads, when preparing and only what is missing
  or changed (spec RN-45), Python and the dependencies from their official
  sources and the built frontend from the project's GitHub releases.
- The browser loads images of custom cards only from the application, images
  of existing printings from the data source's image service, and community
  art from its own hosts (spec RN-33). No font, script or style sheet comes
  from outside the application.
- No new dependency without approval: every dependency weighs on the install.