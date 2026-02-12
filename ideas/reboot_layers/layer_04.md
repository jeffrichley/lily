# Layer 4 — Routing and Policies

Layer 4 defines the **deterministic decision layer** of the kernel:

> Routing rules + Safety policies + Enforcement engine

This layer determines **what happens next** when:

- A step succeeds or fails
- A gate passes or fails
- Retries are exhausted
- Safety policies are violated

Layer 4 turns runtime outcomes into deterministic control flow.

---

## 0. Design Principles

1. Routing decisions are data-driven, not hard-coded.
2. Policies are declarative and enforced by the kernel.
3. Safety checks occur before and/or after step execution.
4. The kernel never embeds domain semantics into routing logic.
5. Routing must be deterministic given the same state and policies.
6. Violations must be recorded as structured artifacts (enveloped).

---

## 1. Routing Rules

Routing determines how the runtime proceeds after a step or gate result.

### 1.1 Routing Inputs

Routing decisions may depend on:

- Step execution result (success/failure)
- Gate results (pass/fail)
- Retry counters
- RunState status
- Policy evaluation results

Routing must not depend on:

- Domain meaning of artifacts
- Unstructured logs
- External mutable state

---

### 1.2 Routing Actions

The kernel must support the following routing outcomes:

- `retry_step`
- `goto_step` (explicit step_id)
- `escalate`
- `abort_run`
- `continue` (default progression)

---

### 1.3 RoutingRule Model

Routing rules must be defined declaratively.

| Field     | Type              | Description        |
| --------- | ----------------- | ------------------ |
| `rule_id` | `str`             | Unique identifier  |
| `when`    | `RoutingCondition` | When to apply     |
| `action`  | `RoutingAction`   | What to do         |

---

### 1.4 RoutingCondition

| Field              | Type                                | Description      |
| ------------------ | ----------------------------------- | ---------------- |
| `step_status`      | `"succeeded"` or `"failed"` or `None` | Step outcome     |
| `gate_status`      | `"passed"` or `"failed"` or `None`   | Gate outcome     |
| `retry_exhausted`  | `bool` or `None`   | Retries exhausted           |
| `policy_violation` | `bool` or `None`   | Policy violation occurred   |
| `step_id`          | `str` or `None`    | Scope to step               |
| `gate_id`          | `str` or `None`    | Scope to gate               |

Conditions are conjunctive (all specified fields must match). If a field is `None`, it is ignored.

---

### 1.5 RoutingAction

| Field            | Type                                                    | Description                         |
| ---------------- | ------------------------------------------------------- | ----------------------------------- |
| `type`           | retry_step, goto_step, escalate, abort_run, or continue | Action to take                      |
| `target_step_id` | `str` or `None`                                         | Required if type is goto_step       |
| `reason`         | `str` or `None`                                         | Optional reason                     |

---

### 1.6 RoutingEngine

**Responsibilities:**

- Evaluate routing rules in deterministic order
- Apply first matching rule
- Default behavior if no rule matches:
  - Step failure → abort
  - Step success → continue

**RoutingEngine must:**

- Not mutate RunState directly
- Return a routing decision to Runner
- Be pure and deterministic

---

## 2. Escalation Semantics

Escalation means:

- RunStatus becomes `blocked`
- RunState records:
  - `escalation_reason`
  - `escalation_step_id`
- No further steps execute until manual intervention

Escalation is not failure. It is a pause.

---

## 3. Safety Policies (Sandboxing)

Safety policies prevent uncontrolled or unsafe execution. They apply at:

- Step execution boundary
- Executor invocation
- Artifact production

### 3.1 SafetyPolicy Model

| Field               | Type                    | Description              |
| ------------------- | ----------------------- | ------------------------ |
| `allow_write_paths` | `list[str]`             | Paths step may write to  |
| `deny_write_paths`  | `list[str]`             | Paths step must not write |
| `max_diff_size_bytes` | `int` or `None`       | Max diff size (optional) |
| `allowed_tools`     | `list[str]`             | Tool allowlist           |
| `network_access`    | `"allow"` or `"deny"`     | Network policy        |

---

### 3.2 Policy Enforcement Points

**Before step execution:**

- Validate executor kind allowed
- Validate tool in allowlist
- Validate network policy (future)
- Validate write targets (if declared)

**After step execution:**

- Validate file writes stay within allowed paths
- Validate no writes occurred in deny paths
- Validate diff size under threshold (optional)

**Violations must:**

- Produce a `policy_violation.v1` envelope
- Trigger routing evaluation

---

## 4. PolicyViolation Envelope

**Schema ID:** `policy_violation.v1`

**Payload:**

| Field             | Type        |
| ----------------- | ----------- |
| `step_id`         | `str`       |
| `violation_type`  | `str`       |
| `details`         | `str`       |
| `timestamp`       | `datetime`  |

Policy violations are first-class artifacts.

---

## 5. Integration with Layer 2 & 3

**Execution order:**

1. Step runs.
2. Gates execute (Layer 3).
3. Safety policies enforced.
4. RoutingEngine evaluates.
5. Runner applies routing decision.

**Layer 4 does not:**

- Execute steps
- Run gates
- Modify artifacts

It only decides next action.

---

## 6. Determinism Guarantees

Layer 4 must ensure:

- Given same RunState + routing rules + policies → same routing decision
- Rule evaluation order deterministic
- No random or time-based branching

---

## 7. Invariants

**Layer 4 guarantees:**

- Routing rules are declarative and externalizable
- Policy violations are captured as artifacts
- Escalation does not destroy run state
- Abort is explicit and recorded
- Kernel does not embed domain logic in routing

**Layer 4 does not guarantee:**

- Correct policy configuration
- Smart remediation
- Automatic recovery

---

## 8. Minimal Initial Implementation Scope

**For first implementation, limit to:**

- RoutingRule
- RoutingEngine
- Abort and retry logic override
- Basic write path enforcement
- Tool allowlist enforcement

**Defer:**

- Max diff enforcement
- Network enforcement
- Complex routing chains

---

## 9. Done Criteria (Layer 4)

Layer 4 is complete when:

- [x] RoutingRule and RoutingEngine implemented
- [x] Runner integrates routing decisions
- [x] Escalation sets run status to blocked
- [x] Abort transitions run to failed
- [x] Basic safety policies enforced (write allow/deny + tool allowlist)
- [x] PolicyViolation envelope registered and stored
- [x] Deterministic rule evaluation tested
- [x] Integration tests validate routing behavior
- [x] All tests pass

---

## 10. One-Line Summary for AI Coder

Implement Layer 4 kernel routing and safety: declarative RoutingRule + RoutingEngine + SafetyPolicy enforcement + PolicyViolation envelope. Integrate into Runner deterministically. Keep domain-neutral.
