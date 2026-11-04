---
name: new-branch
description: Check the Git state and create a milestone branch or a task branch following specs/git-standards.md. Use only when the maintainer asks to start a milestone or a task branch.
disable-model-invocation: true
argument-hint: [task id | milestone id (m0, ma, mb, mc, md, me)] [short description]
---

Prepare the branch for $ARGUMENTS following specs/git-standards.md (section 2,
"Milestone and task branches").

1. Run `git status` and show the current branch. If there are uncommitted
   changes, conflicts or unclear branch ownership, stop and ask. Never discard
   work.
2. List the branches (local and remote). If one already belongs to this task or
   milestone, propose reusing it.
3. Milestone branch (argument is a milestone id):
   - Check in specs/tasks.md that the previous milestone's review task is done
     and its branch is merged into `main`. If not, stop and say why.
   - Switch to `main`, update it with a fast-forward pull, confirm the working
     tree is clean, and create `milestone/<id>-<name>`, for example
     `milestone/m0-foundation`.
4. Task branch (argument is a task id):
   - Find the task's milestone in specs/tasks.md and its branch
     `milestone/<id>-<name>`. If the milestone branch does not exist, stop and
     propose creating it first. Never branch a task from `main`.
   - Switch to the milestone branch, update it with a fast-forward pull, confirm
     the working tree is clean, and create
     `<type>/<task id>-<kebab-case description>` (types: feat, fix, refactor,
     chore), for example `feat/t6-color-identity-validator`.
5. Report the branch name, the branch it starts from and the commit.
