---
description: "Push a branch safely after validation"
---

# Push: Safe Branch Push

## Objective

Push completed work to remote with clean history.

Canonical PR-prep command:
- `.ai/COMMANDS/pr.md`

## Process

### 1. Pre-push readiness checks

- Confirm you are on the intended branch:
  - `git branch --show-current`
- Confirm working tree is clean:
  - `git status --short`
- Confirm commits to push:
  - `git log --oneline --decorate --graph -n 10`

If the tree is not clean, stop and resolve before pushing.

### 2. Sync with remote safely

- Fetch latest refs:
  - `git fetch --all --prune`
- Check divergence from target base branch (usually `main`):
  - `git log --oneline origin/main..HEAD`
  - `git log --oneline HEAD..origin/main`

If rebase/merge is required, do it before push and re-run validations.

### 3. Validate before push

- Run `.ai/COMMANDS/validate.md`.
- Run required project validation commands (at minimum those defined in the active plan).
- Re-run critical smoke checks for user-visible features.

Do not push code that has not passed required validations.

### 4. Push branch

- First push with upstream tracking:
  - `git push -u origin <branch>`
- Subsequent pushes:
  - `git push`

### 5. Handoff to PR step

After successful push, run `.ai/COMMANDS/pr.md` to prepare and open/update the PR.
