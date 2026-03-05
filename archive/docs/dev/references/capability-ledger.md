---
owner: "@team"
last_updated: "2026-03-04"
status: "active"
source_of_truth: true
---

# Lily Capability Ledger (V1 Control Plane)

## Purpose

This is the canonical list of what Lily must do to be considered functional for V1.
If a capability is not listed here, it is out of scope for V1.

## Status Legend

- `Missing`: no runtime implementation yet.
- `Partial`: implementation exists but is not complete as a reliable end-user capability.
- `Implemented`: shipped in runtime and command surface.
- `Verified`: implemented and explicitly covered by stable tests/gates.

## Capability Ledger

| ID | Capability | Status | User Surface | Primary Code | Evidence | Exit Criteria |
|---|---|---|---|---|---|---|
| CAP-001 | Command routing (slash vs conversation) | Verified | `lily run`, `lily repl` | `src/lily/runtime/facade.py` | `tests/e2e/test_phase3_routing.py` | Deterministic parse/route behavior across run+repl |
| CAP-002 | Skills snapshot loading + reload | Verified | `/skills`, `/reload_skills` | `src/lily/skills/loader.py`, `src/lily/commands/handlers/reload_skills.py` | `tests/e2e/test_phase2_session_commands.py`, `tests/unit/skills/test_loader.py` | Deterministic snapshot versioning + diagnostics |
| CAP-003 | Skill invocation (`llm_orchestration`, `tool_dispatch`) | Verified | `/skill <name> ...` | `src/lily/runtime/skill_invoker.py`, `src/lily/runtime/executors/*` | `tests/e2e/test_phase3_routing.py`, `tests/unit/runtime/test_tool_dispatch_executor.py` | Both invocation modes execute with deterministic envelopes |
| CAP-004 | Tool provider dispatch registry | Partial | Tool-dispatch skills | `src/lily/runtime/executors/tool_dispatch.py` | Unit coverage in runtime tests | `builtin`, `plugin`, and `mcp` all work as real providers in default runtime |
| CAP-005 | Plugin security gate + approvals + policy scan | Verified | Plugin-backed `/skill` execution | `src/lily/runtime/security.py`, `src/lily/runtime/security_language_policy.py` | `tests/e2e/test_phase5_security.py` | Deterministic deny/approve/hash-change behavior |
| CAP-006 | Agent identity separate from persona | Verified | `/agent`, `/persona` | `src/lily/session/models.py`, `src/lily/commands/handlers/agent.py` | `tests/e2e/test_phase6_agent_registry.py` | Agent and persona mutate independently |
| CAP-007 | Agent catalog loading (`*.agent.yaml|yml` + legacy md) | Verified | `/agent list|use|show` | `src/lily/agents/repository.py` | `tests/unit/agents/test_agents_repository.py` | Stable agent catalog + deterministic errors |
| CAP-008 | Jobs manual execution + artifacts + history/tail | Verified | `/jobs run|tail|history` | `src/lily/jobs/executor.py`, `src/lily/commands/handlers/jobs.py` | `tests/e2e/test_phase4_memory_jobs.py` | Required artifacts written each run |
| CAP-009 | Jobs scheduler lifecycle controls | Verified | `/jobs status|pause|resume|disable` | `src/lily/jobs/scheduler_runtime.py` | `tests/e2e/test_phase4_memory_jobs.py` | APScheduler state persisted + reconciled |
| CAP-010 | Blueprints as workflow target runtime | Implemented | Jobs target kind `blueprint` | `src/lily/jobs/models.py`, `src/lily/jobs/executor.py` | Jobs unit/e2e suites | Job target compile/invoke path remains stable |
| CAP-011 | Supervisor runtime | Missing | N/A | N/A | N/A | Supervisor process can route at least one delegated request |
| CAP-012 | Subagent typed handoffs | Missing | N/A | N/A | N/A | Typed request/response handoff contracts enforced in runtime |
| CAP-013 | Delegation gate/routing outcomes (`retry/fallback/escalate`) | Missing | N/A | N/A | N/A | Deterministic gate outcomes emitted and persisted |
| CAP-014 | Jobs-to-supervisor bridge | Missing | Future `/jobs` delegated path | N/A | N/A | Jobs can execute supervisor plans with trace metadata |
| CAP-015 | Unified orchestration observability and replay | Partial | Job artifacts + scheduler events | `src/lily/jobs/*`, `src/lily/runtime/*` | Current jobs tests only | Replay/resume covers delegated multi-agent runs |

## V1 Definition Of Done

Lily V1 is complete only when CAP-001 through CAP-015 are at least `Implemented`, and CAP-001 through CAP-010 are `Verified`.

## Deferred Items Rule

Anything from `ideas/` that does not directly advance a `Missing` or `Partial` capability above is deferred by default.

## Capability Jump Anchors

<a id="cap-001"></a>
### CAP-001 - Command routing (slash vs conversation)

<a id="cap-002"></a>
### CAP-002 - Skills snapshot loading + reload

<a id="cap-003"></a>
### CAP-003 - Skill invocation (`llm_orchestration`, `tool_dispatch`)

<a id="cap-004"></a>
### CAP-004 - Tool provider dispatch registry

<a id="cap-005"></a>
### CAP-005 - Plugin security gate + approvals + policy scan

<a id="cap-006"></a>
### CAP-006 - Agent identity separate from persona

<a id="cap-007"></a>
### CAP-007 - Agent catalog loading (`*.agent.yaml|yml` + legacy md)

<a id="cap-008"></a>
### CAP-008 - Jobs manual execution + artifacts + history/tail

<a id="cap-009"></a>
### CAP-009 - Jobs scheduler lifecycle controls

<a id="cap-010"></a>
### CAP-010 - Blueprints as workflow target runtime

<a id="cap-011"></a>
### CAP-011 - Supervisor runtime

<a id="cap-012"></a>
### CAP-012 - Subagent typed handoffs

<a id="cap-013"></a>
### CAP-013 - Delegation gate/routing outcomes (`retry/fallback/escalate`)

<a id="cap-014"></a>
### CAP-014 - Jobs-to-supervisor bridge

<a id="cap-015"></a>
### CAP-015 - Unified orchestration observability and replay
