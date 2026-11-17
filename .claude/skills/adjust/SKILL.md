---
name: adjust
description: Apply the maintainer's notes after testing a milestone (visual or behavioral), as one batch, check them in the running application, commit, and show the touched guide steps again. Use only when the maintainer gives notes on a milestone or asks to adjust.
disable-model-invocation: true
argument-hint: [the notes, free text]
---

Step 4 of the milestone cycle in specs/tasks.md. The notes are in $ARGUMENTS
or in the maintainer's last message.

1. `git status`: the milestone branch. Turn the notes into a short numbered
   list of changes and start; ask only when a note can be read in two very
   different ways, or when it changes a rule of `specs/spec.md` (then change
   the rule in the same commit, with the maintainer's agreement).
2. Apply the changes directly, or with one fresh agent per area (frontend,
   backend) when they are large. No new task IDs. A note that is new scope
   for a later milestone becomes a task there instead.
3. Run the suites the changes touch. Open the application in the browser pane
   and check each change at 1280 and 375 px.
4. Commit (specs/git-standards.md) citing the milestone's review task, and
   push the milestone branch.
5. Reply in the maintainer's language: each note and what was done, the guide
   steps to look at again, and anything not done and why.

When the maintainer is satisfied, suggest /milestone-review to close.
