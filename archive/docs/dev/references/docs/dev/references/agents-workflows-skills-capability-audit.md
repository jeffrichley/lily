---
owner: "@jeffrichley"
last_updated: "2026-03-04"
status: "active"
source_of_truth: false
---

# Agents + Workflows + Skills Capability Audit (Ground Truth)

## Purpose

This document states what is implemented in Lily today vs what remains partial or missing for the "agents + workflows + skills wired together" target.

Status labels:
- `Implemented`: present in runtime code and exercised by tests.
- `Partial`: scaffolding exists, but not complete as an end-user capability.
- `Missing`: not implemented in runtime.

## Executive Verdict

Can Lily run agents + workflows + skills as one coherent system today?

**Answer: Partial.**

What works in production paths now:
- Skills load/validate/snapshot/reload/invoke.
- Agent identity exists and is session-separate from persona.
- Jobs run manually and via cron, with artifacts/history/scheduler controls.

What does not exist yet:
- Supervisor/subagent orchestration runtime.
- Typed delegation handoff execution graphs.
- Delegation gate/routing outcomes (`retry`/`fallback`/`escalate`) across multi-agent runs.

## Capability Matrix

## 1) Skills Platform

### 1.1 Snapshot and command surface
- **Status: `Implemented`**
- Skills are discovered from bundled + workspace roots by default.
- Loader supports user root (`user_dir`) but default CLI session bootstrap does not set it.
- Precedence resolution, frontmatter parsing, eligibility checks, and deterministic snapshot hashing are implemented.
- Session stores immutable `skill_snapshot` and supports `/reload_skills`.
- `/skills` and `/skill <name> ...` are implemented.

### 1.2 Invocation modes
- **Status: `Implemented`** for current two-mode enum:
  - `llm_orchestration`
  - `tool_dispatch`

### 1.3 Provider dispatch and typed I/O
- **Status: `Partial`**
- Registry-style provider dispatch exists (`builtin`, `mcp`, `plugin`).
- Typed input/output contract validation exists in tool dispatch.
- `builtin` and `plugin` execution paths are concrete.
- MCP provider is mostly adapter scaffolding by default (no concrete tools resolved unless externally wired).

### 1.4 Security and capability enforcement
- **Status: `Implemented`** for current platform scope
- Capability declaration checks happen at skill invocation boundary.
- Plugin security gate, language policy scan, approval flow (`run_once`, `always_allow`, `deny`), and provenance/security hash pathways are implemented.

## 2) Agent Runtime Identity

### 2.1 Session model split
- **Status: `Implemented`**
- Session tracks `active_agent` and `active_persona` independently.

### 2.2 Command and catalog behavior
- **Status: `Implemented`**
- `/agent list|use|show` exists via `AgentService` + file repository.
- Agent contracts load from `*.agent.yaml|*.agent.yml`.
- Legacy markdown frontmatter loading remains supported during migration.

### 2.3 Agent authority in orchestration
- **Status: `Partial`**
- Agent identity is present and used by plugin security/capability pathways.
- Full supervisor-based authority delegation across subagents is not implemented.

## 3) Workflow Execution (Jobs)

### 3.1 Jobs command surface
- **Status: `Implemented`**
- `/jobs list|run|tail|history|pause|resume|disable|status` implemented with deterministic envelopes.

### 3.2 Run artifacts and lifecycle
- **Status: `Implemented`**
- Run directories and mandatory artifacts (`run_receipt.json`, `summary.md`, `events.jsonl`) are written.
- Retry and timeout behavior are implemented.

### 3.3 Cron scheduler runtime
- **Status: `Implemented`**
- APScheduler runtime, SQLite-backed scheduler state, reconcile behavior, and lifecycle controls are implemented.

## 4) Supervisor/Subagent Orchestration

- **Status: `Missing` (runtime), `Implemented` (spec only)**
- Spec exists (`docs/specs/agents/supervisor_subagents_v1.md`).
- No supervisor runtime, typed delegated handoff execution, or multi-subagent orchestrator code is present in `src/lily`.

## 5) End-to-End Wiring Quality

Current integrated behavior:
- `Implemented`: agent context + skill invocation in same session.
- `Implemented`: jobs lifecycle + scheduler + artifacts.
- `Partial`: one-system narrative exists conceptually, but lacks supervisor orchestration layer.

## Precision Corrections to Prior Claims

1. Claim that current provider support is fully equivalent across `builtin`, `mcp`, `plugin` was too strong.
- Ground truth: MCP is present as provider interface/scaffold, but default resolver is effectively unbound.

2. Claim that bundled/workspace/user root behavior is broadly "current runtime behavior" was too broad.
- Ground truth: loader supports `user_dir`, but default CLI/session construction does not populate it.

3. Calling supervisor/subagent work merely "proposed" is stale wording.
- Ground truth: spec is active, runtime implementation is still missing.

## Practical Conclusion

For "wired together today":
- **Yes** for a practical stack of `agent identity + skill execution + jobs automation`.
- **No** for `supervisor orchestrates multiple subagents with typed delegation + gate routing`.

That target still requires a new orchestration layer, not just incremental command wiring.
