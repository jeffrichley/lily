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
  -> Skill Catalog Injection Layer
  -> Skill Retrieval Tool Layer
  -> Context Injection Layer
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
  skill_prompt_injector.py  # inject enabled skill catalog into system prompt
  skill_loader.py       # retrieval-only hydration of SKILL.md + linked references
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
  <skill_id>/
    SKILL.md
    references/            # optional linked guidance for the agent
    scripts/               # optional helper code (post-MVP in this repo)
    assets/                # optional templates/assets
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
- frontmatter parsed via `python-frontmatter` (safe YAML loading only; no executable YAML tags).

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
- MVP uses model-driven selection by skill `name` from the system-prompt catalog.
- `$skill:<id>` explicit invocation and deterministic implicit scoring are deferred/backlog.

### Eligibility filters (pre-tool invocation)

- enabled flag in the deterministic skill catalog
- retrieval-tool allow/deny constraints (not execution-mode constraints)

---

## 9. Progressive Disclosure Loader

### Load phases
- Phase A (catalog build / index time): load frontmatter-derived metadata only (for system-prompt catalog injection).
- Phase B (tool request time): hydrate full `SKILL.md` and optional linked `references/...` content.
- Phase C (context injection time): inject retrieved content into the agent context. (MVP does not materialize playbook/procedural/agent adapters.)

### Caching

- in-run cache keyed by `skill_id@version`.
- bounded size; LRU eviction acceptable.
- cache events emitted for hit/miss.

### Failure handling
- missing body for a requested skill name -> deterministic `SkillLoadError`.
- parse failure -> deterministic `SkillValidationError`.
- blocked by policy -> deterministic `SkillPolicyError`.

---

## 10. Retrieval and Context Injection Model

### MVP behavior (retrieval-only)
Execution path:
1. agent requests `SKILL.md` by skill `name` via the skills retrieval tool
2. tool hydrates full `SKILL.md` (and optionally linked `references/...`) from the skill directory
3. retrieved content is injected into the agent context for the next reasoning/tool-calling step
4. continue normal runtime tool-calling loop

Invariant:
- MVP skills have no autonomous execution modes; they provide content/context only.

### Deferred (backlog)
- Playbook/procedural/agent execution adapters and delegated subagent runtime behavior are deferred until after retrieval-only MVP is validated.

---

## 11. Policy, Security, and Safety

### Policy layers

1. Global runtime policies (existing)
2. Skill-level enablement and allow/deny
3. Retrieval-tool policy checks (content return + linked-file constraints)
4. Optional approval gates for sensitive skills

### Safety controls

- denylist precedence over retrieval requests.
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
  - tool-calling paths that depend on disallowed tools fail fast with deterministic `SkillPolicyError`;
  - content retrieval/injection may still be allowed (MVP retrieval-only).

Invariants:
- skill metadata can only restrict tool access; it cannot expand tool access beyond runtime policy.
- retrieval requests do not bypass tool policy resolution.
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
- requested skill names and versions
- source path and scope
- policy decisions applied
- retrieval mode and result

---

## 12. Observability and Telemetry

### Event taxonomy

```text
skill_discovered
skill_shadowed
skill_requested
skill_load_started
skill_loaded
skill_failed
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
- retrieval-by-name correctness (including missing/disabled skill and linked-file errors)
- policy filter correctness
- progressive loader cache behavior

### Integration tests
- tool-based retrieval by skill `name` hydrates full `SKILL.md` and linked `references/...`
- context injection correctness (retrieved content is available to the agent for subsequent reasoning)
- policy blocks and error messaging for retrieval + linked-file constraints
- tool allowlist preservation with retrieval tool

### E2E tests

- CLI `lily run` where the agent requests a known skill by `name` (retrieval-only MVP smoke path)
- CLI/TUI retrieval smoke path for system-prompt catalog injection -> tool request -> content hydration
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

1. create a skill directory containing required `SKILL.md` under a configured skill root
2. author `SKILL.md` with `name` + `description` frontmatter and clear usage guidance
3. optionally include linked guidance/docs under `references/...` for on-demand retrieval
4. run `lily skills doctor` (or equivalent) for validation

### Engineering workflow

1. implement parser and schema models (use `python-frontmatter` for YAML frontmatter extraction).
2. implement discovery + precedence resolver.
3. implement system-prompt skill catalog injection (frontmatter-only).
4. implement retrieval tool (by skill `name`) with linked-file hydration.
5. wire policy checks and event emission for retrieval/loading.
6. add CLI inspect/list tooling.
7. add unit/integration/e2e tests.

### Release workflow

1. phase-gate on deterministic tests and warning-clean runs.
2. update roadmap/status surfaces for SI-007 progress.
3. ship behind default-safe config if needed.

---

## 15. GoF Patterns

This section maps Gang of Four patterns to concrete Lily skills components.

### 15.1 Strategy

Use case:
- multiple system-prompt skill catalog formatting/injection strategies without rewriting the prompt injection flow.

Mapping:
- `SkillCatalogInjectionStrategy` interface
- `DeterministicCatalogInjectionStrategy` (MVP)
- `SemanticRe-rankingStrategy` (post-MVP)

Benefit:
- easy swap/extension of catalog injection/formatting behavior.

### 15.2 Abstract Factory

Use case:
- create retrieval/injection adapters with consistent interfaces.

Mapping:
- `SkillInjectionAdapterFactory`
  - `SkillMarkdownInjectionAdapter`
  - `SkillReferenceFileInjectionAdapter`

Benefit:
- type-safe construction and centralized policy wiring for retrieval/injection.

### 15.3 Builder

Use case:
- build complex retrieved-skill content in stages (summary -> hydrated -> injected).

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
- staged filters for retrieval eligibility and safety before hydration/injection.

Mapping:
- `EnabledFilter -> AgentAllowlistFilter -> DenylistFilter -> CapabilityFilter`

Benefit:
- composable, testable policy chain.

### 15.8 Template Method

Use case:
- standard retrieval request flow with controlled validation and deterministic hydration/injection.

Mapping:
- base retrieval request workflow:
  - normalize prompt / identify requested skill name
  - validate requested skill against catalog + policy
  - hydrate `SKILL.md` (and linked `references/...` if requested)
  - inject retrieved content into context
  - emit retrieval diagnostics

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

