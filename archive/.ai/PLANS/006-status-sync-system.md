# Feature: status-sync-system

Create a durable status sync workflow around `scripts/status_report.py` so operators can run one command any time and trust output freshness.

## Feature Description

Add `.ai` command/rule guidance and runbook commands that keep canonical docs and plan trackers updated in a predictable loop. Ensure docs validation is always part of the loop.

## User Story

As a repo operator,
I want one repeatable status workflow (`just status`/`just status-ready`) tied into `.ai` commands,
So that status output remains accurate without manual rediscovery.

## Problem Statement

`just status` exists, but update responsibilities are implicit and plan surfaces are split between `.ai/PLANS` and `docs/dev/plans`, increasing drift risk.

## Solution Statement

1. Add a dedicated `.ai/COMMANDS/status-sync.md` command.
2. Wire status sync requirements into execute/validate/handoff command docs.
3. Update `scripts/status_report.py` to include `.ai/PLANS` alongside `docs/dev/plans`.
4. Add `just status-ready` (docs validation + status report).
5. Update `.ai/HUMAN_RUNBOOK.md` with explicit status cadence and commands.

## Feature Metadata

**Feature Type**: Enhancement (workflow/docs/ops)  
**Estimated Complexity**: Medium  
**Primary Systems Affected**: `.ai/COMMANDS/*`, `.ai/HUMAN_RUNBOOK.md`, `justfile`, `scripts/status_report.py`  
**Dependencies**: Existing `just docs-check` and `scripts/status_report.py`

## Branch Setup (Required)

```bash
PLAN_FILE=".ai/PLANS/006-status-sync-system.md"
PLAN_SLUG="$(basename "$PLAN_FILE" .md)"
BRANCH_NAME="feat/${PLAN_SLUG}"
git show-ref --verify --quiet "refs/heads/${BRANCH_NAME}" \
  && git switch "${BRANCH_NAME}" \
  || git switch -c "${BRANCH_NAME}"
```

## CONTEXT REFERENCES

- `.ai/RULES.md` - plan-before-code and required validation gates.
- `.ai/COMMANDS/validate.md` - canonical validation workflow.
- `.ai/COMMANDS/execute.md` - phase execution contract.
- `.ai/HUMAN_RUNBOOK.md` - operator command order and cadence.
- `scripts/status_report.py` - current status rendering and plan source logic.
- `justfile` - existing `status` and `docs-check` targets.

## IMPLEMENTATION PLAN

- [x] Phase 1: Add status-sync command and command-doc integration
- [x] Phase 2: Expand status report plan coverage and operator command targets
- [x] Phase 3: Update runbook and validate end-to-end

### Intent Lock: Phase 1

**Source of truth**: `.ai/COMMANDS/execute.md`, `.ai/COMMANDS/validate.md`, `.ai/COMMANDS/handoff.md`  
**Must**:
- introduce a dedicated `status-sync` command doc
- define deterministic steps for status/doc updates and docs validation
- integrate references from execute/handoff without conflicting existing flow

**Must Not**:
- remove required validation gates
- redefine command order semantics outside runbook context

**Acceptance gates**:
- `rg "status-sync" .ai/COMMANDS/execute.md .ai/COMMANDS/handoff.md`
- `just docs-check`

### Intent Lock: Phase 2

**Source of truth**: `scripts/status_report.py`, `justfile`  
**Must**:
- include `.ai/PLANS/*.md` visibility in status report
- keep rich structured rendering style
- add one-command validation+status target in `justfile`

**Must Not**:
- break existing `docs/dev/plans/*_execution_plan.md` reporting
- replace interactive output with raw JSON

**Acceptance gates**:
- `just status`
- `just status-ready`

### Intent Lock: Phase 3

**Source of truth**: `.ai/HUMAN_RUNBOOK.md`, `.ai/COMMANDS/validate.md`  
**Must**:
- document exact commands for quick status checks and phase cadence
- include docs validation explicitly in operator workflow

**Must Not**:
- create ambiguous optional wording for required gates

**Acceptance gates**:
- `just docs-check`
- `just status-ready`

## STEP-BY-STEP TASKS

### Phase 1

- **CREATE** `.ai/COMMANDS/status-sync.md` with objective, required inputs, exact update steps, and required evidence.
- **UPDATE** `.ai/COMMANDS/execute.md` to invoke status-sync after implementation phases.
- **UPDATE** `.ai/COMMANDS/handoff.md` to include final status snapshot command.
- **UPDATE** `.ai/COMMANDS/validate.md` to explicitly include docs validation in baseline checks.

### Phase 2

- **UPDATE** `scripts/status_report.py` to report both domain execution plans and `.ai` implementation plans.
- **UPDATE** `justfile` with `status-ready` target (`docs-check` + `status`).

### Phase 3

- **UPDATE** `.ai/HUMAN_RUNBOOK.md` with quick status commands and post-phase status-sync cadence.
- **RUN** validation commands and capture outcomes.
- **UPDATE** this plan checkboxes and append execution report.

## Required Tests and Gates

- `just docs-check`
- `just status`
- `just status-ready`

## Definition of Visible Done

A human can run:
1. `just status-ready` and see docs validation pass plus rich status output.
2. `just status` and see plan visibility covering both `.ai/PLANS/*.md` and `docs/dev/plans/*_execution_plan.md`.
3. Read `.ai/HUMAN_RUNBOOK.md` and find exact status maintenance cadence/commands.

## Execution Report

### 2026-03-03

- Completion status: Completed
- Commands run and outcomes:
  - `rg "status-sync" .ai/COMMANDS/execute.md .ai/COMMANDS/handoff.md .ai/HUMAN_RUNBOOK.md` -> pass
  - `just docs-check` -> pass
  - `just status` -> pass
  - `just status-ready` -> pass
- Output artifacts verified:
  - rich status report rendered with both `docs/dev/plans` and `.ai/PLANS` surfaces
  - runbook updated with quick status commands and cadence

## Plan Patch

### 2026-03-03 - Add Focus Quality Criteria

Follow-up scope requested after initial completion:
- add explicit rules for how to choose and maintain `## Current Focus`
- include quality criteria and anti-patterns, not just "update this section"

Added phase:
- [x] Phase 4: Document Current Focus quality criteria and best practices
- [x] Phase 5: Add explicit PR checks polling/merge-or-fix loop guidance
- [x] Phase 6: Add missing phase-intent-check command adapted for Lily workflow
- [x] Phase 7: Clarify phase-intent-check argument usage in HUMAN_RUNBOOK

### 2026-03-03 - Phase 4 Execution

- Commands run and outcomes:
  - `just docs-check` -> pass
  - `just status` -> pass
- Output artifacts verified:
  - `.ai/COMMANDS/status-sync.md` includes explicit Current Focus quality criteria
  - `docs/dev/status.md` includes matching Focus Quality Criteria rubric
  - rubric kept in a dedicated `## Focus Quality Criteria` section so `status_report.py` focus extraction remains scoped to active focus bullets only

### 2026-03-03 - Phase 5 Execution

- Commands run and outcomes:
  - `rg -n "Monitor CI checks|gh pr checks|Decision rule" .ai/COMMANDS/pr.md` -> pass
- Output artifacts verified:
  - `.ai/COMMANDS/pr.md` now requires continuous check polling until completion
  - explicit merge-if-green / fix-and-repoll decision loop documented

### 2026-03-03 - Phase 6 Execution

- Commands run and outcomes:
  - `rg --files .ai/COMMANDS | rg 'phase-intent-check.md'` -> pass
- Output artifacts verified:
  - `.ai/COMMANDS/phase-intent-check.md` added and aligned to Lily phase contract requirements
  - command explicitly requires phase intent locks, ambiguity patching before coding, and post-phase `status-sync`

### 2026-03-03 - Phase 7 Execution

- Commands run and outcomes:
  - `just docs-check` -> pass
  - `rg -n "phase-intent-check\\.md" .ai/HUMAN_RUNBOOK.md` -> pass
- Output artifacts verified:
  - runbook now includes exact argument format plus concrete `phase-intent-check` example invocation

### 2026-03-03 - Status Sync Run (`.ai/COMMANDS/status-sync.md .ai/PLANS/006-status-sync-system.md`)

- Updated docs/plans considered:
  - `.ai/PLANS/006-status-sync-system.md`
  - `docs/dev/status.md`
- Commands run and outcomes:
  - `just docs-check` -> pass
  - `just status` -> pass
- Output artifacts verified:
  - status report renders canonical docs + plan trackers + current focus panel

### 2026-03-03 - Status Sync Run (Strict Required-Steps Pass)

- Updated docs/plans:
  - `docs/dev/status.md` (`## Recently Completed`, `## Diary Log`)
  - `.ai/PLANS/006-status-sync-system.md` (execution evidence)
- Canonical docs reviewed for impact:
  - `docs/dev/roadmap.md` -> no priority/order change required
  - `docs/dev/debt/debt_tracker.md` -> no debt create/close/retarget change required
- Plan tracker state:
  - `.ai/PLANS/006-status-sync-system.md` remains fully checked for completed phases
  - `docs/dev/plans/*_execution_plan.md` unchanged (no domain-plan phase work in this pass)
- Commands run and outcomes:
  - `just docs-check` -> pass
  - `just status` -> pass
