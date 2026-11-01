# Shared working conventions

These rules come from the `conventions` plugin in
[dev-conventions](https://github.com/guhilling/dev-conventions), which prints them at the start
of every session. They hold in every repository that enables the plugin. The repository's own
`CLAUDE.md` adds the rules that are its own and names the details these leave to it, such as its
GitHub project; where it says something different, the repository's `CLAUDE.md` wins.

## Ask, don't guess

If a requirement, API contract, data model, or design decision is unclear or
underspecified, **stop and ask** rather than guessing or picking a default
silently. This applies especially to:

- Whatever the repository's `CLAUDE.md` lists under *Ask, don't guess*.
- Anything where multiple reasonable implementations exist and the choice
  affects the design.

Guessing silently and moving on is the failure mode to avoid here, even if it
slows things down.

## Workflow

- Always work on a git branch, never commit directly to `main`.
- Every change reaches `main` through a pull request. How that is enforced, and who merges, is in
  the repository's `CLAUDE.md`.
- **A pull request that finishes an issue gets `/code-review high` before it merges** — any PR
  whose description says `Closes #…`. Fix what it finds, or say in the PR why a finding does
  not apply, and note the review's outcome in the PR. Docs-only changes, Renovate updates and
  follow-up fixes without an issue do not need one. For a particularly critical change Gunnar
  may run `/code-review ultra` himself; Claude cannot start that one.
- Delete a branch once its pull request is merged — locally and on `origin` —
  unless told otherwise. Because pull requests are squash-merged, a merged
  branch does not show up in `git branch --merged main`, so stale branches are
  easy to lose track of if they are not cleaned up straight away.
- Anything that can reasonably be enforced automatically (tests, coverage,
  style/lint checks, build) should be enforced by the standard GitHub Actions
  CI/CD runs, not left as a manual convention.
- Project-level documentation lives in `/doc` and is the source of truth; the
  root `README.md` is a short entry point that links into it. Update `/doc` in
  the same change as the behaviour it describes, never as a follow-up.
- **Long topics are chapters**: `doc/<chapter>/index.md` plus one page per sub-chapter, ordered by
  the chapter's index. A reference anywhere in the repository names the exact page it means
  (`doc/<chapter>/<page>.md`, not a section of a long file), and
  the shared `check-doc-references` action from [dev-conventions](https://github.com/guhilling/dev-conventions)
  fails CI when one names a page that does not exist.
- Never commit secrets (API keys, OIDC client secrets, real credentials,
  etc.). Only local, testing-only placeholder values belong in the repo
  (e.g. `.env.example`-style files or dev/test configuration); real secrets
  are supplied via environment variables / CI secrets only.
- **Dependency updates come from Renovate**, not by hand. Patch and minor
  updates automerge once every check is green; majors wait for Gunnar. The
  `platformAutomerge: false` in the Renovate configuration is load-bearing:
  `main` requires no status checks, so GitHub's own
  auto-merge would merge before anything had run. The `schedule` there is deliberate and
  restricts pull request *creation* only — Renovate acting outside it is
  expected, because it can be run directly from the Mend dashboard, so never
  remove it as leftover setup debris.

## Issues

- A piece of work Claude should finish without a conversation first is written with the
  **Story** issue form (`.github/ISSUE_TEMPLATE/story.yml`): what and why, **done when**,
  constraints, **decisions — yours or mine**, out of scope.
- A goal too large for one story is an **Epic** (`.github/ISSUE_TEMPLATE/epic.yml`). It is never
  implemented directly: it starts with an investigation — options compared, with references —
  whose result is a decision for Gunnar, and is then split into stories linked as sub-issues.
- **Prefer the outcome to the mechanism.** A named mechanism that turns out not to work costs a
  round trip; an outcome does not. ai-assisted-todolist#70 asked for `Optional<T>`, which breaks
  the OpenAPI document, so the ask became a question instead of a change.
- **Say which decisions are delegated.** Ask-don't-guess above means an unmarked decision
  becomes a question and the run stops there, which is right — but most decisions do not need
  Gunnar, and saying so is what lets a story be finished in one go.
- Anything that is neither a story nor an epic — a bug, a question, a note to self — uses the blank form.
- **Every open issue carries a priority, in two places kept in step**: a label —
  `priority: 1 now` (next up, at most two or three), `priority: 2 next` (after that) or
  `priority: 3 later` (wanted, not soon) — and the same value in the *Priority* field of the
  repository's GitHub project, which its `CLAUDE.md` names, whose table is grouped by
  it and ordered by hand within each group. The label is what an issue list shows and filters
  on; the project is the one place with a real order. A new issue gets both when it is opened
  (`gh project item-add <number> --owner guhilling --url …`, then `item-edit --field Priority`) —
  Gunnar's call if the priority is not obvious, so ask. "Work on the next issue" means the top
  of the project's first group.

## Development methodology

- **TDD for implementation.** Write a failing test first, then the minimal
  code to make it pass, then refactor. This applies to every part of the
  codebase, with whatever test framework that part uses. Don't write
  production code without a test driving it.
- **The smallest change that passes the test.** Reuse before adding: look for what the codebase
  has before writing a helper, a type, an option or a dependency. No abstraction for one caller,
  no parameter nobody asked for, no handling of a case that cannot occur; a shortcut taken on
  purpose is said so in the code. The test, the code's own documentation and the page in `/doc`
  are part of the change, never the lines to save.
- **Never change or disable an existing unit test without asking Gunnar
  first.** This includes editing its assertions/setup, deleting it, or
  marking it skipped/disabled — always ask before touching a test that
  already exists, even if it appears to be blocking other work.
