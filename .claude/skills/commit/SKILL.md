---
name: commit
description: Stage and commit the changes of the current task following specs/git-standards.md. Use only when the maintainer asks to commit.
disable-model-invocation: true
argument-hint: [task id]
allowed-tools: Bash(git status), Bash(git diff *), Bash(git log *)
---

Commit the current changes for $ARGUMENTS following specs/git-standards.md.

1. Run `git status` and `git diff` (staged and unstaged). If the current branch
   is `main` or a `milestone/` branch, stop: commits go on the task branch
   (specs/git-standards.md, section 2).
2. Check scope: do the changed files form one logical change? If not, propose a
   split into several commits.
3. Check for secrets: look in the changed files and the diff for text that looks
   like an API key or .env content, and for anything under data/. Stop if found.
4. If a business rule changed, confirm that specs/spec.md changed in this branch,
   before or together with the code. If user-visible behavior changed, check that
   the user documentation was updated too, or flag it.
5. Propose the commit message in English: `type(scope): imperative description`,
   subject up to 72 characters, optional body explaining why, and a footer
   `Refs: <task id>`. List exactly the files to stage.
6. Wait for the maintainer's confirmation. Then stage only the listed files (never
   `git add .` or `git add -A`) and commit. Never push.
7. Show `git log -1 --stat`.