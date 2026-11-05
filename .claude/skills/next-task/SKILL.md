---
name: next-task
description: Finish the current task and start the next one in a single run: commit, push and merge the task branch into its milestone branch, create the branch of the next task of the milestone, then run that task's implementation cycle. Use only when the maintainer asks to close a task and move on.
disable-model-invocation: true
argument-hint: [auto]
---

Close the current task and start the next one. Invoking this skill is the
maintainer's authorization to push the task branch, merge it into its milestone
branch and push the milestone branch (specs/git-standards.md, section 4). It
never authorizes anything that touches `main`.

The steps reuse the project skills by reading their files and following them
exactly: `.claude/skills/commit/SKILL.md`, `.claude/skills/new-branch/SKILL.md`
and `.claude/skills/run-task/SKILL.md`. Where this file adds or overrides a
step, it says so. If `$ARGUMENTS` contains `auto`, pass it on to run-task
(skips its checkpoint A only).

## 0. Pre-flight
1. Run `git status` and show the current branch. It must be a task branch
   (`feat/`, `fix/`, `refactor/` or `chore/` with a task id, for example
   `feat/t1-backend-project-skeleton`). Stop if it is `main`, a `milestone/`
   branch, or a branch with no task id.
2. Find the task id in the branch name and the task in specs/tasks.md. Find its
   milestone and the milestone branch `milestone/<id>-<name>`. Confirm with
   `git merge-base --is-ancestor <milestone branch> HEAD` that the task branch
   was created from it. Stop on any mismatch.
3. If the task is a milestone review task (Agent: maintainer), stop: the
   milestone branch merges into `main` only by the maintainer's decision.

## 1. Commit (follows commit/SKILL.md)
1. Follow every step of `.claude/skills/commit/SKILL.md` for the current task,
   including the secret check and waiting for the maintainer to confirm the
   message and the file list. If there is nothing to commit and the branch
   already has commits ahead of the milestone branch, go on to step 2.
2. Run every test suite that exists in the repository and stop if any fails:
   `pytest -q` from `backend/`; `pytest launcher release` from the root when
   `launcher/` or `release/` exist; `npm run test` and `npx tsc -b` from
   `frontend/` when `frontend/package.json` exists.

## 2. Push and merge (added by this skill)
1. Push the task branch: `git push -u origin <task branch>`. Never force-push.
2. Switch to the milestone branch and update it with `git pull --ff-only`. Stop
   if the pull is not a fast-forward.
3. Merge with `git merge --no-ff <task branch>` and the message
   `Merge branch '<task branch>'` (the format already used in the history).
   On a conflict, stop and report the conflicting files; never resolve a
   conflict by discarding either side.
4. Run the test suites of step 1.2 again on the merged milestone branch. If any
   fails, stop before pushing and report: the merge stays local for the
   maintainer to decide.
5. Push the milestone branch: `git push origin <milestone branch>`.
6. Never merge into `main`, never delete the task branch.
7. Show `git log --graph --oneline --decorate -15`.

## 3. Next task branch (follows new-branch/SKILL.md)
1. Choose the next task of the same milestone in specs/tasks.md:
   - Go through the milestone's tasks in the order they appear in the file.
   - A task is done when a branch with its id (`*/t<id>-*`) is merged into the
     milestone branch (`git branch -a --merged <milestone branch>`).
   - The next task is the first one not done whose `Depends on:` tasks are all
     done.
   - If the only remaining task is the milestone review (Agent: maintainer), or
     if none is ready, stop and report: the next step is the maintainer's.
2. Show the chosen task (id, title, agent, dependencies) and why it was chosen.
3. Follow `.claude/skills/new-branch/SKILL.md` with that task id. Name the branch
   `<type>/t<id>-<kebab-case short title>`, with the type from the task (`feat`
   for new behavior, `chore` for tooling, CI, tests or repository files).

## 4. Run the next task (follows run-task/SKILL.md)
Follow `.claude/skills/run-task/SKILL.md` for the new task id (with `auto` if
given). Its checkpoints apply unchanged: checkpoint A unless `auto`, and
checkpoint B always, with no commit at the end.

## Rules
- Stop at the first failure and report what was done and what was not.
- Never use `git add .`, `git add -A`, force-push, `git reset --hard` or delete
  branches.
- Everything written into the repository stays in English.
