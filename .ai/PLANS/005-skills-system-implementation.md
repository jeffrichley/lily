# Feature: Skills System Full Implementation (PRD + Architecture)

The following plan should be complete, but it is important to validate documentation and codebase patterns and task sanity before starting implementation.

Pay special attention to existing runtime config contracts, deterministic policies, and strict typing/test gates.

## Feature Description

Implement the full SI-007 skills system described in `.ai/SPECS/002-skills-system/PRD.md` and `.ai/SPECS/002-skills-system/SKILLS_ARCHITECTURE.md` on top of Lily's existing runtime/tool-registry foundation. This includes skill package contracts, discovery/indexing/selection/loading/execution, policy enforcement, telemetry, and CLI visibility surfaces.

## User Story

As a Lily operator and skill author  
I want a first-class, deterministic skills system with explicit and implicit invocation  
So that Lily can reuse expertise safely, reduce prompt duplication, and keep runtime behavior auditable.

## Problem Statement

Lily currently has deterministic model/tool runtime wiring but lacks a production skills subsystem. Without this, capabilities are encoded ad hoc in prompts, reuse is poor, selection is not inspectable, and governance controls are fragmented.

## Solution Statement

Deliver a typed, policy-aware skills subsystem in `src/lily/runtime` with progressive disclosure loading and explicit integration into supervisor runtime/CLI surfaces. Implement in phased slices that preserve deterministic behavior and maintain warning-clean quality gates.

## Feature Metadata

**Feature Type**: New Capability  
**Estimated Complexity**: High  
**Primary Systems Affected**:
- `src/lily/runtime/` (new skills components + runtime integration)
- `src/lily/agents/lily_supervisor.py` and/or runtime orchestration surfaces
- `src/lily/cli.py` and new CLI handlers for skills visibility commands
- `.lily/config/*` schema contracts and sample config docs
- `tests/unit`, `tests/integration`, `tests/e2e` for skills coverage
- `docs/dev/*` status/roadmap updates when slices complete

**Dependencies**:
- Existing runtime config loader and tool registry contracts
- Pydantic validation and LangChain runtime boundaries already in repo
- No new external package dependency required for MVP baseline

## Traceability Mapping (Required When Applicable)

- Roadmap system improvements: `SI-007`
- Debt items: `None`
- Debt to roadmap linkage (if debt exists): `N/A`

## Branch Setup (Required)

Branch naming must follow the plan filename:
- Plan: `.ai/PLANS/005-skills-system-implementation.md`
- Branch: `feat/005-skills-system-implementation`

Commands (must be executable as written):
```bash
PLAN_FILE=".ai/PLANS/005-skills-system-implementation.md"
PLAN_SLUG="$(basename "$PLAN_FILE" .md)"
BRANCH_NAME="feat/${PLAN_SLUG}"
git show-ref --verify --quiet "refs/heads/${BRANCH_NAME}" \
  && git switch "${BRANCH_NAME}" \
  || git switch -c "${BRANCH_NAME}"
```

---

## Definition of Visible Done

A reviewer can directly verify the skills system via:

- Running `uv run lily skills list --config .lily/config/agent.toml` and seeing structured tabular output.
- Running `uv run lily skills inspect <skill_id> --config ...` and seeing metadata + policy/selection details.
- Running `uv run lily run --prompt '$skill:<id> ...' --config ...` and observing explicit skill invocation path.
- Running `uv run lily run --prompt 'natural language trigger...' --config ...` and observing implicit selection traces.
- Inspecting emitted structured events/log entries for selection rationale and execution outcomes.

Verification commands (final implementation slice):
- `just quality && just test`
- `uv run pytest tests/unit/runtime -k skill`
- `uv run pytest tests/integration -k skill`
- `uv run pytest tests/e2e -k "skill or skills"`

## Input Provenance

Pre-existing in-repo sources (canonical):
- `.ai/SPECS/002-skills-system/PRD.md`
- `.ai/SPECS/002-skills-system/SKILLS_ARCHITECTURE.md`
- `docs/dev/roadmap.md` (`SI-007`)
- `docs/dev/references/runtime-config-and-interfaces.md`

Skill fixture provenance:
- Generated test fixtures under `tests/fixtures/skills/` during implementation.
- Optional sample local skills under `.lily/skills/` created in-plan as deterministic examples.

Regeneration/setup commands:
```bash
# create or refresh local sample skills fixtures
uv run python scripts/skills_seed_fixtures.py
```

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `.ai/SPECS/002-skills-system/PRD.md` - product requirements and scope boundaries.
- `.ai/SPECS/002-skills-system/SKILLS_ARCHITECTURE.md` - component boundaries, contracts, and lifecycle.
- `src/lily/runtime/config_schema.py` - established strict validation patterns and config model style.
- `src/lily/runtime/config_loader.py` - deterministic loader behavior and fail-fast semantics.
- `src/lily/runtime/tool_catalog.py` - schema parsing, validation, and collision/ID guard patterns.
- `src/lily/runtime/tool_registry.py` - allowlist/policy boundary and deterministic ordering style.
- `src/lily/runtime/agent_runtime.py` - invoke flow, middleware boundaries, and typed runtime result handling.
- `src/lily/agents/lily_supervisor.py` - orchestration wiring from config -> runtime objects.
- `src/lily/cli.py` - existing rich output style and command registration patterns.
- `tests/unit/runtime/test_tool_catalog.py` - unit test pattern for schema + deterministic errors.
- `tests/integration/test_agent_runtime.py` - integration style for runtime wiring behavior.
- `tests/e2e/test_cli_agent_run.py` - CLI e2e shape for new skills commands and run path assertions.

### New Files to Create

Runtime core:
- `src/lily/runtime/skill_types.py`
- `src/lily/runtime/skill_catalog.py`
- `src/lily/runtime/skill_discovery.py`
- `src/lily/runtime/skill_registry.py`
- `src/lily/runtime/skill_selector.py`
- `src/lily/runtime/skill_loader.py`
- `src/lily/runtime/skill_executor.py`
- `src/lily/runtime/skill_policies.py`
- `src/lily/runtime/skill_events.py`

CLI/commands:
- `src/lily/commands/handlers/skills_list.py`
- `src/lily/commands/handlers/skills_inspect.py`
- `src/lily/commands/handlers/skills_doctor.py`

Tests:
- `tests/unit/runtime/test_skill_catalog.py`
- `tests/unit/runtime/test_skill_discovery.py`
- `tests/unit/runtime/test_skill_registry.py`
- `tests/unit/runtime/test_skill_selector.py`
- `tests/unit/runtime/test_skill_loader.py`
- `tests/unit/runtime/test_skill_executor.py`
- `tests/unit/runtime/test_skill_policies.py`
- `tests/integration/test_skills_runtime_flow.py`
- `tests/e2e/test_cli_skills_commands.py`

Scripts/docs (optional but recommended):
- `scripts/skills_seed_fixtures.py`
- `docs/dev/references/skills-runtime-and-contracts.md`

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [OpenAI Codex — Skills](https://platform.openai.com/docs/codex/skills)
  - Why: Canonical `SKILL.md` package and progressive disclosure posture.
- [LangChain Docs — Multi-agent and routing](https://docs.langchain.com/oss/python/langchain/multi-agent)
  - Why: Selection/delegation boundaries between main runtime and delegated agents.
- [LangChain Docs — Tools and structured invocation](https://docs.langchain.com/oss/python/langchain/tools)
  - Why: Procedural skill wrapper contracts and schema-driven execution.
- [Anthropic Docs — Prompting/skills style guidance](https://docs.anthropic.com/)
  - Why: Durable skill authoring and constrained prompt context principles.

### Patterns to Follow

**Naming Conventions:**
- snake_case IDs and module names; explicit `*Error` exception classes for contract failures.

**Error Handling:**
- field-specific deterministic validation errors; avoid silent defaults for required fields.

**Logging Pattern:**
- structured event payloads with stable keys; avoid free-form-only strings for critical decisions.

**Other Relevant Patterns:**
- Registry/strategy dispatch maps preferred over long `if`/`elif` chains.
- Rich tables/panels for CLI user-facing output.

---

## IMPLEMENTATION PLAN

Use markdown checkboxes (`- [ ]`) for implementation phases and task bullets so execution progress can be tracked live.

- [ ] Phase 0: Execution framing and acceptance lock
- [ ] Phase 1: Skill contract + schema foundation
- [ ] Phase 2: Discovery, indexing, precedence, and registry
- [ ] Phase 3: Selection/routing and progressive disclosure loader
- [ ] Phase 4: Execution adapters (playbook/procedural/agent) + policy gates
- [ ] Phase 5: Runtime integration into supervisor invoke path
- [ ] Phase 6: CLI surfaces (`skills list/inspect/doctor`) and UX
- [ ] Phase 7: Telemetry/events, diagnostics, and observability
- [ ] Phase 8: Testing, docs/status sync, and release hardening

### Phase 0: Execution framing and acceptance lock

**Intent Lock**
- **Source of truth**: PRD sections 2/4/6/8; Architecture sections 5-11; `.ai/RULES.md`.
- **Must**:
  - [ ] Freeze MVP scope in a phase checklist before implementation.
  - [ ] Define exact acceptance criteria per phase and required gates.
  - [ ] Define explicit non-goals to prevent scope bleed.
- **Must Not**:
  - [ ] Start coding before criteria/gates are written.
  - [ ] Expand to out-of-scope marketplace/autonomous systems in MVP.
- **Provenance map**:
  - [ ] Every phase maps to PRD scope bullets and architecture sections.
- **Acceptance gates**:
  - [ ] Plan updated with per-phase gates and non-goals.
  - [ ] Team-agreed ordering and dependency graph documented.

**Tasks**
- [ ] Build a phase tracker table with status/owner/dependencies.
- [ ] Define risk register: contract drift, non-deterministic routing, policy bypass, context bloat.
- [ ] Define rollback strategy per phase (feature toggle/config off).

### Phase 1: Skill contract + schema foundation

**Intent Lock**
- **Source of truth**: PRD `Skill package contract`; Architecture `SKILL.md contract` and metadata schema.
- **Must**:
  - [ ] Implement strict pydantic models for skill metadata/frontmatter and normalized summaries.
  - [ ] Enforce snake_case IDs, known enum types, and required fields.
  - [ ] Provide clear field-level errors (no generic parse failures).
- **Must Not**:
  - [ ] Introduce implicit fallback defaults for required fields.
  - [ ] Accept unknown required-contract fields silently.
- **Provenance map**:
  - [ ] `SKILL.md` frontmatter -> `SkillMetadata` model -> `SkillSummary` index record.
- **Acceptance gates**:
  - [ ] Unit tests for valid/invalid frontmatter permutations.
  - [ ] Contract fixtures for all three skill types.

**Tasks**
- [ ] CREATE `skill_types.py` with enums, summary/full models, and typed errors.
- [ ] CREATE `skill_catalog.py` parser for markdown+frontmatter extraction.
- [ ] ADD deterministic validation messages for each required field.
- [ ] ADD fixture packs for success/failure contracts.
- [ ] ADD unit tests for parsing, unknown fields, malformed versions, and ID validation.

### Phase 2: Discovery, indexing, precedence, and registry

**Intent Lock**
- **Source of truth**: PRD `Local skill discovery`, `collision policy`; Architecture sections 7 and 8 prerequisites.
- **Must**:
  - [ ] Discover skills from configured roots/scopes in deterministic order.
  - [ ] Resolve collisions via precedence + semantic version tie-break.
  - [ ] Emit discover/shadow diagnostics records.
- **Must Not**:
  - [ ] Use filesystem iteration order without explicit sorting.
  - [ ] Allow duplicate winner outcomes between runs.
- **Provenance map**:
  - [ ] Scope order + semantic version -> registry winner record.
- **Acceptance gates**:
  - [ ] Unit tests for precedence and tie-break matrix.
  - [ ] Integration test proving deterministic registry across repeated runs.

**Tasks**
- [ ] CREATE `skill_discovery.py` for root walking and candidate collection.
- [ ] CREATE `skill_registry.py` for index build, collision resolution, and query APIs.
- [ ] UPDATE config schema to include skills roots/scopes and enablement flags.
- [ ] ADD unit tests for same-id collisions and lexical deterministic fallback.
- [ ] ADD integration test for merged repo/user/system roots.

### Phase 3: Selection/routing and progressive disclosure loader

**Intent Lock**
- **Source of truth**: PRD `explicit+implicit invocation` and `progressive disclosure`; Architecture sections 8 and 9.
- **Must**:
  - [ ] Support explicit `$skill:<id>` path with highest precedence.
  - [ ] Implement deterministic lexical scoring baseline for implicit selection.
  - [ ] Hydrate full skill bodies only after selection.
- **Must Not**:
  - [ ] Load all full `SKILL.md` bodies at index time.
  - [ ] Use non-deterministic/random tie-break without stable rules.
- **Provenance map**:
  - [ ] Prompt tokens + triggers + tags -> score breakdown -> selected IDs + rationale.
- **Acceptance gates**:
  - [ ] Unit tests for explicit/implicit/none routing modes.
  - [ ] Unit tests for cache hit/miss and deterministic load errors.

**Tasks**
- [ ] CREATE `skill_selector.py` with strategy dispatch map by routing mode.
- [ ] CREATE `skill_loader.py` with summary/full hydration + LRU cache.
- [ ] ADD selection rationale model and candidate score debug output.
- [ ] ADD parser support for explicit invocation syntax normalization.
- [ ] ADD unit tests for routing order and tie-break determinism.

### Phase 4: Execution adapters + policy gates

**Intent Lock**
- **Source of truth**: PRD execution types/policy section; Architecture section 10/11.
- **Must**:
  - [ ] Implement playbook/procedural/agent adapters behind a registry dispatch map.
  - [ ] Enforce skill-level policy checks before execution.
  - [ ] Keep delegated agent execution context-bounded and auditable.
- **Must Not**:
  - [ ] Implement adapter selection with fragile long condition chains.
  - [ ] Allow explicit invocation to bypass deny policies.
- **Provenance map**:
  - [ ] Selected skill + policy record -> adapter invocation contract -> execution result model.
- **Acceptance gates**:
  - [ ] Unit tests for each adapter success/failure path.
  - [ ] Integration tests for denylist, tool allowlist, and agent allowlist enforcement.

**Tasks**
- [ ] CREATE `skill_policies.py` with typed check results and rejection reasons.
- [ ] CREATE `skill_executor.py` with adapter registry and type-specific runners.
- [ ] ADD procedural wrapper contract validation (input/output schema).
- [ ] ADD agent adapter bounds (`max_iterations`, tool/model call limits).
- [ ] ADD policy-focused tests preventing bypass via explicit invocation.

### Phase 5: Runtime integration into supervisor invoke path

**Intent Lock**
- **Source of truth**: PRD integration bullets; Architecture layered flow section.
- **Must**:
  - [ ] Integrate skills flow into runtime without breaking current no-skill behavior.
  - [ ] Preserve current tool allowlist and model routing policies.
  - [ ] Return deterministic skill execution metadata in runtime result structures.
- **Must Not**:
  - [ ] Introduce hidden behavior changes for existing prompts with no skill match.
  - [ ] Break conversation continuity/session threading behavior.
- **Provenance map**:
  - [ ] Prompt ingress -> selection -> load -> policy -> execute -> final output + trace.
- **Acceptance gates**:
  - [ ] Integration tests for explicit skill, implicit skill, and no-skill fallback paths.
  - [ ] Existing runtime integration suites remain green.

**Tasks**
- [ ] UPDATE supervisor/runtime construction to initialize skill subsystem once.
- [ ] ADD invoke-path hook for selection/loading/execution.
- [ ] ADD structured `skill_trace` payload on runtime responses.
- [ ] ADD config toggles to fully disable skill subsystem.
- [ ] ADD integration tests for legacy behavior parity when disabled.

### Phase 6: CLI surfaces and UX

**Intent Lock**
- **Source of truth**: PRD CLI visibility requirement; AGENTS CLI UX Rich-render rule.
- **Must**:
  - [ ] Add `skills list`, `skills inspect`, `skills doctor` user-facing commands.
  - [ ] Use Rich tables/panels for default outputs.
  - [ ] Surface collisions/shadowing/invalid packages with actionable messages.
- **Must Not**:
  - [ ] Default to raw JSON in interactive mode.
  - [ ] Hide policy-block reasons from operator diagnostics.
- **Provenance map**:
  - [ ] Registry + diagnostics -> CLI presenter models -> rendered table/panel output.
- **Acceptance gates**:
  - [ ] E2E CLI tests for command outputs and exit codes.
  - [ ] Snapshot-like assertions for key table headers/rows.

**Tasks**
- [ ] CREATE handlers for list/inspect/doctor commands.
- [ ] UPDATE `src/lily/cli.py` command tree and options.
- [ ] ADD filtering/sorting flags and concise/verbose modes.
- [ ] ADD e2e tests for no-skills, valid-skills, invalid-skills scenarios.
- [ ] ADD docs snippets for command usage.

### Phase 7: Telemetry/events and observability

**Intent Lock**
- **Source of truth**: PRD structured telemetry requirement; Architecture `skill_events` component.
- **Must**:
  - [ ] Emit stable structured events for discover/select/load/execute/outcome.
  - [ ] Include rationale and policy decisions without leaking secrets.
  - [ ] Keep event schema versioned and test-covered.
- **Must Not**:
  - [ ] Emit only free-form logs with no schema guarantee.
  - [ ] Log full prompt/skill body when policy forbids it.
- **Provenance map**:
  - [ ] Runtime decision points -> typed event model -> logger sink.
- **Acceptance gates**:
  - [ ] Unit tests for event schema and serialization.
  - [ ] Integration check that key events appear in explicit+implicit flows.

**Tasks**
- [ ] CREATE `skill_events.py` typed event models and emit helpers.
- [ ] ADD event hooks across discovery, selector, loader, executor paths.
- [ ] ADD redaction/sanitization rules and tests.
- [ ] ADD event schema version constant and compatibility tests.

### Phase 8: Testing, docs/status sync, and release hardening

**Intent Lock**
- **Source of truth**: `.ai/COMMANDS/validate.md`, `.ai/COMMANDS/status-sync.md`, `.ai/RULES.md` gates.
- **Must**:
  - [ ] Run full quality/test gates warning-clean.
  - [ ] Update roadmap/status/backlog/debt docs to reflect completion/defer states.
  - [ ] Produce phased commits following commit policy (feature, UX polish, docs-only as applicable).
- **Must Not**:
  - [ ] Merge with unresolved warning debt undocumented.
  - [ ] Mark SI-007 complete if compatibility-only slices remain.
- **Provenance map**:
  - [ ] Gate outcomes and status updates tied directly to command results and shipped scope.
- **Acceptance gates**:
  - [ ] `just quality && just test` green.
  - [ ] Docs/status checks green.
  - [ ] PR body explicitly calls out complete vs temporary vs deferred.

**Tasks**
- [ ] EXPAND unit/integration/e2e coverage for high-value behavior and failure paths.
- [ ] RUN full gates and capture output in execution report.
- [ ] UPDATE docs status surfaces with SI-007 phase truth.
- [ ] PREPARE PR using repository template headings exactly.

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### 0. PLAN LOCK

- [ ] **UPDATE** `.ai/PLANS/005-skills-system-implementation.md`
  - [ ] **IMPLEMENT**: Freeze scope table mapping PRD requirements to implementation phases.
  - [ ] **VALIDATE**: `uv run python -m compileall src tests`

### 1. CONTRACT MODELS

- [ ] **CREATE** `src/lily/runtime/skill_types.py`
  - [ ] **IMPLEMENT**: Core skill metadata/summary/full models and error taxonomy.
  - [ ] **VALIDATE**: `uv run pytest tests/unit/runtime/test_skill_catalog.py -q`

- [ ] **CREATE** `src/lily/runtime/skill_catalog.py`
  - [ ] **IMPLEMENT**: SKILL.md parser and strict frontmatter validator.
  - [ ] **VALIDATE**: `uv run pytest tests/unit/runtime/test_skill_catalog.py -q`

### 2. DISCOVERY + REGISTRY

- [ ] **CREATE** `src/lily/runtime/skill_discovery.py`
  - [ ] **IMPLEMENT**: Scope-root traversal and deterministic candidate ordering.
  - [ ] **VALIDATE**: `uv run pytest tests/unit/runtime/test_skill_discovery.py -q`

- [ ] **CREATE** `src/lily/runtime/skill_registry.py`
  - [ ] **IMPLEMENT**: Collision resolution and query interface.
  - [ ] **VALIDATE**: `uv run pytest tests/unit/runtime/test_skill_registry.py -q`

### 3. SELECTOR + LOADER

- [ ] **CREATE** `src/lily/runtime/skill_selector.py`
  - [ ] **IMPLEMENT**: Explicit/implicit routing and score rationale model.
  - [ ] **VALIDATE**: `uv run pytest tests/unit/runtime/test_skill_selector.py -q`

- [ ] **CREATE** `src/lily/runtime/skill_loader.py`
  - [ ] **IMPLEMENT**: Progressive disclosure hydration and cache.
  - [ ] **VALIDATE**: `uv run pytest tests/unit/runtime/test_skill_loader.py -q`

### 4. EXECUTION + POLICY

- [ ] **CREATE** `src/lily/runtime/skill_policies.py`
  - [ ] **IMPLEMENT**: Enable/deny/allowlist checks.
  - [ ] **VALIDATE**: `uv run pytest tests/unit/runtime/test_skill_policies.py -q`

- [ ] **CREATE** `src/lily/runtime/skill_executor.py`
  - [ ] **IMPLEMENT**: Adapter registry and bounded execution contracts.
  - [ ] **VALIDATE**: `uv run pytest tests/unit/runtime/test_skill_executor.py -q`

### 5. RUNTIME + CLI INTEGRATION

- [ ] **UPDATE** `src/lily/agents/lily_supervisor.py`, `src/lily/runtime/agent_runtime.py`
  - [ ] **IMPLEMENT**: Inject skill pipeline and trace payload.
  - [ ] **VALIDATE**: `uv run pytest tests/integration/test_skills_runtime_flow.py -q`

- [ ] **UPDATE/CREATE** CLI handlers + `src/lily/cli.py`
  - [ ] **IMPLEMENT**: `skills list|inspect|doctor` commands and rich output.
  - [ ] **VALIDATE**: `uv run pytest tests/e2e/test_cli_skills_commands.py -q`

### 6. EVENTS + HARDENING

- [ ] **CREATE** `src/lily/runtime/skill_events.py`
  - [ ] **IMPLEMENT**: Typed event schema and redacted emitters.
  - [ ] **VALIDATE**: `uv run pytest tests/unit/runtime -k skill_events -q`

- [ ] **UPDATE** docs/status and finish gates
  - [ ] **VALIDATE**: `just quality && just test`
  - [ ] **VALIDATE**: `just docs-check && just status`

---

## TESTING STRATEGY

### Unit Tests

- [ ] Parser/contract tests for SKILL.md metadata validity matrix.
- [ ] Discovery order tests across repo/user/system roots.
- [ ] Collision and precedence tests (scope + semver + deterministic fallback).
- [ ] Selector determinism tests for explicit and lexical implicit paths.
- [ ] Loader caching tests and failure taxonomy tests.
- [ ] Policy and adapter tests for each skill type and deny paths.
- [ ] Event schema serialization and redaction tests.

### Integration Tests

- [ ] End-to-end runtime path from prompt -> selected skill -> execution -> output.
- [ ] Config-driven toggles (skills enabled/disabled) preserve existing behavior.
- [ ] Policy constraints enforced under realistic runtime wiring.

### E2E Tests

- [ ] CLI skills command flows on fixture skills roots.
- [ ] CLI run with explicit invocation and implicit invocation.
- [ ] Failure UX for invalid skill package and policy denial.

### Edge Cases

- [ ] Duplicate IDs across scopes with mixed versions.
- [ ] Explicit invocation of disabled/denied skills.
- [ ] Missing `SKILL.md` body after summary index.
- [ ] Non-ASCII content and long markdown references.
- [ ] Runtime with zero skills configured.

---

## VALIDATION COMMANDS

Primary quality gates:

- [ ] `just lint`
- [ ] `just format-check`
- [ ] `just types`
- [ ] `just test`
- [ ] `just quality && just test`

Focused skills checks during development:

- [ ] `uv run pytest tests/unit/runtime -k skill`
- [ ] `uv run pytest tests/integration -k skill`
- [ ] `uv run pytest tests/e2e -k "skill or skills"`

Docs/status checks:

- [ ] `just docs-check`
- [ ] `just status`

---

## Risks and Mitigations

- [ ] **Risk**: Non-deterministic routing due to unstable scoring ties.  
      **Mitigation**: deterministic tie-break chain + explicit tests.
- [ ] **Risk**: Context bloat from eager loading full skills.  
      **Mitigation**: strict progressive disclosure + cache bounds.
- [ ] **Risk**: Policy bypass via explicit invocation.  
      **Mitigation**: deny checks before adapter dispatch + tests.
- [ ] **Risk**: Operator confusion on why a skill was/wasn't chosen.  
      **Mitigation**: rationale traces + `skills doctor` diagnostics.

## Non-Goals (MVP Guardrails)

- [ ] No autonomous skill generation/promotion/pruning loop.
- [ ] No remote package marketplace or signed distribution service.
- [ ] No mandatory embeddings/vector DB selection dependency.
- [ ] No broad refactor of unrelated runtime modules.

## Execution Report

### Completion Status

- Planned, not yet executed.

### Artifacts Created

- `.ai/PLANS/005-skills-system-implementation.md`

### Commands Run and Outcomes

- `git ls-files` -> pass
- `uv --version` -> pass
- `just --version` -> failed (`just` missing in environment)
- `uv run pytest --version` -> pass
- `git log -10 --oneline` -> pass
- `git status -sb` -> pass

### Partial/Blocked Items

- Runtime command sanity indicates `just` is not installed in this environment, so `just` gates are currently blocked until tool is available.
