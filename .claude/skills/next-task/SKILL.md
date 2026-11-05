---
name: next-task
description: Finish the current task and start the next one in a single run: commit the task on its milestone branch, push the milestone branch, then run the implementation cycle of the next task of the milestone. Use only when the maintainer asks to close a task and move on.
disable-model-invocation: true
argument-hint: [task id] [auto]
---

Close the current task and start the next one. Tasks have no branches of their
own: each task is committed on its milestone branch (specs/git-standards.md,
section 2). Invoking this skill is the maintainer's authorization to commit the
task and push the milestone branch (specs/git-standards.md, section 4). It
never authorizes anything that touches `main`.

The steps reuse the project skills by reading their files and following them
exactly: `.claude/skills/commit/SKILL.md` and `.claude/skills/run-task/SKILL.md`.
Where this file adds or overrides a step, it says so. If `$ARGUMENTS` contains
`auto`, pass it on to run-task (skips its checkpoint A only).

## 0. Pre-flight
1. Run `git status` and show the current branch. It must be a `milestone/`
   branch. Stop if it is `main` or any other branch.
2. Find the current task: the task id in `$ARGUMENTS`, or, if none is given,
   ask. Find it in specs/tasks.md and confirm that its milestone matches the
   current milestone branch `milestone/<id>-<name>`. Stop on any mismatch.
3. If the task is a milestone review task (Agent: maintainer), stop: the
   milestone branch merges into `main` only by the maintainer's decision.

## 1. Commit (follows commit/SKILL.md)
1. Run every test suite that exists in the repository and stop if any fails:
   `pytest -q` from `backend/`; `pytest launcher release` from the root when
   `launcher/` or `release/` exist; `npm run test` and `npx tsc -b` from
   `frontend/` when `frontend/package.json` exists.
2. Follow every step of `.claude/skills/commit/SKILL.md` for the current task,
   including the secret check and waiting for the maintainer to confirm the
   message and the file list. If there is nothing to commit and the milestone
   branch already has a commit with `Refs: <task id>`, go on to step 2.

## 2. Push (added by this skill)
1. Update check: `git fetch origin` and confirm the milestone branch is not
   behind `origin/<milestone branch>`. If it is, stop and report; never merge
   or rebase here.
2. Push the milestone branch: `git push origin <milestone branch>` (add `-u`
   when it has no upstream). Never force-push. If the push fails, stop.
3. Never merge into `main`, never create or delete branches.
4. Show `git log --oneline --decorate -10`.

## 3. Choose the next task
1. Go through the milestone's tasks in specs/tasks.md in the order they appear.
   A task is done when the milestone branch has a commit whose message has
   `Refs: <task id>` (`git log --grep "Refs: <task id>$"`), or when it was
   merged into the milestone branch before tasks became commits (a merged
   branch with its id, `*/t<id>-*`).
2. The next task is the first one not done whose `Depends on:` tasks are all
   done. If the only remaining task is the milestone review (Agent:
   maintainer), or if none is ready, stop and report: the next step is the
   maintainer's.
3. Show the chosen task (id, title, agent, dependencies) and why it was chosen.

## 4. Run the next task (follows run-task/SKILL.md)
Follow `.claude/skills/run-task/SKILL.md` for the chosen task id (with `auto`
if given), on the same milestone branch. Its checkpoints apply unchanged:
checkpoint A unless `auto`, and checkpoint B always, with no commit at the end.

## Rules
- Stop at the first failure and report what was done and what was not.
- Never use `git add .`, `git add -A`, force-push, `git reset --hard`, or
  create, switch or delete branches.
- Everything written into the repository stays in English.
