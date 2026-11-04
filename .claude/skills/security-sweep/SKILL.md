---
name: security-sweep
description: Sweep the repository for API key leakage and sensitive data, before publishing or after touching the key path. Read-only. Use when the maintainer asks.
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash(git status), Bash(git log *), Bash(git ls-files *), Bash(git grep *)
---

Check that the API key and other secrets cannot leak. Read-only: edit nothing,
and never print a secret value. Show only the file, the line and the kind of
finding.

1. Tracked files: confirm that .env and anything under data/ are not tracked
   (`git ls-files`) and that .gitignore covers them.
2. Code: search for text that looks like provider API keys, hard-coded secrets
   and tokens in code, fixtures, documentation and examples.
3. Key path: follow the key from the environment file to the provider adapters.
   Check every place it passes: settings, logs, exceptions and tracebacks,
   serializers and responses, error messages, debug output, URLs and query
   strings. Confirm it never reaches the browser: no endpoint returns it, and
   the frontend code, browser storage and source maps never contain it.
4. Configuration: debug off by default; the server listens only on the local
   machine; .env.example contains no real values; secrets are read
   only from the environment.
5. History: search the Git history for key-like text and for committed .env or
   data files.
6. Network: list the network calls the app makes. The only destinations must be
   the official data sources (during the database build, and Scryfall for the
   image of a chosen base card printing), the configured text provider and
   image provider, and, in `start.cmd`, python.org, PyPI and the project's
   GitHub releases (spec RN-29). Each key goes only to its provider, in a
   header, never in a URL.
7. Data: confirm that no Scryfall data and no rules text is committed.
8. Report findings by severity, with file and line, why it matters and the fix.
   If everything is clean, say what you checked and what you could not check.