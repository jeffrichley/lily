---
owner: "@team"
last_updated: "2026-02-21"
status: "active"
source_of_truth: true
---

# E2E Execution Plan

Purpose: define and track end-to-end coverage for Lily CLI/runtime behavior with deterministic assertions.

## Scope

In scope:
- CLI user journeys (`init`, `run`, `repl`).
- Runtime routing (commands, tool-dispatch, conversation).
- Persistence/restart continuity.
- Jobs lifecycle and scheduler controls.
- Memory and persona reload workflows.
- Security approval and policy-denial flows.

Out of scope:
- Load/perf benchmarking (tracked separately).
- External integration test harnesses beyond local runtime boundaries.

## Required Gates

- [x] `just quality test` remains green with e2e tests included.
- [x] E2E tests run in CI (or explicit `just e2e` gate added and wired).
- [x] Warning-clean test runs maintained.

## Phase 1: Harness Foundation

- [x] Create `tests/e2e/` directory and pytest marker strategy.
- [x] Add stable fixtures for isolated workspace roots (`tmp_path/.lily`).
- [x] Add helper for invoking CLI commands consistently (`init/run/repl`).
- [x] Add helper for parsing deterministic command result/output assertions.
- [x] Define golden assertion helpers for stable code/message/data checks.

Acceptance criteria:
- [x] At least one smoke e2e test executes through new harness.
- [x] No dependency on developer-local state.

## Phase 2: Core Session and Command Flows

- [x] `init -> run -> session persisted`.
- [x] REPL restart continuity (persona/style/skill state retained).
- [x] Slash alias command e2e (`/add 2+2`-style path).
- [x] Reload commands (`/reload_skills`, `/reload_persona`) after filesystem change.
- [x] Corrupt session recovery (backup + recreated valid session).
- [x] Invalid config fallback still allows execution.

Acceptance criteria:
- [x] All tests assert deterministic user-visible behavior and persisted artifacts.
- [x] Session and config recovery paths are covered by e2e (not only unit tests).

## Phase 3: Runtime Routing and Guardrail Flows

- [x] Tool-dispatch success path.
- [x] Tool input validation failure (`tool_input_invalid`) path.
- [x] Provider unbound/missing tool deterministic error path.
- [x] Conversation happy path (`conversation_reply`) path.
- [x] Conversation policy/guardrail denial path.
- [x] Multi-client parity: equivalent scripted flow via `run` and `repl`.

Acceptance criteria:
- [x] Command + conversation routing both validated at e2e boundary.
- [x] Stable error envelopes validated for key denial/invalid flows.

## Phase 4: Memory and Jobs Operational Flows

- [x] Memory flow e2e:
  - [x] `remember` + `/memory show`
  - [x] `/memory evidence ingest`
  - [x] `/memory evidence show`
- [x] Jobs flow e2e:
  - [x] `/jobs list`
  - [x] `/jobs run <id>`
  - [x] `/jobs tail <id>`
  - [x] `/jobs history <id>`
- [x] Scheduler controls e2e:
  - [x] `/jobs status`
  - [x] pause/resume/disable action flow

Acceptance criteria:
- [x] Expected run artifacts are present and validated.
- [x] Scheduler status/action command behavior is deterministic.

## Phase 5: Security Approval Lifecycle

- [x] Approval required path surfaces deterministic alert.
- [x] Approval deny path surfaces deterministic denial result.
- [x] Run-once approval allows single execution.
- [x] Always-allow approval persists and reuses grant when hash unchanged.
- [x] Hash change invalidates prior grant behavior.

Acceptance criteria:
- [x] Security HITL lifecycle is covered end-to-end.
- [x] Approval persistence semantics are validated via storage artifacts.

## Test Inventory Checklist

- [x] `init -> run -> session persisted`
- [x] `repl restart continuity`
- [x] `slash command alias e2e`
- [x] `tool-dispatch validation failures`
- [x] `tool-dispatch provider error path`
- [x] `conversation happy path`
- [x] `conversation guardrails`
- [x] `jobs lifecycle e2e`
- [x] `scheduler controls e2e`
- [x] `memory long + evidence e2e`
- [x] `reload commands`
- [x] `security approval flow`
- [x] `corrupt session recovery`
- [x] `config fallback path`
- [x] `multi-client parity harness`

## Risks and Mitigations

- [x] Risk: flaky REPL interaction assertions.
  - Mitigation: prefer deterministic scripted input/output and artifact assertions.
- [x] Risk: tests become brittle on presentation-only changes.
  - Mitigation: assert stable semantics (`code`, key messages, artifacts) over color/layout.
- [x] Risk: security/HITL tests block.
  - Mitigation: inject deterministic prompt stubs in e2e harness.

## Done Definition

- [x] All inventory tests implemented and passing.
- [x] E2E suite integrated into normal quality workflow.
- [x] Documentation updated with how to run/debug e2e locally.

## Local Run/Debug

- Run e2e suite only: `just e2e`
- Run full gates + tests: `just quality test`
- Run one e2e file: `uv run pytest tests/e2e/test_phase4_memory_jobs.py -q`
- Run one e2e test: `uv run pytest tests/e2e/test_phase4_memory_jobs.py::test_scheduler_controls_e2e -q`
