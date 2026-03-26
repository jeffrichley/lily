---
owner: "@jeffrichley"
last_updated: "2026-03-04"
status: "active"
source_of_truth: true
---

# Dev Status Diary

Purpose: single running diary for what changed, what is active now, and what risks are open.

## Authority

This document is authoritative for:
- current work focus
- chronological development diary entries
- high-level active risks/blockers

This document is not authoritative for:
- feature prioritization/order (`docs/dev/roadmap.md`)
- phase-level implementation checklists (`docs/dev/plans/`)
- debt item definitions/ownership (`docs/dev/debt/debt_tracker.md`)

## Current Focus

- Execute CAP-011 through CAP-015 orchestration implementation phases with standards-first runtime contracts (`.ai/PLANS/014-executable-orchestration-v1-e2e.md`).
- Close executable-type interoperability non-compliance across `agent/tool/skill/workflow/blueprint/job` (`docs/dev/references/interoperability-remediation-matrix-v1.md`).

## Focus Quality Criteria

Use this rubric when updating `## Current Focus`.

1. Selection scope:
   - keep only items expected to be actively executed in the next 3-7 days
   - keep 2-4 bullets maximum
   - ensure each bullet maps to a canonical source (`docs/dev/roadmap.md`, `docs/dev/debt/debt_tracker.md`, or a specific plan path)
2. Bullet quality:
   - write bullets as `outcome + source path`
   - prefer concrete outcomes over generic activity labels
3. Freshness:
   - on each phase completion, either advance the same bullet or replace it with the next active item
   - if unchanged for 7+ days, document blocker rationale in `## Diary Log`
4. Non-goals:
   - do not list completed work
   - do not list long-horizon ideas not in active execution
   - do not mix internal implementation detail into user-visible feature bullets
5. Validation:
   - update `last_updated` in the same edit when focus changes
   - run `just docs-check` and `just status` after edits

## Recently Completed

- Completed Phase 4 supervisor runtime MVP with typed planner contracts, bounded multi-step delegation, deterministic aggregation, and integration coverage (`.ai/PLANS/014-executable-orchestration-v1-e2e.md`).
- Completed Phase 3 executable adapters over existing runtime (`agent`/`skill`/`tool`/`blueprint`/`job`) with canonical envelope normalization and unit/e2e regression coverage (`.ai/PLANS/014-executable-orchestration-v1-e2e.md`).
- Completed Phase 2 resolver/dispatcher registry runtime with deterministic unresolved/ambiguous envelopes and unit coverage (`.ai/PLANS/014-executable-orchestration-v1-e2e.md`).
- Completed Phase 1 common executable contracts with strict envelopes/protocols and unit validation (`.ai/PLANS/014-executable-orchestration-v1-e2e.md`).
- Completed Phase 0 human review and standards-compliance baseline for executable types; recorded non-compliance and remediation draft items (`.ai/PLANS/014-executable-orchestration-v1-e2e.md`, `docs/dev/references/interoperability-remediation-matrix-v1.md`).
- Delivered `just status` Git Context panel with default-on positive `--show-*` flags, lazy panel collection, and explicit `--json` mode (`.ai/PLANS/013-status-git-context-panel.md`).
- Closed P3 debt item for test-suite maintainability via module splits and repetitive-case parameterization (DEBT-011) (`docs/dev/debt/debt_tracker.md`).
- Session persistence schema versioning and deterministic recovery coverage delivered (SI-006) (`.ai/PLANS/011-session-persistence-schema-versioning.md`).
- Seedling Copier template planning phase finalized and synced as complete (`.ai/PLANS/008-seedling-copier-template.md`).
- Closed P1 debt item for deterministic language-policy read/decode/parse denial handling (DEBT-008) (`docs/dev/debt/debt_tracker.md`).
- Closed P1 debt item for pre-execution language restriction layer with closure evidence (DEBT-009) (`docs/dev/debt/debt_tracker.md`).
- Status sync workflow and runbook/command enforcement delivered (`.ai/PLANS/006-status-sync-system.md`).
- Real agent subsystem phase-0 migration completed (`.ai/PLANS/005-p4-agent-subsystem-phase0.md`).
- Jobs execution phases J0-J3 completed (`docs/dev/plans/jobs_execution_plan.md`).
- E2E execution phases 1-5 completed (`docs/dev/plans/e2e_execution_plan.md`).
- RuntimeFacade decomposition plan delivered (`docs/dev/plans/runtime_facade_refactor_plan.md`).

## Open Risks

- Risk: documentation drift between weekly status and plan trackers.
  - Mitigation: on every phase completion, update plan checklist first, then append diary entry here.
- Risk: standards-first rewiring may intentionally break legacy CLI/REPL flows.
  - Mitigation: keep compatibility out-of-scope explicit in plan/checklist and validate against interoperability contract, not legacy behavior.

## Diary Log

- 2026-03-04: Completed `.ai/PLANS/014-executable-orchestration-v1-e2e.md` Phase 4 by implementing `src/lily/runtime/orchestration/{plan_models.py,supervisor.py,aggregator.py}` and wiring supervisor dependency surfaces in `src/lily/runtime/runtime_dependencies.py` + `src/lily/runtime/facade.py`; added `tests/unit/runtime/orchestration/test_supervisor.py` and `tests/integration/runtime/test_supervisor_delegation.py`; validated with `uv run pytest tests/unit/runtime/orchestration/test_supervisor.py tests/integration/runtime/test_supervisor_delegation.py -q`, `just lint`, and `just types`.
- 2026-03-04: Completed `.ai/PLANS/014-executable-orchestration-v1-e2e.md` Phase 3 by implementing adapter handlers for `agent`, `skill`, `tool`, `blueprint`, and `job` under `src/lily/runtime/executables/handlers/*`; added/expanded adapter unit coverage (`tests/unit/runtime/executables/handlers/*`) and validated with `uv run pytest tests/unit/runtime/executables/handlers -q`, `uv run pytest tests/e2e/test_phase3_routing.py tests/e2e/test_phase4_memory_jobs.py -q`, `just format-check`, `just lint`, and `just types`.
- 2026-03-04: Completed `.ai/PLANS/014-executable-orchestration-v1-e2e.md` Phase 2 by implementing deterministic `ExecutableCatalogResolver` and `RegistryExecutableDispatcher` with handler registry protocol in `src/lily/runtime/executables/*` and adding `tests/unit/runtime/executables/test_resolver.py` + `test_dispatcher.py`; validated with targeted unit tests, `just format-check`, `just lint`, `just types`, and `just test`.
- 2026-03-04: Completed `.ai/PLANS/014-executable-orchestration-v1-e2e.md` Phase 1 by adding canonical executable envelopes and protocols under `src/lily/runtime/executables/*` plus `tests/unit/runtime/executables/test_executable_models.py`; validated with `uv run pytest tests/unit/runtime/executables/test_executable_models.py -q`, `just format-check`, `just lint`, and `just types`.
- 2026-03-04: Completed `.ai/PLANS/014-executable-orchestration-v1-e2e.md` Phase 0 human review baseline for `agent`, `blueprint`, `skill`, `tool`, and `job`; confirmed major non-compliance with interoperability contract in missing supervisor/runtime envelopes, stubbed MCP wiring, non-standard skill import semantics, missing workflow kind, and direct blueprint/job bypass paths; captured required remediation in `docs/dev/references/interoperability-remediation-matrix-v1.md` and drafted debt issue candidates (`DRAFT-EO-001` supervisor/handoff runtime gap, `DRAFT-EO-002` MCP policy/registration gap, `DRAFT-EO-003` Agent Skills import/progressive-disclosure gap, `DRAFT-EO-004` workflow executable + trace/replay gap).
- 2026-03-04: Completed status report enhancement plan with Git Context rendering, positive default-on panel visibility flags, visibility-gated command collection, JSON output mode, and unit coverage (`.ai/PLANS/013-status-git-context-panel.md`).
- 2026-03-03: Completed test-suite rejiggering pass: split oversized command/CLI/runtime conversation modules, added shared test helpers, and parameterized repetitive config/security/tool-dispatch matrices; closed related P3 debt item (`docs/dev/debt/debt_tracker.md`).
- 2026-03-03: Completed session persistence schema-version contract hardening with explicit migration dispatch scaffolding, unsupported-version recovery coverage, and deterministic bootstrap reason messaging (`.ai/PLANS/011-session-persistence-schema-versioning.md`).
- 2026-03-03: Updated `Current Focus` to remove P2 debt items per current-focus priority guardrails and shifted active focus to roadmap-prioritized open system improvements.
- 2026-03-03: Completed status sync for seedling Copier template planning (`.ai/PLANS/008-seedling-copier-template.md`) and moved the work item from active focus to completed.
- 2026-03-03: Created the seedling Copier template execution plan (`.ai/PLANS/008-seedling-copier-template.md`) with locked phase intent and status-sync-compatible output expectations for next implementation work.
- 2026-03-03: Closed the remaining P1 language-policy read/decode failure debt item after implementing deterministic `file_read_error`/`file_decode_error` denials and adding scanner + SecurityGate + tool-dispatch coverage.
- 2026-03-03: Closed the P1 language-restriction-layer debt item after re-validating policy/security/dispatch tests and confirming layered security model documentation.
- 2026-03-03: Delivered status-sync system (`status-sync`, `phase-intent-check`, PR polling loop, runbook cadence, `status-ready`, and status report coverage for `.ai/PLANS`) and validated with docs/status gates.
- 2026-03-03: Completed agent subsystem Phase 4 with e2e `/agent` registry coverage and persona/agent state boundary assertions; updated roadmap/spec indexes to reflect first-class agent runtime path completion.
- 2026-03-02: Completed language restriction layer implementation phases (AST policy contract, SecurityGate integration, deterministic scan cache) and related tests; debt closure intentionally deferred pending review conversation.
- 2026-03-02: Docs cleanup pass started. Reconciled stale status references and aligned tracker roles.
- 2026-03-02: Pulled upstream docs updates for debt issue drafts (PR #14).
- 2026-02-22: Runtime refactor and e2e coverage landed on `main` (`9b2e1b7`, `39d9d5a`).
- 2026-02-21: CLI/runtime modularization landed (`6841688`, `6a076c9`).
- 2026-02-19: Blueprints plan completed through B3 (`docs/dev/plans/blueprints_execution_plan.md`).
- 2026-02-19: Jobs plan delivered through J3 (`docs/dev/plans/jobs_execution_plan.md`).

## Update Workflow

When implementation phase work completes:
1. Update the relevant plan in `docs/dev/plans/` (checklist + acceptance status).
2. Append a dated entry in this diary.
3. Update `docs/dev/roadmap.md` only if priorities/story ordering changed.
4. Update `docs/dev/debt/debt_tracker.md` if debt was created or closed.
