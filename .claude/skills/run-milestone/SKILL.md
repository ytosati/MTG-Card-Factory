---
name: run-milestone
description: Run the pending tasks of one milestone in sequence (tests first where rules need them, implementation, batched review, batched commits and push), pausing for the maintainer at testable points and decisions. Use only when the maintainer asks to run a whole milestone or several of its tasks in a row.
disable-model-invocation: true
argument-hint: [milestone id, e.g. m3b] [batch size, default 5] [task limit, optional]
---

Run the pending tasks of the milestone in $ARGUMENTS. The first word is the
milestone id, the second the number of tasks per commit batch (default 5), the
third an optional limit on the number of tasks to run before stopping.

The maintainer supervises this run. Small doubts are decided and listed in the
batch report; large doubts, opinions and anything that changes a rule stop the
run with a question. The cost rules of specs/plan.md, section 12 ("Models and
cost") apply throughout.

## 0. Pre-flight
1. `git status` and the current branch: it must be the milestone's branch
   (`milestone/<id>-<name>`, specs/tasks.md, Process) with a clean working
   tree. Stop otherwise; offer /new-branch when the branch does not exist.
2. Read the milestone section of specs/tasks.md (goal, demo, later work) and
   list its pending tasks (unchecked in Progress, no commit with
   `Refs: <task id>`), in dependency order. Leave out the review task: it runs
   with /milestone-review.
3. For each task, read the RN and CA it cites. A [DECIDE] mark or an open TODO
   in a task about to run stops the run with the question.
4. Show the planned order and the batches, then start.

## 1. Each task
1. Tests first for tasks with rules to protect (endpoints, validators,
   pipelines, screens): a fresh `qa` agent writes the failing tests and reports
   the API it assumed. For small mechanical tasks, the implementing agent
   writes its tests. When the task's agent is `qa`, the tests are the whole
   implementation.
2. A fresh implementing agent (the task's `Agent:`) makes them pass without
   changing tests. Independent tasks of the same batch may run in parallel
   when they touch different files.
3. Every brief names the milestone, the files to read, what the task leaves to
   later tasks, and asks for a report of at most 10–15 lines. Agents run the
   tests of their task, not the full suites.
4. A test the implementer believes wrong goes back to `qa` with the reason, or
   is corrected in place when the error is plain (for example a wrong expected
   value); say so in the batch report.
5. Agents never commit. Agents are not resumed for a new task once their
   context has grown; start a fresh one.

## 2. Each batch
1. Review: one `reviewer` run covers the batch. A task that touches keys,
   provider calls or another non-negotiable rule of CLAUDE.md gets its own
   review on Opus. High and medium findings go back to an implementing agent
   (with `qa` adding the missing tests first); low findings are listed.
2. Screens: when the batch changed screens, run the interface audit and
   critique once for the group of changed screens and hand the findings to
   frontend-dev.
3. Full suites: `pytest -q` from `backend/`, `npm run test` and `npx tsc -b`
   from `frontend/`, and `pytest launcher release` when those changed. Fix
   failures before committing.
4. Commits: one commit per task, following specs/git-standards.md, each ticking
   its box in Progress. Tasks that changed the same files may share one commit
   that cites each task. Stage only the task's files. Plan and spec text that a
   task changed goes with that task.
5. Verify the batch on a clean checkout of HEAD (a git worktree), run the
   backend suite there, then push the milestone branch. Never force-push.
6. Batch report to the maintainer, in their language: tasks committed, test
   results, decisions taken, low findings left open, items for the milestone
   review.

## 3. Pauses
Stop and report, with the state of the run, when:
- the application has something new the maintainer can test by hand (give the
  commands and a short manual checklist);
- a decision belongs to the maintainer (a rule change, a design choice with no
  default, a non-negotiable rule at stake);
- the task limit is reached, or the maintainer asks to pause;
- every task except the review is done.
Never mark a manual check as passed on your own.

## 4. End
Report what was done, what is pending, the findings to record in the review,
and suggest `/milestone-review <id>`. The merge into `main` and the next
milestone branch need the maintainer.

## Rules
- One milestone per run; nothing outside its tasks.
- Never edit specs/spec.md during the run; a rule change goes through
  /spec-change.
- Never ask an agent to edit files outside its ownership (specs/plan.md,
  section 12).
- Never rewrite a provider request to get around a refusal, and never weaken a
  test to make it pass.
