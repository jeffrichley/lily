# Feature: docs-ia-organization

## Feature Description
Reorganize the entire `docs/` information architecture using stable purpose-based directories and explicit authority boundaries, avoiding status-based file shuffling.

## Branch Setup
```bash
PLAN_FILE=".ai/PLANS/002-docs-ia-organization.md"
PLAN_SLUG="$(basename "$PLAN_FILE" .md)"
BRANCH_NAME="feat/${PLAN_SLUG}"
git show-ref --verify --quiet "refs/heads/${BRANCH_NAME}" \
  && git switch "${BRANCH_NAME}" \
  || git switch -c "${BRANCH_NAME}"
```

## Implementation Plan
- [x] Create stable `docs/dev` substructure by purpose (`plans`, `debt`, `references`).
- [x] Move execution plan files under `docs/dev/plans/`.
- [x] Move debt tracker + debt issue drafts under `docs/dev/debt/`.
- [x] Move reference-only dev docs under `docs/dev/references/`.
- [x] Rewrite internal links across repo from old paths to new canonical paths.
- [x] Rewrite `docs/README.md` and `docs/dev/README.md` as authoritative navigation maps.
- [x] Update process docs that reference old `docs/dev` paths.
- [x] Validate docs via `just docs-check`.
- [x] Add `just status` command for one-command docs/project status summary.

## Validation Commands
- `just docs-check`

## Acceptance Criteria
- `docs/dev` no longer mixes trackers, debt, and reference docs in one flat directory.
- Canonical navigation in `docs/README.md` and `docs/dev/README.md` points to new structure.
- Old path references are updated repository-wide.
- `just docs-check` passes.
- `just status` renders a readable summary of branch state, canonical docs, plan lifecycle, and current focus.

## Execution Report

- 2026-03-02: Created purpose-based dev subdirectories: `docs/dev/plans`, `docs/dev/debt`, `docs/dev/references`.
- 2026-03-02: Moved all execution plan docs into `docs/dev/plans/`.
- 2026-03-02: Moved debt tracker and debt issue drafts into `docs/dev/debt/` and `docs/dev/debt/issues/`.
- 2026-03-02: Moved dev reference docs into `docs/dev/references/`.
- 2026-03-02: Rewrote references to old `docs/dev` flat paths across docs/specs/process/archive and plan artifacts.
- 2026-03-02: Rewrote `docs/README.md` and `docs/dev/README.md` for canonical navigation and governance.
- 2026-03-02: Updated docs cadence policy to the new structure.
- 2026-03-02: Validation passed with `just docs-check`.
- 2026-03-02: Added `just status` (`scripts/status_report.py`) to provide one-command status reporting.
- 2026-03-05: Re-executed this archived plan in verification mode for "All Phases" on branch `feat/002-docs-ia-organization`.
- 2026-03-05: Branch safety gate passed (`git branch --show-current` -> `feat/002-docs-ia-organization`).
- 2026-03-05: Phase intent checks were not applicable: this plan has no phase headings or `Intent Lock` sections; all implementation checklist items were already complete at start.
- 2026-03-05: Fixed docs gate blocker by adding required frontmatter to `docs/dev/flow.md` (`owner`, `last_updated`, `status`, `source_of_truth`).
- 2026-03-05: Status sync evidence: `just docs-check` -> pass, `just status` -> pass.
- 2026-03-05: Validation evidence: `just lint` -> pass, `just format-check` -> pass, `just types` -> pass, `just docs-check` -> pass, `just test` -> pass, `just quality && just test` -> pass.
