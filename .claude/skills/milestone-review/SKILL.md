---
name: milestone-review
description: Close a milestone: full test suites, one review of the milestone diff, the demo in the running application, and findings turned into tasks. Use only when the maintainer asks to review a milestone.
disable-model-invocation: true
argument-hint: [milestone id, e.g. m3]
---

Review the milestone in $ARGUMENTS. Never merge, push or switch branches: the
merge into `main` is the maintainer's decision.

1. `git status`: the milestone branch, clean. List pending tasks of the
   milestone, if any.
2. Run every suite: `pytest -q` (backend), `pytest launcher release` (root),
   `npm run test` and `npx tsc -b` (frontend).
3. One `reviewer` run on `git diff main...HEAD`, asking only for high and
   medium findings. When screens changed, run the interface audit and critique
   once and hand the findings to frontend-dev.
4. Print the milestone's demo as numbered steps and wait for the maintainer's
   outcome. Never mark a step as passed on your own.
5. Findings: fix small defects now; propose the rest as tasks in the next
   milestone (next free ID) and apply them after approval.
6. Report briefly in the maintainer's language: suites, findings, demo, and
   what blocks the next milestone. Then suggest the commit with
   `Refs: <review task id>` and the merge into `main`.
