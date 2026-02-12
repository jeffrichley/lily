# Layer 6 — Extension Points (Plugins / Packs)

Layer 6 defines how **domain logic enters the system** without polluting the kernel.

Everything before this layer (0–5) is kernel infrastructure.

Layer 6 is where:

- Coding domains
- Research domains
- Analytics domains
- Business automation domains
- Media generation domains

plug into the kernel.

The kernel must remain small.

The kernel must not know what "coding" means.

The kernel must only know:

> Load packs. Register schemas. Execute graph.

---

## 0. Design Principles

1. The kernel never embeds domain logic.
2. Packs are declarative and self-contained.
3. Packs register contributions into registries.
4. Packs must be loadable/unloadable.
5. Packs cannot mutate kernel core behavior.
6. Kernel remains deterministic regardless of pack content.

Layer 6 does not introduce:

- Domain-specific execution semantics
- Hard-wired workflows
- Custom code paths in Runner

---

## 1. What Is a Pack?

A **Pack** is a domain extension unit.

A pack may contribute:

- Schemas (artifact types)
- Step templates (optional)
- Gate templates (optional)
- Routing policies (optional)
- Default safety policies (optional)

But the kernel sees only:

- Registered schemas
- Valid GraphSpec
- Valid RoutingRules
- Valid SafetyPolicy

---

## 2. Pack Capabilities

### 2.1 Schema Contributions

A pack may register:

- Artifact schemas
- Gate result variants
- Domain envelopes

Example:

- `code_patch.v1`
- `research_report.v1`
- `market_analysis.v1`

These are registered via SchemaRegistry.

The kernel does not interpret payload semantics.

---

### 2.2 Step Templates (Optional)

Packs may provide reusable step blueprints.

A StepTemplate defines:

- Expected input schema IDs
- Expected output schema IDs
- Default executor config
- Default retry policy
- Default gates

Templates are configuration helpers.

They generate StepSpec instances.

Kernel only executes StepSpec.

---

### 2.3 Gate Templates (Optional)

Packs may provide predefined GateSpec templates.

Examples:

- type-check gate
- lint gate
- format gate
- policy gate

Templates expand into concrete GateSpec.

Kernel only runs GateSpec.

---

### 2.4 Routing Policies (Optional)

Packs may contribute RoutingRule sets.

Examples:

- Retry up to N times if test fails
- Escalate if confidence below threshold
- Abort on security violation

Routing rules remain declarative.

Kernel evaluates them uniformly.

---

### 2.5 Safety Defaults (Optional)

Packs may propose default SafetyPolicy:

- Allowed write paths
- Tool allowlist
- Network policy

Kernel merges or applies policy per run.

---

## 3. Pack Interface

Each pack must expose a structured definition.

Example conceptual structure:

```text
PackDefinition:
  name
  version
  schemas: list[SchemaRegistration]
  step_templates: list[StepTemplate]
  gate_templates: list[GateTemplate]
  routing_rules: list[RoutingRule]
  default_safety_policy: SafetyPolicy | None
```

PackDefinition must be:

- Declarative
- Import-safe
- No side effects on import

---

## 4. Pack Loading

Kernel responsibilities:

- Discover packs (local path or configured registry)
- Load pack definitions
- Register schemas
- Register templates into template registry
- Merge routing rules
- Validate compatibility

Kernel must not:

- Execute pack code automatically
- Allow packs to override core behavior
- Allow packs to mutate other packs

---

## 5. Pack Isolation

Packs must be isolated:

- Namespaced schema IDs
- Namespaced step template IDs
- Namespaced gate template IDs

Example:

```text
coding.code_patch.v1
research.summary.v1
analytics.dataset_profile.v1
```

Collision detection required.

---

## 6. Template Expansion Model

Templates are not steps.

Templates are factories that produce StepSpec.

Example flow:

1. User selects template.
2. Template expands into StepSpec.
3. StepSpec inserted into GraphSpec.
4. Runner executes GraphSpec normally.

Kernel never sees template internals.

---

## 7. Versioning and Compatibility

Each pack must declare:

- pack_version
- minimum_kernel_version

Kernel must validate compatibility.

If incompatible:

- Fail at load time
- Do not partially load

---

## 8. Invariants

Layer 6 guarantees:

- Kernel core remains unchanged
- Domain logic is pluggable
- Packs cannot override kernel enforcement
- Schemas must be registered explicitly
- Routing remains declarative
- Safety policies remain enforceable

Layer 6 does not guarantee:

- Pack quality
- Pack correctness
- Domain correctness
- Conflict-free template combinations

---

## 9. Minimal Initial Implementation Scope

For first implementation:

- Support pack registration via Python modules
- Support schema registration
- Support step template registration
- Support routing rule registration
- Validate namespace collisions
- No remote pack loading
- No marketplace system

---

## 10. Done Criteria (Layer 6)

Layer 6 is complete when:

- [x] PackDefinition model exists
- [x] Kernel can load packs
- [x] Schemas from packs register successfully
- [x] Step templates expand into valid StepSpec
- [x] Routing rules from packs merge correctly
- [x] Namespace collisions detected
- [x] Compatibility validation enforced
- [x] Kernel core remains untouched
- [x] All tests pass

---

## 11. One-Line Summary for AI Coder

Implement Layer 6 extension system: PackDefinition + schema/template/routing registration + namespace isolation + compatibility validation. Keep kernel small and domain-agnostic.
