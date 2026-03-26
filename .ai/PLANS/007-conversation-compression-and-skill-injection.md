# Feature: Conversation Compression + Skill Injection Modes

The following plan should be complete, but it is important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models, and mirror strict config validation patterns (Pydantic) and deterministic error messaging.

---

## Feature Description
Implement two internal runtime improvements:

1. **BL-001**: Add conversation compression/summarization policy to reduce token usage while preserving long-session continuity.
2. **BL-002**: Experiment with LangChain middleware strategies for system-prompt skill catalog injection.

Both improvements must preserve Lily’s existing runtime/tool contracts:
- Tool allowlists remain authoritative.
- `skill_retrieve` retrieval behavior remains unchanged.
- Existing session attach/resume continues to work.

---

## User Story
As a Lily operator and runtime engineer
I want long conversations to remain efficient and skill injection to be testable/configurable
So that runs stay within token budgets and prompt injection behavior is auditable and deterministic.

---

## Problem Statement
- Long conversations grow token usage because the agent sees the full checkpointed message history on subsequent turns.
- Skill catalog injection currently happens by mutating the `system_prompt` during agent construction, which makes it harder to experiment with alternative injection points that might be more deterministic or easier to reason about.

---

## Solution Statement
- Add a configuration-driven conversation compression policy using LangChain’s built-in `SummarizationMiddleware` (or a thin wrapper around it).
- Add middleware-based skill catalog injection (LangChain `AgentMiddleware`): rewrite the model request system message right before model invocation.

---

## Feature Metadata
**Feature Type**: Internal engineering task  
**Estimated Complexity**: High  
**Primary Systems Affected**:
- `src/lily/runtime/agent_runtime.py`
- `src/lily/runtime/config_schema.py`
- `src/lily/runtime/agent_runtime.py` middleware wiring
- `src/lily/runtime/skill_prompt_injector.py` (catalog formatting stays the same)
- New runtime modules (likely):
  - `src/lily/runtime/conversation_compression.py` (optional wrapper)
  - `src/lily/runtime/skill_catalog_injection_middleware.py` (middleware strategy)
- Tests:
  - `tests/integration/test_agent_runtime.py`
  - new unit tests for middleware behavior
**Dependencies**:
- Existing LangChain/LangGraph runtime in repo dependencies.
- Use `langchain.agents.middleware.summarization.SummarizationMiddleware` (no new deps).

---

## Traceability Mapping (Required When Applicable)

- Roadmap system improvements: `None`
- Debt items: `DEBT-019, DEBT-020`
- Debt to roadmap linkage (if debt exists): `N/A`
- These debts are tracked for visibility alongside this plan's work; this plan should
  not mask SSE adapter output (DEBT-019) and should ensure secret scanning is
  enforced as part of the commit workflow (DEBT-020).

---

## Branch Setup (Required)
Branch naming must follow the plan filename:
- Plan: `.ai/PLANS/007-conversation-compression-and-skill-injection.md`
- Branch: `feat/007-conversation-compression-and-skill-injection`

Commands (must be executable as written):
```bash
PLAN_FILE=".ai/PLANS/007-conversation-compression-and-skill-injection.md"
PLAN_SLUG="$(basename "$PLAN_FILE" .md)"
BRANCH_NAME="feat/${PLAN_SLUG}"
git show-ref --verify --quiet "refs/heads/${BRANCH_NAME}" \
  && git switch "${BRANCH_NAME}" \
  || git switch -c "${BRANCH_NAME}"
```

---

## CONTEXT REFERENCES
### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!
- `src/lily/runtime/agent_runtime.py` (lines 219-263) - middleware list assembly and current system-prompt catalog append behavior.
- `src/lily/runtime/agent_runtime.py` (lines 273-321) - invoke payload + thread_id wiring; establishes checkpoint continuity inputs.
- `src/lily/runtime/skill_prompt_injector.py` - format of the catalog block injected into system prompt (summaries only).
- `src/lily/runtime/config_schema.py` (not yet extended) - where `PoliciesConfig` and `SkillsConfig` must gain new config fields.
- `tests/integration/test_agent_runtime.py` (lines ~364-396) - checkpoint persistence test (same conversation id yields longer message history).
- `tests/integration/test_agent_runtime.py` (lines ~398-456) - existing test for system prompt skill catalog append.

### Relevant Architecture/Docs (Source-of-truth helpers)
- `.ai/SPECS/003-conversation-compression-and-skill-injection/PRD.md` - this plan’s PRD.
- `.ai/SPECS/002-skills-system/SKILLS_ARCHITECTURE.md` (GoF Strategy, strategy injection) - guidance that supports swapping catalog injection strategies without rewriting flow.

### New Files to Create
- `src/lily/runtime/skill_catalog_injection_middleware.py` - implement `AgentMiddleware` strategy for middleware-based skill catalog injection.
- `src/lily/runtime/conversation_compression.py` (optional) - thin wrapper to translate Lily config -> `SummarizationMiddleware` instance.
- `tests/unit/runtime/test_skill_catalog_injection_middleware.py` (expected) - unit tests for request/system message mutation.
- `tests/unit/runtime/test_conversation_compression.py` (expected) - unit tests for compression trigger/no-trigger decisions (may require stubs).
- Update existing tests in `tests/integration/test_agent_runtime.py` (expected) to add integration coverage for persistence after compression.

---

## IMPLEMENTATION PLAN

Use markdown checkboxes (`- [ ]`) for implementation phases and task bullets so execution progress can be tracked live.

### Phase 1: Config contracts and runtime wiring surface
- [x] Define strict Pydantic config models for:
  - Conversation compression (BL-001): enable/disable, trigger type (tokens/messages/fraction), threshold values, keep policy.
  - Skill catalog injection middleware (BL-002).
- [x] Update `AgentRuntime` construction to consume these config fields.

#### Intent Lock
**Source of truth:**
- `.ai/SPECS/003-conversation-compression-and-skill-injection/PRD.md`
- `src/lily/runtime/agent_runtime.py` (middleware list + system prompt injection)
- `src/lily/runtime/config_schema.py` (strict validation patterns; `extra="forbid"`)

**Must:**
- Add new config fields with strict validation (no silent defaults for required contract values).
- Set defaults such that existing behavior does not change:
  - conversation compression default is **disabled**

**Must Not:**
- Must not change tool allowlist behavior or retrieval authorization.
- Must not introduce runtime-only “magic” config parsing in random files; config schema is the single source of truth.

**Provenance map:**
- `policies.max_*` remains authoritative for agent loop limits; compression must be configured independently.
- `system_prompt` remains the base input; middleware mode must only append the catalog block.

**Acceptance gates:**
- `just types` passes.
- New/updated unit tests for config parsing/validation pass.

---

### Phase 2: Conversation compression (BL-001) implementation
- [x] Integrate `langchain.agents.middleware.summarization.SummarizationMiddleware` into runtime middleware list when enabled.
- [x] Ensure compression modifies checkpointed message state (summary persists for subsequent turns).
- [x] Add unit + integration tests verifying:
  - compression triggers when thresholds are exceeded
  - recent messages are preserved
  - message history is compacted and stays compact across subsequent turns

#### Intent Lock
**Source of truth:**
- `.ai/SPECS/003-conversation-compression-and-skill-injection/PRD.md` (BL-001)
- `tests/integration/test_agent_runtime.py` (checkpoint history persistence)
- `langchain.agents.middleware.summarization.SummarizationMiddleware` behavior:
  - operates via `before_model`/`abefore_model` and returns state updates for `AgentState["messages"]`

**Must:**
- Only enable compression when `skills`/runtime config says it is enabled.
- Configure summarization with:
  - `trigger` based on selected config
  - `keep` based on “verbatim tail” policy
- Ensure the summary replaces older context using LangChain middleware semantics (do not re-implement summarization logic locally).

**Must Not:**
- Must not interfere with `ToolCallLimitMiddleware` or `ModelCallLimitMiddleware` semantics.
- Must not break the existing `thread_id` continuity behavior.

**Provenance map:**
- Summary persistence is achieved by middleware returning state updates that mutate `AgentState["messages"]` (checkpoint saves updated state).

**Acceptance gates:**
- Unit tests for trigger/no-trigger and message replacement pass.
- Integration test asserts that repeated runs with the same `conversation_id` include compressed history rather than unbounded growth.

---

### Phase 3: Skill catalog injection (BL-002)
- [x] Wire middleware-based skill catalog injection into model calls.
- [x] Implement middleware-based injection by mutating model request `system_message`
  right before model invocation.
- [x] Ensure `skill_catalog_injected` telemetry is emitted for the middleware path.

#### Intent Lock
**Source of truth:**
- `.ai/SPECS/003-conversation-compression-and-skill-injection/PRD.md` (BL-002)
- `.ai/SPECS/002-skills-system/SKILLS_ARCHITECTURE.md` Strategy pattern guidance for multiple injection strategies
- `src/lily/runtime/agent_runtime.py` (middleware append)
- `src/lily/runtime/skill_prompt_injector.py` (catalog formatting)
- `src/lily/runtime/skill_events.py` / telemetry patterns for stable event schema

**Must:**
- Implement a dedicated `AgentMiddleware` for middleware-based injection.
- Middleware must append the same formatted catalog block (byte-for-byte string equality after newline normalization where needed).
- Ensure middleware mode does not drop the base system instructions.

**Must Not:**
- Must not duplicate catalog appends (must ensure “exactly once per model call” semantics).
- Must not change `skill_retrieve` tool behavior.

**Provenance map:**
- Injection strategy boundary is internal-only: middleware is always used for catalog injection.

**Acceptance gates:**
- Unit tests for middleware injection verify request system message content includes the catalog block.
- Existing test for pre-build injection remains green (or updated to match default config expectations).
- Integration test (or unit test) ensures telemetry event `skill_catalog_injected` fires for both strategies.

---

### Phase 4: Test hardening, debt closure + docs/status sync
- [x] Add/extend tests for both features.
- [x] Run full quality/test gates (`just quality && just test`).
- [x] Update runtime config docs to include the new fields (if user-visible docs surface exists).
- [x] Close **DEBT-019** (fix/resolve why `Unknown SSE event: endpoint` is produced for MCP `streamable_http` tools; do not “mask” output without understanding it).
- [x] Close **DEBT-020** (ensure commit-time secret scanning is enforced so API keys cannot be committed).

#### Intent Lock
**Source of truth:**
- `.ai/RULES.md` required quality gates
- `docs/dev/references/runtime-config-and-interfaces.md` (config surfaces + documented contracts)
- `docs/dev/debt/debt_tracker.md` (DEBT-019/DEBT-020 intent and remediation requirements)

**Must:**
- Add validation commands for every new/updated test file.
- Run final gates: `just quality && just test`.

**Must Not:**
- Must not leave any failing tests or linter/type errors.
- Must not introduce warning regressions without documenting rationale.

**Acceptance gates:**
- `just quality && just test` is green.
- `just docs-check` and `just status` pass if docs are updated.

---

## STEP-BY-STEP TASKS
IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### 1. CREATE config models and update schema
- **IMPLEMENT**: Extend `PoliciesConfig` with a nested `conversation_compression` config model (enabled/trigger/keep).
- **REMOVE**: No `skills.catalog_injection_strategy` config surface is required; catalog injection is middleware-only.
- **IMPORTS**: `pydantic`, `typing.Literal`, existing patterns in `config_schema.py`.
- **GOTCHA**: `extra="forbid"` means every new field must be added explicitly.
- **VALIDATE**: `just types` and `uv run pytest tests/unit/runtime/test_config_loader.py -q` (or add new targeted config tests).

### 2. UPDATE `src/lily/runtime/agent_runtime.py` to wire compression + injection strategy
- **IMPLEMENT**: Add conditional middleware construction:
  - if compression enabled => append `SummarizationMiddleware(model=<chosen profile>, trigger=..., keep=...)`
  - if a non-empty skill catalog exists => append `SystemPromptSkillCatalogMiddleware` (no build-time `system_prompt` mutation)
- **PATTERN**: preserve existing middleware list pattern and keep deterministic tool allowlist behavior.
- **GOTCHA**: middleware order affects behavior; codify order intentionally and test it.
- **VALIDATE**: `uv run pytest tests/integration/test_agent_runtime.py -q`

### 3. CREATE skill injection middleware
- **IMPLEMENT**: `SystemPromptSkillCatalogMiddleware`:
  - holds `catalog_markdown` and newline normalization rules
  - in `wrap_model_call` / `awrap_model_call`:
    - build new `SystemMessage(content=<base_system_content> + "\n\n" + catalog)`
    - call handler with `request.override(system_message=<new>)`
- **VALIDATE**: `uv run pytest tests/integration/test_agent_runtime.py -q -k skill_catalog_injection`

### 4. CREATE/UPDATE compression tests
- **IMPLEMENT**:
  - unit tests for summarization trigger: ensure state message list is replaced when threshold is exceeded
  - integration test using checkpointed conversation id to ensure summary persists across runs
- **VALIDATE**: `uv run pytest tests/unit/runtime -k compression -q` and updated integration tests.

### 5. UPDATE docs (if applicable)
- **IMPLEMENT**: Extend `docs/dev/references/runtime-config-and-interfaces.md` with:
  - new config fields under `policies` and `skills`
  - examples for both strategies
- **VALIDATE**: `just docs-check` and `just status`

### 6. Close DEBT-019 (SSE adapter “Unknown SSE event: endpoint”)
- **IMPLEMENT**:
  - Reproduce the stderr output in a minimal, deterministic run using the default MCP tool path (e.g. `langgraph_docs` via `streamable_http`):
    - run `uv run lily run --config .lily/config/agent.toml --prompt <prompt_that_triggers_langgraph_docs_tool_call>`
    - capture the exact stderr line(s) containing `Unknown SSE event: endpoint`
  - Determine root cause layer:
    - identify whether the MCP server emits a non-standard SSE event name (`endpoint`) or whether the adapter lacks support for it
    - record current versions relevant to SSE handling (e.g. `langchain-mcp-adapters` and any MCP client packages)
  - Fix at the correct layer (preferred outcomes):
    1. upgrade the relevant dependency so `endpoint` is recognized/handled
    2. adjust adapter-side SSE event mapping/handlers so `endpoint` is treated as an expected event
    3. if upstream requires change, implement a Lily-side translation/handling that resolves the “unknown” classification without hiding diagnostics
- **VALIDATE**:
  - re-run the minimal MCP-triggering command and confirm the `Unknown SSE event: endpoint` message is eliminated or replaced by a clearly explained, deterministic diagnostic that reflects the corrected handling.

### 7. Close DEBT-020 (commit-time secret scanning gate)
- **IMPLEMENT**:
  - Ensure local commit workflow fails fast if secrets are detected:
    - Enforce `gitleaks` via git hooks (`pre-commit` hook path), not via `justfile` coupling.
    - Update `.ai/COMMANDS/commit.md` to require hook installation (`just pre-commit-install`) and explicit verification (`uv run pre-commit run gitleaks --all-files`) before commit flow.
    - Ensure server-side git checks fail pushes/PRs on secret findings (independent of local hook installation).
- **VALIDATE**:
  - manual presubmit validation:
    - run `just pre-commit-install` then confirm `git commit` triggers `gitleaks` hook checks
    - run `uv run pre-commit run gitleaks --all-files` and confirm deterministic pass/fail behavior
    - run commit workflow on a branch with no secrets staged and confirm it proceeds
  - CI validation:
    - confirm push/PR secret-scan workflow exists and fails on findings

---

## TESTING STRATEGY
### Unit Tests
- Config schema parsing/validation for new fields.
- `SystemPromptSkillCatalogMiddleware` verifying it modifies system message as intended.
- Compression trigger behavior tests for summary state replacement logic.

### Integration Tests
- Extend `tests/integration/test_agent_runtime.py` checkpoint persistence tests to assert compression is applied across repeated runs.

### Edge Cases
- Compression disabled: no changes to state.
- Compression enabled: summary created once and older messages removed.
- Middleware injection: base system prompt preserved, catalog appended exactly once.
- Skills disabled: injection middleware not created and events not emitted.

---

## VALIDATION COMMANDS
### Level 1: Syntax & Style
- `just format-check`
- `just lint`

### Level 2: Unit Tests
- `uv run pytest tests/unit/runtime -k "compression or skill_catalog_injection" -q`

### Level 3: Integration Tests
- `uv run pytest tests/integration/test_agent_runtime.py -q`

### Level 4: Final Gate
- `just quality && just test`

---

## OUTPUT CONTRACT (Required For User-Visible Features)
- None (internal engineering task; visible surfaces are config + runtime behavior + tests).

---

## DEFINITION OF VISIBLE DONE (Required For User-Visible Features)
- A human can verify completion by running:
  - `just quality && just test`
  - and inspecting CI/test output to confirm:
    - compression triggers and persists
    - skill catalog injection strategy matches chosen mode

---

## ACCEPTANCE CRITERIA
- [x] Conversation compression config is validated by `pydantic` and defaults keep existing behavior unchanged.
- [x] When enabled, summarization compacts message history and persists across repeated turns with same conversation id.
- [x] Skill catalog injection uses middleware only.
- [x] Skill catalog telemetry `skill_catalog_injected` is emitted for the middleware path.
- [x] DEBT-019 is resolved by fixing SSE parsing/handling so `Unknown SSE event: endpoint` is no longer emitted without explanation.
- [x] DEBT-020 is resolved by enforcing a commit-time secret scanning gate (local + CI), so API keys cannot be committed.
- [x] All updated/new tests pass with zero new warnings.

---

## COMPLETION CHECKLIST
- [x] All phases completed (in execution, not in this planning step).
- [x] `just quality && just test` passes.

---

## NOTES
- Prefer using LangChain’s `SummarizationMiddleware` directly rather than re-implementing summarization.
- For middleware injection, ensure deterministic prompt concatenation to keep telemetry and tests stable.

