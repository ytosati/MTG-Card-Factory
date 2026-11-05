---
name: new-branch
description: Check the Git state and create a milestone branch, or a branch for work outside the milestones, following specs/git-standards.md. Tasks have no branches of their own. Use only when the maintainer asks to start a milestone or a branch.
disable-model-invocation: true
argument-hint: [milestone id (m0 to m10) | type and short description]
---

Prepare the branch for $ARGUMENTS following specs/git-standards.md (section 2,
"Milestone branches and task commits").

1. Run `git status` and show the current branch. If there are uncommitted
   changes, conflicts or unclear branch ownership, stop and ask. Never discard
   work.
2. List the branches (local and remote). If one already belongs to this
   milestone or this work, propose reusing it.
3. If the argument is a task id, stop: tasks are commits on their milestone
   branch. Point to the milestone branch, or offer to create it.
4. Milestone branch (argument is a milestone id):
   - Check in specs/tasks.md that the previous milestone's review task is done
     and its branch is merged into `main`. If not, stop and say why. For `m0`,
     skip this check: it is the first milestone.
   - Take the branch name from the Process section of specs/tasks.md, for
     example `milestone/m3-first-card`.
   - Show the milestone's goal and demo, and the [DECIDE], open question and
     TODO items its review listed as blocking; if any is still open, say so
     before creating the branch.
   - Switch to `main`, update it with a fast-forward pull, confirm the working
     tree is clean, and create the branch.
5. Work outside the milestones (argument is a type and a description):
   - Switch to `main`, update it with a fast-forward pull, confirm the working
     tree is clean, and create `<type>/<kebab-case description>` (types: feat,
     fix, refactor, chore), for example `chore/update-dependencies`.
6. Report the branch name, the branch it starts from and the commit.
