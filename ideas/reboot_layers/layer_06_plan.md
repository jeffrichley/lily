```md
# Layer 6 — Extension Points (Plugins / Packs)
## Phased Implementation Plan (for AI Coder)

You are implementing **Layer 6 (Extension Points / Packs)** for Project **Lily**.

This layer introduces domain extensibility while keeping the kernel small.

The kernel must only:
- Load packs
- Register schemas
- Register templates
- Merge routing rules
- Validate compatibility

The kernel must not:
- Embed domain logic
- Special-case pack behavior
- Allow packs to override core enforcement

---

# Scope (Kernel-only)

Implement:

- PackDefinition model
- PackLoader
- Schema registration from packs
- Step template registration
- Gate template registration
- Routing rule merging
- Namespace collision detection
- Version compatibility validation

---

# Out of Scope (Do NOT implement)

- Remote pack marketplace
- Dynamic hot reload
- Complex dependency resolution between packs
- Runtime unloading
- UI pack management
- Network-based pack registry
- Domain packs themselves (only infrastructure)

---

# Global Constraints

- One phase per PR
- No new dependencies
- No modifications to kernel core behavior
- Packs must be declarative
- Pack loading must be deterministic
- Pack import must not cause side effects
- All pack contributions validated before registration

---

# Phase 6.1 — PackDefinition Model

## Goal
Define the structured representation of a pack.

---

## Tasks

- [x] Add `src/lily/kernel/pack_models.py`
  - [x] Define `PackDefinition`:
    - `name: str`
    - `version: str`
    - `minimum_kernel_version: str`
    - `schemas: list[SchemaRegistration]`
    - `step_templates: list[StepTemplate]`
    - `gate_templates: list[GateTemplate]`
    - `routing_rules: list[RoutingRule]`
    - `default_safety_policy: SafetyPolicy | None`
  - [x] Define `SchemaRegistration`:
    - `schema_id`
    - `model`
  - [x] Define minimal `StepTemplate` model:
    - `template_id`
    - `input_schema_ids`
    - `output_schema_ids`
    - `default_executor`
    - `default_retry_policy`
    - `default_gates`
  - [x] Define `GateTemplate` model:
    - `template_id`
    - `runner_spec`
    - `required`

- [x] Enforce:
  - Pack name required
  - Schema IDs must be namespaced
  - Template IDs must be namespaced

---

## Tests

- [x] `tests/unit/test_pack_models.py`
  - [x] Valid PackDefinition passes
  - [x] Missing required fields fail
  - [x] Namespacing validation enforced

---

## Acceptance Criteria

- [x] PackDefinition model exists
- [x] Namespacing enforced
- [x] Tests pass

---

# Phase 6.2 — PackLoader (Local Python Modules Only)

## Goal
Load pack definitions from local Python modules.

---

## Tasks

- [x] Add `src/lily/kernel/pack_loader.py`
  - [x] `load_pack(module_path: str) -> PackDefinition`
  - [x] Import module safely
  - [x] Expect `PACK_DEFINITION` object exported
  - [x] Validate:
    - minimum_kernel_version
    - structure integrity
  - [x] Fail fast on error

- [x] Add:
  - `load_packs(list[str]) -> list[PackDefinition]`

---

## Tests

- [x] `tests/unit/test_pack_loader.py`
  - [x] Valid pack loads
  - [x] Missing PACK_DEFINITION fails
  - [x] Version mismatch fails
  - [x] Invalid structure fails

---

## Acceptance Criteria

- [x] PackLoader deterministic
- [x] Version compatibility enforced
- [x] Tests pass

---

# Phase 6.3 — Schema Registration from Packs

## Goal
Register pack schemas into SchemaRegistry safely.

---

## Tasks

- [x] For each pack:
  - [x] Register schemas
  - [x] Detect duplicate schema IDs across packs
  - [x] Fail on collision unless identical model
- [x] Ensure:
  - Kernel schemas cannot be overridden
  - Explicit override flag not allowed for packs

---

## Tests

- [x] `tests/unit/test_pack_schema_registration.py`
  - [x] Schema registers successfully
  - [x] Collision between packs fails
  - [x] Kernel schema override blocked

---

## Acceptance Criteria

- [x] Pack schemas registered safely
- [x] Collisions detected
- [x] Tests pass

---

# Phase 6.4 — Template Registry (Step + Gate Templates)

## Goal
Introduce template registries.

---

## Tasks

- [x] Add `TemplateRegistry`
  - [x] register_step_template()
  - [x] register_gate_template()
  - [x] get_step_template()
  - [x] get_gate_template()
- [x] Prevent template ID collisions
- [x] Store templates by fully-qualified ID

- [x] Implement template expansion:
  - StepTemplate → StepSpec
  - GateTemplate → GateSpec

---

## Tests

- [x] `tests/unit/test_template_registry.py`
  - [x] Template registration works
  - [x] Collision fails
  - [x] Expansion produces valid StepSpec
  - [x] Expansion produces valid GateSpec

---

## Acceptance Criteria

- [x] TemplateRegistry implemented
- [x] Expansion works
- [x] No domain semantics introduced
- [x] Tests pass

---

# Phase 6.5 — Routing Rule Merging

## Goal
Merge routing rules from packs deterministically.

---

## Tasks

- [x] Add `merge_routing_rules(pack_rules_list)`
  - Deterministic ordering (e.g., by pack load order)
  - Validate no duplicate rule_id
- [x] Ensure:
  - Rules stored separately from kernel defaults
  - No pack can override kernel default rule behavior silently

---

## Tests

- [x] `tests/unit/test_pack_routing_merge.py`
  - [x] Rules merge correctly
  - [x] Duplicate rule_id fails
  - [x] Deterministic order preserved

---

## Acceptance Criteria

- [x] Routing rules merged safely
- [x] Determinism guaranteed
- [x] Tests pass

---

# Phase 6.6 — Default Safety Policy Integration

## Goal
Allow packs to contribute default SafetyPolicy.

---

## Tasks

- [x] On pack load:
  - [x] Collect default_safety_policy
  - [x] Merge policies conservatively:
    - allowed_tools intersection
    - deny_write_paths union
    - allow_write_paths intersection
    - network_access strictest wins
- [x] Expose merged policy to Runner

---

## Tests

- [x] `tests/unit/test_pack_safety_policy.py`
  - [x] Policy merge deterministic
  - [x] Conservative merge enforced
  - [x] Conflicts resolved safely

---

## Acceptance Criteria

- [x] Pack policies merge correctly
- [x] No pack weakens security
- [x] Tests pass

---

# Global Done Criteria (Layer 6)

- [x] PackDefinition model exists
- [x] PackLoader implemented
- [x] Schema registration safe and collision-checked
- [x] TemplateRegistry implemented
- [x] Step and Gate template expansion works
- [x] Routing rule merging deterministic
- [x] Safety policy merging conservative
- [x] Kernel core untouched
- [x] No domain logic embedded
- [x] All tests pass

---

# Final Reminder to AI Coder

- Do not add remote loading.
- Do not allow pack override of kernel internals.
- Do not add side effects during import.
- Keep extension system declarative.
- One PR per phase.
```
