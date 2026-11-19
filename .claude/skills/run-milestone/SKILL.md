---
name: run-milestone
description: Build a whole milestone in one go (grouped by feature), check it in the running application, polish the screens, and hand the maintainer a visual test guide. Use only when the maintainer asks to run a milestone or several of its tasks.
disable-model-invocation: true
argument-hint: [milestone id, e.g. m3d] [task limit, optional]
---

Run steps 1 to 3 of the milestone cycle in specs/tasks.md ("Milestone cycle",
"Design bar", "Testing policy", "Process") for the milestone in $ARGUMENTS.

## 0. Pre-flight
1. `git status`: the milestone branch, clean (offer /new-branch when it does
   not exist). If the previous milestone is not merged into `main`, say so.
2. List the pending tasks (unchecked in Progress), grouped by feature in
   dependency order. Show the groups in a few lines and start; do not wait.

## 1. Build
1. Small changes are made directly. Larger ones go to one fresh agent per
   feature (the tasks' `Agent:`; backend and frontend parts may run in
   parallel), with a brief quoting the tasks and RN, naming the files to read,
   and asking for a report of at most 10 lines. Screen briefs quote the
   Design bar and point to `frontend/DESIGN.md`.
2. `qa` first only for validators, keys and ownership work.
3. Run the suites the feature touches; fix failures. Never weaken a test.
4. Commit each feature (specs/git-standards.md), citing its task IDs and
   ticking them in Progress. Push the milestone branch every few features.
5. Stop only for a decision that belongs to the maintainer (a rule change, a
   design choice with no default, a security rule at stake). A task that
   needs the maintainer's choice (for example a choice between concepts)
   ends the build early: go to step 2 with what exists and ask in the guide.

## 2. See it working
1. Start the backend (`python manage.py runserver 127.0.0.1:47821` from
   `backend/`) and the frontend (`npm run dev`) in the background and open the
   application in the browser pane.
2. Walk the milestone's demo. Check every new or changed screen at 1280 and
   375 px against `frontend/DESIGN.md` and the Design bar. Run the interface
   audit and critique once for the changed screens.
3. Fix what is broken, plain or generic (directly, or with one frontend-dev
   agent and a list of the fixes), then commit and push.

## 3. Visual test guide
Reply to the maintainer in their language:
- how to start the application (commands in their own code blocks);
- what is new, in a few bullets;
- numbered steps: what to do, what should be seen, and a screenshot when one
  can be attached;
- known limits and the decisions taken on their behalf.
End by asking for their notes, to be applied with /adjust.

## Rules
- One milestone per run; nothing outside its tasks.
- Never rewrite a provider request to get around a refusal.
- Never mark a manual check as passed on your own.
