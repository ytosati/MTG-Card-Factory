# Decisions

Why a protection or convention exists, recorded where the code only points to
it. Business rules live in `specs/spec.md`; architecture in `specs/plan.md`.

| Topic | Decision | Reason |
|---|---|---|
| Application home functions (T1) | `core.paths` exposes `app_home()` and `data_dir()`; every other path is derived from them. | A single place resolves the home, so the launcher, the clone and the tests agree on where `.env` and `data/` live. |
| Empty `CARDFACTORY_HOME` (T1) | An empty or whitespace-only `CARDFACTORY_HOME` counts as unset and falls back to the repository root. Any other value is stripped of surrounding whitespace before use. | A blank value left in a shell or launcher would otherwise resolve to the current directory and scatter `data/` folders; stray spaces or newlines would otherwise become part of the folder name. |
| Relative `CARDFACTORY_HOME` (T1) | A relative value is resolved against the current working directory at the time of each call; the result is always absolute. | The value is read on every call, so it follows the environment as it is when used, and the database path handed to SQLite is never relative. |
| `CARDFACTORY_DEBUG` comparison (T1) | Debug is on only when the value equals `1` after stripping surrounding whitespace. The check lives in `core.environment.debug_enabled()`, read at call time, and settings and configuration reuse it. | Stray spaces or newlines from a shell or file should not silently disable debug, while any other value keeps it off. |
| Test suite home (T1) | The suite runs with a temporary `CARDFACTORY_HOME`, set by the early pytest plugin `tests.isolation` before pytest-django loads the settings. | Tests never read or write the repository `data/` folder or `.env`, and project variables from the developer's shell are cleared. |
| Transitive dependency pins (T1) | `requirements.txt` and `requirements-dev.txt` pin every package the approved dependencies pull in, with the environment markers their authors declare. | A clone installs the pinned requirements (spec RN-45); without exact transitive pins, installs on different days could resolve different versions. |
| SQLite transaction mode (T1) | The database `OPTIONS` set `transaction_mode` to `IMMEDIATE`, so `transaction.atomic()` takes the write lock when it begins. | Writer threads (jobs) and reader threads (server) share the file; a deferred transaction that later upgrades its lock fails at once with "database is locked" instead of waiting for the busy timeout. |
| `django.contrib.auth` and `contenttypes` installed (T1) | Both apps stay in `INSTALLED_APPS` although the application has no accounts. | Django REST Framework's default authentication relies on them; to be revisited when the API is configured. |
| Creating `<home>/data/` (T1) | Settings do not create the data folder; creating it at startup belongs to the startup and secret key step (T5). | `runserver` and `migrate` need the folder, and keeping folder creation in one startup step avoids side effects when the settings are imported. |
