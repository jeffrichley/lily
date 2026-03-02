# Feature: p4-agent-subsystem-phase0

This plan defines and implements Phase 0 foundations for the real agent subsystem migration from persona-backed compatibility commands.

## Feature Description

Create explicit agent domain contracts and migration scaffolding so `/agent` can move from persona compatibility mode to first-class agent entities without breaking deterministic command behavior.

## User Story

As an advanced user,
I want `/agent` to target real agent entities (not personas),
So that future supervisor/subagent workflows have a stable runtime model.

## Problem Statement

Current `/agent` behavior is explicitly persona-backed compatibility mode (`src/lily/commands/handlers/agent.py:1`, `:131`). This blocks progression to planned roadmap work for real agent subsystem.

## Solution Statement

Deliver Phase 0 as decision-complete internal foundation:
1) define agent registry/state model and migration contract,
2) introduce read-path compatibility adapter,
3) preserve existing `/agent list|use|show` envelopes during transition,
4) add command/e2e coverage for compatibility + migration behavior.

## Feature Metadata

**Feature Type**: New capability foundation (P4)
**Estimated Complexity**: High
**Primary Systems Affected**: command handlers, session/runtime model, CLI renderers, tests, docs/specs
**Dependencies**: existing persona catalog and session model

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
- `src/lily/commands/handlers/agent.py:131` - compatibility-mode message contract
- `src/lily/cli/renderers/agent.py:12` - current renderer assumptions for list/use/show payloads
- `tests/unit/commands/test_command_surface.py:644` - compatibility test expectations
- `docs/specs/commands/persona_commands.md:44` - command-level compatibility note
- `docs/specs/agents/supervisor_subagents_v1.md:30` - future orchestration architecture requirements

### New Files to Create

- `docs/specs/agents/agent_subsystem_v1.md` - authoritative contract for agent registry/state/migration
- `src/lily/agents/models.py` - agent entity and registry models
- `src/lily/agents/repository.py` - repository interface + initial file-backed adapter
- `tests/unit/agents/test_repository.py` - unit tests for registry CRUD/read semantics
- `tests/e2e/test_phase6_agent_registry.py` - e2e compatibility/migration path tests

### Files to Update

- `src/lily/commands/handlers/agent.py` - route to agent repository abstraction (compat adapter during phase)
- `src/lily/session/models.py` - explicit agent-id contract if required for migration safety
- `src/lily/cli/renderers/agent.py` - maintain deterministic rendering with new data source
- `tests/unit/commands/test_command_surface.py` - add/adjust assertions for phase-0 compatibility guarantees
- `docs/dev/status.md`, `docs/dev/roadmap.md` - progress and planning updates

### Relevant Documentation

- `docs/specs/agents/supervisor_subagents_v1.md`
- `docs/specs/commands/persona_commands.md`

### Patterns to Follow

- strategy/registry dispatch over large conditionals (`AGENTS.md`)
- deterministic command envelopes from `CommandResult`
- preserve user-facing command stability while refactoring internals

---

## IMPLEMENTATION PLAN

- [ ] Phase 1: Define agent subsystem contract and migration rules
- [ ] Phase 2: Implement registry/repository foundation with compatibility adapter
- [ ] Phase 3: Rebind `/agent` handler internals and preserve envelope parity
- [ ] Phase 4: Add unit/e2e coverage and update roadmap/status docs

### Intent Lock: Phase 1

**Source of truth**:
- `docs/dev/roadmap.md:183`
- `docs/specs/agents/supervisor_subagents_v1.md:30`

**Must**:
- Define explicit `Agent` entity fields and stable IDs
- Define migration mapping from persona IDs to agent IDs
- Define deterministic behavior when mapped entity is missing

**Must Not**:
- Must not change `/agent` command syntax in Phase 0
- Must not introduce multi-agent orchestration execution behavior yet

**Provenance map**:
- `agent.id` from registry source
- compatibility mapping from persona catalog bootstrap rules

**Acceptance gates**:
- spec document approved in PR diff

### Intent Lock: Phase 2

**Source of truth**:
- `src/lily/commands/handlers/agent.py:13`
- `tests/unit/commands/test_command_surface.py:644`

**Must**:
- Add repository abstraction for agent catalog/read/update active
- Keep persona-backed bootstrap adapter for backward compatibility
- Keep session `active_agent` semantics stable

**Must Not**:
- Must not break existing persona commands (`/persona ...`)

**Provenance map**:
- active agent from session state + repository resolution
- list rows from repository catalog

**Acceptance gates**:
- `uv run pytest tests/unit/agents/test_repository.py -q`
- `uv run pytest tests/unit/commands/test_command_surface.py -q`

### Intent Lock: Phase 3

**Source of truth**:
- `src/lily/cli/renderers/agent.py:12`
- current command result codes in handler tests

**Must**:
- Preserve result codes: `agent_listed`, `agent_set`, `agent_shown`
- Preserve deterministic error envelopes for invalid args/not found
- Remove compatibility-mode wording once rebind is complete and truthful

**Must Not**:
- Must not introduce breaking output shape changes for CLI renderer

**Provenance map**:
- rendered data from `CommandResult.data` contract

**Acceptance gates**:
- `uv run pytest tests/unit/commands/test_command_surface.py -q`
- `uv run pytest tests/unit/cli/test_cli.py -q`

### Intent Lock: Phase 4

**Source of truth**:
- roadmap planned feature track + status diary conventions

**Must**:
- Add e2e tests for `/agent list|use|show` through runtime boundary
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
- **CREATE**: `src/lily/agents/models.py`, `src/lily/agents/repository.py`
- **VALIDATE**: unit model/repository tests

### UPDATE command/runtime integration

- **UPDATE**: `src/lily/commands/handlers/agent.py` to use agent repository abstraction
- **UPDATE**: ensure session active-agent handling remains deterministic
- **VALIDATE**: command surface tests + CLI renderer tests

### ADD e2e coverage

- **CREATE**: `tests/e2e/test_phase6_agent_registry.py`
- **VALIDATE**: targeted e2e and full test gate

### UPDATE docs and planning artifacts

- **UPDATE**: `docs/dev/status.md` diary
- **UPDATE**: `docs/dev/roadmap.md` planned feature track status notes
- **VALIDATE**: `just docs-check`

---

## TESTING STRATEGY

### Unit Tests

- repository load/list/get semantics
- compatibility mapping and not-found behavior
- command envelope parity for `/agent` subcommands

### Integration/E2E

- `/agent list|use|show` through runtime command path
- session persistence of active agent across restart path (existing harness style)

### Edge Cases

- active agent points to missing registry entry
- duplicate agent ids in source
- migration bootstrap when persona catalog is empty

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style

- `just quality-check`

### Level 2: Unit Tests

- `uv run pytest tests/unit/agents/test_repository.py -q`
- `uv run pytest tests/unit/commands/test_command_surface.py -q`

### Level 3: Integration/E2E

- `uv run pytest tests/e2e/test_phase6_agent_registry.py -q`

### Level 4: Full Regression

- `just test`

### Level 5: Docs

- `just docs-check`

---

## ACCEPTANCE CRITERIA

- [ ] Agent registry/state contract exists and is documented.
- [ ] `/agent` commands are backed by agent repository abstraction.
- [ ] Existing command codes/envelope semantics remain deterministic.
- [ ] Compatibility migration path is explicitly defined and tested.
- [ ] Roadmap/status docs updated without overstating subsystem completion.

## COMPLETION CHECKLIST

- [ ] All tasks executed in order
- [ ] Unit/integration/e2e validations pass
- [ ] Full gates pass
- [ ] Docs and roadmap/status updates completed

## NOTES

- Phase 0 is foundation + compatibility rebind only. Full supervisor/subagent orchestration remains deferred to subsequent phases.
