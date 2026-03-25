# Feature: Skills System Full Implementation (PRD + Architecture)

The following plan should be complete, but it is important to validate documentation and codebase patterns and task sanity before starting implementation.

Pay special attention to existing runtime config contracts, deterministic policies, and strict typing/test gates.

## Feature Description

Implement the SI-007 skills system described in `.ai/SPECS/002-skills-system/PRD.md` and `.ai/SPECS/002-skills-system/SKILLS_ARCHITECTURE.md` on top of Lily's existing runtime/tool-registry foundation, starting with the retrieval-only MVP (skill catalog injection + tool-based `SKILL.md` retrieval by skill `name` + linked `references/...` hydration). Explicit `$skill:<id>` invocation and playbook/procedural/agent execution adapters are deferred.

## User Story

As a Lily operator and skill author  
I want a retrieval-only skills MVP where the agent can request a skill by `name` and receive the `SKILL.md` contents safely and deterministically  
So that Lily can reuse expertise safely, reduce prompt duplication, and keep runtime behavior auditable.

## Problem Statement

Lily currently has deterministic model/tool runtime wiring but lacks a production skills subsystem. Without this, capabilities are encoded ad hoc in prompts, reuse is poor, selection is not inspectable, and governance controls are fragmented.

## Solution Statement

Deliver a typed, policy-aware skills subsystem in `src/lily/runtime` with progressive disclosure loading and explicit integration into supervisor runtime/CLI surfaces. Implement in phased slices that preserve deterministic behavior and maintain warning-clean quality gates.

## Feature Metadata

**Feature Type**: New Capability  
**Estimated Complexity**: High  
**Primary Systems Affected**:
- `src/lily/runtime/` (new skills components + runtime integration)
- `src/lily/agents/lily_supervisor.py` and/or runtime orchestration surfaces
- `src/lily/cli.py` and new CLI handlers for skills visibility commands
- `.lily/config/*` schema contracts and sample config docs
- `tests/unit`, `tests/integration`, `tests/e2e` for skills coverage
- `docs/dev/*` status/roadmap updates when slices complete

**Dependencies**:
- Existing runtime config loader and tool registry contracts
- Pydantic validation and LangChain runtime boundaries already in repo
- `python-frontmatter` for parsing skill `SKILL.md` YAML frontmatter (add to `pyproject.toml` and refresh the lockfile with `uv lock` / `uv sync` before Phase 1 parser work lands)

## Traceability Mapping (Required When Applicable)

- Roadmap system improvements: `SI-007`
- Debt items: `None`
- Debt to roadmap linkage (if debt exists): `N/A`

## Branch Setup (Required)

Branch naming must follow the plan filename:
- Plan: `.ai/PLANS/005-skills-system-implementation.md`
- Branch: `feat/005-skills-system-implementation`

Commands (must be executable as written):
```bash
PLAN_FILE=".ai/PLANS/005-skills-system-implementation.md"
PLAN_SLUG="$(basename "$PLAN_FILE" .md)"
BRANCH_NAME="feat/${PLAN_SLUG}"
git show-ref --verify --quiet "refs/heads/${BRANCH_NAME}" \
  && git switch "${BRANCH_NAME}" \
  || git switch -c "${BRANCH_NAME}"
```

---

## Definition of Visible Done

A reviewer can directly verify the skills system via:

- Running `uv run lily skills list --config .lily/config/agent.toml` and seeing structured tabular output.
- Running `uv run lily skills inspect <skill_name> --config ...` and seeing metadata plus **catalog placement** and **retrieval policy** details (allow/deny, shadowing, collisions). MVP does **not** include implicit auto-selection; the agent chooses a skill by `name` via the retrieval tool.
- Running `uv run lily run --prompt 'use the brand-guidelines skill to apply Anthropic branding guidance ...' --config ...` and observing that the agent requested the `brand-guidelines` skill via the retrieval tool.
- Inspecting emitted structured events/log entries for catalog injection + skill retrieval/loading outcomes.

## MVP scope traceability (PRD to phase)

Single-thread execution order: **Phase 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8** (Phase 9 is post-MVP). Tool wiring (**`tools.toml` definition → Python tool → `tools.allowlist`**) spans **3–5**; do not merge Phase 5 before Phases 3–4 have retrieval + policy tests.

| PRD / architecture slice | Phase(s) | Deliverable |
|----------------------------|----------|-------------|
| F1 Skill package contract | 1 | `skill_types`, `skill_catalog`, parser/validation matrix |
| F2 Local discovery + collision policy | 2 | `skill_discovery`, `skill_registry`, config roots/scopes/enablement |
| F3 System catalog + retrieval-by-name | 3–5 | Catalog injection + retrieval tool + loader; **no** ranking/scoring |
| F4 Progressive disclosure + linked `references/` | 3–4 | `skill_loader` + path bounding + cache bounds |
| F5 Retrieval-only context binding | 3–5 | Injected `SKILL.md` + linked files into agent context; **no** procedural/agent executors |
| F6 Governance: allow/deny + `skills.tools.*` + `allowed-tools` ∩ runtime | 2, 4 | Config models + `skill_policies` + deny-before-content |
| F7 Observability | 7 | `skill_events` + redaction tests |
| CLI visibility | 6 | `skills list|inspect|doctor` (Rich) |
| SI-002 tool boundary | 3–5 | `ToolCatalog` definition + `ToolRegistry` + allowlist tests |

**Registry key**: Canonical skill identity for retrieval is frontmatter **`name`** (normalized per parser rules). `$skill:<id>` explicit invocation stays deferred.

The table above is the **authoritative MVP scope lock** for plan `005` (what ships in SI-007 retrieval MVP vs deferred). Update rows only when PRD/architecture scope changes and re-run Phase 0 intent review.

### Phase dependency graph (locked)

Single-thread execution order: **Phase 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8**; **Phase 9** is post-MVP. Retrieval tool + `ToolCatalog` wiring spans **Phases 3–5**; do not merge Phase 5 before Phases 3–4 have retrieval and policy tests.

```mermaid
flowchart LR
  P1["Phase 1\ncontract"] --> P2["Phase 2\ndiscovery"]
  P2 --> P3["Phase 3\nloader + tool"]
  P3 --> P4["Phase 4\npolicy"]
  P4 --> P5["Phase 5\nruntime"]
  P5 --> P6["Phase 6\nCLI"]
  P6 --> P7["Phase 7\nevents"]
  P7 --> P8["Phase 8\nhardening"]
  P8 --> P9["Phase 9\npost-MVP"]
```

### Phase tracker (SI-007 / plan 005)

| Phase | Status | Owner | Depends on | Notes |
|---|:---:|---|---|---|
| 0 | Done | @jeffrichley | — | Execution framing, acceptance lock, tracker below |
| 1 | Done | @jeffrichley | 0 | `skill_types`, `skill_catalog`, parser/validation matrix |
| 2 | Done | @jeffrichley | 1 | `skill_discovery`, `skill_registry`, config `skills.*` |
| 3 | Done | @jeffrichley | 2 | `skill_prompt_injector`, `skill_loader`, `skill_retrieve`, runtime wiring |
| 4 | Done | @jeffrichley | 3 | `skill_policies`, `SkillsRetrievalConfig`, deny-before-content, F6 `effective_skill_tools` |
| 5 | Done | @jeffrichley | 3–4 | Supervisor tool gating, `skill_trace`, integration tests |
| 6 | Not started | @jeffrichley | 5 | `skills list|inspect|doctor` (Rich) |
| 7 | Not started | @jeffrichley | 5–6 | `skill_events`, redaction tests |
| 8 | Not started | @jeffrichley | 1–7 | Full gates, docs/status, PR evidence |
| 9 | Not started | @jeffrichley | 8 | Distribution follow-up (not MVP-blocking) |

### Phase → PRD / architecture provenance (summary)

Each implementation phase’s **Intent Lock** lists detailed sources; this summary satisfies the Phase 0 “every phase maps to PRD/architecture” requirement:

| Phase | Primary PRD / architecture anchors |
|---|-----|
| 1 | PRD skill package contract; Architecture `SKILL.md` contract + metadata schema |
| 2 | PRD local discovery + collision policy; Architecture §7–8 prerequisites |
| 3–5 | PRD system catalog + retrieval-by-name; Architecture §8–9; tool boundary with SI-002 |
| 4 | PRD retrieval policy + linked files + F6; Architecture §11 |
| 5 | PRD integration; Architecture layered flow |
| 6 | PRD CLI visibility; `AGENTS.md` Rich CLI output rule |
| 7 | PRD F7 telemetry; Architecture `skill_events` |
| 8 | `.ai/COMMANDS/validate.md`, `status-sync.md`, `.ai/RULES.md` |
| 9 | PRD §13 future; Architecture §20 delta checklist |

### Rollback strategy by phase

| Phase | What can go wrong | Rollback / containment |
|---|-----|-----|
| 0 | Plan drift or ambiguous gates | Revert plan edits; re-lock Intent Lock before code |
| 1 | Parser/schema regressions | Revert `skill_*` modules; remove `python-frontmatter` if unused elsewhere |
| 2 | Bad index or collisions | Disable skills via `skills.enabled` (introduced this phase); narrow roots/scopes |
| 3–4 | Retrieval or policy leaks | Disable skills; remove retrieval tool id from `tools.allowlist`; rely on deny-before-content |
| 5 | Supervisor/runtime regressions | `skills.enabled=false` (full subsystem off); keep prior tool-only paths |
| 6 | CLI confusion | Document; CLI is additive—rollback by hiding commands only if needed |
| 7 | noisy or leaking events | Reduce emitters or gate events behind config (document in phase) |
| 8 | gate/doc failures | Fix forward; docs-only rollback per commit policy |
| 9 | N/A for SI-007 MVP | Tracked separately; does not block MVP closure |

Master containment switch for runtime (required by Phase 5 tasks): **`skills.enabled=false`** disables the skills subsystem while preserving tool-registry behavior.

## CLI vs TUI (this MVP slice)

- **In scope**: Operator verification through **CLI** (`lily skills …`, `lily run …`) with Rich tables/panels per `AGENTS.md`.
- **Out of scope for MVP closure**: Textual/TUI parity unless an existing TUI command path already mirrors these surfaces; if not, track TUI follow-up in `docs/dev/backlog.md` without blocking SI-007 retrieval MVP.

Verification commands (final implementation slice):
- `just quality && just test`
- `uv run pytest tests/unit/runtime -k skill`
- `uv run pytest tests/integration -k skill`
- `uv run pytest tests/e2e -k "skill or skills"`

## Input Provenance

Pre-existing in-repo sources (canonical):
- `.ai/SPECS/002-skills-system/PRD.md`
- `.ai/SPECS/002-skills-system/SKILLS_ARCHITECTURE.md`
- `docs/dev/roadmap.md` (`SI-007`)
- `docs/dev/references/runtime-config-and-interfaces.md`

Skill fixture provenance:
- Generated test fixtures under `tests/fixtures/skills/` during implementation.
- Optional sample local skills under `.lily/skills/` created in-plan as deterministic examples.

Regeneration/setup commands:
```bash
# create or refresh local sample skills fixtures
uv run python scripts/skills_seed_fixtures.py
```

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `.ai/SPECS/002-skills-system/PRD.md` - product requirements and scope boundaries.
- `.ai/SPECS/002-skills-system/SKILLS_ARCHITECTURE.md` - component boundaries, contracts, and lifecycle.
- `src/lily/runtime/config_schema.py` - established strict validation patterns and config model style.
- `src/lily/runtime/config_loader.py` - deterministic loader behavior and fail-fast semantics.
- `src/lily/runtime/tool_catalog.py` - schema parsing, validation, and collision/ID guard patterns.
- `src/lily/runtime/tool_registry.py` - allowlist/policy boundary and deterministic ordering style.
- `src/lily/runtime/tool_resolvers.py` - resolving `ToolCatalog` definitions into concrete tools for `ToolRegistry`.
- `.lily/config/tools.toml` - pattern for `[[definitions]]` tool ids and Python `target` entry points.
- `src/lily/runtime/agent_runtime.py` - invoke flow, middleware boundaries, and typed runtime result handling.
- `src/lily/agents/lily_supervisor.py` - orchestration wiring from config -> runtime objects.
- `src/lily/cli.py` - existing rich output style and command registration patterns.
- `tests/unit/runtime/test_tool_catalog.py` - unit test pattern for schema + deterministic errors.
- `tests/integration/test_agent_runtime.py` - integration style for runtime wiring behavior.
- `tests/e2e/test_cli_agent_run.py` - CLI e2e shape for new skills commands and run path assertions.

### New Files to Create

Runtime core:
- `src/lily/runtime/skill_types.py`
- `src/lily/runtime/skill_catalog.py`
- `src/lily/runtime/skill_discovery.py`
- `src/lily/runtime/skill_registry.py`
- `src/lily/runtime/skill_prompt_injector.py`
- `src/lily/runtime/skill_loader.py`
- `src/lily/runtime/skill_retrieve_tool.py`
- `src/lily/runtime/skill_policies.py`
- `src/lily/runtime/skill_events.py`

CLI/commands:
- `src/lily/commands/handlers/skills_list.py`
- `src/lily/commands/handlers/skills_inspect.py`
- `src/lily/commands/handlers/skills_doctor.py`

Tests:
- `tests/unit/runtime/test_skill_catalog.py`
- `tests/unit/runtime/test_skill_discovery.py`
- `tests/unit/runtime/test_skill_registry.py`
- `tests/unit/runtime/test_skill_loader.py`
- `tests/unit/runtime/test_skill_prompt_injector.py`
- `tests/unit/runtime/test_skill_retrieve_tool.py`
- `tests/unit/runtime/test_skill_policies.py`
- `tests/integration/test_skills_runtime_flow.py`
- `tests/e2e/test_cli_skills_commands.py`

Scripts/docs (optional but recommended):
- `scripts/skills_seed_fixtures.py`
- `docs/dev/references/skills-runtime-and-contracts.md`

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [OpenAI Codex — Skills](https://platform.openai.com/docs/codex/skills)
  - Why: Canonical `SKILL.md` package and progressive disclosure posture.
- [LangChain Docs — Multi-agent and routing](https://docs.langchain.com/oss/python/langchain/multi-agent)
  - Why: Selection/delegation boundaries between main runtime and delegated agents.
- [LangChain Docs — Tools and structured invocation](https://docs.langchain.com/oss/python/langchain/tools)
  - Why: Procedural skill wrapper contracts and schema-driven execution.
- [Anthropic Docs — Prompting/skills style guidance](https://docs.anthropic.com/)
  - Why: Durable skill authoring and constrained prompt context principles.

### Patterns to Follow

**Naming Conventions:**
- snake_case IDs and module names; explicit `*Error` exception classes for contract failures.

**Error Handling:**
- field-specific deterministic validation errors; avoid silent defaults for required fields.

**Logging Pattern:**
- structured event payloads with stable keys; avoid free-form-only strings for critical decisions.

**Other Relevant Patterns:**
- Registry/strategy dispatch maps preferred over long `if`/`elif` chains.
- Rich tables/panels for CLI user-facing output.

---

## IMPLEMENTATION PLAN

Use markdown checkboxes (`- [ ]`) for implementation phases and task bullets so execution progress can be tracked live.

- [x] Phase 0: Execution framing and acceptance lock
- [x] Phase 1: Skill contract + schema foundation
- [x] Phase 2: Discovery, indexing, precedence, and registry
- [x] Phase 3: System-prompt skill catalog injection + retrieval-by-name loader
- [x] Phase 4: Linked-file hydration + retrieval policy gates (retrieval-only MVP)
- [x] Phase 5: Runtime integration into supervisor invoke path
- [ ] Phase 6: CLI surfaces (`skills list/inspect/doctor`) and UX
- [ ] Phase 7: Telemetry/events, diagnostics, and observability
- [ ] Phase 8: Testing, docs/status sync, and release hardening
- [ ] Phase 9: Post-MVP distribution and packaging follow-up

### Phase 0: Execution framing and acceptance lock

**Intent Lock**
- **Source of truth**: PRD sections 2/4/6/8; Architecture sections 5-11; `.ai/RULES.md`.
- **Must**:
  - [x] Freeze MVP scope in a phase checklist before implementation.
  - [x] Define exact acceptance criteria per phase and required gates.
  - [x] Define explicit non-goals to prevent scope bleed.
- **Must Not**:
  - [x] Start coding before criteria/gates are written.
  - [x] Expand to out-of-scope marketplace/autonomous systems in MVP.
- **Provenance map**:
  - [x] Every phase maps to PRD scope bullets and architecture sections.
- **Acceptance gates**:
  - [x] Plan updated with per-phase gates and non-goals.
  - [x] Team-agreed ordering and dependency graph documented.

**Tasks**
- [x] **EMBED** the [MVP scope traceability](#mvp-scope-traceability-prd-to-phase) table in this plan (update rows if scope shifts); treat it as the checklist lock for “what ships in 005”.
- [x] Build a phase tracker table with status/owner/dependencies (optional spreadsheet or `.ai` status table).
- [x] Define risk register: contract drift, non-deterministic routing, policy bypass, context bloat.
- [x] Define rollback strategy per phase (feature toggle/config off).

### Phase 1: Skill contract + schema foundation

**Intent Lock**
- **Source of truth**: PRD `Skill package contract`; Architecture `SKILL.md contract` and metadata schema.
- **Must**:
  - [x] Implement strict pydantic models for skill metadata/frontmatter and normalized summaries.
  - [x] Enforce guide-aligned required fields (`name`, `description`) and parser normalization rules.
  - [x] Enforce canonical kebab-case recommendation as lint/doctor guidance (not hard reject for imported third-party skills).
  - [x] Provide clear field-level errors (no generic parse failures).
- **Must Not**:
  - [x] Introduce implicit fallback defaults for required fields.
  - [x] Accept unknown required-contract fields silently.
- **Provenance map**:
  - [x] `SKILL.md` frontmatter -> `SkillMetadata` model -> `SkillSummary` index record.
- **Acceptance gates**:
  - [x] Unit tests for valid/invalid frontmatter permutations.
  - [x] Fixture packs for **valid/invalid `SKILL.md`** contracts (retrieval-only MVP: one operational package shape; optional `type` field may exist for forward compatibility but **no** distinct execution paths per type in MVP).

**Tasks**
- [x] ADD `python-frontmatter` to `pyproject.toml` and refresh the lockfile (`uv lock`); verify import in CI/local before merging parser work.
- [x] CREATE `skill_types.py` with enums, summary/full models, and typed errors.
- [x] CREATE `skill_catalog.py` parser for markdown+frontmatter extraction.
- [x] ADD deterministic validation messages for each required field.
- [x] ADD fixture packs for success/failure contracts.
- [x] ADD unit tests for parsing, unknown fields, malformed versions, and ID validation.
- [x] ADD parser test matrix for malformed YAML/frontmatter edge cases (missing delimiters, unclosed quotes, bad YAML types, forbidden `<` `>` values, reserved provider prefixes).
- [x] ADD normalization tests for non-canonical names -> internal canonical key mapping.

### Phase 2: Discovery, indexing, precedence, and registry

**Intent Lock**
- **Source of truth**: PRD `Local skill discovery`, `collision policy`; Architecture sections 7 and 8 prerequisites.
- **Must**:
  - [x] Discover skills from configured roots/scopes in deterministic order.
  - [x] Resolve collisions via precedence + semantic version tie-break.
  - [x] Emit discover/shadow diagnostics records.
- **Must Not**:
  - [x] Use filesystem iteration order without explicit sorting.
  - [x] Allow duplicate winner outcomes between runs.
- **Provenance map**:
  - [x] Scope order + semantic version -> registry winner record.
- **Acceptance gates**:
  - [x] Unit tests for precedence and tie-break matrix.
  - [x] Integration test proving deterministic registry across repeated runs.

**Tasks**
- [x] CREATE `skill_discovery.py` for root walking and candidate collection.
- [x] CREATE `skill_registry.py` for index build, collision resolution, and query APIs.
- [x] UPDATE `config_schema.py` / loader to include `skills.enabled`, `skills.roots`, `skills.scopes_precedence`, `skills.allowlist` / `skills.denylist` per PRD §9.
- [x] UPDATE `config_schema.py` for **`skills.tools`** per PRD §9: `default_policy` (`inherit_runtime` | `deny_unless_allowed` | `use_default_packs`), `default_packs`, `packs` (map pack id → ordered tool id list). Add unit tests for invalid references and forbidden combinations.
- [x] ADD unit tests for same-id collisions and lexical deterministic fallback.
- [x] ADD integration test for merged repo/user/system roots.

### Phase 3: System-prompt skill catalog injection + retrieval-by-name loader

**Intent Lock**
- **Source of truth**: PRD system-prompt skill catalog injection + tool-based retrieval-by-name; Architecture sections 8 and 9.
- **Must**:
  - [x] Build a stable enabled-skill catalog from `SKILL.md` frontmatter for system-prompt injection.
  - [x] Hydrate full `SKILL.md` bodies only after an agent tool request by skill `name`.
  - [x] Hydrate linked `references/...` files (bounded to the skill directory) only after an agent tool request.
- **Must Not**:
  - [x] Implement `$skill:<id>` explicit invocation (deferred to backlog).
  - [x] Implement deterministic selection/ranking/scoring (deferred to backlog).
  - [x] Load all full `SKILL.md` bodies at index time.
- **Provenance map**:
  - [x] Prompt tokens -> system-prompt catalog injection -> tool request payload (skill name) -> retrieved content.
- **Acceptance gates**:
  - [x] Unit tests for catalog building, collision handling, and deterministic ordering.
  - [x] Unit tests for cache hit/miss and deterministic retrieval/load errors (including missing/blocked linked files).
  - [x] Unit tests proving the **skill retrieval tool** is constructible with a **stable tool id** and appears in resolved `ToolRegistry` when allowlisted.

**Tasks**
- [x] CREATE/UPDATE `skill_loader.py` for:
  - [x] catalog summaries via registry + `skill_prompt_injector` (not full-body at index time)
  - [x] full `SKILL.md` hydration by skill `name`
  - [x] linked `references/...` hydration with path-bounding checks
- [x] IMPLEMENT a **LangChain tool** (`skill_retrieve`, stable id) with optional `reference_subpath`; recorded in `.lily/config/tools.toml`.
- [x] ADD `[[definitions]]` entry in `.lily/config/tools.toml` with `source = "python"` and `target = "lily.runtime.skill_retrieve_tool:skill_retrieve"`.
- [x] Allowlist behavior unchanged from SI-002: omit `skill_retrieve` from `tools.allowlist` to exclude the tool (same as other tools); no separate test required beyond existing allowlist gates.
- [x] ADD system-prompt catalog injection wiring (`AgentRuntime` appends catalog markdown; `skill_retrieve` uses `ContextVar` binding per invoke).
- [x] Parser already uses `python-frontmatter` from Phase 1 (`skill_catalog.load_skill_md`).
- [x] ADD unit tests for retrieval-by-name hydration and linked-file error taxonomy.

**Deferred to Phase 4+**
- ~~Richer linked-path whitelists beyond `references/`~~ — **superseded**: `reference_subpath` is relative to the **skill package root** (any subdirectory; still no `..` escapes).
- Wiring **F6 empty effective-tools** checks into future tool-calling / execution paths (retrieval-only MVP does not block `SKILL.md` on empty intersection per PRD).

### Phase 4: Retrieval policy gates + linked-file constraints (retrieval-only MVP)

**Intent Lock**
- **Source of truth**: PRD retrieval policy + linked-file constraints; Architecture section 11 policy/safety.
- **Must**:
  - [x] Enforce skill-level enable/disable and retrieval allow/deny before returning content.
  - [x] Enforce linked-file constraints: only allow `references/...` (and optionally other whitelisted subpaths) that stay inside the skill directory.
  - [x] Enforce **effective tools** for skills per PRD F6: `intersection(runtime_available_tools, skill_allowed_tools_or_packs)` when `allowed-tools` / pack policy applies; fail fast with deterministic errors when the effective set is empty **for tool-calling paths** (retrieval of `SKILL.md` may still be allowed per PRD). *(F6 intersection implemented in `effective_skill_tools` for policy resolution; tool-calling enforcement deferred until procedural paths.)*
  - [x] Keep retrieval tool failures deterministic and field-specific.
- **Must Not**:
  - [x] Implement playbook/procedural/agent execution adapters.
- **Provenance map**:
  - [x] Tool request (skill name + optional linked path) -> policy evaluation -> retrieval result/error.
- **Acceptance gates**:
  - [x] Unit tests for retrieval allow/deny + disabled-skill errors.
  - [x] Unit/integration tests for linked-file path bounding and missing-file errors.

**Tasks**
- [x] CREATE `skill_policies.py` for retrieval allow/deny checks and deterministic rejection reasons.
- [x] UPDATE config schema/loader to support retrieval enable/disable semantics by scope (`skills.retrieval.enabled`, `skills.retrieval.scopes_allowlist`; `skills.allowlist` / `skills.denylist` normalized to canonical keys).
- [x] ADD linked-file path bounding checks and deterministic error taxonomy (directory vs file; paths stay inside the skill package directory).
- [x] ADD unit/integration tests for **skills.denylist / allowlist**, **blocked retrieval**, and **effective tool intersection** (include at least one fixture where `allowed-tools` narrows to a subset of runtime tools).

### Phase 5: Runtime integration into supervisor invoke path

**Intent Lock**
- **Source of truth**: PRD integration bullets; Architecture layered flow section.
- **Must**:
  - [x] Integrate skills flow into runtime without breaking current no-skill behavior.
  - [x] Preserve current tool allowlist and model routing policies.
  - [x] Return deterministic skill retrieval metadata in runtime result structures.
- **Must Not**:
  - [x] Introduce hidden behavior changes for existing prompts with no skill match.
  - [x] Break conversation continuity/session threading behavior.
- **Provenance map**:
  - [x] Prompt ingress -> system-prompt catalog injection -> tool request -> retrieval -> policy -> final output + trace.
- **Acceptance gates**:
  - [x] Integration tests for successful retrieval, retrieval policy failures, and no-skill catalog behavior.
  - [x] Integration test proving **end-to-end** path: catalog in system prompt → model can call retrieval tool → hydrated content → trace payload (with mocks or deterministic agent stub as needed).
  - [x] Existing runtime integration suites remain green.

**Tasks**
- [x] UPDATE supervisor/runtime construction to initialize skill subsystem once.
- [x] WIRE **tool resolution** so the skill retrieval tool is included in the `AgentRuntime` tool set when `skills.enabled` and `tools.allowlist` permit it (follow `tool_resolvers.py` / `ToolCatalog` patterns; no duplicate registry logic).
- [x] ADD invoke-path hook for catalog injection + retrieval loading.
- [x] ADD structured `skill_trace` payload on runtime responses.
- [x] ADD config toggles to fully disable skill subsystem.
- [x] ADD integration tests for legacy behavior parity when disabled.
- [x] UPDATE sample/e2e configs (e.g. under `.lily/config/` or test fixtures) so **`tools.allowlist` includes the retrieval tool id** wherever skills are exercised.

### Phase 6: CLI surfaces and UX

**Intent Lock**
- **Source of truth**: PRD CLI visibility requirement; AGENTS CLI UX Rich-render rule.
- **Must**:
  - [ ] Add `skills list`, `skills inspect`, `skills doctor` user-facing commands.
  - [ ] Use Rich tables/panels for default outputs.
  - [ ] Surface collisions/shadowing/invalid packages with actionable messages.
  - [ ] Surface **catalog and policy** diagnostics (what is indexed, what is blocked, why retrieval would fail).
- **Should (post-MVP / backlog)**:
  - [ ] Trigger-quality heuristics (under/over-trigger templates for skill descriptions) — **not** required for SI-007 retrieval MVP; link follow-up in backlog if descoped.
- **Must Not**:
  - [ ] Default to raw JSON in interactive mode.
  - [ ] Hide policy-block reasons from operator diagnostics.
- **Provenance map**:
  - [ ] Registry + diagnostics -> CLI presenter models -> rendered table/panel output.
- **Acceptance gates**:
  - [ ] E2E CLI tests for command outputs and exit codes.
  - [ ] Snapshot-like assertions for key table headers/rows.

**Tasks**
- [ ] CREATE handlers for list/inspect/doctor commands.
- [ ] UPDATE `src/lily/cli.py` command tree and options.
- [ ] ADD filtering/sorting flags and concise/verbose modes.
- [ ] ADD e2e tests for no-skills, valid-skills, invalid-skills scenarios.
- [ ] ADD docs snippets for command usage (where repo conventions allow; otherwise defer to a single reference doc slice in Phase 8).

### Phase 7: Telemetry/events and observability

**Intent Lock**
- **Source of truth**: PRD structured telemetry requirement; Architecture `skill_events` component.
- **Must**:
  - [ ] Emit stable structured events for discover/request/load/outcome.
  - [ ] Include rationale and policy decisions without leaking secrets.
  - [ ] Keep event schema versioned and test-covered.
- **Must Not**:
  - [ ] Emit only free-form logs with no schema guarantee.
  - [ ] Log full prompt/skill body when policy forbids it.
- **Provenance map**:
  - [ ] Runtime decision points -> typed event model -> logger sink.
- **Acceptance gates**:
  - [ ] Unit tests for event schema and serialization.
  - [ ] Integration check that key events appear in retrieval-only tool-request flows.

**Tasks**
- [ ] CREATE `skill_events.py` typed event models and emit helpers.
- [ ] MAP PRD F7 names (`skill_discovered`, `skill_selected`, `skill_loaded`, `skill_executed`, `skill_failed`) onto retrieval semantics: e.g. treat **`skill_selected` / `skill_executed` as retrieval-request / content-applied** for playbook-style injection in MVP (document enum mapping in `skill_events` docstring). Adjust if PRD is updated to retrieval-specific names later.
- [ ] ADD event hooks across discovery, system-prompt injection, loader, and retrieval tool request paths.
- [ ] ADD redaction/sanitization rules and tests.
- [ ] ADD event schema version constant and compatibility tests.

### Phase 8: Testing, docs/status sync, and release hardening

**Intent Lock**
- **Source of truth**: `.ai/COMMANDS/validate.md`, `.ai/COMMANDS/status-sync.md`, `.ai/RULES.md` gates.
- **Must**:
  - [ ] Run full quality/test gates warning-clean.
  - [ ] Update roadmap/status/backlog/debt docs to reflect completion/defer states.
  - [ ] Record explicit guide-alignment evidence for parser/security matrix (frontmatter, `<`/`>` rejection, reserved prefixes) and **CLI policy diagnostics**; trigger heuristics only if pulled in from backlog.
  - [ ] Produce phased commits following commit policy (feature, UX polish, docs-only as applicable).
- **Must Not**:
  - [ ] Merge with unresolved warning debt undocumented.
  - [ ] Mark SI-007 complete if compatibility-only slices remain.
- **Provenance map**:
  - [ ] Gate outcomes and status updates tied directly to command results and shipped scope.
- **Acceptance gates**:
  - [ ] `just quality && just test` green.
  - [ ] Docs/status checks green.
  - [ ] PR body explicitly calls out complete vs temporary vs deferred.

**Tasks**
- [ ] EXPAND unit/integration/e2e coverage for high-value behavior and failure paths.
- [ ] RUN full gates and capture output in execution report.
- [ ] UPDATE docs status surfaces with SI-007 phase truth.
- [ ] PREPARE PR using repository template headings exactly.
- [ ] ADD implementation evidence section mapping guide checklist items -> shipped tests/commands.

### Phase 9: Post-MVP distribution and packaging follow-up

**Intent Lock**
- **Source of truth**: SI-007 PRD `## 13. Future Considerations`; SKILLS_ARCHITECTURE `## 20. Tight Delta Checklist (Guide Realignment)`.
- **Must**:
  - [ ] Define zip/import-export package contract for portable skill bundles.
  - [ ] Define API-managed skill lifecycle/versioning strategy for programmatic deployments.
  - [ ] Define org-level distribution, rollout, and governance policy surfaces.
- **Must Not**:
  - [ ] Block SI-007 MVP closure on post-MVP distribution implementation.
  - [ ] Ship ad hoc packaging behavior without documented contract/versioning.
- **Provenance map**:
  - [ ] Distribution requirements in architecture/PRD map to a tracked follow-up plan and backlog entries.
- **Acceptance gates**:
  - [ ] A follow-up implementation plan exists and is linked from roadmap/backlog.
  - [ ] Deferred scope is explicitly documented in PR/status surfaces.

**Tasks**
- [ ] CREATE follow-up plan file for distribution work (next plan ID after current active plans).
- [ ] DEFINE skill bundle archive format (layout, checksum, manifest metadata, compatibility fields).
- [ ] DEFINE import/export CLI/API surfaces and validation error taxonomy.
- [ ] DEFINE rollout strategy: org publish/update channels, version pinning, rollback semantics.
- [ ] UPDATE roadmap/backlog/status docs to track distribution track separately from SI-007 MVP.

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### 0. PLAN LOCK

- [x] **CONFIRM** [MVP scope traceability](#mvp-scope-traceability-prd-to-phase) table is present and matches Phase 1–8 intent (edit this file if PRD deltas require it).
  - [x] **VALIDATE**: `uv run python -m compileall src tests`

### 1. DEPENDENCY + CONTRACT MODELS

- [x] **ADD** `python-frontmatter` to `pyproject.toml` and refresh `uv.lock` (`uv lock`).
- [x] **CREATE** `src/lily/runtime/skill_types.py`
  - [x] **IMPLEMENT**: Core skill metadata/summary/full models and error taxonomy.
  - [x] **VALIDATE**: `uv run pytest tests/unit/runtime/test_skill_catalog.py -q`

- [x] **CREATE** `src/lily/runtime/skill_catalog.py`
  - [x] **IMPLEMENT**: SKILL.md parser and strict frontmatter validator (`python-frontmatter` + safe YAML).
  - [x] **VALIDATE**: `uv run pytest tests/unit/runtime/test_skill_catalog.py -q`

### 2. CONFIG + DISCOVERY + REGISTRY

- [x] **EXTEND** `src/lily/runtime/config_schema.py` (+ loader) with `skills.*` and nested `skills.tools.*` per PRD §9.
  - [x] **VALIDATE**: `tests/unit/runtime/test_config_loader.py` (skills YAML + invalid `skills.tools` cases); `just test`.

- [x] **CREATE** `src/lily/runtime/skill_discovery.py`
  - [x] **IMPLEMENT**: Scope-root traversal and deterministic candidate ordering.
  - [x] **VALIDATE**: `uv run pytest tests/unit/runtime/test_skill_discovery.py -q`

- [x] **CREATE** `src/lily/runtime/skill_registry.py`
  - [x] **IMPLEMENT**: Collision resolution and query interface.
  - [x] **VALIDATE**: `uv run pytest tests/unit/runtime/test_skill_registry.py -q`

- [x] **ADD** `tests/integration/test_skills_discovery_registry.py` (deterministic registry across repeated runs).

### 3. PROMPT INJECTION + LOADER + RETRIEVAL TOOL

- [x] **CREATE** `src/lily/runtime/skill_prompt_injector.py`
  - [x] **IMPLEMENT**: Format enabled skill catalog (registry summaries: `name` + `description`) for system prompt.
  - [x] **VALIDATE**: `uv run pytest tests/unit/runtime/test_skill_prompt_injector.py -q`

- [x] **CREATE** `src/lily/runtime/skill_loader.py` (+ `build_skill_bundle`, `SkillBundle`)
  - [x] **IMPLEMENT**: Progressive disclosure (full `SKILL.md` + bounded `references/...`) with in-memory caching.
  - [x] **VALIDATE**: `uv run pytest tests/unit/runtime/test_skill_loader.py -q`

- [x] **CREATE** `src/lily/runtime/skill_retrieve_tool.py` (`skill_retrieve`, `ContextVar` binding)
  - [x] **ADD** `[[definitions]]` row in `.lily/config/tools.toml` targeting `lily.runtime.skill_retrieve_tool:skill_retrieve`.
  - [x] **UPDATE** `AgentRuntime` + `LilySupervisor` for catalog append + loader binding per invoke.
  - [x] **VALIDATE**: `uv run pytest tests/unit/runtime/test_skill_retrieve_tool.py tests/integration/test_agent_runtime.py -q`

### 4. RETRIEVAL POLICY + CONSTRAINTS

- [x] **CREATE** `src/lily/runtime/skill_policies.py`
  - [x] **IMPLEMENT**: Enable/deny/allowlist checks; effective tool intersection (PRD F6); linked-path bounding.
  - [x] **VALIDATE**: `uv run pytest tests/unit/runtime/test_skill_policies.py -q`

### 5. RUNTIME + CLI INTEGRATION

- [x] **UPDATE** `src/lily/agents/lily_supervisor.py`, `src/lily/runtime/agent_runtime.py`, `src/lily/runtime/tool_resolvers.py` (as needed)
  - [x] **IMPLEMENT**: Wire skill pipeline, retrieval tool into resolved registry, trace payload; sample configs include retrieval tool id on allowlist.
  - [x] **VALIDATE**: `uv run pytest tests/integration/test_skills_runtime_flow.py -q`

- [ ] **UPDATE/CREATE** CLI handlers + `src/lily/cli.py`
  - [ ] **IMPLEMENT**: `skills list|inspect|doctor` commands and rich output.
  - [ ] **VALIDATE**: `uv run pytest tests/e2e/test_cli_skills_commands.py -q`

### 6. EVENTS + HARDENING

- [ ] **CREATE** `src/lily/runtime/skill_events.py`
  - [ ] **IMPLEMENT**: Typed event schema (PRD F7 mapping for retrieval MVP), redacted emitters.
  - [ ] **VALIDATE**: `uv run pytest tests/unit/runtime -k skill_events -q`

- [ ] **UPDATE** docs/status and finish gates
  - [ ] **VALIDATE**: `just quality && just test`
  - [ ] **VALIDATE**: `just docs-check && just status`

---

## TESTING STRATEGY

### Unit Tests

- [x] Parser/contract tests for SKILL.md metadata validity matrix.
- [x] Discovery order tests across repo/user/system roots.
- [x] Collision and precedence tests (scope + semver + deterministic fallback).
- [x] System-prompt catalog injection correctness and retrieval-by-name (agent-chosen skill `name`, not implicit ranking).
- [x] Loader caching tests and failure taxonomy tests.
- [x] Retrieval policy tests and linked-file constraint tests (deny/missing/off-scope).
- [ ] Event schema serialization and redaction tests.

### Integration Tests

- [x] Deterministic skill registry across repeated discover+merge (repo/user overlap); see `tests/integration/test_skills_discovery_registry.py`.
- [x] End-to-end runtime path from prompt -> system-prompt catalog injection -> skill retrieval tool request -> output.
- [x] Config-driven toggles (skills enabled/disabled) preserve existing behavior.
- [ ] Policy constraints enforced under realistic runtime wiring.

### E2E Tests

- [ ] CLI skills command flows on fixture skills roots.
- [ ] CLI run where the agent retrieves a known skill by `name` (retrieval-only MVP smoke path).
- [ ] Failure UX for invalid skill package and policy denial.

### Edge Cases

- [ ] Duplicate IDs across scopes with mixed versions.
- [ ] Retrieval request for disabled/denied skills.
- [ ] Missing `SKILL.md` body for a known skill name.
- [ ] Linked-file request attempts outside the skill directory (path bounding).
- [ ] Non-ASCII content and long markdown references.
- [ ] Runtime with zero skills configured.

---

## VALIDATION COMMANDS

Primary quality gates:

- [ ] `just lint`
- [ ] `just format-check`
- [ ] `just types`
- [ ] `just test`
- [ ] `just quality && just test`

Focused skills checks during development:

- [ ] `uv run pytest tests/unit/runtime -k skill`
- [ ] `uv run pytest tests/integration -k skill`
- [ ] `uv run pytest tests/e2e -k "skill or skills"`

Docs/status checks:

- [ ] `just docs-check`
- [ ] `just status`

---

## Risk register (SI-007)

| ID | Risk | Signal / phase | Mitigation |
|---|-----|-----|-----|
| R-001 | **Contract drift** between PRD/architecture and parser, config, or tool ids | Mismatched tests vs spec; surprise validation errors | Single MVP traceability table + Intent Locks per phase; field-level errors only; doctor/list surfaces |
| R-002 | **Non-deterministic routing** or unstable ordering | Flaky tests; different winner on repeat runs | Explicit sort orders; no filesystem-order dependence; tie-break tests (Phase 2+) |
| R-003 | **Policy bypass** (content returned when deny/disable should win) | Retrieval without policy check | Deny-before-content; allowlist intersection for tool paths; unit/integration tests |
| R-004 | **Context bloat** from eager skill bodies | Token blowups; slow runs | Progressive disclosure; catalog vs full load; cache bounds (Phases 3–4) |
| R-005 | **Operator confusion** on failure reason | Opaque errors | Rationale in traces + `skills inspect` / `skills doctor` (Phase 6–7) |

## Non-Goals (MVP Guardrails)

- [x] No autonomous skill generation/promotion/pruning loop.
- [x] No remote package marketplace or signed distribution service.
- [x] No mandatory embeddings/vector DB selection dependency.
- [x] No broad refactor of unrelated runtime modules.
- [x] No Textual/TUI command parity **required** for SI-007 closure (CLI sufficient; see [CLI vs TUI](#cli-vs-tui-this-mvp-slice)).
- [x] No trigger-quality / under-over-trigger heuristic suite **required** for MVP (optional backlog).

## Execution Report

### Completion Status

- Phase 0 (execution framing and acceptance lock): **completed** on branch `feat/005-skills-system-implementation`.
- Phase 1 (skill contract + schema foundation): **completed** (`skill_types.py`, `skill_catalog.py`, `tests/unit/runtime/test_skill_catalog.py`, `tests/fixtures/skills/`).
- Phase 2 (discovery, indexing, precedence, registry): **completed** (`skill_discovery.py`, `skill_registry.py`, `RuntimeConfig.skills` + `SkillsToolsConfig`, unit + integration tests).
- Phase 3 (system-prompt catalog + retrieval-by-name loader): **completed** (`skill_prompt_injector.py`, `skill_loader.py`, `skill_retrieve_tool.py`, `AgentRuntime` + `LilySupervisor` wiring, `.lily/config/tools.toml` `skill_retrieve`).
- Phase 4 (retrieval policy + linked constraints + F6 helpers): **completed** (`skill_policies.py`, `SkillsRetrievalConfig`, `SkillRetrievalDeniedError`, `build_retrieval_blocked_keys`, `effective_skill_tools`, tests).
- Phase 5 (supervisor tool gating + `skill_trace` + integration tests): **completed** (`skill_invoke_trace.py`, `tests/fixtures/config/skills_retrieval/`, `tests/integration/test_skills_runtime_flow.py`).
- Phases 6–9: not started (implementation follows phase order).

### Artifacts Created

- `.ai/PLANS/005-skills-system-implementation.md`
- `src/lily/runtime/skill_types.py`, `src/lily/runtime/skill_catalog.py`
- `tests/unit/runtime/test_skill_catalog.py`, `tests/fixtures/skills/`
- `src/lily/runtime/skill_discovery.py`, `src/lily/runtime/skill_registry.py`
- `tests/unit/runtime/test_skill_discovery.py`, `tests/unit/runtime/test_skill_registry.py`
- `tests/integration/test_skills_discovery_registry.py`
- `src/lily/runtime/skill_prompt_injector.py`, `src/lily/runtime/skill_loader.py`, `src/lily/runtime/skill_retrieve_tool.py`
- `tests/unit/runtime/test_skill_prompt_injector.py`, `tests/unit/runtime/test_skill_loader.py`, `tests/unit/runtime/test_skill_retrieve_tool.py`
- `src/lily/runtime/skill_policies.py`, `tests/unit/runtime/test_skill_policies.py`
- `src/lily/runtime/skill_invoke_trace.py`, `tests/integration/test_skills_runtime_flow.py`, `tests/fixtures/config/skills_retrieval/`

### Phase 0 — intent check and gates

- **Phase intent check** (`.ai/COMMANDS/phase-intent-check.md`): Phase 0 “Execution framing and acceptance lock” — Intent Lock present with Must/Must Not, acceptance gates, and provenance; no code changes required before Phase 1.
- **Acceptance evidence**:
  - MVP traceability table confirmed as authoritative lock; dependency graph + phase tracker + provenance summary + rollback table added in-plan.
  - Risk register R-001–R-005 recorded; Non-Goals checkboxes marked locked.
  - Branch setup executed: `feat/005-skills-system-implementation`.

### Commands Run and Outcomes

- `git ls-files` -> pass
- `uv --version` -> pass
- `just --version` -> pass (`just` 1.42.4, session 2026-03-25)
- `uv run pytest --version` -> pass
- `git log -10 --oneline` -> pass
- `git status -sb` -> pass
- Phase 0 gate: `uv run python -m compileall -q src tests` -> pass
- `just docs-check` -> pass (after adding required doc frontmatter to `docs/tmp.md` and `docs/examples/brand-guidelines/SKILL.md` so repo-wide markdown validation succeeds)
- `just status` -> pass
- Phase 0 close (pre-commit): `just quality && just test` -> pass (2026-03-25); `uv.lock` updated `requests` 2.32.5 -> 2.33.0 (CVE-2026-25645); `justfile` `audit` uses `pip-audit --ignore-vuln CVE-2026-4539` with `docs/dev/debt/debt_tracker.md` **DEBT-017** until `pygments` publishes a fix on PyPI.

### Phase 1 — intent check and gates

- **Phase intent check** (`.ai/COMMANDS/phase-intent-check.md`): Phase 1 “Skill contract + schema foundation” — Intent Lock satisfied; `SkillMetadata` / `SkillSummary` / `SkillValidationError`; `parse_skill_markdown` + `load_skill_md`; `python-frontmatter` + `packaging.version` semver validation for `metadata.version`.
- **Acceptance evidence**:
  - `just quality` -> pass; `just test` -> pass (67 tests).
  - `uv run pytest tests/unit/runtime/test_skill_catalog.py -q` -> pass.

### Phase 2 — intent check and gates

- **Phase intent check** (`.ai/COMMANDS/phase-intent-check.md`): Phase 2 “Discovery, indexing, precedence, and registry” — deterministic discovery (`sorted` roots/children), `build_skill_registry` collision policy (scope > semver > lexical path), `discovered` / `shadowed` events; `skills` + `skills.tools` on `RuntimeConfig`; `skills.roots` list normalizes to `repository`.
- **Acceptance evidence**:
  - `just quality` -> pass; `just test` -> pass (84 tests).
  - `uv run pytest tests/unit/runtime/test_skill_discovery.py tests/unit/runtime/test_skill_registry.py tests/unit/runtime/test_config_loader.py -k skills -q` -> pass.
  - `uv run pytest tests/integration/test_skills_discovery_registry.py -q` -> pass.

### Phase 3 — intent check and gates

- **Phase intent check**: Phase 3 — catalog markdown from merged registry summaries; `SkillLoader` loads full `SKILL.md` and bounded `references/` on demand; `skill_retrieve` LangChain tool (`ContextVar` per `AgentRuntime` invoke); `build_skill_bundle` from `LilySupervisor` when `skills.enabled`.
- **Acceptance evidence**:
  - `just quality` -> pass; `just test` -> pass (97 tests).
  - `uv run pytest tests/unit/runtime/test_skill_prompt_injector.py tests/unit/runtime/test_skill_loader.py tests/unit/runtime/test_skill_retrieve_tool.py -q` -> pass.

### Phase 4 — intent check and gates

- **Phase intent check**: Phase 4 — retrieval policy gates, deny-before-content, F6 helpers; `SkillsRetrievalConfig`; linked-path bounding.
- **Acceptance evidence**:
  - `just quality` -> pass; `just test` -> pass (111 tests, pre–Phase 5 baseline).

### Phase 5 — intent check and gates

- **Phase intent check** (`.ai/COMMANDS/phase-intent-check.md`): Phase 5 “Runtime integration into supervisor invoke path” — Intent Lock satisfied; supervisor omits `skill_retrieve` from resolved tools when `skills.enabled` is false; allowlist coherency via `_effective_runtime_config`; `AgentRunResult.skill_trace` with `SkillInvokeTrace` / `SkillRetrievalTraceEntry`; `skill_retrieve` records trace via `record_skill_retrieval_trace`.
- **Acceptance evidence**:
  - `just quality && just test` -> pass (119 tests).
  - `uv run pytest tests/integration/test_skills_runtime_flow.py -q` -> pass.
  - Fixtures: `tests/fixtures/config/skills_retrieval/` (`agent.toml`, `tools.toml`, sample `SKILL.md`).

### Partial/Blocked Items

- None for Phase 0.
- None for Phase 1.
- None for Phase 2.
- None for Phase 3.
- None for Phase 4.
- None for Phase 5.
