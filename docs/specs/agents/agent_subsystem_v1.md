---
owner: "@team"
last_updated: "2026-03-02"
status: "active"
source_of_truth: true
---

# Agent Subsystem V1

Status: Proposed  
Date: 2026-03-02  
Scope: first-class agent runtime identity, agent/persona domain boundary, and deterministic `/agent` command contract.

## 1. Why This Feature Exists

`/agent` currently uses persona-backed compatibility behavior. That coupling mixes user-facing style controls with runtime execution identity and blocks reliable multi-agent orchestration work.

This feature defines a clean-break architecture:
- `Persona` remains user-facing style/voice only.
- `Agent` becomes runtime execution identity and authority.
- No implicit mapping from persona selection to agent authority.

## 2. Locked Decisions (V1)

1. `Agent` and `Persona` are separate domains with independent identifiers.
2. Runtime execution authority is derived from `active_agent` only.
3. Persona selection cannot modify agent capabilities, policy, or tool grants.
4. `/agent` commands must resolve from agent registry/service only.
5. Persona-backed `/agent` fallback is removed in V1.
6. Invalid/missing agent resolution fails with deterministic command errors.
7. Multi-agent delegation behavior is out of scope for this phase.

## 3. Domain Contract

## 3.1 Agent Domain (Execution)

`Agent` is the execution identity. It owns:
- stable `agent_id`
- capability/tool policy references
- execution policy profile references
- deterministic metadata required by runtime enforcement

Definition format (V1):
- primary: structured `*.agent.yaml` / `*.agent.yml` contract files
- migration-only: legacy markdown with YAML frontmatter may be read temporarily

`Agent` must not own:
- user-facing tone/style defaults
- persona instruction text

## 3.2 Persona Domain (User-Facing)

`Persona` is the presentation identity. It owns:
- stable `persona_id`
- tone/style defaults and presentation guidance
- user-visible writing behavior

`Persona` must not own:
- execution capabilities
- runtime policy/approval authority
- delegation permissions

## 3.3 Session State Contract

Session must track independent fields:
- `active_persona`: presentation context
- `active_agent`: execution context

Required invariants:
- changing `active_persona` does not mutate `active_agent`
- changing `active_agent` does not mutate `active_persona`
- runtime/tool dispatch reads execution authority from `active_agent`

## 4. Command Contract (Phase 0 Scope)

`/agent list|use|show`:
- operates on agent registry/service only
- returns deterministic success/error envelopes
- does not reference persona compatibility behavior

`/persona list|use|show`:
- remains a persona UX surface
- must not change runtime execution authority

## 5. Deterministic Failure Contract

At minimum, V1 must keep deterministic handling for:
- unsupported `/agent` subcommand
- invalid argument shape for `/agent` subcommands
- requested agent not found
- active agent missing from registry

Failure outcomes must be deterministic and machine-assertable by tests.

## 6. Non-Goals (Phase 0)

- no supervisor planning/delegation implementation
- no multi-subagent fan-out
- no recursive delegation
- no attempt to preserve persona-backed `/agent` compatibility behavior

## 7. Verification Expectations

Phase 0 follow-up implementation/tests must prove:
- `/agent` no longer resolves through persona catalog
- `/agent use` mutates only `active_agent`
- `/persona use` mutates only `active_persona`
- execution authority/policy checks read from agent context only
- agent registry is loaded from structured YAML contracts (with explicit migration handling)
