# PRD

# Lily Skills System (SI-007)

**Author:** AI Engineering (Codex session)
**Audience:** Product + Engineering
**Status:** Draft v1
**Date:** 2026-03-06
**Roadmap Traceability:** SI-007

---

## 1. Executive Summary

Lily currently has a completed tool registry foundation (SI-002): config-defined Python/MCP tools, allowlist policy, deterministic runtime wiring, and YAML/TOML parity. What is missing is a first-class skills system that lets Lily package reusable expertise, select the right skill for a task, load only relevant detail, and execute reliably without context bloat.

Across OpenAI Codex skills guidance, LangChain skills guidance, and Anthropic skills guidance, the ecosystem has converged on a practical model: `SKILL.md`-centered skill packages, progressive disclosure, explicit/implicit invocation, and clear separation of concerns between skills, tools, and subagents. This PRD defines Lily's MVP implementation of that model.

MVP goal: deliver a production-usable skills layer that can discover skill packages, select skills deterministically, inject playbook context safely, execute procedural/agent-style skills through existing runtime boundaries, and expose auditable behavior for operators.

---

## 2. Mission

Build a standards-aligned, implementation-ready skills system that increases task quality and reuse while preserving Lily's runtime safety and deterministic operating posture.

Core principles:

1. Skills encode reusable competence; tools provide execution capability.
2. Skills load progressively (summary first, full detail on selection) to control context growth.
3. Skills must be explicit artifacts (`SKILL.md` package contract), not hidden prompts.
4. Skill selection must be inspectable and policy-governed (deterministic tie-breaks, allowlists).
5. Skills and subagents are complementary: skills for reusable expertise, subagents for independent execution contexts.

---

## 3. Target Users

### Primary personas

1. Lily operator (primary)
- Technical comfort: intermediate to advanced CLI/TOML/YAML.
- Needs: add capabilities fast, keep behavior deterministic, avoid context explosion.

2. Skill author (primary)
- Technical comfort: ranges from prompt engineer to Python developer.
- Needs: define a skill package once and reuse it across tasks.

3. Runtime reviewer/governance owner (secondary)
- Technical comfort: advanced.
- Needs: verify policy boundaries, inspect what loaded and why, audit outcomes.

### Key pain points addressed

- Repeated instructions across sessions.
- Overly large default prompts and diluted model behavior.
- No reusable package format for domain expertise.
- Lack of explicit routing between "use a skill" vs "call subagent" vs "call tool directly".

---

## 4. MVP Scope

### In Scope

#### Core functionality
- ✅ Skill package contract with required `SKILL.md` and YAML frontmatter.
- ✅ Local skill discovery from configured skill roots.
- ✅ Skill indexing and deterministic selection pipeline.
- ✅ Progressive disclosure loading model (summary index + full body on select).
- ✅ Explicit invocation (`$skill`-style) and implicit invocation (description match).
- ✅ Skill execution types:
  - ✅ Playbook skills (instruction/context injection)
  - ✅ Procedural skills (deterministic wrapper tools)
  - ✅ Agent skills (delegation wrappers with independent runtime boundary)

#### Technical and policy
- ✅ Config surfaces for skill roots, enabled scopes, and precedence order.
- ✅ Deterministic collision policy and tie-break rules.
- ✅ Skill-level policy controls (enabled/disabled, allowed agents, allowed tools).
- ✅ Structured skill telemetry (selection reason, load path, result status).

#### Integration
- ✅ Integrate with existing tool registry boundary (`tools.*`) and runtime allowlist (`agent.*`).
- ✅ Integrate with existing runtime policies (`max_iterations`, tool/model call limits).
- ✅ CLI visibility surface for skill discovery/list/selection traces.

#### Validation
- ✅ Unit tests for parsing, discovery, scoring, conflict handling.
- ✅ Integration tests for runtime invocation and policy boundaries.
- ✅ E2E smoke paths from CLI/TUI for explicit and implicit skill usage.

### Out of Scope

#### Core functionality
- ❌ Autonomous skill generation/evolution loops.
- ❌ Automatic skill pruning/promotion RL system.
- ❌ Embeddings/vector DB dependency as MVP requirement.

#### Technical and integration
- ❌ Cross-repo remote skill installation marketplace as MVP requirement.
- ❌ Full enterprise tenancy/auth model for skill distribution.
- ❌ Broad remote package manager integration beyond local configured roots.

#### Deployment and governance
- ❌ Org-wide remote signing service for skills (future hardening).
- ❌ Auto-migration of archived historical skill assets.

---

## 5. User Stories

1. As a Lily operator, I want to add a new skill by dropping a folder with `SKILL.md`, so that I can add behavior without changing runtime code.
Example: add `skills/playbooks/literature_review/SKILL.md` and have Lily discover it.

2. As a Lily operator, I want the runtime to load only skill summaries until needed, so that token usage stays bounded.
Example: 200 skills installed, only the matched skill body is injected.

3. As a skill author, I want explicit invocation syntax, so that I can force a specific skill when needed.
Example: `$skill:literature_review` in prompt.

4. As a skill author, I want implicit invocation by description match, so that skills can be used naturally without remembering exact IDs.
Example: "do a literature review" routes to the review skill.

5. As a governance owner, I want deterministic collision and precedence rules, so that behavior is auditable.
Example: same skill ID in two scopes resolves by configured precedence and logs the winner.

6. As a runtime reviewer, I want selection rationale in logs, so that I can debug why a skill was chosen.
Example: match score, tie-break path, disabled-policy filters.

7. As an engineer, I want skills/subagents/tools clearly separated, so that system design remains maintainable.
Example: procedural skill wraps deterministic pipeline tool; subagent runs isolated policy set.

8. As a maintainer, I want compatibility with current tool registry and policy surfaces, so that SI-007 can ship incrementally without destabilizing SI-002.

---

## 6. Core Architecture and Patterns

### High-level architecture

```text
User Prompt
  -> Skill Selector
  -> Skill Loader (progressive disclosure)
  -> Runtime Binding
     -> Playbook injection and/or
     -> Procedural tool wrapper and/or
     -> Agent-skill wrapper (delegated runtime)
  -> Existing Tool Registry + Policy middleware
```

### Core pattern decisions

- Skill package contract: directory + `SKILL.md` + optional assets, aligned with OpenAI/LangChain/Anthropic patterns.
- Progressive disclosure: metadata/summary index first; full content only on selection.
- Routing hierarchy: explicit invocation > policy-eligible exact match > scored implicit match > no-skill fallback.
- Boundary rule: skills do not replace tools/MCP; they orchestrate/reuse them.
- Subagent rule: use subagent skill only when independent execution context is required.

### Repository target surfaces (MVP)

```text
.lily/
  skills/
    playbooks/<skill_id>/SKILL.md
    procedures/<skill_id>.py
    agents/<skill_id>.py

src/lily/runtime/
  skill_catalog.py
  skill_registry.py
  skill_selector.py
  skill_loader.py
  skill_policies.py
  skill_types.py
```

---

## 7. Tools/Features

### F1. Skill package specification

- Required artifact: `SKILL.md`.
- Required frontmatter fields: `name`, `description`.
- Optional frontmatter fields (guide-aligned): `license`, `compatibility`, `allowed-tools`, `metadata`.
- Optional artifacts: `scripts/`, `references/`, `assets/`.

Naming and compatibility policy:
- Canonical authoring recommendation: `name` should be kebab-case and should match folder name.
- Runtime compatibility behavior: parser accepts non-canonical imported names but normalizes to an internal canonical key for indexing/matching.
- Normalization is internal-only; original author-facing `name` is preserved in loaded metadata.
- `SKILL.md` filename is exact/case-sensitive; no in-skill `README.md` (keep docs in `SKILL.md` and `references/`).

Acceptance:
- deterministic parse failures with field-specific errors.

### F2. Discovery and indexing

- Discover from configured skill roots and enabled scopes.
- Build normalized index with summary fields for fast matching.
- Enforce deterministic precedence and collision handling.

Acceptance:
- duplicate IDs resolved by configured precedence with warning/event.

### F3. Selection and routing

- Explicit routing via invocation keyword.
- Implicit routing via deterministic scoring on description/tags/examples.
- Hard policy filters before ranking.

Acceptance:
- selection rationale emitted in logs/trace.

### F4. Progressive disclosure loader

- Load summary at startup/index build.
- Load full `SKILL.md` (and optional assets) only when selected.
- Cache loaded skills for the active run with bounded memory policy.

Acceptance:
- measurable token/context reduction in benchmark prompts.

### F5. Execution bindings by skill type

- Playbook skill: inject structured instructions into next reasoning step.
- Procedural skill: call deterministic tool wrapper.
- Agent skill: invoke delegated mini-agent runtime with restricted tool/policy set.

Acceptance:
- all three modes validated by unit + integration tests.

### F6. Governance and controls

- Enable/disable by scope or skill ID.
- Agent-level skill allowlist/denylist.
- Optional manual-approval gates for high-risk skills.

Tool-access resolution policy (normative):
- Runtime boundary remains authoritative: skills cannot grant access to tools outside `agent.* tools.allowlist` and global runtime policies.
- If `allowed-tools` is omitted in skill frontmatter: apply no additional skill-level restriction (skill inherits runtime-available tools).
- If `allowed-tools` is present: effective tools are `intersection(runtime_available_tools, skill_allowed_tools)`.
- If `allowed-tools` resolves to an empty effective set: skill may still load for playbook-only behavior, but any tool-calling path must fail fast with deterministic policy error messaging.

Acceptance:
- blocked skills cannot be invoked implicitly or explicitly.

### F7. Observability

- Emit structured events:
  - `skill_discovered`
  - `skill_selected`
  - `skill_loaded`
  - `skill_executed`
  - `skill_failed`
- Include source path, version, selection reason, execution mode, latency.

Acceptance:
- deterministic event schema with warning-clean test output.

---

## 8. Technology Stack

### Existing stack leveraged

- Python runtime in `src/lily`
- Pydantic validation patterns
- YAML/TOML config loaders
- LangChain/LangGraph runtime and tool middleware
- Rich/Textual CLI surfaces

### Proposed additions (MVP-friendly)

- No mandatory external DB/search service required for MVP.
- Deterministic lexical scoring baseline; optional embeddings in post-MVP.
- Reuse existing config and policy schema strategy.

### Third-party integration posture

- Tools remain sourced from Python and MCP via existing SI-002 interfaces.
- Skills layer references these capabilities and does not duplicate resolver logic.

---

## 9. Security and Configuration

### Security scope (MVP in scope)

- Validate skill metadata and reject unknown required-contract violations.
- Enforce skill allowlist/denylist and execution policy boundaries.
- Restrict agent-skill delegation through explicit policy and max-call limits.
- Log and surface unsafe/blocked invocation attempts.
- Enforce frontmatter security restrictions aligned with the guide:
  - reject XML angle brackets (`<` and `>`) in frontmatter values;
  - reject reserved provider prefixes in skill `name` (`claude*`, `anthropic*`);
  - parse YAML with safe loading only (no executable YAML tags).

### Security out of scope (post-MVP)

- Skill package signing and attestation pipeline.
- Centralized trust-store service for remote skill artifacts.

### Configuration surfaces (proposed)

Agent config (`agent.yaml`/`agent.toml`):
- `skills.enabled`
- `skills.roots`
- `skills.scopes_precedence`
- `skills.allowlist` / `skills.denylist`
- `skills.implicit_selection.enabled`
- `skills.selection.max_candidates`
- `skills.tools.default_policy` (`inherit_runtime` | `deny_unless_allowed` | `use_default_packs`)
- `skills.tools.default_packs` (list of named pack IDs)
- `skills.tools.packs` (map of pack ID -> ordered tool ID list)

Optional skill catalog (`skills.yaml`/`skills.toml`) for explicit registrations.

Tool-policy mode semantics:
- `inherit_runtime`:
  - if skill omits `allowed-tools`, skill inherits runtime-available tools.
- `deny_unless_allowed`:
  - if skill omits `allowed-tools`, skill has no tool access (playbook-only behavior still allowed).
- `use_default_packs`:
  - if skill omits `allowed-tools`, effective tools come from union of configured `default_packs`.

Precedence and safety:
- Runtime boundary remains authoritative; skills cannot grant tools outside runtime policy.
- Effective skill tools are always intersected with runtime-available tools.
- If both `allowed-tools` and default packs are present for one skill, explicit `allowed-tools` wins.

Example config (YAML):
```yaml
skills:
  enabled: true
  roots:
    - .lily/skills
  scopes_precedence: [repository, user, system]
  tools:
    default_policy: use_default_packs
    default_packs: [core-research, docs-safe]
    packs:
      core-research:
        - web_search
        - web_fetch
      docs-safe:
        - read_file
        - rg
```

Example config (TOML):
```toml
[skills]
enabled = true
roots = [".lily/skills"]
scopes_precedence = ["repository", "user", "system"]

[skills.tools]
default_policy = "use_default_packs"
default_packs = ["core-research", "docs-safe"]

[skills.tools.packs]
core-research = ["web_search", "web_fetch"]
docs-safe = ["read_file", "rg"]
```

---

## 10. API Specification (Runtime Interfaces)

### Internal interfaces

```python
class SkillSummary(BaseModel):
    id: str
    name: str
    description: str
    type: Literal["playbook", "procedural", "agent"]
    tags: list[str]
    version: str
    source_path: str

class SkillRegistry:
    def discover(self, roots: list[str]) -> list[SkillSummary]: ...
    def get(self, skill_id: str) -> SkillSummary: ...

class SkillSelector:
    def select(self, prompt: str, candidates: list[SkillSummary]) -> list[SkillSummary]: ...

class SkillLoader:
    def load(self, skill_id: str) -> "LoadedSkill": ...
```

### CLI surface candidates

- `lily skills list`
- `lily skills inspect <skill_id>`
- `lily skills doctor`

---

## 11. Success Criteria

### MVP success definition

A user can author/discover/select/execute skills with deterministic behavior and policy controls, while maintaining compatibility with the existing runtime and tool registry.

### Functional requirements

- ✅ Skill package parsing and validation are deterministic.
- ✅ Discovery and selection work for explicit and implicit routes.
- ✅ Progressive disclosure behavior is implemented and measurable.
- ✅ Playbook/procedural/agent skill types execute through defined boundaries.
- ✅ Policy controls reliably block disallowed skills.
- ✅ Observability captures selection reason and execution outcome.

### Quality indicators

- ✅ `just docs-check` and `just status` pass after documentation changes.
- ✅ Unit/integration/e2e coverage for new skills runtime surfaces.
- ✅ No warning regressions in quality/test gates.

### User experience goals

- Skill authoring should feel lightweight and repeatable.
- Operators should understand selection outcomes without reading code.

---

## 12. Implementation Phases

### Phase 1: Contracts and schema

Goal: define skill package and runtime contracts.

Deliverables:
- ✅ Skill metadata schema and parser contract.
- ✅ Deterministic validation error taxonomy.
- ✅ Config schema additions for skills policy.

Validation:
- parser/unit tests for success/failure matrices.

### Phase 2: Discovery, indexing, and selection

Goal: make skills discoverable and selectable deterministically.

Deliverables:
- ✅ Skill registry discovery/indexing implementation.
- ✅ Selection/ranking with deterministic tie-breaks.
- ✅ Explicit invocation precedence.

Validation:
- unit tests for precedence, collision, and ranking behavior.

### Phase 3: Runtime execution integration

Goal: integrate skill loading and execution into existing runtime.

Deliverables:
- ✅ Progressive disclosure loader.
- ✅ Playbook/procedural/agent skill execution adapters.
- ✅ Policy gate enforcement and events.

Validation:
- integration tests against runtime/tool registry boundaries.

### Phase 4: UX and hardening

Goal: operationalize and validate end-to-end.

Deliverables:
- ✅ CLI inspect/list surfaces.
- ✅ telemetry/event documentation.
- ✅ e2e validation scenarios and docs updates.

Validation:
- e2e tests + quality gates.

Estimated timeline (engineering weeks):
- Phase 1: 1 week
- Phase 2: 1-2 weeks
- Phase 3: 1-2 weeks
- Phase 4: 1 week

---

## 13. Future Considerations

- Embedding-assisted semantic skill search and re-ranking.
- Skill effectiveness scoring and promotion workflows.
- Remote skill package distribution with provenance checks.
- Automated extraction of candidate skills from execution traces.
- Distribution/packaging follow-up:
  - zip/package validation and import/export workflow for skill bundles;
  - compatibility profile for cross-platform skill portability;
  - API-managed skill lifecycle and version rollout strategy;
  - organization-wide publishing/update/governance controls.

---

## 14. Risks and Mitigations

1. Risk: Ambiguous skill matching causes unstable behavior.
- Mitigation: deterministic routing order, explicit invocation precedence, full selection trace.

2. Risk: Skills bypass policy boundaries and call unsafe capabilities.
- Mitigation: enforce runtime allowlist and policy middleware before execution.

3. Risk: Context inflation from loading many skill bodies.
- Mitigation: progressive disclosure and bounded in-run cache.

4. Risk: Conceptual overlap between skills and subagents creates design drift.
- Mitigation: hard decision matrix and type-specific contracts.

5. Risk: Authoring quality variance makes skills brittle.
- Mitigation: skill templates, lint checks, and validation tooling.

---

## 15. Appendix

### A. External standards references (primary)

- OpenAI Codex Skills: https://developers.openai.com/codex/skills
- LangChain Multi-agent Skills: https://docs.langchain.com/oss/python/langchain/multi-agent/skills
- LangChain Multi-agent Overview: https://docs.langchain.com/oss/python/langchain/multi-agent
- LangChain Subagents: https://docs.langchain.com/oss/python/langchain/multi-agent/subagents
- LangChain Deep Agents Skills: https://docs.langchain.com/oss/python/deepagents/skills
- Anthropic Skills Explained: https://claude.com/blog/skills-explained
- Anthropic Introducing Agent Skills: https://claude.com/blog/skills
- Agent Skills Specification: https://agentskills.io/specification
- Agent Skills Support Guide: https://agentskills.io/adding-skills-support

### B. Local Lily references

- Roadmap SI-007: `docs/dev/roadmap.md`
- Runtime boundaries: `docs/dev/references/runtime-config-and-interfaces.md`
- Skill ideas: `docs/ideas/reboot.md`, `docs/ideas/tool_registries.md`

### C. Key assumptions

- Assumption 1: SI-007 ships incrementally on top of existing SI-002 runtime/tool infrastructure.
- Assumption 2: MVP starts with deterministic lexical selection before any vector dependency.
- Assumption 3: Skill package roots remain local filesystem paths for MVP.

