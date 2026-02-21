---
owner: "@team"
status: "active"
last_updated: "2026-02-21"
source_of_truth: true
---

# RuntimeFacade Refactor Plan

Goal: split composition/wiring out of `RuntimeFacade` into explicit composition roots:
- `ConversationRuntimeFactory`
- `ToolingFactory`
- `JobsFactory`

`RuntimeFacade` should remain a thin coordinator for routing and lifecycle only.

## Scope

In scope:
- Extract construction/wiring logic from `RuntimeFacade` into factories.
- Preserve behavior and deterministic command/result envelopes.
- Add targeted tests for factory outputs and facade orchestration seams.

Out of scope:
- New user-facing features.
- Changing command syntax, result codes, or policy semantics.
- Reworking memory/consolidation feature behavior beyond wiring relocation.

## Acceptance Criteria

- [x] `RuntimeFacade` no longer directly constructs tooling providers, job runtime objects, or conversation executor defaults inline.
- [x] `RuntimeFacade` remains responsible for:
  - input parse/routing (`command` vs `conversation`)
  - per-session serialization boundary
  - turn recording
  - close/shutdown delegation
- [x] Command and conversation behavior stays parity-equivalent (validated by tests).
- [x] Docs updated to reflect new composition boundaries.

## Required Gates

- [x] `just quality test` passes warning-clean.
- [x] Runtime/commands regression tests pass.
- [x] New factory unit tests pass.

## Phase A: Contracts and Build Specs

- [x] Define minimal build specs:
  - [x] `ConversationRuntimeSpec`
  - [x] `ToolingSpec`
  - [x] `JobsSpec`
- [x] Define factory protocols/interfaces for testability.
- [x] Add `RuntimeDependencies` (or equivalent) aggregate model passed into `RuntimeFacade`.
- [x] Ensure no behavior changes in this phase.

Acceptance checks:
- [x] `RuntimeFacade.__init__` consumes dependencies instead of constructing subsystems.
- [x] Existing tests remain green.

Non-goals:
- [x] Do not move command handler logic.
- [x] Do not alter config schema.

## Phase B: ToolingFactory Extraction

- [x] Create `ToolingFactory` module.
- [x] Move wiring for:
  - [x] `LangChainBackend`
  - [x] builtin arithmetic tools
  - [x] provider set (`builtin`/`mcp`/`plugin`)
  - [x] `SecurityGate` + `SecurityApprovalStore` + `SecurityHashService` + `SecurityPreflightScanner`
  - [x] `DockerPluginRunner`
  - [x] `SkillInvoker`
- [x] Keep deterministic error behavior identical.

Acceptance checks:
- [x] Tool dispatch and plugin security paths match current behavior.
- [x] No facade-level direct provider construction remains.

Non-goals:
- [x] No provider feature additions.
- [x] No plugin policy changes.

## Phase C: JobsFactory Extraction

- [x] Create `JobsFactory` module.
- [x] Move wiring for:
  - [x] `JobRepository`
  - [x] `JobExecutor`
  - [x] scheduler runtime build/start configuration
  - [x] `jobs_dir`/`runs_root`/scheduler sqlite path resolution
- [x] Return a jobs bundle suitable for `CommandRegistry`.

Acceptance checks:
- [x] `/jobs` command behavior unchanged.
- [x] Scheduler startup/shutdown parity preserved.

Non-goals:
- [x] No new scheduler capabilities.
- [x] No run artifact format changes.

## Phase D: ConversationRuntimeFactory Extraction

- [x] Create `ConversationRuntimeFactory` module.
- [x] Move default conversation executor construction:
  - [x] `LangChainConversationExecutor`
  - [x] checkpointer wiring
  - [x] compaction backend/max-token mapping integration seam
- [x] Expose clear dependency seam for prompt/memory summary collaborators.

Acceptance checks:
- [x] Conversation execution behavior parity (timeouts/retries/tool-loop boundary).
- [x] Existing conversation regression tests pass unchanged.

Non-goals:
- [x] No prompt policy redesign.
- [x] No model/provider behavior changes.

## Phase E: Facade Slim-Down and Final Cleanup

- [x] Remove dead imports and redundant constructor arguments.
- [x] Ensure facade methods are orchestration-only.
- [ ] Add/update architecture documentation diagram.

Acceptance checks:
- [x] `RuntimeFacade` is materially smaller and easier to reason about.
- [x] Composition ownership is clear in code and docs.

## Test Plan (Detailed)

- [x] `tests/unit/runtime/test_tooling_factory.py`
  - [x] verifies provider registry composition
  - [x] verifies security dependencies are wired
- [x] `tests/unit/runtime/test_jobs_factory.py`
  - [x] verifies paths and scheduler configuration
  - [x] verifies optional scheduler enable/disable behavior
- [x] `tests/unit/runtime/test_conversation_factory.py`
  - [x] verifies executor construction from spec
- [x] update existing facade tests to assert coordination-only responsibilities
- [x] run full suite in gate

## Risks and Mitigations

- [x] Risk: accidental behavior drift while moving wiring code.
  - Mitigation: move-only commits by phase + regression tests after each phase.
- [x] Risk: constructor churn across modules.
  - Mitigation: introduce temporary compatibility adapters during transition.
- [x] Risk: scheduler lifecycle regressions.
  - Mitigation: explicit tests for startup/shutdown and close delegation.

## Done Definition

- [x] All phase acceptance criteria checked.
- [x] `just quality test` green.
- [x] No new warning suppressions.
- [ ] PR description clearly states completed vs deferred work.
