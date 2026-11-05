---
name: milestone-review
description: Run the review task of a milestone (vertical slice): test suites, coverage of the milestone's RN and CA parts, the demo in the running application, findings turned into spec questions or tasks, and the readiness of the next milestone. Use only when the maintainer asks to review a milestone.
disable-model-invocation: true
argument-hint: [milestone id, e.g. m3]
---

Review the milestone in $ARGUMENTS following specs/tasks.md ("Delivery method"
and the milestone's review task). Never merge, push or switch branches: the
merge into `main` is the maintainer's decision.

## 0. Pre-flight
1. Run `git status` and show the current branch. It must be the milestone's
   branch (`milestone/<id>-<name>`, specs/tasks.md, Process) with a clean
   working tree. Stop otherwise.
2. Find the milestone's review task. Check that every other task of the
   milestone is done: the branch has a commit with `Refs: <task id>`
   (`git log --grep "Refs: <task id>$"`). List any that are not, and stop.

## 1. Suites and coverage
1. Run every test suite that exists: `pytest -q` from `backend/`;
   `pytest launcher release` from the root; `npm run test` and `npx tsc -b`
   from `frontend/`; the repository content check under `release/`.
2. Follow `.claude/skills/trace/SKILL.md` with the milestone id. Report each RN
   and CA part of the milestone as covered, partial or missing.
3. Use the reviewer agent on the milestone branch against `main`
   (`git diff main...HEAD`). Report its findings; fix nothing here.

## 2. Demo
1. Print the milestone's demo as numbered steps for the maintainer, from the
   locally built zip from Milestone 1 on, with the manual checks of
   `specs/manual-checks.md` that belong to the milestone.
2. Wait for the maintainer to report the outcome of each step. Never mark a
   manual step as passed on your own.

## 3. Findings
1. Sort every finding (suites, coverage, reviewer, demo, the extra checks the
   review task names) into:
   - rule or plan changes: propose them for `/spec-change`;
   - work for this milestone: a defect in its own deliverable, proposed as a
     new task in this milestone;
   - work for later: proposed as a new task in the right later milestone.
2. Propose the edits to specs/tasks.md (new tasks with the next free ID, and
   the review task's dependencies) and wait for approval before applying them.

## 4. Next milestone
1. Read the next milestone's tasks against the spec as it stands now. List the
   [DECIDE] items, open questions and TODO lines that block them, and the
   tasks whose text no longer fits the findings.
2. Offer the architect agent's milestone check and the spec-reviewer agent for
   the blocking items.

## 5. Report
Summarize: suite results, coverage, demo outcome, findings by kind, edits
applied or pending, and the blocking items of the next milestone. The review
task is done when its "Done when" holds; then suggest the commit of the review
findings with `Refs: <review task id>` and remind that the merge into `main`,
the push and the next milestone branch (/new-branch) need the maintainer.

## Rules
- Read-only for code and tests. Only specs/tasks.md changes here, after
  approval; spec changes go through /spec-change.
- Everything written into the repository stays in English.
