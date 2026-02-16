# Personality Execution Plan

Purpose: execution tracker for shipping Lily personality architecture in a controlled order.

Related:
- `docs/dev/personality_roadmap.md`
- `docs/adr/ADR-001-memory-model.md`

## Tracking Rules

- Do phases in order unless a step is explicitly marked parallel-safe.
- Do not start persona command expansion until Gate A is complete.
- Update this file in every PR that changes phase status.

## Gate A (Must Pass Before Persona Command Expansion)

- [x] Non-command conversation turn path implemented
- [x] `PersonaContext` interface implemented and wired
- [x] `PromptBuilder` interface implemented and wired
- [x] ADR-001 memory model status updated to `Accepted`
- [x] Policy precedence contract documented in code/docs:
  - [x] `safety > user style > persona default > stochastic expression`

## Phase 1: Core Conversation Runtime (`P5`)

- [x] Introduce LangChain v1 conversation runtime path
  - [x] Add `create_agent`-based conversation executor
  - [x] Use LangGraph checkpointer + `thread_id` for per-session resume
  - [x] Keep existing command runtime path unchanged
- [x] Replace `conversation_unimplemented` with real turn execution flow
  - [x] Add conversation execution entry in runtime facade
  - [x] Keep deterministic `CommandResult`/error envelope behavior
  - [x] Add tests for command vs conversation routing
- [x] Add minimal conversation orchestration contract
  - [x] Request object
  - [x] Response object
  - [x] Tool-call loop boundary
- [x] Persist conversation outputs in session state
  - [x] Verify restart continuity tests
- [x] Define and implement conversation/tool loop limits config contract
  - [x] Use explicit boolean enablement (`enabled: true|false`)
  - [x] Keep value fields explicit (`max_rounds`, `timeout_ms`, `max_retries`)
  - [x] Add config validation tests for enabled/disabled paths
  - [x] Document defaults and override behavior

## Phase 2: Persona Compiler Foundations (`P5`)

- [x] Implement `PersonaContext` model
  - [x] Active persona id
  - [x] Active style level
  - [x] User preference summary
  - [x] Session/task hints
- [x] Implement `PromptBuilder` as section-based builder
  - [x] Identity section
  - [x] Safety section
  - [x] Skills section
  - [x] Memory section
  - [x] Runtime section
- [x] Add prompt modes
  - [x] `full`
  - [x] `minimal`
- [x] Wire PersonaContext into LangChain middleware/runtime context
  - [x] Add `context_schema` for invocation-scoped persona/task metadata
  - [x] Add `@dynamic_prompt` middleware for deterministic prompt section injection
  - [x] Add `@before_model`/`@after_model` hooks for tracing and guardrail entry points
- [x] Add bounded/truncated context injection
  - [x] Deterministic truncation marker format
  - [x] Tests for boundary behavior

Phase 2 current-state note:
- Prompt rendering is live and deterministic, but several sections are baseline content until later phases.
- Currently baseline/simple:
  - identity/style values (until `/persona` and `/style` command surface lands)
  - safety wording (initial baseline policy text)
  - skills section (name list only)
  - memory section (summary string, not repository-backed retrieval yet)
  - runtime hints (basic session/task hints)
- Planned enrichment:
  - policy precedence enforcement (Phase 4)
  - split-store memory retrieval wiring (Phase 3)
  - richer persona controls and persisted profile data (Phase 6)

## Phase 3: Memory Repositories (`P5`)

- [x] Implement repository interfaces
  - [x] `PersonalityMemoryRepository`
  - [x] `TaskMemoryRepository`
- [x] Implement file-backed adapters (v1)
- [x] Enforce store separation
  - [x] No implicit cross-store query in default path
  - [x] Namespace isolation for task memory
- [x] Implement deterministic memory error codes
  - [x] `memory_invalid_input`
  - [x] `memory_not_found`
  - [x] `memory_store_unavailable`
  - [x] `memory_namespace_required`
  - [x] `memory_schema_mismatch`
- [x] Mark ADR-001 as `Accepted` once implementation contract matches

## Phase 4: Policy Boundaries (`P5`)

- [x] Add pre-LLM policy check stage
- [x] Add post-LLM policy check stage
- [x] Enforce precedence contract in runtime path
- [x] Implement policy boundaries with LangChain middleware hooks
  - [x] `before_model` for pre-generation policy checks
  - [x] `after_model` for post-generation policy checks
  - [x] `wrap_tool_call` for tool-call guardrails
- [x] Add deterministic policy-denied envelope and tests
- [x] Add deterministic memory policy-denied handling and tests
  - [x] Emit `memory_policy_denied` on blocked memory writes
- [x] Add policy test fixtures for redline scenarios

## Phase 5: Typed Skill/Tool Contracts (`P5`)

- [x] Add input schema validation in tool dispatch pipeline
- [x] Add output schema validation in tool dispatch pipeline
- [x] Keep deterministic error envelopes for validation failures
- [x] Use LangChain structured output where applicable for final-response schema guarantees
- [x] Add conformance tests for at least 3 skills/tools

## Gate B (Must Pass Before Broader Feature Expansion)

- [x] Typed tool/skill validation enabled end-to-end
- [x] Deterministic error envelopes verified by tests
- [x] Baseline eval set created (10-20 canonical cases)
- [x] Baseline thresholds documented and passing
  - Thresholds:
  - `minimum_cases >= 10`
  - `maximum_cases <= 20`
  - `minimum_pass_rate >= 0.95`
  - Enforced by `tests/unit/evals/test_baseline.py`

## Phase 6: Persona Command Surface (`P5`)

- [x] `/persona list`
- [x] `/persona use <name>`
- [x] `/persona show`
- [x] `/style focus|balanced|playful`
- [x] `/remember`
- [x] `/forget`
- [x] `/memory show`
- [x] Command help/docs for all above

## Phase 7: Quality + CI Gates (`P5`)

- [ ] Personality consistency test suite
  - [ ] Restart consistency
  - [ ] Multi-turn consistency
- [ ] Task effectiveness suite with personality enabled
- [ ] Fun/delight rubric suite
- [ ] Safety redline suite
- [ ] CI gating on agreed thresholds

## Phase 8: Next Elevation (`P4+`)

- [ ] `/reload_persona`
- [ ] Persona export/import
- [ ] Context-aware tone adaptation
- [ ] Multi-agent personalities (when agent subsystem is ready)

## Status Log

- 2026-02-16: Initial execution tracker created from roadmap + ADR-001 decisions.
- 2026-02-16: Added explicit LangChain v1 integration steps (create_agent, middleware hooks, checkpointer, context schema, structured output).
- 2026-02-16: Phase 1 conversation baseline landed (LangChain `create_agent` path, deterministic conversation envelopes, per-session thread routing, tests, and quality checks green).
- 2026-02-16: Added boolean-first conversation limit settings (`enabled` + explicit value fields) with strict validation tests and documented defaults.
- 2026-02-16: Implemented tool-loop boundary enforcement with deterministic timeout/retry/loop-limit handling and tests.
- 2026-02-16: Completed Phase 2 foundations (`PersonaContext`, sectioned `PromptBuilder`, prompt modes, LangChain `context_schema` + middleware hooks, deterministic bounded/truncated injection).
- 2026-02-16: Verified rendered prompt output manually; documented current baseline section content vs planned enrichments.
- 2026-02-16: Completed Phase 3 memory repositories (split interfaces + file adapters, namespace-isolated task queries, deterministic memory error model, and tests).
- 2026-02-16: Completed Phase 4 policy boundaries (pre/post policy checks, precedence enforcement, tool-call guardrails, conversation/memory policy-denied envelopes, and redline fixtures).
- 2026-02-16: Completed Phase 5 typed contracts (`command_tool` input/output schemas, deterministic validation envelopes, LangChain structured-response extraction, and conformance tests for add/subtract/multiply).
- 2026-02-16: Completed Gate B baseline quality enforcement with 10-20 canonical eval coverage and pass-rate threshold tests.
- 2026-02-16: Completed Phase 6 persona command surface (`/persona`, `/style`, `/remember`, `/forget`, `/memory show`) with bundled persona profiles (`lily`, `chad`, `barbie`) and docs in `docs/dev/persona_commands.md`.

## LangChain v1 Leverage (Out-of-the-Box)

- [x] `create_agent` runtime used for conversation path
- [x] LangGraph checkpointer persistence used for thread/session continuity
- [x] Runtime context (`context_schema`) used for persona/task invocation metadata
- [x] Middleware hooks used for prompt assembly + policy guardrails
- [ ] HITL interrupt middleware available for sensitive tools
- [ ] Long-term memory store API used for repository adapters
- [ ] Structured output strategy used where response schemas are required
