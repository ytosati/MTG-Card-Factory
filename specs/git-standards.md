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
- Cite the task in a footer: `Refs: T6`.
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

    Refs: T6

## 2. Branch naming

Prefixes:

- `feat/`: new features
- `fix/`: bug fixes
- `refactor/`: internal restructuring
- `chore/`: maintenance, documentation, tests and CI

- `milestone/`: one branch per milestone of `specs/tasks.md`

Rules:

- English, lowercase kebab-case, short and descriptive.
- Start the description with the task ID when there is one.
- One branch per independent unit of work (normally one task from
  `specs/tasks.md`).

Examples:

- `milestone/m0-foundation`, `milestone/ma-data`, `milestone/mb-validators`,
  `milestone/mc-generation`, `milestone/md-api-interface`, `milestone/me-release`
- `feat/t6-color-identity-validator`
- `fix/session-key-leak`
- `chore/update-dependencies`

### Milestone and task branches

- Each milestone has one branch, created from an updated `main` when the
  milestone starts.
- Each task of a milestone has its own branch, created from the updated
  milestone branch, never from `main`.
- A finished task branch merges into its milestone branch, never into `main`.
  The next task starts from the milestone branch after that merge.
- The milestone branch merges into `main` only after its review task passes,
  with every test suite green.
- No commits are made directly on a milestone branch; it changes only by
  merging task branches. Work outside the milestones (for example spec or
  tooling changes) branches from `main` as before.

## 3. Before starting work

1. Inspect the current branch and the working tree.
2. Identify the task scope.
3. Check whether an appropriate task branch already exists.
4. Reuse it when the task belongs to it.
5. Create a new branch only for an independent task.
6. Branch with a clean working tree: a milestone branch from an updated `main`,
   a task branch from its updated milestone branch.
7. If there are local changes, conflicts or unclear branch ownership, stop and
   ask. Never discard existing work.

Do not create a branch for every prompt, file, commit or minor adjustment.

## 4. Protection and authorization

- Never commit directly to `main`, except the very first scaffold commit that
  bootstraps the repository. Never commit directly to a milestone branch.
- Never merge a task branch into `main`; it merges into its milestone branch.
  Merging into a milestone branch also needs authorization.
- Never force-push. Never delete branches without authorization.
- Never merge into `main` without authorization.
- Never overwrite or discard uncommitted changes. Never modify unrelated work.
- AI agents commit only after the maintainer has reviewed the diff or asked for the
  commit. Push, pull request creation and merge always need authorization.
- Enforce what you can outside the text: Claude Code permissions in
  `.claude/settings.json` and branch protection on GitHub.

## 5. Spec-driven workflow

1. Inspect the repository status and the current branch.
2. Identify the task, its rules (RN) and its acceptance criteria (CA).
3. Select or create the branch.
4. If a business rule changes, update `specs/spec.md` first, then the tests,
   then the code, in the same branch. If user-visible behavior changes, update
   the user documentation too.
5. Implement within the agreed scope.
6. Run the tests, formatter, linter and type check.
7. Review the diff for correctness and unintended changes (the maintainer reads it).
8. Create logically cohesive commits.
9. Report what changed, the validation results and the remaining issues.
10. Open a pull request when authorized: a task branch targets its milestone
    branch; a milestone branch targets `main`.
11. Merge only after checks and review.

Pull request: the title follows the commit format. The description states what
and why, the tasks, RN and CA covered, how to test, and the risks.

## 6. Decision rules

- Same task: same branch.
- New independent task: new branch.
- Bug related to the current implementation: current branch.
- Unrelated bug: separate task and branch.
- Changes requested during PR review: the existing PR branch.
- Merged task: start the next task of the milestone from the updated milestone
  branch.
- Milestone review passed and merged: start the next milestone branch from the
  updated `main`.
- Unclear scope or conflicting Git state: ask before any destructive or
  irreversible action.

Core principle: a branch represents one unit of work. A commit represents one
logical change.