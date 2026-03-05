# Layer 4 — Routing and Policies
## Phased Implementation Plan (for AI Coder)

You are implementing **Layer 4 (Routing and Policies)** for Project **Lily**.

This layer turns runtime outcomes into **deterministic control flow** and enforces sandbox safety.

It must remain:
- Kernel-pure
- Data-driven
- Deterministic
- Minimal for first implementation

---

# Scope (Kernel-only)

Implement:

- RoutingRule
- RoutingEngine
- PolicyViolation schema
- SafetyPolicy model
- Basic enforcement (write path + tool allowlist)
- Integration into Runner

---

# Out of Scope (Do NOT implement)

- Domain-specific routing
- LLM-based routing
- Smart retry heuristics
- Complex diff engine
- Network enforcement (placeholder only)
- Plugin integration
- UI for routing configuration

---

# Global Constraints

- One phase per PR
- No new dependencies
- Routing must be deterministic
- Policies must be declarative
- Violations must be stored as envelopes
- Do not refactor Layer 2 beyond required integration points

---

# Phase 4.1 — RoutingRule + RoutingEngine (Standalone)

## Goal
Implement deterministic routing based on structured rule definitions.

---

## Tasks

- [x] Add `src/lily/kernel/routing_models.py`
  - [x] `RoutingActionType` enum:
    - `retry_step`
    - `goto_step`
    - `escalate`
    - `abort_run`
    - `continue`
  - [x] `RoutingCondition`
    - `step_status: Optional[...]`
    - `gate_status: Optional[...]`
    - `retry_exhausted: Optional[bool]`
    - `policy_violation: Optional[bool]`
    - `step_id: Optional[str]`
    - `gate_id: Optional[str]`
  - [x] `RoutingAction`
    - `type`
    - `target_step_id`
    - `reason`
  - [x] `RoutingRule`
    - `rule_id`
    - `when: RoutingCondition`
    - `action: RoutingAction`

- [x] Add `RoutingEngine`
  - [x] `evaluate(context, rules) -> RoutingAction`
  - [x] Deterministic rule evaluation (first match wins)
  - [x] Default behavior:
    - step failed → abort_run
    - step succeeded → continue

---

## Tests

- [x] `tests/unit/test_routing_engine.py`
  - [x] matching rule triggers correct action
  - [x] rule order respected
  - [x] default behavior when no rules match
  - [x] goto_step requires target_step_id

---

## Acceptance Criteria

- [x] RoutingEngine deterministic
- [x] No side effects inside engine
- [x] Unit tests pass

---

# Phase 4.2 — PolicyViolation Schema

## Goal
Introduce structured policy violation reporting.

---

## Tasks

- [x] Add `policy_violation.v1` schema:
  - `step_id`
  - `violation_type`
  - `details`
  - `timestamp`
- [x] Register schema in SchemaRegistry
- [x] Add model in `src/lily/kernel/policy_models.py`

---

## Tests

- [x] `tests/unit/test_policy_violation.py`
  - [x] Valid payload passes
  - [x] Missing required fields fail
  - [x] Envelope validation works

---

## Acceptance Criteria

- [x] policy_violation.v1 registered
- [x] Validation enforced
- [x] Tests pass

---

# Phase 4.3 — SafetyPolicy Model (No Enforcement Yet)

## Goal
Define safety policy configuration object.

---

## Tasks

- [x] Add `SafetyPolicy` model:
  - `allow_write_paths: list[str]`
  - `deny_write_paths: list[str]`
  - `max_diff_size_bytes: Optional[int]`
  - `allowed_tools: list[str]`
  - `network_access: Literal["allow","deny"]`
- [x] Add default policy constructor
- [x] Validate fields

---

## Tests

- [x] `tests/unit/test_safety_policy.py`
  - [x] Valid config passes
  - [x] Invalid network_access fails

---

## Acceptance Criteria

- [x] SafetyPolicy model exists
- [x] Validates correctly
- [x] Tests pass

---

# Phase 4.4 — Tool Allowlist Enforcement

## Goal
Prevent unauthorized executors from running.

---

## Tasks

- [x] Modify Runner:
  - Before executing step:
    - [x] Verify executor kind/tool is allowed under SafetyPolicy
  - If violation:
    - [x] Create `policy_violation.v1` envelope
    - [x] Route using RoutingEngine (policy_violation=True)
- [x] Integrate RoutingEngine decision

---

## Tests

- [x] `tests/unit/test_tool_allowlist.py`
  - [x] Allowed tool executes
  - [x] Disallowed tool triggers policy_violation
  - [x] Routing abort works

---

## Acceptance Criteria

- [x] Disallowed tools blocked
- [x] PolicyViolation envelope stored
- [x] RoutingEngine invoked
- [x] Tests pass

---

# Phase 4.5 — Write Path Enforcement

## Goal
Prevent steps from writing outside allowed paths.

---

## Tasks

- [x] After step execution:
  - [x] Detect files modified (simple implementation: compare mtime snapshot before/after within run workspace)
  - [x] Validate against:
    - allow_write_paths
    - deny_write_paths
  - [x] On violation:
    - Create `policy_violation.v1` envelope
    - Trigger routing
- [x] Keep detection minimal (no full diff engine yet)

---

## Tests

- [x] `tests/unit/test_write_path_policy.py`
  - [x] Writing to allowed path passes
  - [x] Writing to denied path triggers violation
  - [x] Routing behavior correct

---

## Acceptance Criteria

- [x] Write policy enforced
- [x] Violations recorded
- [x] Routing invoked
- [x] Tests pass

---

# Phase 4.6 — Runner Integration with RoutingEngine

## Goal
Centralize post-step routing decisions.

---

## Tasks

- [x] After step execution + gates + policy checks:
  - [x] Build routing context
  - [x] Call RoutingEngine
  - [x] Apply RoutingAction:
    - retry_step
    - goto_step
    - escalate (set RunStatus=blocked)
    - abort_run (set RunStatus=failed)
    - continue (normal flow)
- [x] Ensure deterministic ordering
- [x] Persist RunState after routing decision

---

## Tests

- [x] `tests/unit/test_runner_routing.py`
  - [x] Retry rule triggers retry
  - [x] goto_step changes execution order
  - [x] escalate sets run blocked
  - [x] abort_run sets run failed

---

## Acceptance Criteria

- [x] Routing fully integrated
- [x] Escalation works
- [x] Abort works
- [x] Retry override works
- [x] Tests pass

---

# Global Done Criteria (Layer 4)

- [x] RoutingRule + RoutingEngine implemented
- [x] PolicyViolation schema registered
- [x] SafetyPolicy model implemented
- [x] Tool allowlist enforced
- [x] Write path policy enforced
- [x] Runner integrates routing decisions
- [x] Escalation supported
- [x] Abort supported
- [x] All tests pass
- [x] No domain logic introduced

---

# Final Reminder to AI Coder

- Do not add plugin hooks.
- Do not implement network sandboxing beyond config.
- Do not add complex diff engines.
- Do not implement LLM routing.
- Keep routing deterministic and data-driven.
- One PR per phase.
