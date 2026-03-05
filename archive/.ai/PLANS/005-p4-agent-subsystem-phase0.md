# Feature: p4-agent-subsystem-phase0

This plan defines and implements Phase 0 foundations for a first-class agent subsystem with hard separation from personas.

## Feature Description

Create explicit agent domain contracts and command/runtime wiring so `/agent` operates on real agent entities only. Persona remains a user-facing style system and is not used as an execution identity.

## User Story

As an advanced user,
I want `/agent` to target real agent entities (not personas),
So that supervisor/subagent workflows have a stable runtime model that is independent of user-facing persona state.

## Problem Statement

Current `/agent` behavior is explicitly persona-backed compatibility mode (`src/lily/commands/handlers/agent.py:1`, `:131`). This blocks progression to planned roadmap work for real agent subsystem.

## Solution Statement

Deliver Phase 0 as decision-complete internal foundation:
1) define explicit `Agent` and `Persona` boundary contracts,
2) add first-class agent registry/repository/service foundation,
3) rebind `/agent list|use|show` to agent entities only (no persona compatibility layer),
4) add tests that enforce persona/agent boundary and deterministic runtime behavior.

## Feature Metadata

**Feature Type**: New capability foundation (P4)
**Estimated Complexity**: High
**Primary Systems Affected**: command handlers, session/runtime model, CLI renderers, tests, docs/specs
**Dependencies**: session model and command/runtime infrastructure

## Branch Setup (Required)

```bash
PLAN_FILE=".ai/PLANS/005-p4-agent-subsystem-phase0.md"
PLAN_SLUG="$(basename "$PLAN_FILE" .md)"
BRANCH_NAME="feat/${PLAN_SLUG}"
git show-ref --verify --quiet "refs/heads/${BRANCH_NAME}" \
  && git switch "${BRANCH_NAME}" \
  || git switch -c "${BRANCH_NAME}"
```

---

## CONTEXT REFERENCES

### Relevant Codebase Files (Read First)

- `docs/dev/roadmap.md:183` - planned feature track for real `/agent` migration
- `src/lily/commands/handlers/agent.py:1` - current persona-backed compatibility handler
- `src/lily/session/models.py` - current active persona/agent session coupling surface
- `src/lily/cli/renderers/agent.py:12` - current renderer assumptions for list/use/show payloads
- `tests/unit/commands/test_command_surface.py:644` - command behavior expectations
- `docs/specs/commands/persona_commands.md:44` - current `/agent` compatibility note to remove/update
- `docs/specs/agents/supervisor_subagents_v1.md:30` - future orchestration architecture requirements

### New Files to Create

- `docs/specs/agents/agent_subsystem_v1.md` - authoritative contract for agent runtime domain and persona boundary
- `src/lily/agents/models.py` - agent entity and registry models
- `src/lily/agents/repository.py` - repository interface + initial file-backed adapter
- `src/lily/agents/service.py` - lifecycle/selection rules above repository
- `tests/unit/agents/test_repository.py` - unit tests for registry CRUD/read semantics
- `tests/unit/agents/test_service.py` - unit tests for agent selection/validation semantics
- `tests/e2e/test_phase6_agent_registry.py` - e2e runtime command path tests for real agents

### Files to Update

- `src/lily/commands/handlers/agent.py` - route to agent service (no persona fallback)
- `src/lily/session/models.py` - separate explicit `active_persona` and `active_agent` contracts
- `src/lily/cli/renderers/agent.py` - maintain deterministic rendering with new data source
- `tests/unit/commands/test_command_surface.py` - add/adjust assertions for phase-0 separation guarantees
- `docs/dev/status.md`, `docs/dev/roadmap.md` - progress and planning updates

### Relevant Documentation

- `docs/specs/agents/supervisor_subagents_v1.md`
- `docs/specs/commands/persona_commands.md`

### Patterns to Follow

- strategy/registry dispatch over large conditionals (`AGENTS.md`)
- deterministic command envelopes from `CommandResult`
- explicit boundary contracts between domains; no hidden cross-coupling

---

## IMPLEMENTATION PLAN

- [x] Phase 1: Define agent/persona boundary contract and clean-break rules
- [x] Phase 2: Implement registry/repository/service foundation for real agents
- [x] Phase 3: Rebind `/agent` handler internals to agent service and remove compatibility paths
- [x] Phase 4: Add unit/e2e coverage and update roadmap/status/docs/spec notes

### Intent Lock: Phase 1

**Source of truth**:
- `docs/dev/roadmap.md:183`
- `docs/specs/agents/supervisor_subagents_v1.md:30`

**Must**:
- Define explicit `Agent` entity fields and stable IDs
- Define explicit `Persona` scope as user-facing style/voice only
- Define strict boundary rule: persona selection cannot alter agent capability/policy state

**Must Not**:
- Must not introduce persona->agent implicit mapping
- Must not introduce multi-agent orchestration execution behavior yet

**Provenance map**:
- `agent.id` from agent registry source
- `persona.id` from persona catalog source
- runtime authority from agent service/policy only

**Acceptance gates**:
- spec document approved in PR diff

### Intent Lock: Phase 2

**Source of truth**:
- `src/lily/commands/handlers/agent.py:13`
- `tests/unit/commands/test_command_surface.py:644`

**Must**:
- Add repository abstraction for agent catalog/read/update active agent
- Add service layer for selection/validation logic
- Keep session semantics deterministic with explicit separated fields

**Must Not**:
- Must not use persona catalog as `/agent` backing store
- Must not break existing `/persona ...` commands

**Provenance map**:
- active agent from session state + agent service resolution
- list rows from repository catalog

**Acceptance gates**:
- `uv run pytest tests/unit/agents/test_repository.py -q`
- `uv run pytest tests/unit/agents/test_service.py -q`
- `uv run pytest tests/unit/commands/test_command_surface.py -q`

### Intent Lock: Phase 3

**Source of truth**:
- `src/lily/cli/renderers/agent.py:12`
- current command result codes in handler tests

**Must**:
- Rebind `/agent list|use|show` to real agent entities only
- Preserve deterministic error envelopes for invalid args/not found
- Remove all persona-backed compatibility wording and fallback paths

**Must Not**:
- Must not let `/agent use` mutate `active_persona`
- Must not let `/persona use` mutate `active_agent`

**Provenance map**:
- rendered agent data from `CommandResult.data` contract
- execution authority from `active_agent` only

**Acceptance gates**:
- `uv run pytest tests/unit/commands/test_command_surface.py -q`
- `uv run pytest tests/unit/cli/test_cli.py -q`

### Intent Lock: Phase 4

**Source of truth**:
- roadmap planned feature track + status diary conventions

**Must**:
- Add e2e tests for `/agent list|use|show` through runtime boundary
- Add boundary tests proving persona changes do not alter agent execution behavior
- Update roadmap/status entries with phase completion and deferred remainder

**Must Not**:
- Must not claim full multi-agent orchestration complete

**Provenance map**:
- e2e assertions from command outputs and session state transitions

**Acceptance gates**:
- `uv run pytest tests/e2e/test_phase6_agent_registry.py -q`
- `just quality-check`
- `just test`
- `just docs-check`

---

## STEP-BY-STEP TASKS

### CREATE spec and domain model

- **CREATE**: `docs/specs/agents/agent_subsystem_v1.md`
- **CREATE**: `src/lily/agents/models.py`, `src/lily/agents/repository.py`, `src/lily/agents/service.py`
- **VALIDATE**: unit model/repository/service tests

### UPDATE command/runtime integration

- **UPDATE**: `src/lily/commands/handlers/agent.py` to use agent service (no persona fallback)
- **UPDATE**: ensure session `active_agent` and `active_persona` handling are explicit and independent
- **VALIDATE**: command surface tests + CLI renderer tests

### ADD e2e coverage

- **CREATE**: `tests/e2e/test_phase6_agent_registry.py`
- **ADD**: boundary assertions for persona/agent separation in runtime path
- **VALIDATE**: targeted e2e and full test gate

### UPDATE docs and planning artifacts

- **UPDATE**: `docs/dev/status.md` diary
- **UPDATE**: `docs/dev/roadmap.md` planned feature track status notes
- **VALIDATE**: `just docs-check`

---

## TESTING STRATEGY

### Unit Tests

- repository load/list/get semantics
- service-level selection/validation semantics
- command deterministic behavior for `/agent` subcommands with real agents only
- boundary tests: persona operations do not alter agent authority state

### Integration/E2E

- `/agent list|use|show` through runtime command path
- `/persona use` and `/agent use` state independence across command sequence
- session persistence of active agent across restart path (existing harness style)

### Edge Cases

- active agent points to missing registry entry
- duplicate agent ids in source
- persona catalog empty while agent registry exists
- agent registry empty while persona catalog exists

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style

- `just quality-check`

### Level 2: Unit Tests

- `uv run pytest tests/unit/agents/test_repository.py -q`
- `uv run pytest tests/unit/agents/test_service.py -q`
- `uv run pytest tests/unit/commands/test_command_surface.py -q`

### Level 3: Integration/E2E

- `uv run pytest tests/e2e/test_phase6_agent_registry.py -q`

### Level 4: Full Regression

- `just test`

### Level 5: Docs

- `just docs-check`

---

## ACCEPTANCE CRITERIA

- [x] Agent registry/state contract exists and is documented.
- [x] Persona/agent boundary contract is explicit and tested.
- [x] `/agent` commands are backed by agent repository + service abstractions.
- [x] `/agent` path has no persona-backed compatibility fallback.
- [x] Command codes and deterministic error behavior remain stable where still applicable.
- [x] Session state stores `active_persona` and `active_agent` as independent fields.
- [x] Roadmap/status docs updated without overstating subsystem completion.

## COMPLETION CHECKLIST

- [x] All tasks executed in order
- [x] Unit/integration/e2e validations pass
- [x] Full gates pass
- [x] Docs and roadmap/status updates completed

## NOTES

- Phase 0 is a clean-break foundation (no persona-backed compatibility layer). Full supervisor/subagent orchestration remains deferred to subsequent phases.

## Execution Report

### 2026-03-02 - Phase 1

- Completion status: Completed
- Scope executed: `Phase 1: Define agent/persona boundary contract and clean-break rules`
- Branch safety gate:
  - executed plan branch setup commands
  - current branch: `feat/005-p4-agent-subsystem-phase0` (not `main`)
- Phase intent check:
  - attempted to run `.ai/COMMANDS/phase-intent-check.md`
  - result: command file not present in repository; performed manual intent-lock verification against `Intent Lock: Phase 1`
- Commands run and outcomes:
  - `sed -n '1,280p' .ai/COMMANDS/execute.md` (pass)
  - `sed -n '1,320p' .ai/PLANS/005-p4-agent-subsystem-phase0.md` (pass)
  - branch setup command block from this plan (pass)
  - `git branch --show-current` -> `feat/005-p4-agent-subsystem-phase0` (pass)
  - `rg --files .ai/COMMANDS | sort` (pass; confirmed no phase-intent-check command)
- Output artifacts:
  - created `docs/specs/agents/agent_subsystem_v1.md`
- Acceptance gate evidence:
  - spec document added in diff and aligned to Phase 1 must/must-not contract
- Partial/blocked items:
  - none for Phase 1 scope

### 2026-03-02 - Phase 2

- Completion status: Completed
- Scope executed: `Phase 2: Implement registry/repository/service foundation for real agents`
- Phase intent check:
  - attempted to run `.ai/COMMANDS/phase-intent-check.md`
  - result: command file not present in repository; performed manual verification against `Intent Lock: Phase 2`
- Commands run and outcomes:
  - `uv run pytest tests/unit/agents/test_repository.py -q` (pass)
  - `uv run pytest tests/unit/agents/test_service.py -q` (pass)
  - `uv run pytest tests/unit/commands/test_command_surface.py -q` (pass)
  - `just quality-check` (pass)
- Output artifacts:
  - created `src/lily/agents/models.py`
  - created `src/lily/agents/repository.py`
  - created `src/lily/agents/service.py`
  - created `src/lily/agents/__init__.py`
  - created `tests/unit/agents/test_repository.py`
  - created `tests/unit/agents/test_service.py`
  - updated `src/lily/session/models.py`
  - updated `src/lily/session/factory.py`
  - updated `src/lily/session/store.py`
  - updated `tests/unit/session/test_factory.py`
  - updated `tests/unit/session/test_store.py`
  - updated `docs/specs/agents/agent_subsystem_v1.md`
- Post-implementation hardening applied in-scope (user-requested):
  - removed surprising `active_persona <- active_agent` default coupling in session factory
  - removed brittle default-agent-root path discovery from `lily.agents` API
  - switched agent repository to schema-first `*.agent.yaml|*.agent.yml` loading with legacy markdown migration support
- Acceptance gate evidence:
  - repository abstraction and service layer exist and are covered by dedicated unit tests
  - command surface suite remains green after foundation changes
- Partial/blocked items:
  - none for Phase 2 scope

### 2026-03-03 - Phase 3

- Completion status: Completed
- Scope executed: `Phase 3: Rebind /agent handler internals to agent service and remove compatibility paths`
- Phase intent check:
  - attempted to run `.ai/COMMANDS/phase-intent-check.md`
  - result: command file not present in repository; performed manual verification against `Intent Lock: Phase 3`
- Commands run and outcomes:
  - `uv run pytest tests/unit/commands/test_command_surface.py -q` (pass)
  - `uv run pytest tests/unit/cli/test_cli.py -q` (pass)
  - `just quality-check` (pass)
- Output artifacts:
  - updated `src/lily/commands/handlers/agent.py` to use `AgentService` (removed persona-backed compatibility behavior)
  - updated `src/lily/commands/registry.py` to wire `/agent` through agent repository/service
  - updated `src/lily/runtime/facade.py` for agent repository plumbing into command registry
  - updated `src/lily/commands/handlers/persona.py` to use `active_persona` only
  - updated `src/lily/commands/handlers/reload_persona.py` to validate/switch `active_persona` only
  - updated `src/lily/runtime/conversation_orchestrator.py` to resolve persona via `active_persona`
  - updated `src/lily/commands/handlers/_memory_support.py` to use persona namespace from `active_persona`
  - updated `tests/unit/commands/test_command_surface.py` for real-agent repository behavior and persona/agent boundary assertions
  - updated `docs/specs/commands/persona_commands.md` to remove compatibility wording
- Acceptance gate evidence:
  - `/agent` commands now resolve from real agent repository/service
  - deterministic result codes/envelopes preserved for list/use/show and invalid args/not found paths
  - `/agent use` no longer mutates persona state and `/persona use` no longer mutates agent state (covered by unit assertions)
- Partial/blocked items:
  - none for Phase 3 scope

### 2026-03-03 - Phase 4

- Completion status: Completed
- Scope executed: `Phase 4: Add unit/e2e coverage and update roadmap/status/docs/spec notes`
- Phase intent check:
  - attempted to run `.ai/COMMANDS/phase-intent-check.md`
  - result: command file not present in repository; performed manual verification against `Intent Lock: Phase 4`
- Commands run and outcomes:
  - `uv run pytest tests/e2e/test_phase6_agent_registry.py -q` (pass)
  - `just quality-check` (pass)
  - `just test` (pass, 280 passed)
  - `just docs-check` (pass)
- Output artifacts:
  - created `tests/e2e/test_phase6_agent_registry.py`
  - updated `docs/dev/roadmap.md`
  - updated `docs/dev/status.md`
  - updated `docs/specs/README.md`
  - updated `docs/specs/commands/persona_commands.md`
- Acceptance gate evidence:
  - e2e coverage validates `/agent list|use|show` with real agent registry contracts
  - e2e boundary assertions validate `/persona` and `/agent` state independence in runtime path
  - roadmap/status/spec docs updated to reflect completed phase scope and deferred supervisor work
- Partial/blocked items:
  - none for Phase 4 scope
