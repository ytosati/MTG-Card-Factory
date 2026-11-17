---
name: milestone-review
description: Close a milestone after the maintainer approved it: full test suites, one review of the milestone diff, the review task checked, and the merge proposed. Use only when the maintainer asks to review or close a milestone.
disable-model-invocation: true
argument-hint: [milestone id, e.g. m3d]
---

Step 5 of the milestone cycle in specs/tasks.md, for the milestone in
$ARGUMENTS.

1. `git status`: the milestone branch, clean. List pending tasks, if any.
2. Run every suite: `pytest -q` (backend), `pytest launcher release` (root),
   `npm run test` and `npx tsc -b` (frontend).
3. One `reviewer` run on `git diff main...HEAD`, high and medium findings
   only. Fix small defects directly; propose the rest as tasks in the next
   milestone (next free ID).
4. Tick the review task, commit with `Refs: <review task id>`, push, and
   ask the maintainer to approve the merge into `main` and the next
   milestone's branch.
5. Report briefly in the maintainer's language.
