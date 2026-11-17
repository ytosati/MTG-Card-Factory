---
name: run-milestone
description: Run the pending tasks of one milestone in sequence, grouped by feature, with batched commits and push, pausing for the maintainer when there is something to try or decide. Use only when the maintainer asks to run a whole milestone or several of its tasks in a row.
disable-model-invocation: true
argument-hint: [milestone id, e.g. m3b] [task limit, optional]
---

Run the pending tasks of the milestone in $ARGUMENTS, following
specs/tasks.md ("Delivery method", "Testing policy", "Process").

## 0. Pre-flight
1. `git status`: the milestone branch with a clean working tree; stop
   otherwise (offer /new-branch when the branch does not exist).
2. List the pending tasks (unchecked in Progress) and group them by feature:
   tasks that touch the same screen, endpoint or pipeline step go together.
   Show the groups in order and start.

## 1. Each feature
1. Small changes are made directly. Larger ones go to one fresh agent (the
   tasks' `Agent:`; backend and frontend parts of one feature may run in
   parallel), with a brief quoting the tasks and RN and asking for a report
   of at most 10 lines. The agent writes code and tests together.
2. `qa` first only for validators, security and ownership work.
3. Run the suites the feature touches; fix failures. Never weaken a test.
4. Commit the feature (specs/git-standards.md), citing each task ID and
   ticking their boxes in Progress. Push the milestone branch after every
   two or three features. Never force-push.

## 2. Pauses
Stop and report, in the maintainer's language and briefly, when:
- something new can be tried in the application (give the commands);
- a decision belongs to the maintainer (a rule change, a design choice with no
  default, a security rule at stake);
- the task limit is reached, or only the review task is left.
Never mark a manual check as passed on your own.

## 3. End
Report what was done and what is pending, and suggest
`/milestone-review <id>`. The merge into `main` needs the maintainer.

## Rules
- One milestone per run; nothing outside its tasks.
- Never rewrite a provider request to get around a refusal.
