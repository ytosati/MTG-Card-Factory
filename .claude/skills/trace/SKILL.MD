---
name: trace
description: Build the traceability matrix from rules to acceptance criteria, tests, tasks and code, and list the orphans. Read-only. Use when the maintainer asks, typically at the end of a milestone.
disable-model-invocation: true
allowed-tools: Read, Grep, Glob
---

Build the traceability matrix. Read-only: edit nothing.

1. List every rule (RN-xx) and acceptance criterion (CA-xx) in specs/spec.md, and
   mark the open [DECIDE] items.
2. For each task in specs/tasks.md, list the RN and CA it cites.
3. Search the tests (backend and frontend) for citations of each RN and CA, in
   test names or docstrings.
4. For each RN, find the code that enforces it, using specs/plan.md and a search
   of the code. Cite file and symbol.
5. Print a table: RN | CA | task | tests | code | status (covered, partial,
   missing).
6. List the orphans: rules with no CA; CA with no rule; rules with no task;
   tasks that cite no rule; tests that cite a missing ID; code that implements
   behavior no rule asks for; open [DECIDE] items.
7. Summarize: coverage by milestone, the three most important gaps and the next
   action for each.

Rules: report only what you found in the files. Mark anything you could not
verify as "not verified".