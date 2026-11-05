---
name: spec-change
description: Change a business rule or acceptance criterion the spec-driven way: propose the spec diff first, review it, list the affected tests and tasks, and only then allow implementation. Use only when the maintainer asks to change the spec.
disable-model-invocation: true
argument-hint: [short description of the change]
---

Handle a spec change for $ARGUMENTS. The spec changes first, then the tests,
then the code.

1. Read specs/spec.md, specs/tasks.md and specs/plan.md. Restate the requested
   change in one or two sentences. If it is unclear, ask.
2. Identify the affected rules (RN), acceptance criteria (CA), screens, tasks and
   plan sections.
3. Propose the exact spec diff (new, changed and removed lines) without editing
   the file yet. Keep it about behavior: no technical solutions. Keep IDs
   stable: new items get new IDs, and a retired ID is never reused.
4. Use the spec-reviewer agent on the proposed text and show its findings.
5. Wait for the maintainer's approval, then apply the spec edit.
6. List what must change next: tests (which CA need new or updated tests), tasks
   (new, changed or obsolete), plan sections and user documentation. Propose the
   edits to specs/tasks.md and specs/plan.md and apply them only after approval.
7. Stop. Implementation starts with /run-task on the updated task.

Rules:
- Never change code or tests in this skill.
- If the change contradicts a non-negotiable rule in CLAUDE.md, stop and say so.
- Suggest a `docs(spec): ...` commit on the current milestone branch, or on a
  branch outside the milestones (specs/git-standards.md). Do not commit.