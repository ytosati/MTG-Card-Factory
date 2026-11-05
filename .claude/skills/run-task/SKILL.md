---
name: run-task
description: Run the full implementation cycle for one task from specs/tasks.md (tests, implementation, review) with the project agents, stopping for the maintainer at checkpoints. Use only when the maintainer asks to run a task, or when /next-task starts the next task.
disable-model-invocation: true
argument-hint: [task id, e.g. T29] [auto]
---

Run the implementation cycle for the task in $ARGUMENTS (for example `T29`).
If the second word is `auto`, skip checkpoint A. Checkpoint B is never skipped.

## 0. Pre-flight
1. Read specs/tasks.md and find the task. If it does not exist or is ambiguous,
   stop and ask.
2. Run `git status` and show the current branch. Tasks have no branches of
   their own: the work happens on the branch of the task's milestone
   (`milestone/<id>-<name>`, specs/git-standards.md, section 2). Stop and ask
   if the working tree is dirty or if the current branch is not that milestone
   branch. Do not create or switch branches here; if the milestone branch does
   not exist, offer /new-branch.
3. Read the RN and CA the task cites in specs/spec.md. If any is marked
   [DECIDE], stop and ask.
4. Use the implementing agent named in the task's `Agent:` field. If it is
   `maintainer`, stop: the task is not run by this skill. If it is `qa`, step 1
   is the whole implementation: skip step 2 and go to review. If the agent file
   does not exist in `.claude/agents/`, stop and say so.

## 1. Tests first
Use the qa agent to write the tests for the task. Show the maintainer the list of
tests, which RN or CA each protects, and why they fail now.
Checkpoint A: wait for the maintainer to approve or request changes.

## 2. Implementation
Use the chosen agent to implement the task, then run the whole suite. If tests
fail, give the agent the failing output and retry, at most 3 rounds. If they
still fail, stop and report. Never change tests to make them pass.

## 3. Review
Use the reviewer agent on the uncommitted changes. High and medium findings go
back to the implementing agent (at most 2 rounds). Low findings are listed for
the maintainer.

## 4. Report
Summarize: task, files changed, test results, review findings fixed and still
open, doubts, which parts of the diff to read first (the riskiest), and what
still needs manual testing.
Checkpoint B: stop. Do not commit, push, merge or switch branches. Offer
/explain-diff for the riskiest parts, and suggest `/next-task <task id>` after
the maintainer has read the diff: it commits on the milestone branch, pushes it
and starts the next task (`/commit` only commits). If the task is the milestone review, remind that the
milestone branch merges into `main` only after the review passes.

## Rules
- One task per run.
- Never edit specs/spec.md during the cycle. If the spec is wrong, stop and say
  which rule.
- Never ask an agent to edit files outside its ownership.
