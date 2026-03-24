# SKILLS_ARCHITECTURE

# Lily Skills Architecture (SI-007)

**Author:** AI Engineering (Codex session)
**Audience:** Engineers implementing skills runtime and tooling
**Status:** Draft v1
**Date:** 2026-03-06

---

## 1. Purpose

Define an implementation-grade architecture for Lily's first-class skills system, aligned to external standards and Lily's existing runtime boundaries.

This document describes:
- the skill package contract
- discovery/index/selection/load/execute lifecycle
- component boundaries and interfaces
- policy and security controls
- observability and testing
- GoF pattern mapping for maintainable implementation

---

## 2. Standards Baseline

### External alignment targets

1. OpenAI Codex skills model
- `SKILL.md`-centered packages with optional resources/scripts.
- Explicit and implicit invocation.
- Progressive disclosure loading.

2. LangChain skills model
- Skills as prompt-driven specializations (single-agent and deep agents patterns).
- Directory-based skills and source precedence.
- Skills and subagents as separate but composable patterns.

3. Anthropic skills guidance
- Skills as reusable expertise units.
- Skills vs subagents vs MCP separation of concerns.

4. Agent Skills open specification
- Portable package metadata and `SKILL.md` conventions.
- Interop-minded support model.

### Lily compatibility constraints

- Must integrate with current `agent.*` + `tools.*` runtime contracts.
- Must preserve existing tool allowlist and runtime policy gates.
- Must not assume autonomous skill evolution in MVP.

---

## 3. Scope and Non-Goals

### In-scope architecture (MVP)

- Skill package parsing and validation.
- Local discovery, indexing, selection, and progressive loading.
- Skill execution adapters for playbook/procedural/agent modes.
- Policy enforcement and structured events.

### Out-of-scope architecture (post-MVP)

- Autonomous skill generation, promotion, pruning.
- Distributed signed package registry.
- Mandatory semantic/vector retrieval infrastructure.

---

## 4. Vocabulary and Domain Model

### Definitions

- Skill: reusable capability package selected for a task.
- Playbook skill: instruction/context module.
- Procedural skill: deterministic executable workflow wrapper.
- Agent skill: delegated subagent wrapper with isolated runtime context.
- Skill summary: minimal metadata loaded for matching.
- Loaded skill: full skill body and assets hydrated at execution time.

### Canonical type enum

```python
SkillType = Literal["playbook", "procedural", "agent"]
```

---

## 5. Architecture Overview

### Layered design

```text
Prompt Ingress
  -> Skill Selection Layer
  -> Skill Loading Layer
  -> Skill Execution Layer
  -> Existing Tool + Runtime Layer
  -> External Systems (Python tools, MCP tools, files, APIs)
```

### Component map

```text
src/lily/runtime/
  skill_types.py        # models + enums
  skill_catalog.py      # parse/validate package metadata
  skill_discovery.py    # filesystem discovery by roots/scopes
  skill_registry.py     # indexed summaries + collision resolution
  skill_selector.py     # routing and ranking
  skill_loader.py       # progressive disclosure hydration
  skill_executor.py     # playbook/procedural/agent execution adapters
  skill_policies.py     # allow/deny + safety gates
  skill_events.py       # event schema + emit helpers
```

### Sidecar CLI surfaces

```text
src/lily/commands/handlers/
  skills_list.py
  skills_inspect.py
  skills_doctor.py
```

---

## 6. Skill Package Contract

### Directory forms

```text
.lily/skills/
  playbooks/<skill_id>/
    SKILL.md
    examples.md            # optional
    references/            # optional
  procedures/<skill_id>.py
  agents/<skill_id>.py
```

Critical packaging rules (guide-aligned):
- `SKILL.md` filename is exact and case-sensitive.
- Skill folder naming recommendation is kebab-case (portability-friendly baseline).
- Do not place `README.md` inside a skill folder; keep skill docs in `SKILL.md` and `references/`.

### `SKILL.md` contract

Required:
- title/name
- purpose/goal
- description (for matching)
- trigger cues
- execution guidance

Recommended:
- examples
- guardrails/non-goals
- success criteria
- references

### Metadata/frontmatter contract

```yaml
name: literature-review
description: Structured synthesis workflow for papers. Use when user asks for literature review or related-work synthesis.
license: MIT
compatibility: Claude Code / local Lily runtime with MCP enabled
allowed-tools: "Bash(python:*) WebFetch"
metadata:
  author: Team
  version: 0.1.0
  mcp-server: arxiv
  tags: [research, synthesis, papers]
```

Validation rules:
- required frontmatter keys are only `name` and `description`.
- `name` authoring recommendation: kebab-case and folder-aligned.
- parser accepts non-canonical imported names, then normalizes to an internal canonical key for index/matching.
- `description` must include both WHAT the skill does and WHEN to use it (trigger guidance).
- `description` max length: 1024 chars.
- unknown required-contract violations fail fast with field-specific errors.
- safe YAML parsing only (no executable YAML tags).

---

## 7. Discovery and Precedence

### Skill roots and scopes

Proposed scope order (configurable):
1. repository
2. user
3. system

### Discovery algorithm

1. enumerate roots by configured precedence
2. discover candidate skill packages/files
3. parse summary metadata
4. apply schema validation
5. resolve collisions by precedence and version policy
6. emit `skill_discovered` / `skill_shadowed`

### Collision policy (MVP default)

- primary rule: scope precedence wins.
- tie-break within same scope: highest semantic version.
- deterministic fallback: lexical `id` + path.

---

## 8. Selection and Routing

### Routing order

1. explicit invocation (`$skill:<id>`) when present
2. exact normalized-key or alias match
3. implicit scoring match (description + tags + trigger cues)
4. no-skill fallback to normal runtime path

### Eligibility filters (pre-ranking)

- enabled flag
- agent allowlist
- policy denylist
- environment/runtime constraints

### Deterministic scoring baseline

MVP baseline:
- weighted lexical overlap across prompt and skill fields
- trigger phrase boost
- recent-success tie-break optional

No vector dependency required for MVP.

### Selection output model

```python
class SkillSelection(BaseModel):
    selected_ids: list[str]
    rationale: str
    candidate_scores: list[tuple[str, float]]
    mode: Literal["explicit", "implicit", "none"]
```

---

## 9. Progressive Disclosure Loader

### Load phases

- Phase A (index time): load summary metadata only.
- Phase B (selection time): hydrate full `SKILL.md` and optional assets.
- Phase C (execution time): materialize adapters/wrappers.

### Caching

- in-run cache keyed by `skill_id@version`.
- bounded size; LRU eviction acceptable.
- cache events emitted for hit/miss.

### Failure handling

- missing body after summary selection -> deterministic `SkillLoadError`.
- parse failure -> deterministic `SkillValidationError`.
- blocked by policy -> deterministic `SkillPolicyError`.

---

## 10. Execution Model by Skill Type

### 10.1 Playbook skills

Execution path:
1. load skill text
2. convert to bounded context block
3. inject into next reasoning turn
4. continue normal tool-calling loop

Invariant:
- playbook skill does not execute side effects directly.

### 10.2 Procedural skills

Execution path:
1. resolve wrapper callable
2. validate input schema
3. execute deterministic pipeline
4. return structured output

Invariant:
- procedural skill side effects must remain policy-gated and auditable.

### 10.3 Agent skills

Execution path:
1. resolve delegated agent wrapper
2. create restricted runtime context (tool/policy subset)
3. execute with bounded iteration/call limits
4. return summarized artifacts/outcome

Invariant:
- delegated context isolation must be explicit.

---

## 11. Policy, Security, and Safety

### Policy layers

1. Global runtime policies (existing)
2. Skill-level enablement and allow/deny
3. Execution-mode policy checks (playbook/procedural/agent)
4. Optional approval gates for sensitive skills

### Safety controls

- explicit denylist precedence over explicit invocation.
- restricted tool allowlist per skill (optional but recommended).
- schema validation before execution.
- refusal path for blocked skills with actionable diagnostics.
- frontmatter content restrictions:
  - reject XML angle brackets (`<` and `>`) in frontmatter values;
  - reject reserved provider prefixes in `name` (`claude*`, `anthropic*`).

### Tool access resolution (normative)

Config inputs (agent config):
- `skills.tools.default_policy`: `inherit_runtime` | `deny_unless_allowed` | `use_default_packs`
- `skills.tools.default_packs`: list of pack IDs
- `skills.tools.packs`: mapping of pack ID -> ordered tool ID list

Resolution algorithm:
1. Start with `runtime_available_tools` from existing runtime/tool registry policy boundaries.
2. Resolve skill candidate set:
   - if skill defines `allowed-tools`: `skill_candidate_tools = allowed-tools` (explicit wins)
   - else if policy is `inherit_runtime`: `skill_candidate_tools = runtime_available_tools`
   - else if policy is `deny_unless_allowed`: `skill_candidate_tools = []`
   - else if policy is `use_default_packs`: `skill_candidate_tools = union(default_packs[*])`
3. Compute effective tools:
   - `effective_tools = runtime_available_tools ∩ skill_candidate_tools`
4. If `effective_tools` is empty:
   - playbook-only execution remains allowed;
   - any procedural/agent/tool-call path fails fast with deterministic `SkillPolicyError`.

Invariants:
- skill metadata can only restrict tool access; it cannot expand tool access beyond runtime policy.
- explicit invocation does not bypass tool policy resolution.
- unknown pack IDs or unknown tools in packs fail fast at config-validation time.

Reference config shapes:

YAML:
```yaml
skills:
  tools:
    default_policy: deny_unless_allowed
    default_packs: [safe-readonly]
    packs:
      safe-readonly:
        - read_file
        - rg
        - web_fetch
```

TOML:
```toml
[skills.tools]
default_policy = "deny_unless_allowed"
default_packs = ["safe-readonly"]

[skills.tools.packs]
safe-readonly = ["read_file", "rg", "web_fetch"]
```

### Frontmatter optional fields (guide-aligned)

- `license`
- `compatibility`
- `allowed-tools`
- `metadata` (custom key-values such as author/version/mcp-server/tags/documentation/support)

### Provenance and audit

Each execution trace includes:
- selected skill IDs and versions
- source path and scope
- policy decisions applied
- execution mode and result

---

## 12. Observability and Telemetry

### Event taxonomy

```text
skill_discovered
skill_shadowed
skill_selected
skill_load_started
skill_loaded
skill_execution_started
skill_execution_completed
skill_execution_failed
```

### Minimum event payload

```python
class SkillEvent(BaseModel):
    event: str
    skill_id: str | None
    version: str | None
    scope: str | None
    mode: str | None
    reason: str | None
    latency_ms: int | None
    success: bool | None
```

### Operator-facing outputs

- `lily skills list` for inventory.
- `lily skills inspect <id>` for metadata and policy status.
- runtime trace snippets in CLI/TUI debug surfaces.

---

## 13. Test Architecture

### Unit tests

- metadata parsing and validation matrix
- collision and precedence behavior
- ranking and tie-break determinism
- policy filter correctness
- progressive loader cache behavior

### Integration tests

- explicit and implicit selection through runtime
- playbook/procedural/agent mode execution
- policy blocks and error messaging
- tool allowlist preservation with skill wrappers

### E2E tests

- CLI `lily run` with explicit skill invocation
- CLI/TUI implicit skill routing smoke path
- operator commands (`skills list`, `skills inspect`) output sanity

### Gate expectations

- `just lint`
- `just format-check`
- `just types`
- `just test`
- final: `just quality && just test`

---

## 14. Implementation Blueprint (How Skills Are Made)

### Author workflow

1. choose skill type (`playbook`, `procedural`, `agent`).
2. create package/file under `.lily/skills/...`.
3. author `SKILL.md` with clear triggers, goal, guardrails.
4. add metadata/frontmatter and examples.
5. run `lily skills doctor` (or equivalent) for validation.
6. run tests for discovery/selection/execution paths.

### Engineering workflow

1. implement parser and schema models.
2. implement discovery + precedence resolver.
3. implement selector and routing contracts.
4. implement loader with progressive disclosure.
5. implement mode-specific executors.
6. wire policy checks and event emission.
7. add CLI inspect/list tooling.
8. add unit/integration/e2e tests.

### Release workflow

1. phase-gate on deterministic tests and warning-clean runs.
2. update roadmap/status surfaces for SI-007 progress.
3. ship behind default-safe config if needed.

---

## 15. GoF Patterns

This section maps Gang of Four patterns to concrete Lily skills components.

### 15.1 Strategy

Use case:
- multiple selection/ranking algorithms without rewriting selector flow.

Mapping:
- `SkillScoringStrategy` interface
- `LexicalScoringStrategy` (MVP)
- `EmbeddingScoringStrategy` (future)

Benefit:
- easy swap/extension of ranking behavior.

### 15.2 Abstract Factory

Use case:
- create mode-specific executors with consistent interfaces.

Mapping:
- `SkillExecutorFactory`
  - `PlaybookExecutor`
  - `ProceduralExecutor`
  - `AgentExecutor`

Benefit:
- type-safe construction and centralized policy wiring.

### 15.3 Builder

Use case:
- build complex loaded-skill objects in stages (summary -> hydrated -> executable).

Mapping:
- `LoadedSkillBuilder` with steps:
  - `with_summary`
  - `with_body`
  - `with_assets`
  - `build`

Benefit:
- clearer lifecycle and fewer partially-initialized objects.

### 15.4 Adapter

Use case:
- normalize different skill execution primitives into runtime-compatible callables.

Mapping:
- `PlaybookAdapter` (text injection)
- `ProcedureAdapter` (callable wrapper)
- `AgentAdapter` (delegated runtime wrapper)

Benefit:
- uniform execution contract at runtime boundary.

### 15.5 Composite

Use case:
- represent skill bundles or hierarchical skills as one selectable unit.

Mapping:
- `SkillNode` interface
- `AtomicSkill`
- `SkillBundle`

Benefit:
- allows future hierarchical composition without selector rewrite.

### 15.6 Decorator

Use case:
- add observability, caching, or policy checks around executors.

Mapping:
- `TelemetryExecutorDecorator`
- `PolicyExecutorDecorator`
- `CachingLoaderDecorator`

Benefit:
- cross-cutting concerns added without modifying core executors.

### 15.7 Chain of Responsibility

Use case:
- staged filters for eligibility and safety before scoring.

Mapping:
- `EnabledFilter -> AgentAllowlistFilter -> DenylistFilter -> CapabilityFilter`

Benefit:
- composable, testable policy chain.

### 15.8 Template Method

Use case:
- standard selection flow with overridable scoring details.

Mapping:
- base selector workflow:
  - normalize prompt
  - filter candidates
  - score
  - tie-break
  - emit rationale

Benefit:
- strict deterministic flow with controlled extension points.

### 15.9 Command

Use case:
- treat skill executions as command objects for replay/audit.

Mapping:
- `SkillExecutionCommand` objects with `execute()` and serialized inputs.

Benefit:
- better auditability and optional replay tooling.

### 15.10 Observer

Use case:
- subscribe telemetry/reporting sinks to skill lifecycle events.

Mapping:
- event bus with listeners for logs, metrics, and debug UI.

Benefit:
- decoupled observability pipeline.

### 15.11 Facade

Use case:
- provide one entry point for runtime call sites.

Mapping:
- `SkillsRuntimeFacade.select_and_execute(prompt, context)`

Benefit:
- shields callers from internal subsystem complexity.

---

## 16. Decision Matrix: Skill vs Tool vs Subagent vs MCP

### Use a skill when

- reusable expertise or procedure should be packaged and selected repeatedly.
- context should load on demand.

### Use a tool when

- a direct deterministic operation is needed without additional reasoning scaffolding.

### Use a subagent when

- independent execution context, separate policies, or specialized internal loop is required.

### Use MCP when

- capability access comes from an external system/server protocol.

---

## 17. Migration Path from Current State

1. keep SI-002 tool registry unchanged as base capability layer.
2. add skills discovery/indexing modules in runtime package.
3. wire selection + loader into supervisor runtime.
4. add playbook/procedural/agent adapters incrementally.
5. add operator command surfaces.
6. add policies and telemetry hardening.

---

## 18. Open Questions

1. Should MVP support both frontmatter and sidecar metadata files, or frontmatter only?
2. Should agent-skill wrappers require explicit per-skill tool allowlists at launch?
3. What is the minimum operator UX for skill debugging in TUI?
4. Which tie-break signals are acceptable before adding embeddings?

---

## 20. Tight Delta Checklist (Guide Realignment)

Status legend:
- `[aligned]` complete in spec
- `[partial]` present but needs refinement
- `[missing]` not yet specified clearly

Contract and naming:
- `[aligned]` `SKILL.md` is required.
- `[aligned]` required frontmatter is only `name` + `description`.
- `[aligned]` kebab-case naming is recommended; normalization behavior is required via parser + `skills doctor` tests (planned in `.ai/PLANS/005-skills-system-implementation.md`, Phases 1 and 6).

Progressive disclosure and execution:
- `[aligned]` three-level load model is defined (summary, body, linked artifacts).
- `[aligned]` playbook/procedural/agent execution paths are defined.

Security guardrails:
- `[aligned]` angle-bracket rejection in frontmatter is explicit.
- `[aligned]` reserved provider prefixes (`claude*`, `anthropic*`) are blocked.
- `[aligned]` parser test matrix for malformed YAML/frontmatter edge cases is required in implementation plan (`.ai/PLANS/005-skills-system-implementation.md`, Phase 1).

Authoring and validation UX:
- `[aligned]` trigger-test templates (trigger/paraphrase/negative) are required in docs + `skills doctor` (`.ai/PLANS/005-skills-system-implementation.md`, Phase 6).
- `[aligned]` over-trigger/under-trigger remediation guidance is required in operator docs (`.ai/PLANS/005-skills-system-implementation.md`, Phase 6).

Distribution and packaging (future work):
- `[aligned]` zip/import-export package contract is tracked as post-MVP in `.ai/PLANS/005-skills-system-implementation.md` (Phase 9).
- `[aligned]` API-managed skill lifecycle/versioning is tracked as post-MVP in `.ai/PLANS/005-skills-system-implementation.md` (Phase 9).
- `[aligned]` org-level distribution, rollout, and governance surfaces are tracked as post-MVP in `.ai/PLANS/005-skills-system-implementation.md` (Phase 9).

---

## 19. Source References

- OpenAI Codex Skills: https://developers.openai.com/codex/skills
- LangChain Multi-agent Skills: https://docs.langchain.com/oss/python/langchain/multi-agent/skills
- LangChain Deep Agents Skills: https://docs.langchain.com/oss/python/deepagents/skills
- LangChain Multi-agent Overview: https://docs.langchain.com/oss/python/langchain/multi-agent
- LangChain Subagents: https://docs.langchain.com/oss/python/langchain/multi-agent/subagents
- Anthropic Skills Explained: https://claude.com/blog/skills-explained
- Anthropic Introducing Agent Skills: https://claude.com/blog/skills
- Agent Skills Specification: https://agentskills.io/specification
- Agent Skills Support Guide: https://agentskills.io/adding-skills-support

