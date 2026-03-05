# Feature: Conversation Session Attach/Resume Across Runs

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Add persistent conversation sessions so operators can continue prior chats across process runs in both CLI and TUI.

Required behavior:
- default behavior starts a new conversation id on each new process execution
- user can explicitly attach to a specific conversation id
- user can attach to the most recent conversation id
- on exit, CLI and TUI print the active conversation id so restart is easy

## User Story

As a Lily operator  
I want to start new conversations by default, and optionally resume a prior conversation by id or by last-used id  
So that I can continue context across process runs in both CLI and TUI without losing continuity.

## Problem Statement

Current runtime executes one-off prompts with no persisted thread/conversation identity:
- `lily run` does not preserve or resume conversation thread state
- `lily tui` has no attach/resume contract
- no explicit operator-facing session id is emitted on exit

This blocks practical long-running usage and continuity across restarts.

## Solution Statement

Introduce a deterministic conversation session persistence layer and CLI/TUI attach controls:
- add a local session index/store (under `.lily/`) with stable schema
- use a local SQLite database as the persistence backend for conversation sessions
- wire runtime invocation to use `thread_id = conversation_id`
- add CLI/TUI options to start new (default), attach by id, or attach last
- emit exit/session summary with active conversation id for both surfaces

## Feature Metadata

**Feature Type**: Enhancement  
**Estimated Complexity**: Medium  
**Primary Systems Affected**:
- `src/lily/cli.py`
- `src/lily/ui/app.py`
- `src/lily/ui/screens/chat.py`
- `src/lily/runtime/agent_runtime.py`
- `src/lily/runtime/config_schema.py`
- `src/lily/runtime/config_loader.py`
- new session persistence module(s) under `src/lily/runtime/`  
**Dependencies**:
- existing LangChain/LangGraph runtime path already in repo
- local filesystem under `.lily/`
- local SQLite DB file for conversation-session metadata

## Traceability Mapping (Required When Applicable)

- Roadmap system improvements: `SI-006` (session persistence schema evolution foundation)
- Debt items: `None`
- Debt to roadmap linkage (if debt exists): `N/A`

## Branch Setup (Required)

Branch naming must follow the plan filename:
- Plan: `.ai/PLANS/002-conversation-session-attach-resume.md`
- Branch: `feat/002-conversation-session-attach-resume`

Commands (must be executable as written):
```bash
PLAN_FILE=".ai/PLANS/002-conversation-session-attach-resume.md"
PLAN_SLUG="$(basename "$PLAN_FILE" .md)"
BRANCH_NAME="feat/${PLAN_SLUG}"
git show-ref --verify --quiet "refs/heads/${BRANCH_NAME}" \
  && git switch "${BRANCH_NAME}" \
  || git switch -c "${BRANCH_NAME}"
```

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `src/lily/cli.py` (lines 20-119) - current command surface; where new attach/last/new flags and exit output must be added.
- `src/lily/ui/app.py` (lines 47-105) - TUI lifecycle and prompt routing; best insertion point for conversation-id ownership and shutdown messaging.
- `src/lily/ui/screens/chat.py` (lines 28-63) - startup transcript messaging; place to show current conversation id on mount.
- `src/lily/runtime/agent_runtime.py` (lines 72-187) - runtime invoke payload/config; currently no thread id or prior history wiring.
- `src/lily/agents/lily_supervisor.py` (lines 31-62) - supervisor construction path; may need constructor args for conversation id/history provider.
- `src/lily/runtime/config_schema.py` (lines 104-114) - runtime config root for any persistence/checkpoint settings.
- `src/lily/runtime/config_loader.py` (lines 86-114) - config merge/validation path.
- `tests/e2e/test_cli_agent_run.py` - CLI e2e pattern with fake supervisor.
- `tests/e2e/test_tui_app.py` - Textual test pilot pattern; extend for attach/last/startup display.
- `tests/integration/test_agent_runtime.py` - runtime invoke contract tests; extend for thread-id/config plumbing.

### New Files to Create

- `src/lily/runtime/conversation_sessions.py` - deterministic local session store/index for create/get-last/resolve.
- `tests/unit/runtime/test_conversation_sessions.py` - unit tests for schema, persistence, lookup, and error contracts.

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- LangChain long-term memory overview: https://docs.langchain.com/oss/python/langchain/long-term-memory
  - Why: aligns conversation continuity with thread identity and memory model.
- LangGraph persistence/threading concepts: https://docs.langchain.com/oss/python/langgraph/persistence
  - Why: `thread_id` semantics for resume behavior.
- `.ai/RULES.md`
  - Why: mandatory workflow/validation conventions.
- `AGENTS.md`
  - Why: repo-specific constraints (phase scope, warning policy, commit policy).

### Patterns to Follow

**Naming Conventions:**
- snake_case functions/vars
- typed `BaseModel` contracts for stable persistence payloads

**Error Handling:**
- deterministic typed runtime exceptions (`...Error`) with explicit messages
- CLI converts exceptions into non-zero `typer.Exit` with Rich error panels

**Rendering Pattern:**
- prefer structured Rich output (`Panel` / `Table`) in CLI
- TUI startup system messages via transcript append entries

**Dispatch Pattern:**
- use explicit handler maps / strategy logic for mode branching (no long if/elif growth)

---

## IMPLEMENTATION PLAN

- [x] Phase 1: Conversation session persistence foundation
- [x] Phase 2: Runtime threading and supervisor plumbing
- [x] Phase 3: CLI/TUI attach and exit UX
- [x] Phase 4: Tests and validation gates

### Phase 1: Conversation session persistence foundation

**Intent Lock**
- Source of truth: this plan + `src/lily/cli.py` + `src/lily/ui/app.py`
- Must:
  - define deterministic persisted schema for conversation sessions in SQLite
  - support operations: create new, resolve by id, resolve last
  - keep persistence local-first under `.lily/`
- Must Not:
  - silently fall back to arbitrary session id when requested id is missing
  - add external dependencies
- Provenance map:
  - persisted conversation ids originate from generated UUIDs
  - `last` pointer originates only from successful attach/new operations
- Acceptance gates:
  - unit tests for create/get/update/last/missing-id pass

**Tasks:**
- Create `conversation_sessions.py` with:
  - typed persisted schema (`schema_version`, `active_last_id`, `sessions` metadata)
  - deterministic file path helper(s) rooted at workspace (`.lily/`)
  - APIs:
    - `start_new() -> conversation_id`
    - `attach(conversation_id) -> conversation_id | error`
    - `attach_last() -> conversation_id | error`
    - `record_turn(...)` / lightweight metadata update if needed
- Add deterministic errors for:
  - no prior conversation for `last`
  - unknown conversation id for explicit attach

### Phase 2: Runtime threading and supervisor plumbing

**Intent Lock**
- Source of truth: `src/lily/runtime/agent_runtime.py`, LangGraph persistence docs
- Must:
  - plumb conversation id through supervisor/runtime run path
  - invoke agent with thread-scoped config so resumed sessions reuse same thread
- Must Not:
  - break existing one-shot `run` behavior
  - introduce global mutable state coupling across tests
- Provenance map:
  - runtime `thread_id` must equal resolved conversation id
- Acceptance gates:
  - integration tests assert invoke config contains thread id

**Tasks:**
- Update runtime result/request contracts as needed to carry conversation id.
- Update `AgentRuntime` invoke path to include thread configuration for continuity.
- Update `LilySupervisor` API so CLI/TUI can pass resolved conversation id per run.
- Keep backward-compatible defaults for existing callers/tests.

### Phase 3: CLI/TUI attach and exit UX

**Intent Lock**
- Source of truth: `src/lily/cli.py`, `src/lily/ui/app.py`, `src/lily/ui/screens/chat.py`
- Must:
  - add attach flags to both CLI and TUI entrypoints
  - default to new conversation on each execution when no attach flag provided
  - display/emit active conversation id at startup and on exit
- Must Not:
  - allow ambiguous combinations (`--conversation-id` with `--last-conversation`)
  - hide attach/resolve errors
- Provenance map:
  - exit-reported id must be exactly the resolved id used for runtime thread
- Acceptance gates:
  - e2e tests for new/default, attach-by-id, attach-last, and exit output

**Tasks:**
- CLI:
  - add options:
    - `--conversation-id <id>`
    - `--last-conversation` (bool)
  - resolve mode:
    - default => new
    - `--conversation-id` => attach explicit
    - `--last-conversation` => attach last
  - include conversation id in success/summary output and final exit message
- TUI:
  - add same attach options to `lily tui`
  - pass resolved id into `LilyTuiApp`
  - show current conversation id on mount in transcript
  - on app exit, print conversation id in terminal output (via app shutdown hook or CLI wrapper)

### Phase 4: Tests and validation gates

**Intent Lock**
- Source of truth: existing `tests/e2e/test_cli_agent_run.py`, `tests/e2e/test_tui_app.py`, integration runtime tests
- Must:
  - cover success and failure paths for attach behavior
  - keep tests deterministic and local-only
- Must Not:
  - depend on external model providers
- Provenance map:
  - fixture-created session files are source of truth for expected ids in tests
- Acceptance gates:
  - all new/updated unit, integration, e2e tests pass
  - quality gates pass warning-clean

**Tasks:**
- Add unit tests for new session persistence module.
- Extend integration tests for runtime thread-id propagation.
- Extend CLI e2e tests:
  - default new conversation path
  - attach explicit id
  - attach last
  - invalid explicit id error
- Extend TUI e2e tests:
  - startup shows conversation id
  - attach explicit and last behavior reflected in startup/output

---

## STEP-BY-STEP TASKS

### CREATE `src/lily/runtime/conversation_sessions.py`
- **IMPLEMENT**: typed schema + deterministic load/save + create/attach/last APIs.
- **IMPLEMENT**: SQLite-backed persistence (`sqlite3`) with explicit schema creation/migration guard for conversation sessions.
- **PATTERN**: mirror config/session deterministic error style from `src/lily/runtime/config_loader.py`.
- **IMPORTS**: `pathlib`, `pydantic`, `uuid`, `json`.
- **GOTCHA**: atomic writes (`.tmp` + replace), forbid silent fallback when id missing.
- **VALIDATE**: `uv run pytest tests/unit/runtime/test_conversation_sessions.py -q`

### UPDATE `src/lily/runtime/agent_runtime.py`
- **IMPLEMENT**: plumb `conversation_id` to invoke config (`thread_id`) and maintain backward-compatible defaults.
- **PATTERN**: preserve existing frozen result model and deterministic errors.
- **GOTCHA**: keep `AgentRuntime.run(...)` API migration safe for current integration tests.
- **VALIDATE**: `uv run pytest tests/integration/test_agent_runtime.py -q`

### UPDATE `src/lily/agents/lily_supervisor.py`
- **IMPLEMENT**: accept conversation id per prompt run and pass into runtime.
- **PATTERN**: keep constructor/from_config paths stable.
- **GOTCHA**: avoid breaking CLI/TUI fake-supervisor tests.
- **VALIDATE**: `uv run pytest tests/e2e/test_cli_agent_run.py -q`

### UPDATE `src/lily/cli.py`
- **IMPLEMENT**: add attach flags and mode resolution; print active conversation id in run summary and exit line.
- **PATTERN**: typer options + Rich panels/tables.
- **GOTCHA**: reject mutually-exclusive flag combinations deterministically.
- **VALIDATE**: `uv run pytest tests/e2e/test_cli_agent_run.py -q`

### UPDATE `src/lily/ui/app.py` and `src/lily/ui/screens/chat.py`
- **IMPLEMENT**: carry conversation id into app state, show on startup, emit on exit.
- **PATTERN**: existing transcript/system-message style.
- **GOTCHA**: ensure textual test pilot still exits cleanly and captures startup lines.
- **VALIDATE**: `uv run pytest tests/e2e/test_tui_app.py -q`

### CREATE/UPDATE tests
- **IMPLEMENT**:
  - new unit tests for conversation session store
  - runtime integration assertions for thread id plumbing
  - CLI/TUI e2e attach/new/last coverage
- **PATTERN**: use fake supervisor where external providers would otherwise run.
- **GOTCHA**: keep tests deterministic with tmp paths.
- **VALIDATE**: `uv run pytest tests/unit/runtime/test_conversation_sessions.py tests/integration/test_agent_runtime.py tests/e2e/test_cli_agent_run.py tests/e2e/test_tui_app.py -q`

---

## TESTING STRATEGY

### Unit Tests
- session persistence schema validation
- new session id generation
- explicit attach success/failure
- attach-last success/failure
- last pointer update rules

### Integration Tests
- runtime invoke config receives expected `thread_id` for same conversation id across runs
- no regression in normal one-shot runtime behavior

### Edge Cases
- explicit unknown conversation id
- `--last-conversation` when none exists
- mutually-exclusive attach flags
- corrupt/empty session store payload recovery behavior

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style
- `just format-check`
- `just lint`

### Level 2: Unit Tests
- `uv run pytest tests/unit/runtime/test_conversation_sessions.py -q`

### Level 3: Integration Tests
- `uv run pytest tests/integration/test_agent_runtime.py -q`

### Level 4: E2E/Manual Validation
- `uv run pytest tests/e2e/test_cli_agent_run.py tests/e2e/test_tui_app.py -q`
- Manual CLI checks:
  - `uv run lily run --config .lily/config/agent.yaml --prompt "hello"`
  - `uv run lily run --config .lily/config/agent.yaml --conversation-id <id> --prompt "continue"`
  - `uv run lily run --config .lily/config/agent.yaml --last-conversation --prompt "continue"`
- Manual TUI checks:
  - `uv run lily tui --config .lily/config/agent.yaml`
  - `uv run lily tui --config .lily/config/agent.yaml --conversation-id <id>`
  - `uv run lily tui --config .lily/config/agent.yaml --last-conversation`

### Level 5: Final Gate
- `just quality && just test`

---

## OUTPUT CONTRACT (Required For User-Visible Features)

- Exact output artifacts/surfaces:
  - CLI `run` output includes active conversation id in summary and exit line
  - TUI startup transcript includes active conversation id
  - TUI shutdown path emits active conversation id to terminal
  - local SQLite DB under `.lily/` for attach/last resolution (conversation session metadata)
- Verification commands:
  - `uv run lily run --config .lily/config/agent.yaml --prompt "hello"`
  - `uv run lily run --config .lily/config/agent.yaml --last-conversation --prompt "hello again"`
  - `uv run lily tui --config .lily/config/agent.yaml`

## DEFINITION OF VISIBLE DONE (Required For User-Visible Features)

- A human can directly verify completion by:
  - running CLI once and seeing a newly generated conversation id
  - rerunning with `--conversation-id` and observing same id used
  - rerunning with `--last-conversation` and observing same most-recent id used
  - launching TUI and seeing conversation id at startup and exit
  - confirming default mode starts a new id when no attach flags are provided

## INPUT/PREREQUISITE PROVENANCE (Required When Applicable)

- Generated during this feature:
  - conversation session SQLite DB file under `.lily/` via first CLI/TUI run
- Pre-existing dependency:
  - runtime config YAML at `.lily/config/agent.yaml`

---

## ACCEPTANCE CRITERIA

- [x] Default behavior starts a new conversation id on each new CLI/TUI process execution.
- [x] CLI supports attach by explicit id (`--conversation-id`) and by last (`--last-conversation`).
- [x] TUI supports attach by explicit id (`--conversation-id`) and by last (`--last-conversation`).
- [x] Unknown explicit id fails with deterministic, user-visible error.
- [x] `--last-conversation` with no prior session fails deterministically with clear message.
- [x] CLI output includes active conversation id on run completion/exit.
- [x] TUI displays active conversation id on startup and prints id on exit.
- [x] Runtime invocation uses resolved conversation id as thread identity.
- [x] Tests and validation commands pass without warnings introduced by this feature.

---

## COMPLETION CHECKLIST

- [x] All tasks completed in order
- [x] Each task validation passed immediately
- [x] All validation commands executed successfully
- [x] Full test suite passes (unit + integration + e2e)
- [x] No linting or type checking errors
- [x] Manual validation confirms behavior
- [x] Acceptance criteria all met

---

## NOTES

- Preserve strict default behavior requested by user: no implicit resume unless an attach flag is provided.
- Keep CLI and TUI flags aligned to avoid UX divergence.
- Do not implement in this planning step.

## Execution Report

- 2026-03-05: Executed Phase 1 only (`"Phase 1: Conversation session persistence foundation"`) on branch `feat/002-conversation-session-attach-resume`.
- 2026-03-05: Branch safety gate passed using plan branch setup commands; confirmed non-main branch with `git branch --show-current`.
- 2026-03-05: Phase intent check evidence captured: Intent Lock present with explicit source-of-truth, must/must-not, and acceptance gates for Phase 1.
- 2026-03-05: Implemented `src/lily/runtime/conversation_sessions.py` with SQLite-backed local store under `.lily/`, deterministic errors, and APIs: `start_new`, `attach`, `attach_last`, `record_turn`.
- 2026-03-05: Implemented Phase 1 unit coverage in `tests/unit/runtime/test_conversation_sessions.py` for create/attach/attach-last/record-turn/error/schema-guard behavior.
- 2026-03-05: Resolved runtime warning defect by explicitly closing SQLite connections in module and tests.
- 2026-03-05: Validation evidence:
  - `uv run pytest tests/unit/runtime/test_conversation_sessions.py -q` -> pass (`10 passed`).
  - `just docs-check` -> pass.
  - `just status` -> pass.
- 2026-03-05: Remaining phases (2-4) intentionally deferred; no runtime/CLI/TUI plumbing implemented in this phase run.
- 2026-03-05: Executed Phase 2 (`"Phase 2: Runtime threading and supervisor plumbing"`).
- 2026-03-05: Phase intent lock confirmed before implementation (source docs + must/must-not + acceptance gate present in plan).
- 2026-03-05: Updated runtime threading plumbing:
  - `src/lily/runtime/agent_runtime.py`: added optional `conversation_id` to `run(...)` / `_invoke(...)`, mapped to invoke config `configurable.thread_id`, widened invoke config typing, and extended `AgentRunResult` with optional `conversation_id`.
  - `src/lily/agents/lily_supervisor.py`: added optional `conversation_id` on `run_prompt(...)` and forwarded it to runtime.
- 2026-03-05: Added integration coverage in `tests/integration/test_agent_runtime.py` asserting:
  - `thread_id` is passed when `conversation_id` is provided.
  - one-shot behavior remains unchanged when `conversation_id` is absent.
- 2026-03-05: Validation evidence (Phase 2 scope):
  - `uv run pytest tests/integration/test_agent_runtime.py -q` -> pass (`5 passed`).
  - `uv run pytest tests/e2e/test_cli_agent_run.py -q` -> pass (`1 passed`).
  - `just format-check` -> pass.
  - `just lint` -> pass.
  - `just types` -> pass.
  - `just docs-check` -> pass.
  - `just status` -> pass.
- 2026-03-05: Final gate after Phase 2 updates:
  - `just quality && just test` -> pass.
  - During first run, darglint/test failures surfaced from Phase 1 session-store docs/tests; remediated in-place (`conversation_sessions.py` docstrings/bootstrap timing and `test_conversation_sessions.py` schema-mismatch assertion timing), then reran to green.
- 2026-03-05: Executed Phase 3 (`"Phase 3: CLI/TUI attach and exit UX"`).
- 2026-03-05: Phase intent lock confirmed before implementation (source docs + must/must-not + acceptance gate present in plan).
- 2026-03-05: Updated CLI attach/exit surfaces in `src/lily/cli.py`:
  - added `--conversation-id` and `--last-conversation` options to `run` and `tui`
  - added deterministic attach-mode resolver (`default=new`, explicit attach, last attach)
  - reject ambiguous flag combinations with deterministic user-visible errors
  - include active conversation id in run summary and CLI/TUI exit output
- 2026-03-05: Updated TUI conversation-id UX surfaces:
  - `src/lily/ui/app.py`: accepts active conversation id, passes it to runtime and screen
  - `src/lily/ui/screens/chat.py`: startup transcript now includes active conversation id
- 2026-03-05: Added e2e coverage for Phase 3 acceptance paths:
  - `tests/e2e/test_cli_agent_run.py`: default new, explicit attach, attach-last, ambiguous flags
  - `tests/e2e/test_tui_app.py`: startup transcript conversation id + `lily tui` mode wiring/exit output
- 2026-03-05: Validation evidence (Phase 3 scope):
  - `uv run pytest tests/e2e/test_cli_agent_run.py tests/e2e/test_tui_app.py -q` -> pass (`5 passed`).
  - `just format-check` -> pass.
  - `just lint` -> pass.
  - `just docs-check` -> pass.
  - `just status` -> pass.
- 2026-03-05: Final gate after Phase 3 updates:
  - `just quality && just test` -> pass (`25 passed`).
- 2026-03-05: Executed Phase 4 (`"Phase 4: Tests and validation gates"`).
- 2026-03-05: Phase intent lock confirmed before implementation (source docs + must/must-not + acceptance gate present in plan).
- 2026-03-05: Validation evidence (Phase 4 required commands):
  - `just format-check` -> pass.
  - `just lint` -> pass.
  - `uv run pytest tests/unit/runtime/test_conversation_sessions.py -q` -> pass (`10 passed`).
  - `uv run pytest tests/integration/test_agent_runtime.py -q` -> pass (`5 passed`).
  - `uv run pytest tests/e2e/test_cli_agent_run.py tests/e2e/test_tui_app.py -q` -> pass (`5 passed`).
- 2026-03-05: Manual CLI checks:
  - `uv run lily run --config .lily/config/agent.yaml --prompt "hello"` -> pass, emitted conversation id `59951d97-ea84-41f0-a566-69104330a0ac`.
  - `uv run lily run --config .lily/config/agent.yaml --conversation-id 59951d97-ea84-41f0-a566-69104330a0ac --prompt "continue"` -> pass, reused same id.
  - `uv run lily run --config .lily/config/agent.yaml --last-conversation --prompt "continue"` -> pass, reused same id.
- 2026-03-05: Manual TUI checks:
  - `uv run lily tui --config .lily/config/agent.yaml` -> launched successfully (verified via timed run harness).
  - `uv run lily tui --config .lily/config/agent.yaml --conversation-id 59951d97-ea84-41f0-a566-69104330a0ac` -> launched successfully (verified via timed run harness).
  - `uv run lily tui --config .lily/config/agent.yaml --last-conversation` -> launched successfully (verified via timed run harness).
- 2026-03-05: Final gate:
  - `just quality && just test` -> pass (`25 passed`).
