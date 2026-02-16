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
- [ ] `PersonaContext` interface implemented and wired
- [ ] `PromptBuilder` interface implemented and wired
- [x] ADR-001 memory model status updated to `Accepted`
- [ ] Policy precedence contract documented in code/docs:
  - [ ] `safety > user style > persona default > stochastic expression`

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

- [ ] Implement `PersonaContext` model
  - [ ] Active persona id
  - [ ] Active style level
  - [ ] User preference summary
  - [ ] Session/task hints
- [ ] Implement `PromptBuilder` as section-based builder
  - [ ] Identity section
  - [ ] Safety section
  - [ ] Skills section
  - [ ] Memory section
  - [ ] Runtime section
- [ ] Add prompt modes
  - [ ] `full`
  - [ ] `minimal`
- [ ] Wire PersonaContext into LangChain middleware/runtime context
  - [ ] Add `context_schema` for invocation-scoped persona/task metadata
  - [ ] Add `@dynamic_prompt` middleware for deterministic prompt section injection
  - [ ] Add `@before_model`/`@after_model` hooks for tracing and guardrail entry points
- [ ] Add bounded/truncated context injection
  - [ ] Deterministic truncation marker format
  - [ ] Tests for boundary behavior

## Phase 3: Memory Repositories (`P5`)

- [ ] Implement repository interfaces
  - [ ] `PersonalityMemoryRepository`
  - [ ] `TaskMemoryRepository`
- [ ] Implement file-backed adapters (v1)
- [ ] Enforce store separation
  - [ ] No implicit cross-store query in default path
  - [ ] Namespace isolation for task memory
- [ ] Implement deterministic memory error codes
  - [ ] `memory_invalid_input`
  - [ ] `memory_not_found`
  - [ ] `memory_policy_denied`
  - [ ] `memory_store_unavailable`
  - [ ] `memory_namespace_required`
  - [ ] `memory_schema_mismatch`
- [ ] Mark ADR-001 as `Accepted` once implementation contract matches

## Phase 4: Policy Boundaries (`P5`)

- [ ] Add pre-LLM policy check stage
- [ ] Add post-LLM policy check stage
- [ ] Enforce precedence contract in runtime path
- [ ] Implement policy boundaries with LangChain middleware hooks
  - [ ] `before_model` for pre-generation policy checks
  - [ ] `after_model` for post-generation policy checks
  - [ ] `wrap_tool_call` for tool-call guardrails
- [ ] Add deterministic policy-denied envelope and tests
- [ ] Add policy test fixtures for redline scenarios

## Phase 5: Typed Skill/Tool Contracts (`P5`)

- [ ] Add input schema validation in tool dispatch pipeline
- [ ] Add output schema validation in tool dispatch pipeline
- [ ] Keep deterministic error envelopes for validation failures
- [ ] Use LangChain structured output where applicable for final-response schema guarantees
- [ ] Add conformance tests for at least 3 skills/tools

## Gate B (Must Pass Before Broader Feature Expansion)

- [ ] Typed tool/skill validation enabled end-to-end
- [ ] Deterministic error envelopes verified by tests
- [ ] Baseline eval set created (10-20 canonical cases)
- [ ] Baseline thresholds documented and passing

## Phase 6: Persona Command Surface (`P5`)

- [ ] `/persona list`
- [ ] `/persona use <name>`
- [ ] `/persona show`
- [ ] `/style focus|balanced|playful`
- [ ] `/remember`
- [ ] `/forget`
- [ ] `/memory show`
- [ ] Command help/docs for all above

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

## LangChain v1 Leverage (Out-of-the-Box)

- [x] `create_agent` runtime used for conversation path
- [x] LangGraph checkpointer persistence used for thread/session continuity
- [ ] Runtime context (`context_schema`) used for persona/task invocation metadata
- [ ] Middleware hooks used for prompt assembly + policy guardrails
- [ ] HITL interrupt middleware available for sensitive tools
- [ ] Long-term memory store API used for repository adapters
- [ ] Structured output strategy used where response schemas are required
