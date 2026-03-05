---
description: "Create a commit with Commitizen/Conventional Commit compliance and high-signal context"
---

# Commit: High-Signal, Commitizen-Compliant

## Objective

Create a single atomic commit for the intended changes with a Commitizen-compliant message that explains both **what changed** and **why it changed**.

Reusable guidance:
- `.ai/COMMANDS/_shared/story-writing.md`
- `.ai/COMMANDS/_shared/review-checklist.md`

## Process

### 1. Review change scope

Run `.ai/COMMANDS/review.md` first.

Branch safety check (required):
- `git branch --show-current`
- If branch is `main`, stop and create/switch to a feature branch before committing.

- Run:
  - `git status`
  - `git diff HEAD`
  - `git status --porcelain`
- Confirm the commit scope is coherent and atomic.
- If unrelated changes are present, do not include them.

### 2. Stage only intended files

- Add modified and untracked files that belong to this commit.
- Re-check staged scope:
  - `git diff --cached --stat`
  - `git diff --cached`

### 3. Write Commitizen-compliant message

Message must follow Conventional Commits / Commitizen:

`<type>(<optional-scope>): <short imperative summary>`

Allowed types:
- `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`

Optional breaking-change marker:
- `type(scope)!: summary`
- or `BREAKING CHANGE:` footer in body

### 4. Tell the story in the body

Commit body is required for non-trivial changes. Include:
- Context/problem: what was missing or broken.
- Key changes: what was implemented (major files/components).
- Reasoning: why this approach was chosen.
- Outcome: what is now possible/verified.

Recommended body structure:

```text
Context:
- ...

Changes:
- ...

Why:
- ...

Validation:
- <command/result>
- <command/result>
```

### 5. Add footers when relevant

- Reference plans/issues:
  - `Refs: .ai/PLANS/<NNN>-<feature>.md`
- Breaking changes:
  - `BREAKING CHANGE: ...`

## Quality Bar

- Subject line is <= 72 chars, imperative, specific.
- Type/scope accurately reflect the primary intent.
- Body explains both implementation and motivation.
- Future readers (human or AI) can understand the change without re-reading the full diff.
- Message matches staged content exactly.

## Example

```text
docs(reboot): align rules and command references with reboot baseline

Context:
- command guidance referenced removed targets and legacy architecture paths.

Changes:
- updated `.ai/RULES.md` architecture/boundary guidance for current repository layout
- updated command/reference docs to use active `just` targets
- removed stale examples that referenced legacy render subsystem paths

Why:
- keep workflow docs actionable so validation and execution commands match real repo state

Validation:
- just quality-check (pass)
- just status (pass)

Refs: .ai/PLANS/016-example-reboot-docs-alignment.md
```
