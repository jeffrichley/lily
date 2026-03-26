# Feature: Named Agents and Identity Context Injection

The following plan should be complete, but it is important to validate documentation and codebase patterns and task sanity before implementation begins.

Pay special attention to strict config validation, deterministic CLI behavior, and the documented middleware context injection contract for special agent markdown files.

---

## Feature Description

Introduce first-class named agents under `.lily/agents/<agent-name>/` with:
- default agent at `.lily/agents/default/`
- CLI selection via `--agent`
- isolated per-agent sessions/memory
- required identity/behavior markdown files
- deterministic middleware injection of those markdown files into model context

This plan is both user-visible and internal: users gain CLI agent selection and maintainers gain a stable foundation for future multi-agent orchestration.

---

## User Story

As a Lily operator
I want to run and resume conversations with specific named agents
So that each agent has isolated memory/session state and a clearly defined identity loaded into runtime context.

---

## Problem Statement

Current runtime assumes a single config-centric agent path (`.lily/config/agent.toml`) and cwd-scoped session persistence. That prevents robust persona isolation and does not provide an explicit contract for identity markdown context files.

---

## Solution Statement

Add an agent resolution layer between CLI and runtime, define a strict agent workspace contract, and add deterministic loading/injection of required special markdown files (`AGENTS.md`, `IDENTITY.md`, `SOUL.md`, `USER.md`, `TOOLS.md`) via middleware.

---

## Feature Metadata

**Feature Type**: Enhancement
**Estimated Complexity**: Medium-High
**Primary Systems Affected**:
- `src/lily/cli.py`
- `src/lily/cli_options.py`
- `src/lily/runtime/conversation_sessions.py` (path usage behavior)
- `src/lily/agents/lily_supervisor.py` (construction path resolution context)
- `docs/dev/references/runtime-config-and-interfaces.md`
- tests in `tests/e2e` and `tests/unit/runtime`

**Dependencies**:
- No new external dependencies required.
- Uses existing runtime/config loader and session store patterns.

---

## Traceability Mapping (Required When Applicable)

- Roadmap system improvements: `None`
- Debt items: `None`
- Debt to roadmap linkage (if debt exists): `N/A`
- `No SI/DEBT mapping for this feature.`

---

## Branch Setup (Required)

Branch naming must follow the plan filename:
- Plan: `.ai/PLANS/008-named-agents-and-identity-context.md`
- Branch: `feat/008-named-agents-and-identity-context`

Commands (must be executable as written):
```bash
PLAN_FILE=".ai/PLANS/008-named-agents-and-identity-context.md"
PLAN_SLUG="$(basename "$PLAN_FILE" .md)"
BRANCH_NAME="feat/${PLAN_SLUG}"
git show-ref --verify --quiet "refs/heads/${BRANCH_NAME}" \
  && git switch "${BRANCH_NAME}" \
  || git switch -c "${BRANCH_NAME}"
```

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `src/lily/cli.py` - existing `run`/`tui` command option and runtime wiring.
- `src/lily/cli_options.py` - shared option definitions for `--config` and `--override`.
- `src/lily/agents/lily_supervisor.py` - config-to-runtime construction boundaries.
- `src/lily/runtime/conversation_sessions.py` - default session DB path and attach semantics.
- `docs/dev/references/runtime-config-and-interfaces.md` - current public runtime contract and deferred boundaries.
- `tests/e2e/test_cli_agent_run.py` - CLI behavior regression/e2e patterns.
- `tests/e2e/test_tui_app.py` - TUI command behavior patterns.

### New Files to Create (Expected)

- `src/lily/runtime/agent_locator.py` - named-agent directory resolution and validation.
- `src/lily/runtime/agent_identity_context.py` - load + structure required special markdown files for injection.
- `tests/unit/runtime/test_agent_locator.py`
- `tests/unit/runtime/test_agent_identity_context.py`

### Relevant Documentation YOU SHOULD READ BEFORE IMPLEMENTING!

- `.ai/SPECS/008-named-agents-and-identity-context/PRD.md`
- [OpenClaw templates directory](https://github.com/openclaw/openclaw/tree/main/docs/zh-CN/reference/templates)
- [AGENTS.md template](https://raw.githubusercontent.com/openclaw/openclaw/main/docs/zh-CN/reference/templates/AGENTS.md)
- [IDENTITY.md template](https://raw.githubusercontent.com/openclaw/openclaw/main/docs/zh-CN/reference/templates/IDENTITY.md)
- [SOUL.md template](https://raw.githubusercontent.com/openclaw/openclaw/main/docs/zh-CN/reference/templates/SOUL.md)
- [TOOLS.md template](https://raw.githubusercontent.com/openclaw/openclaw/main/docs/zh-CN/reference/templates/TOOLS.md)
- [USER.md template](https://raw.githubusercontent.com/openclaw/openclaw/main/docs/zh-CN/reference/templates/USER.md)

### Patterns to Follow

**Naming conventions**
- Permit agent directory names such as `pepper-potts` (kebab-case/hyphens allowed).
- Keep deterministic validation errors with explicit missing path names.

**Error handling**
- Mirror CLI deterministic error pattern: display Rich error panel and exit code 1.

**Config/path behavior**
- Resolve default paths from selected agent directory rather than process cwd where applicable for agent-scoped artifacts.

---

## IMPLEMENTATION PLAN

Use markdown checkboxes (`- [ ]`) for implementation phases and task bullets so execution progress can be tracked live.

### Phase 1: Agent workspace contract and locator

#### Intent Lock
**Source of truth:**
- `.ai/SPECS/008-named-agents-and-identity-context/PRD.md`
- `docs/dev/references/runtime-config-and-interfaces.md` (current contract to be extended)
- `src/lily/cli.py` and `src/lily/agents/lily_supervisor.py`

**Must:**
- Define agent root as `.lily/agents/`.
- Define default agent as `default`.
- Validate required agent files/dirs:
  - `AGENTS.md`, `IDENTITY.md`, `SOUL.md`, `USER.md`, `TOOLS.md`
  - `skills/`, `memory/`
  - runtime config (`agent.toml` or `agent.yaml`) and paired tools config.
- Support directory names like `pepper-potts`.

**Must Not:**
- Do not silently fall back to legacy `.lily/config/*` paths once this feature is active (unless explicitly documented compatibility mode is accepted in implementation review).
- Do not auto-create missing required identity files at runtime.

**Provenance map:**
- Agent identity = folder name.
- Agent contract requirements sourced from PRD + this plan.

**Acceptance gates:**
- Unit tests for valid/missing contract paths.
- `just types` and targeted unit tests pass.

**Tasks:**
- [x] CREATE `agent_locator` with strict validation and deterministic errors.
- [x] ADD tests for naming and missing-path failures.

---

### Phase 2: CLI + runtime selection and per-agent session isolation

#### Intent Lock
**Source of truth:**
- `src/lily/cli.py`
- `src/lily/runtime/conversation_sessions.py`
- `.ai/SPECS/008-named-agents-and-identity-context/PRD.md`

**Must:**
- Add `--agent` to `run` and `tui`.
- Default to `default` agent when no flag is provided.
- Use per-agent session DB path.
- Resolve runtime config and relative resources from selected agent directory.

**Must Not:**
- Do not allow ambiguous precedence behavior without explicit rules (`--agent` + `--config` conflict policy must be deterministic).
- Do not share session DB across agents.

**Provenance map:**
- Session isolation requirement from PRD user stories.
- Relative path requirement from user intent.

**Acceptance gates:**
- E2E tests:
  - default agent run
  - named agent run
  - missing agent failure
  - attach-last isolation per agent

**Tasks:**
- [x] UPDATE CLI options and command signatures.
- [x] UPDATE session path resolution to selected agent scope.
- [x] ADD e2e coverage in CLI tests.

---

### Phase 3: Identity markdown context injection via middleware (special files)

#### Intent Lock
**Source of truth:**
- `.ai/SPECS/008-named-agents-and-identity-context/PRD.md`
- OpenClaw template references (identity file semantics)

**Must:**
- Load and inject the required special markdown files:
  - `AGENTS.md`
  - `IDENTITY.md`
  - `SOUL.md`
  - `USER.md`
  - `TOOLS.md`
- Define fixed injection order and deterministic formatting.
- Inject personality/context through dedicated runtime middleware right before model invocation.
- Ensure injection is documented as part of runtime contract.

**Must Not:**
- Do not inject files in nondeterministic filesystem order.
- Do not silently skip missing required files.
- Do not rely on static startup-time system prompt mutation for personality layer injection.

**Provenance map:**
- Context payload keys map one-to-one to required markdown files.

**Acceptance gates:**
- Unit tests for order/content assembly.
- Integration or runtime tests confirming injected context appears in final system context path.

**Tasks:**
- [x] CREATE identity context loader module.
- [x] CREATE personality/context middleware for identity injection.
- [x] UPDATE runtime/supervisor pipeline to include middleware-based identity context injection.
- [x] ADD tests for exact file order and required-file enforcement.

---

### Phase 4: Documentation and migration updates

#### Intent Lock
**Source of truth:**
- `docs/dev/references/runtime-config-and-interfaces.md`
- `.ai/SPECS/008-named-agents-and-identity-context/PRD.md`

**Must:**
- Add a dedicated doc section that explicitly defines:
  - the required special markdown files
  - the context injection contract (order + behavior + failure semantics)
  - agent directory contract under `.lily/agents/<name>/`
  - migration from `.lily/config/*` to `.lily/agents/default/*`

**Must Not:**
- Do not leave context injection behavior undocumented.
- Do not describe identity files as optional.

**Provenance map:**
- Doc contract directly reflects phase 1-3 implementation contracts.

**Acceptance gates:**
- `just docs-check`
- Manual spot-check examples in docs are executable and accurate.

**Tasks:**
- [ ] UPDATE runtime reference docs with new named-agent and context injection sections.
- [ ] ADD examples for `run`/`tui` with `--agent`.

---

## STEP-BY-STEP TASKS

### CREATE `src/lily/runtime/agent_locator.py`
- **IMPLEMENT**: Resolve `.lily/agents/<name>/` and validate required files/dirs.
- **PATTERN**: Follow deterministic error style used in config/session validation.
- **VALIDATE**: `uv run pytest tests/unit/runtime/test_agent_locator.py -q`

### UPDATE `src/lily/cli.py` and `src/lily/cli_options.py`
- **IMPLEMENT**: add `--agent` and route run/tui through locator.
- **GOTCHA**: define and enforce conflict policy for `--agent` + `--config`.
- **VALIDATE**: `uv run pytest tests/e2e/test_cli_agent_run.py -q`

### UPDATE session scoping behavior
- **IMPLEMENT**: derive session DB path from selected agent directory.
- **VALIDATE**: e2e attach-last tests across two agents.

### CREATE `src/lily/runtime/agent_identity_context.py`
- **IMPLEMENT**: read required markdown files in fixed order and assemble injection block.
- **VALIDATE**: `uv run pytest tests/unit/runtime/test_agent_identity_context.py -q`

### UPDATE runtime/supervisor context path
- **IMPLEMENT**: inject assembled identity context into runtime model context pipeline via middleware.
- **VALIDATE**: integration tests for context inclusion.

### UPDATE docs
- **IMPLEMENT**: add named-agent contract + **special markdown context injection** section.
- **VALIDATE**: `just docs-check`

---

## TESTING STRATEGY

### Unit Tests
- Agent locator: naming, required files, error cases.
- Identity context loader: required files, stable ordering, deterministic formatting.

### Integration / E2E Tests
- CLI run/tui with default and named agents.
- Session attach-last isolation between agents.
- Runtime context injection behavior.

### Edge Cases
- Hyphenated names (`pepper-potts`).
- Missing one required markdown file.
- Missing `skills/` or `memory/`.
- Agent exists but config pairing invalid.

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style
- `just format-check`
- `just lint`

### Level 2: Types + Unit
- `just types`
- `uv run pytest tests/unit/runtime/test_agent_locator.py -q`
- `uv run pytest tests/unit/runtime/test_agent_identity_context.py -q`

### Level 3: E2E/Integration
- `uv run pytest tests/e2e/test_cli_agent_run.py -q`
- `uv run pytest tests/e2e/test_tui_app.py -q`

### Level 4: Final Gate
- `just quality && just test`

---

## OUTPUT CONTRACT (Required For User-Visible Features)

- Exact output artifacts/surfaces:
  - CLI flag behavior: `lily run --agent <name>`, `lily tui --agent <name>`
  - Agent workspace contract in docs
  - Special markdown context injection contract in docs
- Verification commands:
  - CLI e2e test commands above
  - `just docs-check`

## DEFINITION OF VISIBLE DONE (Required For User-Visible Features)

- A human can directly verify completion by:
  - creating `.lily/agents/default/` and `.lily/agents/pepper-potts/`
  - running `lily run --agent pepper-potts --prompt "hello"`
  - confirming sessions are isolated by agent
  - reading runtime docs and finding explicit special markdown context injection contract

## INPUT/PREREQUISITE PROVENANCE (Required When Applicable)

- Generated during this feature:
  - New PRD and plan artifacts under `.ai/SPECS/008-*` and `.ai/PLANS/008-*`.
- Pre-existing dependency:
  - Existing runtime + CLI scaffolding under `src/lily`.

---

## ACCEPTANCE CRITERIA

- [ ] Named agents are resolved from `.lily/agents/<agent-name>/`.
- [ ] `default` agent is used when `--agent` is absent.
- [ ] Hyphenated agent names (e.g. `pepper-potts`) are supported.
- [ ] Sessions are scoped per agent.
- [ ] Required special markdown files are enforced.
- [ ] Runtime injects special markdown files via middleware in deterministic order.
- [ ] Runtime docs include explicit section for special markdown context injection.
- [ ] `just quality && just test` passes warning-clean.

---

## COMPLETION CHECKLIST

- [ ] All phase tasks completed in dependency order.
- [ ] Unit + integration/e2e validation executed.
- [ ] Docs updated and verified.
- [ ] Acceptance criteria satisfied.

---

## NOTES

- This plan intentionally includes a dedicated documentation requirement for "special markdown context injection" per user request.
- Implementation should prefer small, reversible diffs and deterministic runtime behavior.

---

## Execution Report

### 2026-03-26 - Phase 1: Agent workspace contract and locator

- Status: Completed
- Completed tasks:
  - Created `src/lily/runtime/agent_locator.py` with strict named-agent workspace validation.
  - Added `tests/unit/runtime/test_agent_locator.py` for:
    - default root/name helpers
    - hyphenated names (`pepper-potts`)
    - missing required markdown/dir failures
    - config/tools pairing (`agent.toml` -> `tools.toml`, `agent.yaml` -> `tools.yaml`)
- Validation evidence:
  - `uv run pytest tests/unit/runtime/test_agent_locator.py -q` -> pass (9 passed)
  - `just types` -> pass
  - `just docs-check` -> pass
  - `just status` -> pass
- Phase intent lock compliance:
  - Must: agent root/default, strict required files/dirs, hyphenated name support -> implemented.
  - Must Not: silent legacy fallback and auto-create of required files -> preserved by fail-fast errors.

### 2026-03-26 - Phase 2: CLI + runtime selection and per-agent session isolation

- Status: Completed
- Completed tasks:
  - Updated `src/lily/cli.py` to add `--agent` for `run` and `tui`.
  - Added runtime mode resolver with deterministic conflict handling:
    - `--agent` and `--config` together -> error (`Choose only one runtime mode`).
  - Wired named-agent path resolution through `resolve_agent_workspace`.
  - Updated conversation resolution to scope session DB by selected workspace root.
  - Extended E2E coverage in:
    - `tests/e2e/test_cli_agent_run.py`
    - `tests/e2e/test_tui_app.py`
- Validation evidence:
  - `uv run pytest tests/e2e/test_cli_agent_run.py tests/e2e/test_tui_app.py -q` -> pass (12 passed)
  - `just types` -> pass
  - `just docs-check` -> pass
  - `just status` -> pass
- Phase intent lock compliance:
  - Must: `--agent` support, default `default` behavior, per-agent session scoping -> implemented.
  - Must Not: ambiguous runtime precedence and shared session DB -> prevented by explicit mode conflict + scoped DB root.

### 2026-03-26 - Phase 3: Identity markdown context injection via middleware

- Status: Completed
- Completed tasks:
  - Created `src/lily/runtime/agent_identity_context.py` to load required special
    markdown files in fixed order:
    - `AGENTS.md`, `IDENTITY.md`, `SOUL.md`, `USER.md`, `TOOLS.md`
  - Created `src/lily/runtime/agent_identity_injection_middleware.py` with
    `SystemPromptAgentIdentityMiddleware`.
  - Updated runtime wiring:
    - `AgentRuntime` accepts `agent_identity_context_markdown`
    - identity/personality context is injected via middleware before model calls
  - Updated supervisor and app plumbing:
    - `LilySupervisor.from_config_paths(..., agent_workspace_dir=...)`
    - `LilyTuiApp` / default supervisor factory pass optional workspace dir
    - CLI passes selected agent workspace through to supervisor.
  - Added tests:
    - `tests/unit/runtime/test_agent_identity_context.py`
    - `tests/unit/runtime/test_agent_identity_injection_middleware.py`
    - integration assertion in `tests/integration/test_agent_runtime.py`
- Validation evidence:
  - `uv run pytest tests/unit/runtime/test_agent_identity_context.py tests/unit/runtime/test_agent_identity_injection_middleware.py tests/integration/test_agent_runtime.py -q` -> pass
  - `uv run pytest tests/e2e/test_cli_agent_run.py tests/e2e/test_tui_app.py -q` -> pass
  - `just types` -> pass
- Phase intent lock compliance:
  - Must: middleware-based identity injection with deterministic ordering and documentation contract compatibility -> implemented.
  - Must Not: static startup-only mutation path for personality layer -> avoided; injection occurs via middleware.
