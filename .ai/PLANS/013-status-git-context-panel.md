# Feature: status-git-context-panel

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Extend `just status` with a dedicated `Git Context` panel that provides richer git/PR diagnostics for operators, while preserving the existing Rich-first UX, adding explicit panel visibility controls, and adding an explicit machine-readable JSON mode.

## User Story

As a maintainer using `just status`,
I want a compact Git Context panel with divergence, working tree breakdown, commit/stash context, PR/CI summary, and optional JSON output,
So that I can quickly understand branch health and next actions without running multiple git/gh commands.

## Problem Statement

Current `just status` output only reports branch name and clean/dirty state. It does not show divergence, staged vs unstaged detail, commit/stash context, PR state, or CI rollup. It also lacks explicit positive panel-visibility flags with default-on behavior. This forces maintainers to run manual follow-up commands and makes automation harder because there is no JSON mode.

## Solution Statement

Enhance `scripts/status_report.py` to compute and render a new `Git Context` panel with:
1. Branch divergence (vs upstream branch and `origin/main`)
2. Working tree breakdown (staged, unstaged, untracked, conflicted)
3. Last commit context (sha, subject, author, relative age)
4. Stash visibility (count + latest stash summary)
5. PR/remote context (PR number/state + CI rollup)
6. Positive panel flags (`--show-*`) for every status panel, defaulting to `true`, with explicit false values to hide panels.
7. Lazy panel collection: only execute subprocess/data-gathering work for panels whose `show_*` flag is `true`.
8. `--json` mode that emits a deterministic `git_context` object while keeping Rich output as default.

## Feature Metadata

**Feature Type**: Enhancement (operator UX + diagnostics)
**Estimated Complexity**: Medium
**Primary Systems Affected**: `scripts/status_report.py`, `justfile`, docs references for status surfaces
**Dependencies**: `git` CLI (required), `gh` CLI (optional; graceful degradation), Python stdlib (`argparse`, `json`, `subprocess`, `datetime`)

## Traceability Mapping (Required When Applicable)

- Roadmap system improvements: `None`
- Debt items: `None`
- Debt to roadmap linkage (if debt exists): `None`
- No SI/DEBT mapping for this feature.

## Branch Setup (Required)

Branch naming must follow the plan filename:
- Plan: `.ai/PLANS/013-status-git-context-panel.md`
- Branch: `feat/013-status-git-context-panel`

Commands (must be executable as written):
```bash
PLAN_FILE=".ai/PLANS/013-status-git-context-panel.md"
PLAN_SLUG="$(basename "$PLAN_FILE" .md)"
BRANCH_NAME="feat/${PLAN_SLUG}"
git show-ref --verify --quiet "refs/heads/${BRANCH_NAME}" \
  && git switch "${BRANCH_NAME}" \
  || git switch -c "${BRANCH_NAME}"
```

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `scripts/status_report.py` (lines 14-19, 70-88, 91-177) - Existing status report structure, current git-state probe, and Rich panel/table rendering sequence.
- `justfile` (lines 144-149) - `status` and `status-ready` command surface contract.
- `.ai/REF/project-types/cli-tool.md` (lines 5-13, 30-31) - CLI UX rule: Rich default output; JSON only with explicit mode.
- `.ai/REF/just-targets.md` (lines 17-20) - Canonical expectation for `just status` surface.
- `.ai/COMMANDS/status-sync.md` (lines 8-35, 67-72) - `just status` trustworthiness and maintenance workflow constraints.
- `scripts/validate_docs_frontmatter.py` (lines 16-38, 41-62) - Existing argparse/main pattern for deterministic script CLI behavior.
- `tests/unit/config/test_docs_frontmatter_validator.py` (lines 77-123) - Preferred AAA-style unit test format and deterministic assertions.

### New Files to Create

- `tests/unit/scripts/test_status_report.py` - Unit tests for git-context parsing, fallback behavior, and `--json` output contract.

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [Rich Panel](https://rich.readthedocs.io/en/stable/panel.html)
  - Specific section: panel title/content patterns
  - Why: keep new `Git Context` output consistent with existing Rich panel styling.
- [Rich Table](https://rich.readthedocs.io/en/stable/tables.html)
  - Specific section: compact table row formatting choices
  - Why: fallback if panel content becomes too dense and needs structured rows.
- [git status porcelain format](https://git-scm.com/docs/git-status#_porcelain_format_version_1)
  - Specific section: XY status codes
  - Why: deterministic staged/unstaged/untracked/conflicted counting.
- [git rev-list](https://git-scm.com/docs/git-rev-list)
  - Specific section: `--left-right --count` usage
  - Why: robust ahead/behind computation.
- [GitHub CLI: gh pr view](https://cli.github.com/manual/gh_pr_view)
  - Specific section: `--json` fields
  - Why: derive PR number/state and status checks rollup.

### Patterns to Follow

**Naming Conventions:**
- Keep script-local helper names prefixed with `_` and descriptive noun phrases (`_git_state`, `_current_focus_items` in `scripts/status_report.py:55-88`).
- Use typed dataclasses for grouped metadata (`DocMeta` pattern at `scripts/status_report.py:22-27`).

**Error Handling:**
- Use subprocess calls with `check=False` and explicit fallback values for unavailable tool output (`scripts/status_report.py:72-87`).
- Degrade gracefully when optional tools (for example `gh`) are missing or unauthenticated.

**CLI Pattern:**
- Follow argparse + `main() -> int` + `SystemExit(main())` contract from `scripts/validate_docs_frontmatter.py:16-62`.

**Rendering Pattern:**
- Rich default with panels/tables (`scripts/status_report.py:101-172`), no raw JSON unless explicit flag.

**Testing Pattern:**
- Use AAA comments and deterministic assertions as in `tests/unit/config/test_docs_frontmatter_validator.py:77-123`.

---

## IMPLEMENTATION PLAN

Use markdown checkboxes (`- [ ]`) for implementation phases and task bullets so execution progress can be tracked live.

### Phase 1: Git-context domain model and collection helpers

**Intent Lock**

- Source of truth docs for this phase:
  - `scripts/status_report.py` current helper boundaries and flow (`70-99`, `101-177`)
  - git porcelain / rev-list docs (links above)
- Must:
  - Introduce typed structures for git-context fields.
  - Compute all requested fields (1, 2, 4, 6, 8) deterministically.
  - Gate collection commands behind panel visibility so hidden panels do not trigger subprocess calls.
  - Keep optional integrations (`gh`) non-fatal.
- Must Not:
  - Do network calls directly from Python HTTP clients.
  - Replace Rich default output.
  - Hide command failures silently; expose `unknown`/`unavailable` states explicitly.
- Provenance map:
  - divergence fields <- `git rev-list --left-right --count`
  - working tree counts <- `git status --porcelain`
  - commit context <- `git log -1 --format=...`
  - stash context <- `git stash list`
  - PR/CI context <- `gh pr view --json ...`
- Acceptance gates:
  - helper-level tests cover success and fallback parsing paths.

**Tasks:**

- [x] Add dataclasses and helper functions in `scripts/status_report.py` for git-context collection.
- [x] Implement resilient subprocess wrapper utility for reusable command execution + fallback semantics.
- [x] Add visibility-aware collection entrypoints so panel-specific command execution is skipped when `show_*` is `false`.
- [x] Implement PR/CI rollup normalization logic (`pass/failing/pending/none/unavailable`).

### Phase 2: Render new `Git Context` panel in Rich mode

**Intent Lock**

- Source of truth docs for this phase:
  - `scripts/status_report.py` panel/table rendering order (`101-172`)
  - `.ai/REF/project-types/cli-tool.md` (Rich default output requirement)
- Must:
  - Add exactly one new panel for git info.
  - Keep existing top-level status/docs/plans/current-focus surfaces intact.
  - Keep all panels enabled by default in Rich mode.
  - Ensure hidden panels are both not rendered and not collected.
  - Present fields compactly and scan-friendly.
- Must Not:
  - Replace existing panels/tables with JSON in default mode.
  - Introduce nested/unreadable multi-panel complexity.
- Provenance map:
  - panel lines must map directly to dataclass fields from Phase 1.
- Acceptance gates:
  - `just status` renders successfully with panel present on clean and dirty states.

**Tasks:**

- [x] Render `Git Context` panel with branch/upstream, divergence, tree breakdown, commit, stash, PR/CI lines.
- [x] Add panel rendering gates keyed by positive `show_*` booleans for summary/docs/plans/current-focus/git-context surfaces.
- [x] Ensure graceful text for unavailable upstream/gh/stash states.
- [x] Keep summary panel and existing docs/plan/current-focus outputs unchanged unless needed for consistency.

### Phase 3: Add explicit CLI output mode and panel visibility flag contract

**Intent Lock**

- Source of truth docs for this phase:
  - `.ai/REF/project-types/cli-tool.md` (explicit JSON mode only)
  - `scripts/validate_docs_frontmatter.py` argparse/main structure
- Must:
  - Add `--json` flag to `scripts/status_report.py`.
  - Add positive `--show-*` flags for each panel and default each to `true`.
  - Allow operators to hide panels by setting the corresponding `--show-*` flag to `false`.
  - Apply the same visibility contract to data collection so hidden panels incur no command work.
  - Emit deterministic JSON including `git_context` fields requested by user.
  - Preserve current Rich output behavior when `--json` not supplied.
- Must Not:
  - Introduce negative primary panel flags (`--hide-*`, `--no-*`) as the canonical interface.
  - Change `just status` default behavior to JSON.
  - Emit ambiguous field names or shape drift between runs.
- Provenance map:
  - JSON object mirrors in-memory dataclass values; no duplicate ad-hoc computations.
- Acceptance gates:
  - `uv run python scripts/status_report.py --json` exits `0` with parseable JSON.

**Tasks:**

- [x] Add argparse parsing and output mode dispatch.
- [x] Add `--show-summary`, `--show-docs`, `--show-plans`, `--show-current-focus`, and `--show-git-context` flags with default `true` values.
- [x] Wire collection dispatch to `show_*` booleans so each panel's probes run only when enabled.
- [x] Define stable `git_context` schema with nullable fields for unavailable data.
- [x] Add JSON serialization path and keep Rich path as default.

### Phase 4: Tests, docs touchpoints, and validation

**Intent Lock**

- Source of truth docs for this phase:
  - `.ai/REF/testing-and-gates.md`
  - `.ai/REF/just-targets.md` (status contract)
  - `.ai/COMMANDS/status-sync.md` (`just status` expectation)
- Must:
  - Add unit coverage for parsing/fallback and JSON schema shape.
  - Run required gates for script and docs surfaces.
  - Update docs references only where command behavior contract changed.
- Must Not:
  - Leave warning-producing test paths.
  - Skip fallback coverage for missing upstream/gh.
- Provenance map:
  - each acceptance criterion has a corresponding test/assertion and command output.
- Acceptance gates:
  - targeted unit tests pass
  - `just status` and `just status-ready` pass

**Tasks:**

- [x] Create `tests/unit/scripts/test_status_report.py` with monkeypatched subprocess fixtures.
- [x] Add tests for divergence/tree/commit/stash/PR parsing + unavailable fallbacks.
- [x] Add tests for `--json` shape and deterministic key presence.
- [x] Update docs references if needed (`.ai/REF/just-targets.md` or command docs when behavior text changes).

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### UPDATE scripts/status_report.py

- **IMPLEMENT**: Add typed git-context dataclasses and a single command-runner helper returning `(stdout, returncode)`.
- **PATTERN**: Mirror current helper style and fallback behavior from `scripts/status_report.py:70-88`.
- **IMPORTS**: `argparse`, `json`, `datetime` (for relative age formatting), optional typing helpers.
- **GOTCHA**: Do not assume upstream exists; detached HEAD and no-remote repos must render safely.
- **VALIDATE**: `uv run python scripts/status_report.py`

### UPDATE scripts/status_report.py

- **IMPLEMENT**: Parse porcelain output into `staged`, `unstaged`, `untracked`, `conflicted` counts.
- **PATTERN**: Reuse existing subprocess invocation conventions and deterministic string parsing.
- **IMPORTS**: none beyond prior step.
- **GOTCHA**: Handle rename/copy/conflict XY codes correctly; count each file once per category semantics.
- **VALIDATE**: `uv run python scripts/status_report.py`

### UPDATE scripts/status_report.py

- **IMPLEMENT**: Add divergence computation for upstream and `origin/main` using `git rev-list --left-right --count`.
- **PATTERN**: Keep return fallback states (`n/a`/`unknown`) explicit instead of inferred defaults.
- **IMPORTS**: none beyond prior step.
- **GOTCHA**: Upstream may be absent; do not fail command.
- **VALIDATE**: `uv run python scripts/status_report.py`

### UPDATE scripts/status_report.py

- **IMPLEMENT**: Add commit context (`sha`, `subject`, `author`, `age`) and stash summary (`count`, latest entry + age).
- **PATTERN**: Use deterministic short-format git commands; avoid locale-sensitive parsing where possible.
- **IMPORTS**: `datetime`, `timezone` utilities as needed.
- **GOTCHA**: Empty stash list should render as `0` and `none`.
- **VALIDATE**: `uv run python scripts/status_report.py`

### UPDATE scripts/status_report.py

- **IMPLEMENT**: Add PR/CI context collection via `gh pr view --json ...` with fallback to `unavailable` when `gh` missing/not configured.
- **PATTERN**: Avoid hard failure on non-zero subprocess results.
- **IMPORTS**: `json`.
- **GOTCHA**: Ensure no network/API assumptions beyond `gh` command availability; timeouts should fail closed to `unavailable`.
- **VALIDATE**: `uv run python scripts/status_report.py`

### UPDATE scripts/status_report.py

- **IMPLEMENT**: Introduce `--json` mode and dispatch between Rich rendering and JSON serialization.
- **PATTERN**: Mirror argparse entrypoint structure from `scripts/validate_docs_frontmatter.py:16-62`.
- **IMPORTS**: `argparse`, `json`.
- **GOTCHA**: JSON mode must include existing summary/docs/plan/focus payloads plus new `git_context` object; avoid breaking current default output.
- **VALIDATE**: `uv run python scripts/status_report.py --json`

### UPDATE scripts/status_report.py

- **IMPLEMENT**: Add positive panel flags (`--show-summary`, `--show-docs`, `--show-plans`, `--show-current-focus`, `--show-git-context`) parsed as booleans that default to `true` and can be set to `false` to suppress a panel.
- **PATTERN**: Keep flag naming affirmative and map directly to panel render decisions.
- **IMPORTS**: `argparse` bool parsing helper if needed.
- **GOTCHA**: All panels must render by default when flags are omitted, and hidden panels must not execute their collection subprocesses.
- **VALIDATE**: `uv run python scripts/status_report.py && uv run python scripts/status_report.py --show-git-context false`

### CREATE tests/unit/scripts/test_status_report.py

- **IMPLEMENT**: Add unit tests for helper parsing logic and fallback states by monkeypatching subprocess responses.
- **PATTERN**: AAA test structure from `tests/unit/config/test_docs_frontmatter_validator.py:77-123`.
- **IMPORTS**: `pytest`, `pathlib.Path`, module under test.
- **GOTCHA**: Keep tests independent from real git repo state.
- **VALIDATE**: `uv run pytest tests/unit/scripts/test_status_report.py -q`

### UPDATE docs refs (only if behavior contract text changes)

- **IMPLEMENT**: Add minimal mention that JSON mode exists for `status_report.py` without changing default `just status` contract.
- **PATTERN**: Keep `just status` described as Rich snapshot in `.ai/REF/just-targets.md`.
- **IMPORTS**: n/a.
- **GOTCHA**: Do not document JSON as default interactive mode.
- **VALIDATE**: `just docs-check`

---

## TESTING STRATEGY

### Unit Tests

- Add dedicated script-level unit tests in `tests/unit/scripts/test_status_report.py`:
  - divergence parsing from `rev-list` output
  - porcelain status breakdown classification
  - commit/stash parsing
  - `gh` unavailable fallback
  - `show_*` flags default `true` and false-suppression behavior
  - hidden panel skips associated subprocess probes
  - `--json` schema keys and nullable fields

### Integration Tests

- CLI smoke checks in real repo context:
  - `uv run python scripts/status_report.py`
  - `uv run python scripts/status_report.py --json`
  - `just status`

### Edge Cases

- No upstream tracking branch
- Detached HEAD
- No stashes
- `gh` not installed or unauthenticated
- PR exists but no checks yet
- Conflicted working tree entries

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

- `uv run ruff check scripts/status_report.py tests/unit/scripts/test_status_report.py`
- `uv run ruff format --check scripts/status_report.py tests/unit/scripts/test_status_report.py`

### Level 2: Unit Tests

- `uv run pytest tests/unit/scripts/test_status_report.py -q`

### Level 3: Integration Tests

- `uv run python scripts/status_report.py`
- `uv run python scripts/status_report.py --show-git-context false`
- `uv run python scripts/status_report.py --json`
- `just status`
- `just status-ready`

### Level 4: Manual Validation

- Verify `Git Context` panel appears and includes all selected fields (1, 2, 4, 6, 8).
- Verify all panels render when no `--show-*` flags are provided.
- Verify each `--show-* false` setting hides only its target panel.
- Verify disabled panels do not trigger their collection command paths (for example via monkeypatch/asserted call counts in tests).
- Verify default output remains Rich-rendered and human-readable.
- Verify JSON mode returns parseable payload including `git_context` (10).

### Level 5: Additional Validation (Optional)

- `just quality && just test`

For user-visible features, include explicit artifact verification commands (for example endpoint checks, file probes, UI smoke steps, or API assertions).

---

## OUTPUT CONTRACT (Required For User-Visible Features)

- Exact output artifacts/surfaces:
  - terminal output from `just status` with a dedicated `Git Context` panel
  - JSON payload from `uv run python scripts/status_report.py --json`
- Verification commands:
  - `just status`
  - `uv run python scripts/status_report.py --json`

## DEFINITION OF VISIBLE DONE (Required For User-Visible Features)

- A human can directly verify completion by:
  - running `just status` and seeing `Git Context` with divergence/tree/commit/stash/PR lines
  - running `uv run python scripts/status_report.py` and seeing all panels by default
  - running `uv run python scripts/status_report.py --show-git-context false` and confirming only the Git Context panel is hidden
  - running `uv run python scripts/status_report.py --json` and confirming `git_context` contains deterministic keys for all requested dimensions

## INPUT/PREREQUISITE PROVENANCE (Required When Applicable)

- Generated during this feature:
  - `tests/unit/scripts/test_status_report.py` via implementation tasks in this plan
- Pre-existing dependency:
  - git repository metadata via local `.git`
  - optional PR metadata via `gh` CLI (`gh auth status` for setup verification)

---

## ACCEPTANCE CRITERIA

- [x] `just status` includes a dedicated `Git Context` panel.
- [x] Panel includes branch divergence vs upstream and `origin/main`.
- [x] Panel includes working tree counts: staged, unstaged, untracked, conflicted.
- [x] Panel includes last commit context (sha, subject, author, age).
- [x] Panel includes stash context (count + latest stash summary when present).
- [x] Panel includes PR/CI summary when `gh` is available; otherwise explicit `unavailable` state.
- [x] `scripts/status_report.py --json` returns deterministic parseable JSON including `git_context`.
- [x] Panel visibility flags are positive `--show-*` names and default to `true`.
- [x] Setting any `--show-*` flag to `false` hides only that panel.
- [x] Panel collection/probe commands execute only for panels with `show_* == true`.
- [x] Default `just status` output remains Rich-first (no default raw JSON).
- [x] New unit tests cover success and fallback paths.
- [x] Validation commands pass with zero errors.

---

## COMPLETION CHECKLIST

- [x] All tasks completed in order
- [x] Each task validation passed immediately
- [x] All validation commands executed successfully
- [x] Full test suite passes (unit + integration)
- [x] No linting or type checking errors
- [x] Manual testing confirms feature works
- [x] Acceptance criteria all met
- [x] Code reviewed for quality and maintainability

---

## NOTES

- Keep implementation modular: prefer a helper registry/dispatch for output mode (`rich` vs `json`) instead of long conditional chains.
- Preserve command latency: avoid expensive git invocations where one call can be parsed for multiple fields.
- Ensure output text remains compact and operator-first; do not overwhelm the primary status surfaces.

## Execution Report

### Completion Status

- Completed on `2026-03-04` on branch `feat/013-status-git-context-panel`.
- All planned phases completed.
- All required validations passed.

### Files Modified

- `scripts/status_report.py`
- `tests/unit/scripts/test_status_report.py` (created)
- `.ai/PLANS/013-status-git-context-panel.md`

### Phase Intent Checks Run

- Phase 1 lock reviewed against:
  - `scripts/status_report.py` helper/render boundaries
  - git porcelain/rev-list guidance in plan references
  - Outcome: proceeded with typed models, resilient command wrapper, and visibility-gated collection.
- Phase 2 lock reviewed against:
  - Rich default-output requirements (`.ai/REF/project-types/cli-tool.md`)
  - Outcome: added dedicated `Git Context` panel and show-flag rendering gates.
- Phase 3 lock reviewed against:
  - argparse/main contract from `scripts/validate_docs_frontmatter.py`
  - Outcome: added `--json` and positive `--show-*` flags with default `true`.
- Phase 4 lock reviewed against:
  - test/gate references in `.ai/REF/testing-and-gates.md` and command docs
  - Outcome: added script unit tests and executed full validation stack.

### Commands Run and Outcomes

- `uv run python scripts/status_report.py` -> pass
- `uv run python scripts/status_report.py --show-git-context false` -> pass
- `uv run python scripts/status_report.py --json` -> pass
- `uv run ruff check scripts/status_report.py tests/unit/scripts/test_status_report.py` -> pass
- `uv run ruff format --check scripts/status_report.py tests/unit/scripts/test_status_report.py` -> pass
- `uv run pytest tests/unit/scripts/test_status_report.py -q` -> pass (`7 passed`)
- `just status` -> pass
- `just status-ready` -> pass
- `just quality && just test` -> pass (`326 passed`)

### Acceptance Gate Evidence

- `Git Context` panel renders with branch/upstream, divergence, tree counts, commit, stash, and PR/CI summary.
- Positive flags `--show-summary`, `--show-docs`, `--show-plans`, `--show-current-focus`, `--show-git-context` default to `true`.
- Panels can be hidden via explicit false values (for example `--show-git-context false`).
- Collection is visibility-gated: hidden panels are not collected; unit tests assert no subprocess probes when all panels disabled.
- JSON mode emits deterministic payload with `git_context` schema.

### Output Artifacts

- `/tmp/status_default.out`
- `/tmp/status_no_git.out`
- `/tmp/status_payload.json`
- `/tmp/just_status.out`
- `/tmp/just_status_ready.out`

### Partial/Blocked Items

- None.

### Status Sync Follow-Up (2026-03-04)

- Updated canonical status surface:
  - `docs/dev/status.md` (`last_updated`, `Recently Completed`, `Diary Log`)
- Validation:
  - `just docs-check` -> pass
  - `just status` -> pass
