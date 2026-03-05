---
owner: "@team"
last_updated: "2026-02-17"
status: "archived"
source_of_truth: false
---

# Slice 001 Development Plan

Purpose: execution checklist for the vertical slice.

Scope: `load -> snapshot -> /skills -> /skill <name> -> execute echo`.

## Naming Freeze (Slice 001)

- Canonical invocation modes are:
  - `llm_orchestration`
  - `tool_dispatch`
- New docs, examples, and emitted metadata must use canonical names only.

## Phase 0 - Setup And Alignment

- [x] Confirm branch is `feat/slice-001-vertical-slice`.
- [x] Confirm scope lock: no extra commands beyond `/skills` and `/skill <name>` in this slice.
- [x] Confirm terminology lock: `llm_orchestration` + `tool_dispatch`.
- [x] Confirm package naming lock: `src/lily/<component>` (no `lily_` prefixes).
- [x] Confirm tooling lock: Typer CLI + Rich logging.

- [x] Phase exit gate: `just quality` and `just test` are green.


## Phase 1 - Package Skeleton

- [x] Create package dirs under `src/lily/`: `cli`, `runtime`, `session`, `skills`, `commands`, `prompting`.
- [x] Add `__init__.py` files for each package.
- [x] Add module stubs for planned files:
  - [x] `runtime/facade.py`
  - [x] `runtime/skill_invoker.py`
  - [x] `runtime/executors/base.py`
  - [x] `runtime/executors/llm_orchestration.py`
  - [x] `commands/parser.py`
  - [x] `commands/registry.py`
  - [x] `commands/handlers/skills_list.py`
  - [x] `commands/handlers/skill_invoke.py`
  - [x] `session/models.py`
  - [x] `session/factory.py`
  - [x] `skills/types.py`
  - [x] `skills/frontmatter.py`
  - [x] `skills/discover.py`
  - [x] `skills/precedence.py`
  - [x] `skills/eligibility.py`
  - [x] `skills/loader.py`
  - [x] `prompting/prompt_builder.py`
  - [x] `cli/cli.py`

- [x] Phase exit gate: `just quality` and `just test` are green.


## Phase 2 - Core Models (Pydantic)

- [x] Implement `SkillSource` enum.
- [x] Implement `InvocationMode` enum (`llm_orchestration`, `tool_dispatch`).
- [x] Implement `SkillEntry` model (`frozen=True`).
- [x] Implement `SkillSnapshot` model (`frozen=True`).
- [x] Implement `Session` model.
- [x] Add/confirm `extra='forbid'` policy where appropriate.

- [x] Phase exit gate: `just quality` and `just test` are green.


## Phase 3 - Skills Loader (Deterministic)

- [x] Implement immediate-child discovery for bundled + workspace roots.
- [x] Require `SKILL.md` presence for candidate validity.
- [x] Parse frontmatter from `SKILL.md`.
- [x] Implement deterministic precedence (`workspace > bundled`; user deferred).
- [x] Implement eligibility strategy checks (`os`, `env`, `binaries`).
- [x] Exclude ineligible/malformed skills with diagnostics.
- [x] Build deterministic index sorted by `skill_name`.
- [x] Build snapshot version token.
- [x] Ensure no fallback to lower precedence if winner is ineligible.

- [x] Phase exit gate: `just quality` and `just test` are green.


## Phase 4 - Session Factory

- [x] Implement `SessionFactory.create(...)`.
- [x] Build snapshot during session creation.
- [x] Store snapshot in session model.
- [x] Ensure snapshot is treated immutable for session lifetime.

- [x] Phase exit gate: `just quality` and `just test` are green.


## Phase 5 - Deterministic Command Surface (Slice Commands Only)

- [x] Implement strict slash parser (`/` prefix required).
- [x] Implement exact command match (no fuzzy logic).
- [x] Implement command registry dispatch.
- [x] Implement `/skills` handler (snapshot-only read).
- [x] Implement `/skill <name>` handler (exact skill lookup only).
- [x] Implement explicit errors:
  - [x] unknown command
  - [x] missing `/skill` arg
  - [x] skill not found

- [x] Phase exit gate: `just quality` and `just test` are green.


## Phase 6 - Execution Layer Seam

- [x] Implement `SkillInvoker` orchestrator.
- [x] Implement `SkillExecutor` interface.
- [x] Implement `LlmOrchestrationExecutor` for this slice.
- [x] Define and document user-specific LLM integration contract before coding executor internals.
- [x] Wire `/skill <name>` command handler to delegate to invoker (no direct execution in handler).
- [x] Keep `ToolDispatchExecutor` as stub or deferred placeholder.
- [x] Keep LangChain v1 implementation isolated behind internal backend adapter boundary.
- [x] Add unit tests for invoker dispatch and explicit unknown-mode errors.

- [x] Phase exit gate: `just quality` and `just test` are green.


## Phase 7 - Echo Skill (Proof Skill)

- [x] Create bundled skill folder: `skills/echo/`.
- [x] Create `skills/echo/SKILL.md`.
- [x] Set `invocation_mode: llm_orchestration`.
- [x] Define deterministic expected behavior for smoke tests (echo-uppercase contract).

- [x] Phase exit gate: `just quality` and `just test` are green.


## Phase 8 - CLI Delivery

- [x] Implement Typer app entrypoint.
- [x] Implement REPL mode (primary).
- [x] Implement single-shot mode (for scripting/tests).
- [x] Add Rich logging/output formatting.
- [x] Ensure command path bypasses conversational routing.

- [x] Phase exit gate: `just quality` and `just test` are green.


## Phase 9 - Test Coverage

- [x] Add loader precedence test.
- [x] Add no-fallback-on-ineligible test.
- [x] Add deterministic ordering test for `/skills`.
- [x] Add snapshot stability test (filesystem change mid-session does not affect session).
- [x] Add `/skill` exact-match test.
- [x] Add `/skill` missing-name error test.
- [x] Add `/skill missing_name` no-fallback test.
- [x] Add echo forced invocation test.

- [x] Phase exit gate: `just quality` and `just test` are green.


## Phase 10 - Manual Smoke Validation

- [x] Start CLI REPL.
- [x] Run `/skills` and verify deterministic ordered output.
- [x] Run `/skill echo hello world` and verify expected echo behavior.
- [x] Modify filesystem skills during active session and re-run `/skills`.
- [x] Verify snapshot stability (no implicit drift).
- [x] Start new session and verify new snapshot reflects filesystem.

- [x] Phase exit gate: `just quality` and `just test` are green.


## Phase 11 - Documentation And Handoff

- [x] Update `implementation_design_plan.md` if implementation diverges.
- [x] Record deviations and rationale in `docs/dev/slice_001/`.
- [x] Add follow-up items to `docs/dev/later_backlog.md`.
- [x] Prepare short completion report with:
  - [x] what passed
  - [x] what failed
  - [x] what is deferred

- [x] Phase exit gate: `just quality` and `just test` are green.

## Definition Of Done (Slice 001)

- [x] Loader deterministic and contract-compliant.
- [x] Session snapshot immutable and used by commands.
- [x] `/skills` and `/skill <name>` deterministic and snapshot-only.
- [x] `echo` executes end-to-end via `SkillInvoker` + `LlmOrchestrationExecutor`.
- [x] No silent fallback anywhere in slice behavior.
