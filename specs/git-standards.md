# Git standards

Applies to people and AI agents.

## 1. Commit conventions

Follow Conventional Commits. Format: `type(scope): description`

Allowed types:

- `feat`: new functionality
- `fix`: bug fixes
- `refactor`: internal code changes without behavior changes
- `docs`: documentation and specifications
- `test`: automated tests
- `chore`: maintenance, dependencies, configuration and tooling
- `ci`: CI/CD pipeline changes

Rules:

- Write commit messages in English.
- Describe the change only: no first person, no personal context, no references
  to conversations or to how the work was organized.
- Subject: imperative, concise, up to 72 characters, no trailing period.
- Use a scope when it improves clarity (for example `backend`, `frontend`,
  `providers`, `validators`, `ingest`, `generation`, `api`, `agents`).
- Cite the task in a footer: `Refs: T29`.
- Use the body, when needed, to explain why rather than what.
- Keep commits atomic and logically cohesive: one logical change per commit.
- Mark breaking changes with `!` and explain compatibility implications in a
  `BREAKING CHANGE:` footer.
- Never use generic messages such as "update", "changes" or "wip".
- Stage only files that belong to the intended change. Never `git add .` or
  `git add -A`.
- Never commit secrets, credentials, `.env` files or anything under `data/`.

Example:

    feat(validators): reject cards outside the requested color identity

    Refs: T29

## 2. Branch naming

Prefixes:

- `feat/`: new features
- `fix/`: bug fixes
- `refactor/`: internal restructuring
- `chore/`: maintenance, documentation, tests and CI

- `milestone/`: one branch per milestone of `specs/tasks.md`

Rules:

- English, lowercase kebab-case, short and descriptive.
- One branch per milestone, or per independent unit of work outside the
  milestones. Tasks have no branches of their own.

Examples:

- `milestone/m0-foundation`, `milestone/ma-data`, `milestone/mb-validators`,
  `milestone/mc-generation`, `milestone/md-api-interface`, `milestone/me-release`
- `fix/session-key-leak`
- `chore/update-dependencies`

### Milestone branches and task commits

- Each milestone has one branch, created from an updated `main` when the
  milestone starts.
- Tasks of a milestone are commits on the milestone branch. A finished task
  becomes one or more commits there, each citing the task in its `Refs:`
  footer. The next task continues on the same branch.
- A task is committed only after its tests pass and the maintainer has read
  the diff. The milestone branch is then pushed, never force-pushed.
- The findings of a milestone review task are committed on the milestone
  branch.
- The milestone branch merges into `main` only after its review task passes,
  with every test suite green.
- Work outside the milestones (for example spec or tooling changes) branches
  from `main`.

## 3. Before starting work

1. Inspect the current branch and the working tree.
2. Identify the task scope.
3. A task of a milestone works on that milestone's branch. Work outside the
   milestones checks whether an appropriate branch already exists and reuses it.
4. Create a new branch only for a new milestone or for independent work outside
   the milestones.
5. Branch with a clean working tree: a milestone branch from an updated `main`.
6. If there are local changes, conflicts or unclear branch ownership, stop and
   ask. Never discard existing work.

Do not create a branch for a task, prompt, file, commit or minor adjustment.

## 4. Protection and authorization

- Never commit directly to `main`, except the very first scaffold commit that
  bootstraps the repository. Task commits go on their milestone branch.
- Never force-push. Never delete branches without authorization.
- Never merge into `main` without authorization.
- Never overwrite or discard uncommitted changes. Never modify unrelated work.
- AI agents commit only after the maintainer has reviewed the diff or asked for the
  commit. Push, pull request creation and merge always need authorization; the
  maintainer asking for a task commit authorizes its commit and the push of
  the milestone branch.
- Enforce what you can outside the text: Claude Code permissions in
  `.claude/settings.json` and branch protection on GitHub.

## 5. Spec-driven workflow

1. Inspect the repository status and the current branch.
2. Identify the task, its rules (RN) and its acceptance criteria (CA).
3. Select the branch: the milestone branch for a task, or a branch for work
   outside the milestones.
4. If a business rule changes, update `specs/spec.md` first, then the tests,
   then the code, on the same branch. If user-visible behavior changes, update
   the user documentation too.
5. Implement within the agreed scope.
6. Run the tests and the type check (`specs/plan.md`, section 13, Tooling).
7. Review the diff for correctness and unintended changes (the maintainer reads it).
8. Create logically cohesive commits.
9. Report what changed, the validation results and the remaining issues.
10. Open a pull request when authorized: a milestone branch, or a branch of work
    outside the milestones, targets `main`.
11. Merge only after checks and review.

Pull request: the title follows the commit format. The description states what
and why, the tasks, RN and CA covered, how to test, and the risks.

## 6. Versioning

- `VERSION` holds the application version in Semantic Versioning
  (`MAJOR.MINOR.PATCH`).
- A release tag is `v` followed by `VERSION` (for example `v1.2.0`), and the
  `frontend-dist` asset of that release carries the same version (spec RN-45).
- `VERSION` changes in the commit that prepares a release, never on its own.

## 7. Decision rules

- Task of a milestone: the milestone branch, one or more commits.
- Next task of the same milestone: the same milestone branch.
- Bug related to the current implementation: current branch.
- Unrelated bug: separate task.
- Changes requested during PR review: the existing PR branch.
- Milestone review passed and merged: start the next milestone branch from the
  updated `main`.
- Unclear scope or conflicting Git state: ask before any destructive or
  irreversible action.

Core principle: a branch represents one milestone or one unit of work outside
the milestones. A commit represents one logical change.