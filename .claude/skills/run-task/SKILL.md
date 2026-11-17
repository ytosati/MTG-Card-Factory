---
name: run-task
description: Implement one task or feature from specs/tasks.md (code and its tests together), run the suites and report. Use only when the maintainer asks to run a task, or when /next-task starts the next task.
disable-model-invocation: true
argument-hint: [task id or ids, e.g. T29 or T140,T146]
---

Implement the task (or the group of related tasks) in $ARGUMENTS, following
specs/tasks.md ("Delivery method", "Testing policy", "Process").

## 0. Pre-flight
1. `git status` and the current branch: it must be the milestone branch with
   a clean working tree. Stop and ask otherwise.
2. Read the task text and the RN it cites (search by ID). A [DECIDE] mark
   stops the run with the question; anything else unclear is decided by the
   simplest reading and listed in the report.

## 1. Implementation
- Small change (a few files, no key, account or ownership rule): do it
  directly, without a subagent.
- Otherwise: one fresh agent, the one named in `Agent:`, with a brief that
  quotes the task and the RN, names the files to read, and asks for a report
  of at most 10 lines. The agent writes the code and its tests together,
  following the Testing policy.
- Validators, security or ownership work: a `qa` agent writes the tests first.

## 2. Check
Run the suites the change touches (`pytest -q` in `backend/`, `npm run test`
and `npx tsc -b` in `frontend/`, `pytest launcher release`). Fix failures,
at most 3 rounds. Never weaken a test to make it pass. Work that touches keys,
accounts or ownership gets a `reviewer` pass now; anything else waits for the
milestone review.

## 3. Report
In the maintainer's language, short: what changed, test results, decisions
taken, what to look at in the running application. Do not commit; suggest
`/next-task <id>` (commit, push and next task).

## Rules
- Nothing outside the task. Never edit files outside an agent's ownership
  (specs/plan.md, section 12).
