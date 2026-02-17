---
owner: "@team"
last_updated: "2026-02-17"
status: "active"
source_of_truth: true
---

# Supervisor + Subagents V1

Status: Proposed  
Date: 2026-02-17  
Scope: supervisor runtime, subagent delegation, typed handoffs, aggregation, and delegation quality gates.

## 1. Why This Feature Exists

We need first-class orchestration beyond single-skill execution:
- supervisor planning/routing across specialized subagents.
- deterministic delegation boundaries and fallback behavior.
- typed handoff contracts and traceability.

This feature adds orchestration after the skills substrate is hardened.

## 2. Dependency Contract

This feature starts only after `docs/specs/agents/skills_platform_v1.md` gates are complete through:
- capability contracts + enforcement.
- provider registry path.
- deterministic typed envelopes for execution boundaries.

## 3. Architecture Contract

## 3.1 Runtime Roles

- `SupervisorRuntime`: decides plan and delegates work units.
- `SubagentExecutor`: executes a scoped skill/task with least-privilege capabilities.
- `Aggregator`: merges subagent outputs into final deterministic envelope.

## 3.2 Delegation Rules

- supervisor is the only component allowed to delegate.
- subagents cannot recursively delegate in V1.
- delegation depth is fixed at 1 for V1.
- each handoff uses typed request/response models.
- failures are isolated to subagent scope and surfaced deterministically.

## 3.3 Trace and Audit

Record for each delegated run:
- supervisor run id.
- subagent call ids and routing decisions.
- typed handoff payload metadata.
- outcome and fallback path.

## 4. Migration Plan (Fixed Scope)

## Phase 1: Supervisor Core + Typed Handoff Models

User-visible features:
- none (internal foundation).

Internal engineering tasks:
- add supervisor planner interface.
- add typed handoff request/response models.
- add deterministic routing config contract.

Acceptance criteria:
- supervisor can select a target subagent deterministically for supported routes.
- invalid handoff payloads fail with deterministic contract errors.

Non-goals:
- no multi-subagent fan-out yet.
- no user-facing command changes yet.

Required tests and gates:
- routing unit tests.
- handoff schema validation tests.
- `just quality-check`.

## Phase 2: Multi-Subagent Delegation + Aggregation

User-visible features:
- delegated tasks can involve at least two specialized subagents.

Internal engineering tasks:
- implement sequential multi-subagent execution path.
- implement aggregation strategy and fallback contract.
- enforce isolation of per-subagent failures.

Acceptance criteria:
- at least one workflow executes 2+ subagents in one run.
- failed subagent does not crash supervisor run; fallback envelope is deterministic.

Non-goals:
- no recursive or autonomous background subagents.
- no open-ended planner loops.

Required tests and gates:
- integration tests for multi-subagent scenarios.
- failure containment tests.
- `just quality-check`.

## Phase 3: Quality Gates + Operational Governance

User-visible features:
- stable delegation behavior and operator diagnostics.

Internal engineering tasks:
- add delegation eval suite (correct routing, error containment, output quality).
- add runbook docs for supervisor/subagent failures.
- wire delegation evals into CI gate target.

Acceptance criteria:
- delegation eval thresholds documented and enforced.
- CI fails on delegation regressions.

Non-goals:
- no new UI mode (TUI/Studio).

Required tests and gates:
- eval tests for routing correctness and containment.
- regression snapshots for delegation envelopes.
- `just quality-check` and `just eval-gates`.

## 5. Open Questions

- default planning strategy in V1 (rule-based vs model-assisted).
- session-level vs turn-level supervisor planning state retention.
- initial canonical subagent set for V1 rollout.

