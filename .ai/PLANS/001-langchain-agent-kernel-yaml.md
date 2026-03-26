# Feature: LangChain Agent Kernel + Textual TUI With YAML Runtime Config

The following plan should be complete, but it is important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Build Lily’s reboot kernel around LangChain’s agent runtime (`create_agent`) instead of a custom tool-loop implementation, drive runtime behavior from YAML configuration files, and provide a basic Textual TUI as the primary interactive interface. The kernel should be a thin, typed wrapper over LangChain agent execution with explicit policy controls (model/provider/tool allowlist/iteration limits/timeout/logging mode).

## User Story

As a Lily operator
I want to configure and run the supervisor agent from YAML through a simple TUI
So that I can change models, policies, and enabled capabilities without changing Python code or low-level runtime wiring.

## Problem Statement

Current reboot docs describe a custom minimal kernel loop, but the desired direction is to use LangChain’s agent runtime as the kernel substrate. We need a concrete plan to translate that direction into repository structure, contracts, and tests while keeping the reboot implementation small and deterministic.

## Solution Statement

Implement a LangChain-centered runtime layer where:
- `AgentRuntime` composes a validated YAML config + tool registry + model adapter and creates a LangChain agent.
- Runtime execution goes through LangChain’s standard agent APIs (`create_agent`, tool-calling, invoke/stream) with a small policy wrapper.
- Dynamic model routing is implemented using LangChain model middleware (`wrap_model_call`) so model choice can change per turn.
- Config is stored in `.lily/config/*.yaml` and parsed into strict typed models before runtime use.
- A basic Textual app provides chat-style input/output and invokes the configured supervisor runtime.

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: Medium
**Primary Systems Affected**: `src/lily/runtime`, `src/lily/agents`, `src/lily/tools`, `src/lily/ui`, CLI entrypoint, tests
**Dependencies**: Existing `langchain`, `langchain-openai`, `langchain-ollama`, `pyyaml`, `pydantic`; add `textual`

## Traceability Mapping (Required When Applicable)

No SI/DEBT mapping for this feature.

## Branch Setup (Required)

Branch naming must follow the plan filename:
- Plan: `.ai/PLANS/001-langchain-agent-kernel-yaml.md`
- Branch: `feat/001-langchain-agent-kernel-yaml`

Commands (must be executable as written):

```bash
PLAN_FILE=".ai/PLANS/001-langchain-agent-kernel-yaml.md"
PLAN_SLUG="$(basename "$PLAN_FILE" .md)"
BRANCH_NAME="feat/${PLAN_SLUG}"
git show-ref --verify --quiet "refs/heads/${BRANCH_NAME}" \
  && git switch "${BRANCH_NAME}" \
  || git switch -c "${BRANCH_NAME}"
```

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `pyproject.toml` - Why: Declares LangChain/YAML dependencies and CLI entrypoint contract (`lily = lily.cli:app`).
- `justfile` - Why: Defines required validation gates (`just quality && just test`).
- `src/lily/docs_validator.py` - Why: Current coding style expectations (typed dataclasses, strict validation, deterministic errors).
- `.ai/RULES.md` - Why: Non-negotiables (`No plan, no code`, warning policy, validation requirements).
- `.ai/SPECS/001-reboot/PRD.md` - Why: Reboot intent, minimal kernel + policy constraints.
- `.ai/SPECS/001-reboot/LILY_ARCHITECTURE.md` - Why: Desired runtime boundaries (kernel, registries, policies).
- `.ai/SPECS/001-reboot/IMPLEMENTATION_ROADMAP.md` - Why: Runnable-stage discipline and sequencing.

### New Files to Create

- `src/lily/runtime/config_schema.py` - Pydantic models for YAML config.
- `src/lily/runtime/config_loader.py` - YAML loading + validation + defaults policy.
- `src/lily/runtime/agent_runtime.py` - LangChain agent runtime wrapper.
- `src/lily/runtime/model_factory.py` - Model provider dispatch from config.
- `src/lily/runtime/model_router.py` - Dynamic model selection policy + LangChain middleware wiring.
- `src/lily/runtime/tool_registry.py` - Tool registration and allowlist filtering.
- `src/lily/agents/lily_supervisor.py` - Supervisor constructor wired to runtime.
- `src/lily/cli.py` - CLI command to run prompt against configured agent.
- `src/lily/ui/app.py` - Basic Textual application shell for interactive agent use.
- `src/lily/ui/screens/chat.py` - Chat screen with input + transcript panel.
- `src/lily/ui/widgets/transcript.py` - Transcript rendering widget.
- `src/lily/ui/styles/app.tcss` - Minimal Textual styling.
- `.lily/config/agent.yaml` - Primary runtime config.
- `.lily/config/tools.yaml` - Tool enablement/allowlist config.
- `tests/unit/runtime/test_config_loader.py` - YAML parse/validation tests.
- `tests/unit/runtime/test_model_factory.py` - Provider dispatch tests.
- `tests/unit/runtime/test_tool_registry.py` - Allowlist/lookup tests.
- `tests/integration/test_agent_runtime.py` - Runtime integration with fake tool/model behavior.
- `tests/e2e/test_cli_agent_run.py` - CLI smoke test with test config.

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [LangChain Agents (Python OSS)](https://docs.langchain.com/oss/python/langchain/agents)
  - Specific section: `create_agent`, model/tool wiring, and execution loop behavior.
  - Why: This is the target kernel substrate.
- [LangChain Tools](https://docs.langchain.com/oss/python/langchain/tools)
  - Specific section: tool definition and agent tool-calling integration.
  - Why: Needed for runtime tool registry compatibility.
- [LangChain Models](https://docs.langchain.com/oss/python/langchain/models)
  - Specific section: provider/model initialization patterns.
  - Why: Needed for config-driven model factory.
- [LangChain Middleware](https://docs.langchain.com/oss/python/langchain/middleware)
  - Specific section: guardrails/policies hooks.
  - Why: Candidate path for iteration/time/tool policy enforcement.
- [LangChain Agents (Dynamic Model)](https://docs.langchain.com/oss/python/langchain/agents)
  - Specific section: dynamic model selection via middleware (`wrap_model_call`).
  - Why: Required pattern for per-turn model routing in kernel runtime.
- [Textual Guide](https://textual.textualize.io/guide/)
  - Specific section: app structure, widgets, events, layout/CSS.
  - Why: Baseline implementation reference for the TUI shell.
- [Textual Tutorial](https://textual.textualize.io/tutorial/)
  - Specific section: composing widgets and handling actions.
  - Why: Practical pattern for building the initial interactive screen.
- [Textual Repository](https://github.com/Textualize/textual)
  - Specific section: examples and supported release patterns.
  - Why: Source-aligned examples for app architecture and packaging.

### Patterns to Follow

**Naming Conventions:**
- snake_case modules and functions, `PascalCase` data models/classes.
- Runtime boundaries under `src/lily/runtime/`.

**Error Handling:**
- Validate early, fail explicitly with field-level messages.
- No silent fallback for missing required config keys.

**Logging Pattern:**
- Structured runtime events (config loaded, tools enabled, invoke start/end, errors).
- Avoid noisy debug output by default.

**Dispatch Pattern:**
- Use registry maps (provider key -> constructor, tool name -> tool object) over `if/elif` chains.

---

## Input/Resource Provenance

- External source of truth: LangChain official docs at `docs.langchain.com`.
- Local requirements source: reboot specs under `.ai/SPECS/001-reboot/`.
- Runtime configs are generated in-plan under `.lily/config/` and committed as baseline templates.

## Output Artifacts And Verification Commands

Artifacts:
- Configurable runtime kernel files under `src/lily/runtime/`.
- Basic Textual TUI files under `src/lily/ui/`.
- YAML config files under `.lily/config/`.
- CLI/TUI run surfaces via `lily` entrypoint.
- Unit/integration/e2e tests for config + runtime.

Verification commands:
- `uv run lily --help`
- `uv run lily run --config .lily/config/agent.yaml --prompt "list enabled tools"`
- `uv run lily tui --config .lily/config/agent.yaml`
- `just lint`
- `just format-check`
- `just types`
- `just test`
- `just quality && just test`

## Definition of Visible Done

A human can:
- Open `.lily/config/agent.yaml` and change model/provider/tool allowlist values.
- Launch a basic Textual UI and exchange at least one prompt/response with Lily.
- Run one CLI command and observe agent output that reflects the same YAML configuration used by TUI.
- Intentionally break a required YAML field and get a specific, field-level validation error.
- Run quality and test gates without warnings newly introduced by this feature.

---

## IMPLEMENTATION PLAN

Use markdown checkboxes (`- [ ]`) for implementation phases and task bullets so execution progress can be tracked live.

### Phase 1: Runtime Contracts + YAML Schema

**Intent Lock**
- Source-of-truth references:
  - LangChain agents/tool docs.
  - `.ai/SPECS/001-reboot/LILY_ARCHITECTURE.md` sections 3, 4, 17.
- Must:
  - Define strict typed config models for agent/model/tools/policies.
  - Load YAML deterministically with field-level validation errors.
  - Support config composition for base + environment override.
- Must Not:
  - Execute agent logic yet.
  - Add hidden fallback defaults for required keys.
- Provenance mapping:
  - Reboot policy constraints -> config schema policy block.
  - LangChain runtime expectations -> model/tool config blocks.
- Acceptance gates:
  - Unit tests for valid/invalid YAML paths.
  - `just lint && just types && just test`.

**Tasks:**
- [x] Create `config_schema.py` with pydantic models.
- [x] Create `config_loader.py` with YAML parser + merge + validation.
- [x] Add unit tests for schema and loader failure modes.

### Phase 2: LangChain Kernel Wrapper

**Intent Lock**
- Source-of-truth references:
  - LangChain `create_agent` docs.
  - `.ai/SPECS/001-reboot/PRD.md` section 5 kernel responsibilities.
- Must:
  - Implement `AgentRuntime` wrapper that instantiates and invokes LangChain agent.
  - Enforce runtime policies (max iterations, timeout, allowlisted tools) via wrapper/middleware.
  - Return deterministic final response contract.
- Must Not:
  - Reimplement a custom ReAct loop in parallel with LangChain.
  - Hardcode provider-specific behavior in runtime core.
- Provenance mapping:
  - "LangChain agent is kernel" user direction -> runtime wrapper centered on `create_agent`.
- Acceptance gates:
  - Integration test proving tool call cycle and final answer.
  - Unknown/disallowed tool paths fail cleanly.

**Tasks:**
- [x] Add `model_factory.py` with provider registry dispatch.
- [x] Add `model_router.py` with YAML-driven dynamic model routing middleware.
- [x] Add `tool_registry.py` with allowlist filtering.
- [x] Add `agent_runtime.py` using LangChain agent APIs.
- [x] Add integration tests for core execution behavior and dynamic model selection paths.

### Phase 3: Supervisor + CLI + Config Wiring

**Intent Lock**
- Source-of-truth references:
  - `pyproject.toml` script contract (`lily.cli:app`).
  - Reboot docs on single supervisor entrypoint.
- Must:
  - Provide CLI run command using YAML config path.
  - Wire supervisor constructor to runtime + registries.
  - Produce clear user-facing output and actionable error messages.
- Must Not:
  - Add sub-agent framework in this phase.
  - Add registry/evolution subsystems beyond required bootstrap.
- Provenance mapping:
  - Kernel-first roadmap -> one runnable supervisor command.
- Acceptance gates:
  - E2E smoke test for CLI run with test config.
  - `just quality && just test` passes.

**Tasks:**
- [x] Create `src/lily/agents/lily_supervisor.py` and `src/lily/cli.py`.
- [x] Add baseline `.lily/config/*.yaml` templates.
- [x] Add e2e test for CLI with fixture config.

### Phase 4: Basic Textual TUI

**Intent Lock**
- Source-of-truth references:
  - Textual guide/tutorial docs.
  - `pyproject.toml` entrypoint contract and runtime modules from prior phases.
- Must:
  - Implement a minimal Textual UI with transcript pane and prompt input.
  - Route prompt submission to the same `LilySupervisor` runtime path as CLI.
  - Read the same YAML config schema used by CLI runtime.
- Must Not:
  - Build advanced multi-screen workflows, async job orchestration, or visual polish beyond baseline usability.
  - Fork business logic between CLI and TUI.
- Provenance mapping:
  - User requirement for basic TUI -> `src/lily/ui/*` and `lily tui` command.
  - Kernel consistency -> single runtime path shared by interfaces.
- Acceptance gates:
  - E2E smoke test for TUI startup and one prompt cycle (test harness appropriate for Textual).
  - `just lint && just types && just test`.

**Tasks:**
- [x] Add Textual dependency and minimal `src/lily/ui/` app structure.
- [x] Implement chat input + transcript output using supervisor runtime.
- [x] Add `lily tui` command and tests for startup/interaction path.

### Phase 5: Guardrails + Documentation

**Intent Lock**
- Source-of-truth references:
  - `.ai/RULES.md` warning policy and docs hygiene requirements.
  - LangChain middleware/guardrails references.
- Must:
  - Document config schema and runtime policy behavior.
  - Ensure warning-clean quality/test runs.
  - Record deferred items explicitly (skill registry/sub-agents/logging depth).
- Must Not:
  - Expand scope into hybrid skills implementation.
- Provenance mapping:
  - Phase boundary protection from reboot roadmap.
- Acceptance gates:
  - Docs updated for runtime usage.
  - `just quality && just test` final gate.

**Tasks:**
- [x] Add developer docs for runtime YAML config and CLI usage.
- [x] Add explicit deferred roadmap notes in docs/dev surfaces as needed.
- [x] Run and record final quality/test gate output in execution report.

---

## Risks And Mitigations

- Risk: LangChain internals evolve and break thin wrapper assumptions.
  - Mitigation: isolate LangChain touchpoints in `agent_runtime.py` and `model_factory.py`; keep integration tests focused on contracts.
- Risk: YAML sprawl or ambiguous config precedence.
  - Mitigation: explicit precedence rules (base -> env override -> CLI flags), documented and tested.
- Risk: Provider-specific differences (OpenAI vs Ollama) leak into core.
  - Mitigation: provider registry dispatch with provider-specific adapters.

## Non-Goals For This Feature

- Implementing full hybrid skill system (playbook/procedure/agent skills).
- Implementing long-term memory or autonomous evolution engine.
- Building a multi-agent supervisor graph.
- Building advanced Textual UX (multi-pane workflow builder, history browser, theme system).

## Test Plan Summary

- Unit:
  - YAML schema validation and helpful errors.
  - Provider dispatch and tool allowlist behavior.
- Integration:
  - Runtime invoke path with tool-call roundtrip.
  - Policy enforcement (iteration/timeout/disallowed tools).
- E2E:
  - CLI run command using YAML config fixture.
  - TUI startup and prompt/response path using YAML config fixture.
- Final gate:
  - `just quality && just test`.

## Execution Report

### 2026-03-04 — Phase 1: Runtime Contracts + YAML Schema (Completed)

- Status: completed
- Phase intent check: completed before implementation using:
  - `.ai/COMMANDS/phase-intent-check.md`
  - `.ai/RULES.md`
  - `.ai/SPECS/001-reboot/LILY_ARCHITECTURE.md` sections 3, 4, 17
  - LangChain docs references listed in this plan
- Must / Must Not adherence:
  - Implemented strict typed config contracts for agent/model/tools/policies.
  - Implemented deterministic YAML loading + merge (base + override) and field-level validation errors.
  - Did not add runtime execution logic.
  - Did not add silent defaults for missing required fields.

Artifacts created:
- `src/lily/runtime/__init__.py`
- `src/lily/runtime/config_schema.py`
- `src/lily/runtime/config_loader.py`
- `tests/unit/runtime/test_config_loader.py`

Commands run and outcomes:
- `just lint` -> pass
- `just types` -> pass
- `just test` -> initially fail (AAA structure comments required by `pytest-drill-sergeant`), then pass after test updates
- `just lint && just types && just test` -> pass
- `just docs-check` -> fail (pre-existing repo issue: `docs/ideas/reboot.md` missing frontmatter)
- `just status` -> pass

Acceptance gate evidence:
- Unit tests cover:
  - valid config parsing
  - missing required field errors
  - top-level non-mapping YAML errors
  - recursive base/override merge behavior
  - invalid dynamic-routing profile references
- Phase acceptance gate (`just lint && just types && just test`) passed.

Partial/blocked items:
- Status-sync `docs-check` remains blocked by pre-existing non-phase doc issue:
  - `docs/ideas/reboot.md` missing frontmatter block.

### 2026-03-04 — Blocker Resolution (docs-check)

- Added required frontmatter to `docs/ideas/reboot.md`.
- Re-ran status sync commands:
  - `just docs-check` -> pass
  - `just status` -> pass

### 2026-03-04 — Phase 2: LangChain Kernel Wrapper (Completed)

- Status: completed
- Phase intent check: completed and locked for `Phase 2: LangChain Kernel Wrapper`.
- Must / Must Not adherence:
  - Implemented `AgentRuntime` wrapper around LangChain `create_agent`.
  - Enforced policies via runtime timeout and recursion limit plus allowlisted tools.
  - Implemented YAML-driven dynamic model routing middleware via `wrap_model_call`.
  - Did not add custom parallel ReAct loop logic.
  - Kept provider handling isolated in a dispatch registry.

Artifacts created:
- `src/lily/runtime/model_factory.py`
- `src/lily/runtime/model_router.py`
- `src/lily/runtime/tool_registry.py`
- `src/lily/runtime/agent_runtime.py`
- `tests/integration/test_agent_runtime.py`

Commands run and outcomes:
- `just lint` -> pass
- `just types` -> pass
- `just test` -> pass
- `just lint && just types && just test` -> pass
- `just docs-check` -> pass
- `just status` -> pass

Acceptance gate evidence:
- Integration tests now cover:
  - tool-call cycle with final response extraction
  - unknown/disallowed tool allowlist failure path
  - dynamic model routing switching model by prompt complexity
- Phase acceptance gates passed.

### 2026-03-04 — Phase 3: Supervisor + CLI + Config Wiring (Completed)

- Status: completed
- Phase intent check: completed and locked for `Phase 3: Supervisor + CLI + Config Wiring`.
- Must / Must Not adherence:
  - Added CLI run command with explicit YAML config path support.
  - Added supervisor constructor wiring runtime + built-in tools.
  - Added actionable CLI error rendering using Rich panel output.
  - Did not add sub-agent framework or registry/evolution expansion.

Artifacts created:
- `src/lily/agents/__init__.py`
- `src/lily/agents/lily_supervisor.py`
- `src/lily/cli.py`
- `.lily/config/agent.yaml`
- `.lily/config/tools.yaml`
- `tests/e2e/test_cli_agent_run.py`

Commands run and outcomes:
- `just lint && just types && just test` -> pass
- `just quality && just test` -> pass
- `just docs-check` -> pass (within quality)

Acceptance gate evidence:
- E2E smoke test `tests/e2e/test_cli_agent_run.py` passes.
- Phase acceptance gate `just quality && just test` passes.

### 2026-03-04 — Phase 4: Basic Textual TUI (Completed)

- Status: completed
- Phase intent check: completed and locked for `Phase 4: Basic Textual TUI`.
- Must / Must Not adherence:
  - Added minimal Textual TUI with transcript and prompt input.
  - Routed prompt execution through the same `LilySupervisor` runtime path used by CLI.
  - Reused YAML config path inputs (`--config`, `--override`) via `lily tui`.
  - Did not add advanced multi-screen workflows or duplicate business logic.

Artifacts created/updated:
- `pyproject.toml` (added `textual` dependency)
- `uv.lock` (dependency lock update)
- `src/lily/ui/__init__.py`
- `src/lily/ui/app.py`
- `src/lily/ui/screens/chat.py`
- `src/lily/ui/widgets/transcript.py`
- `src/lily/ui/styles/app.tcss`
- `src/lily/cli.py` (added `tui` command)
- `tests/e2e/test_tui_app.py`

Commands run and outcomes:
- `just lint && just types && just test` -> pass
- `just quality && just test` -> pass
- `just docs-check` -> pass
- `just status` -> pass

Acceptance gate evidence:
- E2E smoke test `tests/e2e/test_tui_app.py` verifies startup and one prompt cycle.
- Phase acceptance gate `just lint && just types && just test` passes.

### 2026-03-04 — Phase 5: Guardrails + Documentation (Completed)

- Status: completed
- Phase intent check: completed and locked for `Phase 5: Guardrails + Documentation`.
- Must / Must Not adherence:
  - Added developer-facing runtime/config/interface documentation.
  - Added explicit deferred internal roadmap items for next slices.
  - Kept scope out of hybrid skill implementation details.

Artifacts created/updated:
- `docs/dev/references/runtime-config-and-interfaces.md`
- `docs/dev/references/README.md`
- `docs/dev/roadmap.md`
- `docs/dev/status.md`

Commands run and outcomes:
- `just quality && just test` -> pass
- `just status` -> pass

Acceptance gate evidence:
- Runtime usage docs now cover YAML schema, policies, CLI/TUI commands, and test surfaces.
- Deferred internal items documented as roadmap IDs: `SI-002`, `SI-003`, `SI-004`.
- Final gate passed warning-clean.
