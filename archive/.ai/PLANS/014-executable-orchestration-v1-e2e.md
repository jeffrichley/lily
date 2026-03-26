# Feature: executable-orchestration-v1-e2e

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Deliver a full end-to-end orchestration runtime for Lily V1 that introduces a supervisor-led execution model over all executable targets (`agent`, `blueprint`, `skill`, `tool`, `job`) using typed contracts, resolver/dispatcher abstractions, deterministic gate outcomes, and trace/replay infrastructure. This plan covers the complete implementation checklist in `docs/dev/references/executable-orchestration-implementation-checklist-v1.md`.

Compatibility posture for this feature:
- Backward compatibility is explicitly out of scope.
- Legacy CLI/REPL behavior may be removed or changed when needed for standards compliance.
- Do not add compatibility shims unless explicitly requested by the user.

## User Story

As an operations lead at Northstar Reliability Group (NRG),
I want Lily to interpret intent, delegate work across agents/skills/blueprints/jobs through one orchestration system, and provide deterministic traceable outcomes,
So that my team can automate recurring analysis workflows with strong safety, reliability, and auditability.

## Problem Statement

Lily currently has strong subsystem capabilities (skills, tool dispatch, agent identity context, jobs, blueprints), but no unified orchestration layer that can plan and delegate across executable types under one typed contract. Without this, the platform cannot satisfy CAP-011 through CAP-015 and cannot deliver complete multi-agent workflow orchestration.

## Solution Statement

Implement a supervisor-centered orchestration architecture with:

1. Common executable envelopes (`ExecutableRequest`, `ExecutableResult`, `GateDecision`).
2. Resolver + dispatcher registry abstractions.
3. Adapter handlers over current runtime systems.
4. Supervisor MVP with typed handoffs and bounded delegation depth.
5. Deterministic gate pipeline outcomes (`ok/retry/fallback/escalate/abort`).
6. Jobs-to-supervisor bridge.
7. Unified trace/replay artifacts.

## Feature Metadata

**Feature Type**: New Capability  
**Estimated Complexity**: High  
**Primary Systems Affected**: `src/lily/runtime/*`, `src/lily/jobs/*`, `tests/unit/runtime/*`, `tests/integration/runtime/*`, `tests/e2e/*`, orchestration specs and references  
**Dependencies**: Existing repo dependencies only (`pydantic`, `apscheduler`, `pytest`, `typer`, existing Lily runtime stack)

## Traceability Mapping (Required When Applicable)

- Roadmap system improvements: `SI-007`
- Debt items: `None`
- Debt to roadmap linkage (if debt exists): `None`

## Branch Setup (Required)

Branch naming must follow the plan filename:
- Plan: `.ai/PLANS/014-executable-orchestration-v1-e2e.md`
- Branch: `feat/014-executable-orchestration-v1-e2e`

Commands (must be executable as written):
```bash
PLAN_FILE=".ai/PLANS/014-executable-orchestration-v1-e2e.md"
PLAN_SLUG="$(basename "$PLAN_FILE" .md)"
BRANCH_NAME="feat/${PLAN_SLUG}"
git show-ref --verify --quiet "refs/heads/${BRANCH_NAME}" \
  && git switch "${BRANCH_NAME}" \
  || git switch -c "${BRANCH_NAME}"
```

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `docs/specs/runtime/executable-orchestration-architecture-v1.md` (lines 26-35, 91-185, 187-249, 251-320) - Canonical orchestration contract, envelopes, dispatcher model, authority/gate/replay semantics, and CAP mapping.
- `docs/specs/runtime/lily-interoperability-contract-v1.md` (lines 1-190) - Normative interoperability contract (`MUST/SHOULD`) and adapter rules for `blueprint` and `job` with standards alignment targets.
- `docs/dev/references/executable-orchestration-implementation-checklist-v1.md` (lines 14-141) - End-to-end execution checklist and phase ordering that this plan must fully cover.
- `docs/dev/references/interoperability-remediation-matrix-v1.md` (lines 1-95) - Type-by-type non-compliance matrix and required remediation tasks mapped to CAP IDs.
- `docs/dev/references/capability-ledger.md` (lines 24-40, 42-49) - CAP-001..CAP-015 status and completion target contract.
- `docs/diagrams/lily-capability-flow.md` (lines 14-88) - Current vs target capability dependency flow.
- `docs/specs/lily-v1-business-story.md` (lines 31-50, 63-73, 75-89) - Business-grade definition of fully functional Lily V1 and scope guardrails.
- `docs/specs/agents/supervisor_subagents_v1.md` (lines 34-53, 56-123) - Existing delegation/handoff/failure isolation requirements.
- `src/lily/runtime/facade.py` (lines 146-197, 233-332) - Existing command/conversation routing and composition seams for orchestration insertion.
- `src/lily/runtime/skill_invoker.py` (lines 14-43, 45-92) - Strategy-map executor pattern and deterministic capability error mapping.
- `src/lily/runtime/executors/tool_dispatch.py` (lines 40-85, 87-155, 157-200, 202-230) - Provider registry dispatch pattern and typed IO/error envelopes.
- `src/lily/commands/registry.py` (lines 163-203, 219-248) - Deterministic handler map registration + dispatch surface.
- `src/lily/commands/handlers/jobs.py` (lines 126-153) - Registry dispatch pattern for subcommands.
- `src/lily/jobs/executor.py` (lines 292-420, 427-470) - Retry loop, deterministic failure finalization, and artifact/event writes.
- `src/lily/jobs/scheduler_runtime.py` (lines 95-105, 149-166, 185-237, 238-259) - Scheduler lifecycle operations and deterministic status payloads.
- `src/lily/runtime/security.py` (lines 526-605, 606-640) - Deterministic preflight/approval gate and provenance persistence pattern.
- `src/lily/commands/types.py` (lines 21-69) - Existing deterministic envelope shape used at command boundary.
- `src/lily/runtime/runtime_dependencies.py` (lines 20-71) - Existing composition contracts and bundle specs for adding orchestration dependencies.
- `src/lily/runtime/jobs_factory.py` (lines 15-39, 42-59) - Runtime composition and startup pattern for optional runtime components.
- `tests/e2e/test_phase4_memory_jobs.py` - Existing command-level jobs lifecycle behavior.
- `tests/e2e/test_phase5_security.py` - Security flow behavior and deterministic code expectations.
- `tests/e2e/test_phase6_agent_registry.py` - Agent/persona identity boundary behavior.
- `tests/unit/runtime/test_tool_dispatch_executor.py` - Typed provider dispatch and deterministic code mapping pattern.

### New Files to Create

- `src/lily/runtime/executables/__init__.py`
- `src/lily/runtime/executables/models.py`
- `src/lily/runtime/executables/types.py`
- `src/lily/runtime/executables/resolver.py`
- `src/lily/runtime/executables/dispatcher.py`
- `src/lily/runtime/executables/handlers/__init__.py`
- `src/lily/runtime/executables/handlers/base.py`
- `src/lily/runtime/executables/handlers/agent_handler.py`
- `src/lily/runtime/executables/handlers/skill_handler.py`
- `src/lily/runtime/executables/handlers/tool_handler.py`
- `src/lily/runtime/executables/handlers/blueprint_handler.py`
- `src/lily/runtime/executables/handlers/job_handler.py`
- `src/lily/runtime/orchestration/__init__.py`
- `src/lily/runtime/orchestration/plan_models.py`
- `src/lily/runtime/orchestration/supervisor.py`
- `src/lily/runtime/orchestration/aggregator.py`
- `src/lily/runtime/orchestration/gate_models.py`
- `src/lily/runtime/orchestration/gates.py`
- `src/lily/runtime/orchestration/trace_store.py`
- `src/lily/runtime/orchestration/replay.py`
- `tests/unit/runtime/executables/test_executable_models.py`
- `tests/unit/runtime/executables/test_resolver.py`
- `tests/unit/runtime/executables/test_dispatcher.py`
- `tests/unit/runtime/executables/handlers/test_skill_handler.py`
- `tests/unit/runtime/executables/handlers/test_blueprint_handler.py`
- `tests/unit/runtime/executables/handlers/test_job_handler.py`
- `tests/unit/runtime/orchestration/test_supervisor.py`
- `tests/unit/runtime/orchestration/test_gates.py`
- `tests/integration/runtime/test_supervisor_delegation.py`
- `tests/integration/runtime/test_gate_outcomes.py`
- `tests/integration/runtime/test_orchestration_trace.py`
- `tests/integration/runtime/test_orchestration_replay.py`
- `tests/unit/jobs/test_supervisor_job_target.py`
- `tests/e2e/test_phaseX_jobs_supervisor_bridge.py`

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [Pydantic Models](https://docs.pydantic.dev/latest/concepts/models/)
  - Specific section: strict schema modeling and validation behavior
  - Why: executable envelope correctness and deterministic validation errors.
- [Python typing.Protocol](https://docs.python.org/3/library/typing.html#typing.Protocol)
  - Specific section: protocol contracts and structural typing
  - Why: handler/dispatcher interfaces without inheritance coupling.
- [Python dataclasses](https://docs.python.org/3/library/dataclasses.html)
  - Specific section: immutable composition specs
  - Why: preserving existing runtime composition style where appropriate.
- [APScheduler User Guide](https://apscheduler.readthedocs.io/en/3.x/userguide.html)
  - Specific section: lifecycle behavior and job execution semantics
  - Why: safe jobs-to-supervisor bridge design.
- [Pytest Good Practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html)
  - Specific section: test layout and fixture design
  - Why: consistent unit/integration/e2e test structure for orchestration features.
- [Agent Skills Specification](https://agentskills.io/specification)
  - Specific section: `SKILL.md` contract and metadata requirements
  - Why: standards-compliant skill interoperability and import behavior.
- [OpenAI Tools Guide](https://platform.openai.com/docs/guides/tools)
  - Specific section: tool contracts and execution model
  - Why: align Lily tool invocation semantics with ecosystem conventions.
- [OpenAI MCP Guide](https://platform.openai.com/docs/guides/tools-connectors-mcp)
  - Specific section: MCP server registration, policy, and approvals
  - Why: ensure first-class MCP interoperability and policy controls.

### Patterns to Follow

**Naming Conventions:**
- Deterministic runtime components use explicit nouns and stable suffixes (`*Runtime`, `*Factory`, `*Store`, `*Executor`) as in `src/lily/runtime/facade.py` and `src/lily/runtime/jobs_factory.py`.

**Dispatch Pattern:**
- Use registry maps, not long conditionals, for behavior dispatch (`src/lily/commands/handlers/jobs.py:135-153`, `src/lily/commands/registry.py:163-203`, `src/lily/runtime/skill_invoker.py:20-42`).

**Envelope Pattern:**
- Emit typed deterministic response envelopes with explicit `code` and structured `data` (`src/lily/commands/types.py:21-69`, `src/lily/runtime/executors/tool_dispatch.py:76-85`).

**Error Handling Pattern:**
- Map subsystem exceptions into deterministic machine-readable codes at boundaries (`src/lily/runtime/executors/tool_dispatch.py:114-141`, `src/lily/jobs/executor.py:335-377`, `src/lily/runtime/security.py:545-604`).

**Observability Pattern:**
- Persist run events/artifacts with explicit timestamps and stable fields (`src/lily/jobs/executor.py:318-420`, `src/lily/jobs/scheduler_runtime.py:238-259`).

**Composition Pattern:**
- Build dependencies via bundles/specs rather than ad-hoc inline construction (`src/lily/runtime/runtime_dependencies.py:20-71`, `src/lily/runtime/facade.py:282-332`).

---

## IMPLEMENTATION PLAN

Use markdown checkboxes (`- [ ]`) for implementation phases and task bullets so execution progress can be tracked live.

### Phase 0: Human Review + Standards Compliance Baseline

User-visible features:
- none.

Internal engineering tasks:
- execute human review checklist for executable types and compliance baseline.
- document findings and open debt if any type fails baseline.

**Intent Lock**

- Source of truth docs for this phase:
  - `docs/specs/runtime/lily-interoperability-contract-v1.md` (sections 4-12)
  - `docs/dev/references/executable-orchestration-implementation-checklist-v1.md` (lines 14-28)
  - `docs/dev/references/capability-ledger.md` (lines 24-40)
  - `docs/specs/runtime/executable-orchestration-architecture-v1.md` (sections 6-10)
- Must:
  - complete explicit review for `agent`, `blueprint`, `skill`, `tool`, `job`.
  - assess deterministic contract, explicit error codes, policy checks, trace emission.
  - write summary findings in `docs/dev/status.md` before feature code.
- Must Not:
  - start CAP-011+ implementation before baseline review is documented.
  - silently accept standard violations without explicit debt/rationale.
- Provenance map:
  - baseline findings -> `docs/dev/status.md` entry with CAP linkage.
- Acceptance gates:
  - checklist items completed and recorded.
  - `just docs-check` passes after status update.

**Tasks:**

- [x] Run and document human standards review for each executable type.
- [x] Record compliance findings in `docs/dev/status.md`.
- [x] Create debt issue draft(s) if any type violates baseline contracts.

### Phase 1: Common Executable Contracts

User-visible features:
- none.

Internal engineering tasks:
- add canonical executable envelope models and types.

**Intent Lock**

- Source of truth docs for this phase:
  - architecture spec section 6 (`ExecutableRef`, `ExecutableRequest`, `ExecutableResult`, `GateDecision`)
  - checklist phase 1 (`docs/dev/references/executable-orchestration-implementation-checklist-v1.md:32-40`)
- Must:
  - enforce explicit required fields; no silent defaults for required contract fields.
  - model contracts with strict validation (`extra=forbid` / equivalent).
  - include caller authority and run-step identity fields.
- Must Not:
  - use untyped dict payloads as first-class interfaces.
  - defer contract validation to downstream handlers.
- Provenance map:
  - request/result identity fields -> used by trace/replay phases.
- Acceptance gates:
  - new model tests pass.
  - `just types` and targeted unit tests pass.

**Tasks:**

- [x] Add executable models and type aliases/protocols under `src/lily/runtime/executables/`.
- [x] Add unit tests for schema validity, rejection cases, and deterministic error shape.

### Phase 2: Resolver + Dispatcher Registry

User-visible features:
- none.

Internal engineering tasks:
- add resolver and dispatcher with registry-based handler dispatch.

**Intent Lock**

- Source of truth docs for this phase:
  - architecture spec sections 7-8
  - checklist phase 2 (`docs/dev/references/executable-orchestration-implementation-checklist-v1.md:42-52`)
- Must:
  - caller submits objective/target hint; resolver owns final kind binding.
  - dispatcher uses map-based `kind -> handler` resolution.
  - unresolved/ambiguous results are deterministic envelope errors.
- Must Not:
  - add long `if/elif` dispatch chains.
  - bypass resolver for direct handler calls in orchestration path.
- Provenance map:
  - resolver decisions -> trace fields in CAP-015 phase.
- Acceptance gates:
  - resolver/dispatcher unit tests for success/ambiguous/unresolved.
  - no lint/type issues.

**Tasks:**

- [x] Create resolver and dispatcher modules with protocol-driven handler contracts.
- [x] Add resolver/dispatcher unit tests, including deterministic error code assertions.

### Phase 3: Adapter Handlers Over Existing Runtime

User-visible features:
- none (internal restructuring may break legacy CLI/REPL command behavior).

Internal engineering tasks:
- wrap existing agent/skill/tool/blueprint/job behavior behind executable handler adapters.

**Intent Lock**

- Source of truth docs for this phase:
  - architecture spec section 14.4 (Adapter pattern)
  - checklist phase 3 (`docs/dev/references/executable-orchestration-implementation-checklist-v1.md:54-67`)
  - existing subsystem behavior from `src/lily/runtime/skill_invoker.py`, `src/lily/jobs/executor.py`, `src/lily/runtime/executors/tool_dispatch.py`
- Must:
  - enforce executable-envelope boundaries through adapters.
  - normalize all adapter outputs into executable result envelope.
  - keep deterministic code mapping for failures.
- Must Not:
  - add compatibility shims that bypass orchestration contracts.
  - keep direct legacy invocation paths when they conflict with standards.
- Provenance map:
  - adapter outputs map 1:1 with existing subsystem result data and error code fields.
- Acceptance gates:
  - adapter handler tests pass.
  - existing e2e suites for skills/jobs still pass.

**Tasks:**

- [x] Implement handler adapters for `agent`, `skill`, `tool`, `blueprint`, `job`.
- [x] Add adapter-specific unit tests.
- [x] Remove or rewrite direct legacy call paths that bypass adapters.

### Phase 4: Supervisor Runtime MVP + Typed Handoffs

User-visible features:
- deterministic supervisor execution path for delegated multi-step runs.

Internal engineering tasks:
- implement supervisor runtime, plan models, and aggregation skeleton.

**Intent Lock**

- Source of truth docs for this phase:
  - architecture spec sections 3-4, 9, 12
  - supervisor spec (`docs/specs/agents/supervisor_subagents_v1.md:34-53, 56-92`)
  - checklist phase 4 (`docs/dev/references/executable-orchestration-implementation-checklist-v1.md:69-82`)
- Must:
  - supervisor planner is LLM-backed in V1 (PydanticAI-backed planner implementation first).
  - supervisor is only delegator in V1.
  - delegation depth fixed at 1.
  - typed handoff request/response contracts enforced.
  - planner may emit bounded multi-step plans in one typed response.
  - planner outputs must be schema-validated typed plans/handoffs (no free-form planner output at execution boundary).
  - planner follow-up context is a typed execution digest by default (status, key outputs/errors, gate decisions, refs/artifacts), not full raw history.
  - aggregation preserves provenance references.
- Must Not:
  - recursive delegation.
  - introduce a rule-based-first planner implementation as the primary Phase 4 path.
  - treat orchestration execution as a primary LLM tool-call loop.
  - free-form untyped handoff payloads.
- Provenance map:
  - `run_id/step_id/parent_step_id` originate in supervisor plan and propagate to every delegated call.
- Acceptance gates:
  - supervisor unit + integration tests pass.
  - at least one multi-step delegated flow is deterministic.

**Tasks:**

- [x] Add supervisor/plan/aggregation modules.
- [x] Wire supervisor dependencies into runtime composition.
- [x] Add unit + integration tests for typed delegation and aggregation behavior.

### Phase 5: Gate Pipeline Outcomes

User-visible features:
- deterministic orchestration outcomes for retry/fallback/escalate/abort decisions.

Internal engineering tasks:
- implement gate pipeline modules and result semantics.

**Intent Lock**

- Source of truth docs for this phase:
  - architecture spec section 10
  - checklist phase 5 (`docs/dev/references/executable-orchestration-implementation-checklist-v1.md:84-94`)
- Must:
  - implement all outcomes: `ok`, `retry`, `fallback`, `escalate`, `abort`.
  - keep decision fields deterministic and machine-assertable.
  - compose gates as ordered chain; no implicit outcome coercion.
- Must Not:
  - collapse gate outcomes into generic success/error only.
  - hide gate reasoning metadata.
- Provenance map:
  - decision reason code/message sourced from concrete gate evaluation step.
- Acceptance gates:
  - gate unit/integration tests cover all outcomes.

**Tasks:**

- [ ] Add gate models and pipeline implementation.
- [ ] Integrate gate results with supervisor control flow.
- [ ] Add tests for each outcome path and deterministic branching.

### Phase 6: Jobs-to-Supervisor Bridge

User-visible features:
- `/jobs run <id>` can execute supervisor-targeted jobs with delegated orchestration trace references.

Internal engineering tasks:
- extend jobs target handling and bridge to supervisor handler path.

**Intent Lock**

- Source of truth docs for this phase:
  - architecture spec section 11 and section 17 (M4)
  - checklist phase 6 (`docs/dev/references/executable-orchestration-implementation-checklist-v1.md:96-105`)
  - existing jobs execution contract (`src/lily/jobs/executor.py:292-470`)
- Must:
  - route job execution through executable contracts for all supported targets.
  - support supervisor-target target kind with deterministic envelopes.
  - persist run artifacts including orchestration references.
- Must Not:
  - break scheduler lifecycle controls.
  - bypass executable contracts when invoking supervisor from jobs path.
- Provenance map:
  - job receipt fields include supervisor run and trace identifiers.
- Acceptance gates:
  - unit + e2e job bridge tests pass.
  - existing jobs e2e still passes.

**Tasks:**

- [ ] Extend job target modeling and executor bridge logic.
- [ ] Add tests for supervisor-targeted jobs (`unit`, `e2e`).
- [ ] Validate no regressions in current jobs command behavior.

### Phase 7: Unified Trace + Replay

User-visible features:
- replayable orchestrated runs with per-step trace artifacts.

Internal engineering tasks:
- add trace store and replay modules and integrate with supervisor path.

**Intent Lock**

- Source of truth docs for this phase:
  - architecture spec section 13
  - checklist phase 7 (`docs/dev/references/executable-orchestration-implementation-checklist-v1.md:107-116`)
  - roadmap linkage to SI-007
- Must:
  - persist request/result snapshots and gate decisions with stable IDs.
  - implement run-level and step-level replay entrypoints.
  - support explicit replay modes (`dry_run`, `side_effecting`).
- Must Not:
  - generate non-deterministic trace identifiers.
  - couple replay directly to command rendering code.
- Provenance map:
  - trace artifacts are generated from executable envelopes and gate decision envelopes.
- Acceptance gates:
  - trace/replay integration tests pass.
  - artifacts are inspectable and linked from execution outputs.

**Tasks:**

- [ ] Add trace store and replay modules.
- [ ] Integrate trace emission with supervisor, resolver, dispatcher, and job bridge paths.
- [ ] Add integration tests for trace fidelity and replay determinism.

### Phase 8: Docs, Governance, and Final Hardening

User-visible features:
- updated docs that accurately describe shipped orchestration behavior and limits.

Internal engineering tasks:
- update capability ledger statuses, architecture/spec docs, and status diary.
- complete final gates and produce execution report.

**Intent Lock**

- Source of truth docs for this phase:
  - `docs/dev/references/capability-ledger.md`
  - `docs/specs/runtime/executable-orchestration-architecture-v1.md`
  - `.ai/RULES.md` quality gate requirements
- Must:
  - update CAP statuses based on implemented evidence.
  - preserve warning-clean quality policy.
  - append full execution evidence to this plan's `## Execution Report`.
- Must Not:
  - mark CAP complete without passing tests and manual verification steps.
  - leave doc/spec drift relative to implementation.
- Provenance map:
  - status updates cite tests and validation commands.
- Acceptance gates:
  - final `just quality && just test` pass.
  - docs-check pass.

**Tasks:**

- [ ] Update docs and capability ledger with implemented statuses.
- [ ] Run final full gates and record outputs.
- [ ] Prepare PR description per template with complete/deferred/temporary scope clarity.

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### UPDATE docs/dev/status.md

- **IMPLEMENT**: Add human review summary for `agent`, `blueprint`, `skill`, `tool`, `job` standards compliance.
- **PATTERN**: Follow status journal style from existing dated entries in `docs/dev/status.md`.
- **IMPORTS**: none.
- **GOTCHA**: Do not start runtime feature coding before this entry is committed.
- **VALIDATE**: `just docs-check`

### UPDATE docs/dev/references/interoperability-remediation-matrix-v1.md

- **IMPLEMENT**: Record final per-type remediation status as implementation progresses.
- **PATTERN**: Keep CAP mapping explicit for every remediation row/task.
- **IMPORTS**: none.
- **GOTCHA**: Do not mark a type compliant without contract tests + policy tests + trace/replay evidence.
- **VALIDATE**: `just docs-check`

### CREATE src/lily/runtime/executables/models.py

- **IMPLEMENT**: Add strict executable envelopes (`ExecutableRef`, `ExecutableRequest`, `ExecutableResult`, `GateDecision`).
- **PATTERN**: Mirror `CommandResult` strict pydantic pattern from `src/lily/commands/types.py:21-69`.
- **IMPORTS**: `pydantic.BaseModel`, `ConfigDict`, `Field`, typed enums where appropriate.
- **GOTCHA**: No silent fallback defaults for required contract fields.
- **VALIDATE**: `uv run pytest tests/unit/runtime/executables/test_executable_models.py -q`

### CREATE src/lily/runtime/executables/types.py

- **IMPLEMENT**: Add executable kind enum, resolver/dispatcher protocols, handler base protocol.
- **PATTERN**: Use protocol style from `src/lily/commands/types.py:72-76`.
- **IMPORTS**: `typing.Protocol`, enums, model imports.
- **GOTCHA**: Keep interfaces minimal and stable.
- **VALIDATE**: `just types`

### CREATE src/lily/runtime/executables/resolver.py

- **IMPLEMENT**: Deterministic target resolution from objective/hint to `kind + handler binding`.
- **PATTERN**: Deterministic error-envelope mapping style from `src/lily/runtime/executors/tool_dispatch.py:114-141`.
- **IMPORTS**: executable models/types, registry references.
- **GOTCHA**: Return explicit `resolver_ambiguous` and `resolver_unresolved` codes.
- **VALIDATE**: `uv run pytest tests/unit/runtime/executables/test_resolver.py -q`

### CREATE src/lily/runtime/executables/dispatcher.py

- **IMPLEMENT**: Registry dispatch `kind -> handler` and standardized result normalization.
- **PATTERN**: Map-driven dispatch from `src/lily/commands/handlers/jobs.py:135-153` and `src/lily/runtime/skill_invoker.py:20-42`.
- **IMPORTS**: executable types and models.
- **GOTCHA**: Do not use long conditional chains.
- **VALIDATE**: `uv run pytest tests/unit/runtime/executables/test_dispatcher.py -q`

### CREATE src/lily/runtime/executables/handlers/*.py

- **IMPLEMENT**: Adapter handlers for `agent`, `skill`, `tool`, `blueprint`, `job` that call existing runtime subsystems.
- **PATTERN**: Adapter-style wrapping while preserving subsystem internals.
- **IMPORTS**: existing runtime services (`SkillInvoker`, jobs executor, blueprint registry wrappers, etc).
- **GOTCHA**: Preserve existing deterministic error codes where possible.
- **VALIDATE**: `uv run pytest tests/unit/runtime/executables/handlers -q`

### CREATE src/lily/runtime/orchestration/plan_models.py

- **IMPLEMENT**: Typed supervisor plan and handoff payload contracts.
- **PATTERN**: Pydantic strict modeling pattern from current domain models.
- **IMPORTS**: executable model references.
- **GOTCHA**: Ensure delegation depth constraints can be validated.
- **VALIDATE**: `uv run pytest tests/unit/runtime/orchestration/test_supervisor.py -q`

### CREATE src/lily/runtime/orchestration/supervisor.py

- **IMPLEMENT**: Supervisor runtime using resolver + dispatcher + gates + aggregator.
- **PATTERN**: Thin orchestration coordinator pattern from `src/lily/runtime/facade.py:146-197`.
- **IMPORTS**: resolver, dispatcher, gate pipeline, plan models.
- **GOTCHA**: Supervisor is sole delegator; subagents cannot recursively delegate.
- **VALIDATE**: `uv run pytest tests/integration/runtime/test_supervisor_delegation.py -q`

### CREATE src/lily/runtime/orchestration/aggregator.py

- **IMPLEMENT**: Deterministic synthesis over typed step outputs and gate outcomes.
- **PATTERN**: Deterministic envelope merging style from jobs payload shaping in `src/lily/jobs/executor.py:387-395`.
- **IMPORTS**: plan/result models.
- **GOTCHA**: Preserve provenance references in final envelope.
- **VALIDATE**: `uv run pytest tests/unit/runtime/orchestration/test_supervisor.py -q`

### CREATE src/lily/runtime/orchestration/gate_models.py and gates.py

- **IMPLEMENT**: Ordered gate chain and all outcomes (`ok/retry/fallback/escalate/abort`).
- **PATTERN**: Chain-of-responsibility and deterministic code mapping from security/job error handling.
- **IMPORTS**: gate decision models, runtime policy checks.
- **GOTCHA**: Outcomes must remain machine-assertable and explicit.
- **VALIDATE**: `uv run pytest tests/unit/runtime/orchestration/test_gates.py tests/integration/runtime/test_gate_outcomes.py -q`

### UPDATE src/lily/runtime/runtime_dependencies.py and src/lily/runtime/facade.py

- **IMPLEMENT**: Add orchestration dependency specs/bundles and runtime wiring points.
- **PATTERN**: Existing composition-root pattern from `src/lily/runtime/runtime_dependencies.py:20-71` and `src/lily/runtime/facade.py:282-332`.
- **IMPORTS**: orchestration/resolver/dispatcher modules.
- **GOTCHA**: Keep `RuntimeFacade` thin; avoid new god-object behavior.
- **VALIDATE**: `uv run pytest tests/unit/runtime -q`

### UPDATE src/lily/jobs/models.py and src/lily/jobs/executor.py

- **IMPLEMENT**: Add supervisor-target job kind and bridge into orchestrated dispatch path.
- **PATTERN**: Preserve existing retry/artifact/failure envelope contract from `src/lily/jobs/executor.py:292-470`.
- **IMPORTS**: executable dispatcher/supervisor interfaces.
- **GOTCHA**: Do not regress current blueprint target path.
- **VALIDATE**: `uv run pytest tests/unit/jobs/test_supervisor_job_target.py tests/e2e/test_phaseX_jobs_supervisor_bridge.py -q`

### CREATE src/lily/runtime/orchestration/trace_store.py and replay.py

- **IMPLEMENT**: Unified trace persistence and replay entrypoints (`dry_run` / `side_effecting`).
- **PATTERN**: Artifact/event persistence style from jobs executor and scheduler runtime.
- **IMPORTS**: executable request/result models and gate decision models.
- **GOTCHA**: Ensure stable IDs and deterministic replay behavior.
- **VALIDATE**: `uv run pytest tests/integration/runtime/test_orchestration_trace.py tests/integration/runtime/test_orchestration_replay.py -q`

### UPDATE docs/dev/references/capability-ledger.md and docs/specs/runtime/executable-orchestration-architecture-v1.md

- **IMPLEMENT**: Move CAP statuses based on evidence and reflect any accepted scope narrowing.
- **PATTERN**: Existing CAP table status semantics from `docs/dev/references/capability-ledger.md:24-40`.
- **IMPORTS**: none.
- **GOTCHA**: Do not mark CAP complete without corresponding tests and validation evidence.
- **VALIDATE**: `just docs-check`

### UPDATE .ai/PLANS/014-executable-orchestration-v1-e2e.md

- **IMPLEMENT**: Append `## Execution Report` with commands, outcomes, and phase acceptance evidence.
- **PATTERN**: Execution report style from `.ai/PLANS/013-status-git-context-panel.md`.
- **IMPORTS**: none.
- **GOTCHA**: Include exact command evidence for each completed phase.
- **VALIDATE**: `just docs-check`

---

## TESTING STRATEGY

### Unit Tests

- Envelope model validation and deterministic error shape:
  - `tests/unit/runtime/executables/test_executable_models.py`
- Resolver and dispatcher behavior:
  - `tests/unit/runtime/executables/test_resolver.py`
  - `tests/unit/runtime/executables/test_dispatcher.py`
- Adapter handler normalization and error mapping:
  - `tests/unit/runtime/executables/handlers/*`
- Supervisor planning and aggregation behavior:
  - `tests/unit/runtime/orchestration/test_supervisor.py`
- Gate outcomes:
  - `tests/unit/runtime/orchestration/test_gates.py`
- Jobs target bridge:
  - `tests/unit/jobs/test_supervisor_job_target.py`

### Integration Tests

- Delegated execution flow across resolver -> dispatcher -> handlers:
  - `tests/integration/runtime/test_supervisor_delegation.py`
- Gate outcome route transitions:
  - `tests/integration/runtime/test_gate_outcomes.py`
- Trace and replay fidelity:
  - `tests/integration/runtime/test_orchestration_trace.py`
  - `tests/integration/runtime/test_orchestration_replay.py`

### End-to-End Tests

- Supervisor-targeted jobs execution path:
  - `tests/e2e/test_phaseX_jobs_supervisor_bridge.py`
- Regression suites to protect existing behavior:
  - `tests/e2e/test_phase3_routing.py`
  - `tests/e2e/test_phase4_memory_jobs.py`
  - `tests/e2e/test_phase5_security.py`
  - `tests/e2e/test_phase6_agent_registry.py`

### Edge Cases

- ambiguous resolution target.
- unresolved target with no handler.
- gate outcome loops exceeding retry budget.
- fallback path to alternate executable kind.
- supervisor step failure isolation.
- replay with missing artifact references.
- scheduler-enabled job invoking supervisor target after restart.

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and end-to-end correctness.

### Level 1: Syntax & Style

- `just format-check`
- `just lint-check`
- `just types`
- `just docs-check`

### Level 2: Unit Tests

- `uv run pytest tests/unit/runtime/executables -q`
- `uv run pytest tests/unit/runtime/orchestration -q`
- `uv run pytest tests/unit/jobs/test_supervisor_job_target.py -q`

### Level 3: Integration Tests

- `uv run pytest tests/integration/runtime/test_supervisor_delegation.py -q`
- `uv run pytest tests/integration/runtime/test_gate_outcomes.py -q`
- `uv run pytest tests/integration/runtime/test_orchestration_trace.py -q`
- `uv run pytest tests/integration/runtime/test_orchestration_replay.py -q`

### Level 4: End-to-End + Regression

- `uv run pytest tests/e2e/test_phaseX_jobs_supervisor_bridge.py -q`
- `uv run pytest tests/e2e/test_phase3_routing.py tests/e2e/test_phase4_memory_jobs.py tests/e2e/test_phase5_security.py tests/e2e/test_phase6_agent_registry.py -q`

### Level 5: Final Gate

- `just quality && just test`

### Level 6: Manual Validation

- `uv run lily run "/jobs run <supervisor_job_id>" --workspace-dir <tmp_workspace>`
- Inspect run artifact directory under `<tmp_workspace>/runs/<job_id>/<run_id>/` for:
  - run receipt
  - events
  - orchestration trace/replay index artifact(s)

---

## OUTPUT CONTRACT (Required For User-Visible Features)

- Exact output artifacts/surfaces:
  - `src/lily/runtime/executables/*` (new executable contract + dispatch stack)
  - `src/lily/runtime/orchestration/*` (new supervisor, gates, trace, replay)
  - `src/lily/jobs/*` bridge updates for supervisor target
  - `tests/unit/runtime/executables/*`, `tests/unit/runtime/orchestration/*`, `tests/integration/runtime/*`, `tests/e2e/test_phaseX_jobs_supervisor_bridge.py`
  - Updated CAP statuses in `docs/dev/references/capability-ledger.md`
  - Updated execution evidence in `.ai/PLANS/014-executable-orchestration-v1-e2e.md` -> `## Execution Report`
- Verification commands:
  - all commands in `## VALIDATION COMMANDS`

## DEFINITION OF VISIBLE DONE (Required For User-Visible Features)

- A human can directly verify completion by:
  - running supervisor-targeted jobs and observing successful deterministic delegated execution.
  - inspecting run artifacts with run/step/gate trace references and replay metadata.
  - confirming CAP-011 through CAP-015 statuses changed based on passing evidence.

## INPUT/PREREQUISITE PROVENANCE (Required When Applicable)

- Generated during this feature:
  - orchestration envelopes and trace/replay artifacts via runtime execution.
  - supervisor-target test job fixtures created inside test suites.
- Pre-existing dependency:
  - existing skills/jobs/agents runtime subsystems and docs contracts.
  - setup/refresh commands: `uv sync`, `just docs-check`, `just quality-check`.

---

## ACCEPTANCE CRITERIA

- [x] Phase 0 human review gate completed and documented.
- [ ] CAP-011 supervisor runtime implemented and test-covered.
- [ ] CAP-012 typed handoff contracts implemented and test-covered.
- [ ] CAP-013 gate outcomes implemented (`ok/retry/fallback/escalate/abort`) and test-covered.
- [ ] CAP-014 jobs-to-supervisor bridge implemented with e2e coverage.
- [ ] CAP-015 trace and replay implemented with integration coverage.
- [ ] Existing phase-3/4/5/6 e2e suites show no regressions.
- [ ] `just quality && just test` passes with no new warnings.
- [ ] Capability ledger and runtime architecture docs reflect final shipped behavior.
- [ ] Execution report includes exact command evidence and outcomes.

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully
- [ ] Full test suite passes (unit + integration + e2e)
- [ ] No linting or type checking errors
- [ ] Manual validation confirms delegated orchestration workflow works
- [ ] Acceptance criteria all met
- [ ] Code reviewed for quality and maintainability

---

## NOTES

- Commit policy for execution phase:
  - commit at end of each completed phase.
  - after completed phases, use one separate commit for UX polish and one separate commit for docs-only updates.
- Keep scope fixed to CAP-011..CAP-015 with standards-first rewiring; backward compatibility is explicitly out of scope.
- If a phase cannot pass gates warning-clean, stop and document exact warning signature + owner + target date before proceeding.
- Confidence score for one-pass execution success (with this plan): **8/10**.

## Execution Report

### 2026-03-04 - Phase 0 Completed (Human Review + Standards Compliance Baseline)

Completion status:
- Completed Phase 0 gate and task checklist.

Phase intent checks run:
- Reviewed Phase 0 intent lock requirements from `.ai/PLANS/014-executable-orchestration-v1-e2e.md` (Must/Must Not/Acceptance gates).
- Validated source-of-truth alignment against:
  - `docs/specs/runtime/lily-interoperability-contract-v1.md`
  - `docs/dev/references/executable-orchestration-implementation-checklist-v1.md`
  - `docs/dev/references/capability-ledger.md`
  - `docs/specs/runtime/executable-orchestration-architecture-v1.md`

Artifacts updated:
- `docs/dev/status.md` (recorded baseline findings + risk + diary entry + debt draft IDs)
- `docs/dev/references/interoperability-remediation-matrix-v1.md` (compliance matrix + remediation tasks + phase-0 debt draft list)
- `docs/dev/references/executable-orchestration-implementation-checklist-v1.md` (Phase 0 checklist items marked complete)
- `.ai/PLANS/014-executable-orchestration-v1-e2e.md` (Phase 0 tasks + acceptance criterion marked complete)

Commands run and outcomes:
- `git branch --show-current` -> initially `main`.
- Plan branch setup commands -> created/switched to `feat/014-executable-orchestration-v1-e2e`.
- `just docs-check` -> pass.
- `just status` -> pass.

Acceptance gate evidence:
- Checklist items for executable-type reviews completed.
- Findings recorded before Phase 1 implementation.
- Non-compliance remediation and debt drafts captured with CAP mapping.

Blocked/partial items:
- none for Phase 0.

### 2026-03-04 - Phase 1 Completed (Common Executable Contracts)

Completion status:
- Completed Phase 1 scope only.

Implemented artifacts:
- `src/lily/runtime/executables/models.py`
- `src/lily/runtime/executables/types.py`
- `src/lily/runtime/executables/__init__.py`
- `tests/unit/runtime/executables/test_executable_models.py`

Validation commands and outcomes:
- `uv run pytest tests/unit/runtime/executables/test_executable_models.py -q` -> pass (`7 passed`)
- `just format-check` -> pass
- `just lint` -> pass
- `just types` -> pass

Acceptance gate evidence:
- Canonical envelopes `ExecutableRequest`, `ExecutableResult`, `GateDecision` are implemented, strict (`extra=forbid`), and importable.
- Required run/step identity and caller authority fields are validated with rejection tests.
- Status/error envelope consistency is enforced by model validation.

Blocked/partial items:
- none for Phase 1.

### 2026-03-04 - Phase 2 Completed (Resolver + Dispatcher Registry)

Completion status:
- Completed Phase 2 scope only.

Implemented artifacts:
- `src/lily/runtime/executables/resolver.py`
- `src/lily/runtime/executables/dispatcher.py`
- `src/lily/runtime/executables/handlers/base.py`
- `src/lily/runtime/executables/handlers/__init__.py`
- `tests/unit/runtime/executables/test_resolver.py`
- `tests/unit/runtime/executables/test_dispatcher.py`

Validation commands and outcomes:
- `uv run pytest tests/unit/runtime/executables/test_resolver.py tests/unit/runtime/executables/test_dispatcher.py -q` -> pass (`9 passed`)
- `just format-check` -> pass
- `just lint` -> pass
- `just types` -> pass
- `just test` -> pass (`342 passed`)

Acceptance gate evidence:
- Resolver is deterministic over catalog snapshot and emits machine-readable ambiguity/unresolved errors.
- Dispatcher uses registry map (`kind -> handler`) with no kind-based conditional dispatch chain.
- Resolver/dispatcher success and failure paths are covered by dedicated unit tests.

Blocked/partial items:
- none for Phase 2.

### 2026-03-04 - Phase 3 Completed (Adapter Handlers Over Existing Runtime)

Completion status:
- Completed Phase 3 scope only.

Implemented artifacts:
- `src/lily/runtime/executables/handlers/_common.py`
- `src/lily/runtime/executables/handlers/agent_handler.py`
- `src/lily/runtime/executables/handlers/skill_handler.py`
- `src/lily/runtime/executables/handlers/tool_handler.py`
- `src/lily/runtime/executables/handlers/blueprint_handler.py`
- `src/lily/runtime/executables/handlers/job_handler.py`
- `src/lily/runtime/executables/handlers/__init__.py`
- `src/lily/runtime/executables/__init__.py`
- `tests/unit/runtime/executables/handlers/test_agent_handler.py`
- `tests/unit/runtime/executables/handlers/test_skill_handler.py`
- `tests/unit/runtime/executables/handlers/test_tool_handler.py`
- `tests/unit/runtime/executables/handlers/test_blueprint_handler.py`
- `tests/unit/runtime/executables/handlers/test_job_handler.py`

Validation commands and outcomes:
- `uv run pytest tests/unit/runtime/executables/handlers -q` -> pass (`11 passed`)
- `uv run pytest tests/e2e/test_phase3_routing.py tests/e2e/test_phase4_memory_jobs.py -q` -> pass (`9 passed`)
- `just format-check` -> pass
- `just lint` -> pass
- `just types` -> pass

Acceptance gate evidence:
- Adapter handlers now exist for all required executable kinds and normalize outputs to `ExecutableResult`.
- Failure paths across adapter boundaries map to deterministic error codes in canonical envelopes.
- Dispatcher-facing handler path is envelope-driven with no direct subsystem bypass in the orchestration adapter stack.
- Existing skills/jobs end-to-end regression suites remain green.

Blocked/partial items:
- none for Phase 3.

### 2026-03-04 - Phase 4 Completed (Supervisor Runtime MVP + Typed Handoffs)

Completion status:
- Completed Phase 4 scope only.

Implemented artifacts:
- `src/lily/runtime/orchestration/__init__.py`
- `src/lily/runtime/orchestration/plan_models.py`
- `src/lily/runtime/orchestration/supervisor.py`
- `src/lily/runtime/orchestration/aggregator.py`
- `src/lily/runtime/runtime_dependencies.py`
- `src/lily/runtime/facade.py`
- `tests/unit/runtime/orchestration/test_supervisor.py`
- `tests/integration/runtime/test_supervisor_delegation.py`

Validation commands and outcomes:
- `uv run pytest tests/unit/runtime/orchestration/test_supervisor.py tests/integration/runtime/test_supervisor_delegation.py -q` -> pass (`4 passed`)
- `just lint` -> pass
- `just types` -> pass

Acceptance gate evidence:
- Supervisor is the sole delegator and executes planner-emitted typed multi-step plans via dispatcher boundaries.
- Planner output is schema-validated (`SupervisorPlan.model_validate`) before execution; invalid payloads fail with deterministic envelope `supervisor_plan_invalid`.
- Delegation depth remains fixed at one level (`parent_step_id` of delegated steps is root supervisor step id, no recursive planning path).
- Aggregation preserves provenance references/artifacts and surfaces deterministic failed-step envelopes.
- Deterministic multi-step delegated flow is covered by integration test.

Blocked/partial items:
- PydanticAI backend runner wiring is represented by `PydanticAiPlanRunner`/`PydanticAiSupervisorPlanner` ports; concrete provider bootstrap is deferred to subsequent phase wiring.
