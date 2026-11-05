---
name: explain-diff
description: Explain a set of changes step by step: what each part does, why it is written that way, what happens on failure and what to check. Use only when the maintainer asks to understand a diff.
disable-model-invocation: true
argument-hint: [optional: base branch, file or task id]
allowed-tools: Read, Grep, Glob, Bash(git status), Bash(git diff *), Bash(git log *)
---

Explain the changes for $ARGUMENTS (default: the uncommitted changes of the
current task, compared with `HEAD`, including new files; a task id means that
task's commits, found by its `Refs:` footer; a branch means that branch compared
with `main`). Read-only: edit nothing.

1. Find the changes (specs/git-standards.md, section 2). Run
   `git status` and `git diff HEAD --stat` (or `git diff <base>...HEAD --stat`),
   then read the diff, the new files and the surrounding code. State the purpose in two sentences, tied to the task and to the rules
   (RN, CA) it serves.
2. Walk through the changes in a sensible order (data model, services, API,
   interface). For each part: what it does in plain language, why it is written
   this way and what it relies on.
3. For the riskiest parts, answer explicitly: what happens with empty or invalid
   input; what happens if the network or the provider fails midway; what
   happens with two simultaneous requests; where the API key could appear;
   which test protects this behavior.
4. Point out anything surprising: code outside the task scope, comments that
   break specs/code-standards.md, rules duplicated in views, tests that cover
   only the happy path.
5. End with a short checklist: what to read first and what to try by hand.

Rules: explain what is in the code, not what you assume. Say "not clear from the
code" when it is not. Do not edit anything.