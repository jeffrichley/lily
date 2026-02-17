# Memory Execution Plan (V1)

Purpose: phased implementation plan for `docs/dev/memory_spec_v1.md` with deterministic gates.

Scope contract:
- This plan is fixed-scope per phase.
- Before implementation of each phase:
  - acceptance criteria are explicit
  - non-goals are explicit
  - required tests and gates are explicit
- Work items are split into:
  - `User-visible features`
  - `Internal engineering tasks`

---

## Gate M0: Alignment (Must Pass Before Migration Work)

`User-visible features`
- None (alignment gate only).

`Internal engineering tasks`
- [x] Spec accepted by team (`docs/dev/memory_spec_v1.md`).
- [x] Command contracts frozen for migration window:
  - [x] `/remember`
  - [x] `/memory show`
  - [x] `/forget`
- [x] Baseline eval snapshot captured:
  - [x] Gate B suite passing
  - [x] Phase 7 quality suite passing
- [x] Baseline observability snapshot captured:
  - [x] average prompt/context size per turn
  - [x] memory retrieval hit rate
  - [x] policy-denied memory write count

`Acceptance criteria`
- [x] All M0 checkboxes complete and logged.
- [x] Migration branch starts from frozen contract baseline.

`Non-goals`
- No runtime behavior changes.
- No command surface expansion.

`Required tests and gates`
- [x] Existing CI baseline green.
- [x] Baseline eval report artifact stored.

---

## Phase 1: Short-Term Memory Migration to Persistent Checkpointer (`P5`)

Goal: replace ephemeral `InMemorySaver` runtime behavior with persistent checkpointer backend.

`User-visible features`
- [x] Conversation continuity across process restarts.
- [x] Global Lily config for checkpointer backend/path with local default:
  - [x] backend default `sqlite`
  - [x] path default `.lily/checkpoints/checkpointer.sqlite`

`Internal engineering tasks`
- [x] Add persistent checkpointer adapter selection (`sqlite` first).
- [x] Define backend profile policy:
  - [x] local profile (`sqlite`)
  - [x] production-ready profile contract (`postgres`/managed saver)
- [x] Keep `thread_id = session_id` invariant.
- [x] Add config contract wiring from global Lily config to runtime construction.
- [x] Add restart/resume support tests for checkpointer continuity.
- [x] Add checkpoint-history/replay tests:
  - [x] `get_state_history` continuity
  - [x] replay from explicit checkpoint id
- [x] Validate no regression in existing session JSON behavior.

`Acceptance criteria`
- [x] Restarted process resumes conversation state from persistent checkpointer.
- [x] Default local startup writes checkpoints to `.lily/checkpoints/checkpointer.sqlite`.
- [x] Existing command/conversation tests remain green.

`Non-goals`
- No long-term Store migration yet.
- No semantic evidence retrieval.
- No LangMem automation.

`Required tests and gates`
- [x] New restart continuity unit/integration tests.
- [x] Existing command surface regression suite.
- [x] Existing Phase 7 suite remains green.

---

## Phase 2: Long-Term Memory Store Adapter Layer (`P5`)

Goal: move custom file-repository internals to LangGraph Store-backed adapters while preserving behavior.

`User-visible features`
- [x] Existing memory commands continue to work without behavior break.
- [x] Initial three-level memory command family introduced (compatibility preserved):
  - [x] `/memory short show`
  - [x] `/memory long show [query]`
  - [x] `/memory long show --domain persona_core [query]`
  - [x] `/memory long show --domain user_profile [query]`
  - [x] `/memory long show --domain working_rules [query]`
  - [x] `/memory long task show --namespace <task_or_project> [query]`
  - [x] `/memory evidence show [query]` (placeholder until Phase 6 backend)

`Internal engineering tasks`
- [x] Define `StoreBackedPersonalityMemoryRepository`.
- [x] Define `StoreBackedTaskMemoryRepository`.
- [x] Implement canonical long-term subdomain model:
  - [x] `persona_core`
  - [x] `user_profile`
  - [x] `working_rules`
  - [x] `task_memory`
- [x] Implement namespace builders/mappers for subdomains:
  - [x] `("memory", "personality", "persona_core", <user_or_workspace>, <scope>)`
  - [x] `("memory", "personality", "user_profile", <user_or_workspace>, <scope>)`
  - [x] `("memory", "personality", "working_rules", <user_or_workspace>, <scope>)`
  - [x] `("memory", "task", "task_memory", <task_or_project>, <scope>)`
- [x] Preserve deterministic error mapping:
  - [x] `memory_invalid_input`
  - [x] `memory_not_found`
  - [x] `memory_store_unavailable`
  - [x] `memory_namespace_required`
  - [x] `memory_schema_mismatch`
  - [x] `memory_policy_denied`
- [x] Preserve split-domain semantics via namespace policy.
- [x] Keep `/remember` and `/forget` as compatibility aliases to long-term personality writes/deletes.
- [x] Keep file-backed implementation as fallback adapter (non-primary).
- [x] Add command handler wiring to repository interfaces (not concrete file classes).

`Acceptance criteria`
- [x] Existing handlers run against Store-backed repositories with unchanged deterministic envelopes.
- [x] New command family routes to correct domains and namespace constraints.
- [x] No cross-subdomain leakage across `persona_core`, `user_profile`, `working_rules`, and `task_memory`.
- [x] File-backed fallback remains functional.

`Non-goals`
- No prompt memory retrieval/ranking logic yet.
- No background consolidation.

`Required tests and gates`
- [x] Parity tests: file-backed vs store-backed behavior.
- [x] Command contract snapshot tests for legacy commands.
- [x] Namespace isolation tests for task memory commands.
- [x] Subdomain isolation tests for personality long-term domains.

---

## Phase 3: Runtime Retrieval Wiring and Context Budgeting (`P5`)

Goal: make prompt memory injection repository-backed, selective, and bounded.

`User-visible features`
- [x] More relevant responses from retrieved long-term memory.
- [x] Stable output quality on long-running threads via deterministic context compaction.

`Internal engineering tasks`
- [x] Add retrieval service for prompt assembly:
  - [x] `persona_core` query path
  - [x] `user_profile` query path
  - [x] `working_rules` query path
  - [x] `task_memory` query path (namespace constrained)
- [x] Add deterministic ranking/filter policy:
  - [x] confidence threshold
  - [x] recency tie-break
  - [x] bounded result count
- [x] Inject retrieved summary into `PromptBuildContext.memory_summary`.
- [x] Add context compaction policy:
  - [x] deterministic summarize/trim strategy
  - [x] low-value tool output eviction rules
  - [x] context budget guardrails and truncation controls

`Acceptance criteria`
- [x] Prompt memory section is repository-backed (not manual-only).
- [x] Retrieval composition preserves priority of durable operating constraints:
  - [x] `working_rules` + `persona_core` before `user_profile` before `task_memory` (within configured caps)
- [x] Token/context bloat remains bounded under long transcripts.
- [x] Retrieval behavior is deterministic under same inputs/state.

`Non-goals`
- No autonomous long-term memory writes.
- No semantic evidence as canonical truth.

`Required tests and gates`
- [x] Retrieval relevance tests.
- [x] Prompt-size and truncation tests.
- [x] Long-transcript compaction effectiveness tests.
- [x] Retrieval-priority tests across long-term subdomains.

---

## Phase 4: LangMem Tooling Integration (Controlled) (`P4`)

Goal: reduce custom write/search glue by integrating LangMem tools in controlled paths.

`User-visible features`
- [ ] Optional command/agent paths backed by LangMem manage/search tools.
- [ ] No change to deterministic command envelope format.

`Internal engineering tasks`
- [ ] Introduce manage/search memory tools in experimental mode.
- [ ] Restrict tool usage to explicit paths first.
- [ ] Keep deterministic output envelope adapter on top of tool results.
- [ ] Enforce tool UX quality contract:
  - [ ] concise/high-signal tool outputs
  - [ ] stable, namespaced tool naming conventions
- [ ] Add opt-in config flag for automatic memory tooling.
- [ ] Add safety/policy interceptors around tool writes.

`Acceptance criteria`
- [ ] LangMem tools are usable without breaking deterministic command outputs.
- [ ] Policy-denied behavior remains unchanged.

`Non-goals`
- No default-on autonomous memory tooling.
- No replacement of canonical structured memory with tool-native outputs.

`Required tests and gates`
- [ ] Deterministic envelope regression tests.
- [ ] Policy redline tests around tool writes.
- [ ] Opt-in flag behavior tests.

---

## Phase 5: Background Consolidation Pipeline (`P4`)

Goal: add post-run memory consolidation and profile merging.

`User-visible features`
- [ ] More coherent long-term profile/task memory over time (when enabled).

`Internal engineering tasks`
- [ ] Define consolidation input/output schema.
- [ ] Implement deterministic rule-based extractor (phase 1).
- [ ] Add optional LLM-assisted extractor (phase 2, guarded).
- [ ] Implement lifecycle/retention policy from spec:
  - [ ] `persona_core`: high stability, no expiry by default
  - [ ] `working_rules`: high stability, no expiry by default
  - [ ] `user_profile`: periodic reverification with `last_verified`
  - [ ] `task_memory`: optional namespace expiry/archive metadata
  - [ ] lifecycle state is metadata-only (no automatic hard deletion)
- [ ] Add merge/conflict policy:
  - [ ] provenance preserved
  - [ ] confidence updates controlled
  - [ ] stale/conflicting memory handling
- [ ] Add scheduled/triggered execution path.

`Acceptance criteria`
- [ ] Consolidation produces stable, auditable profile updates.
- [ ] No uncontrolled writes without explicit configuration.
- [ ] Expired/archived task memory is excluded from default retrieval unless explicitly requested.
- [ ] `last_verified` is updated only on explicit confirmation events.
- [ ] Lifecycle processing performs no automatic hard deletion.

`Non-goals`
- No fully autonomous always-on consolidation by default.
- No hidden mutation of canonical records without provenance.
- No automatic hard-deletion behavior from lifecycle processing.

`Required tests and gates`
- [ ] Consolidation determinism tests.
- [ ] Provenance/conflict resolution tests.
- [ ] Configuration guard tests (disabled means no writes).
- [ ] Lifecycle policy tests (expiry/archive/reverification behavior, no-delete guarantee).

---

## Phase 6: Optional Semantic Evidence Layer (`P3`)

Goal: add semantic retrieval for large artifacts while preserving structured truth.

`User-visible features`
- [ ] Evidence retrieval for large artifacts with citations.
- [ ] Explicitly labeled evidence outputs (`non-canonical`).

`Internal engineering tasks`
- [ ] Add vector/evidence store abstraction.
- [ ] Add ingestion path for long artifacts (transcripts/notes/logs).
- [ ] Add retrieval API returning evidence citations.
- [ ] Keep structured memory as canonical in resolver policy.
- [ ] Complete `/memory evidence ...` command functionality.

`Acceptance criteria`
- [ ] Semantic retrieval improves recall without overriding canonical records.
- [ ] Evidence outputs include citation/provenance metadata.

`Non-goals`
- No semantic-results-only decision path for canonical memory facts.
- No silent override of structured memory by similarity hits.

`Required tests and gates`
- [ ] Contradiction handling tests (structured vs semantic evidence).
- [ ] Evidence citation integrity tests.
- [ ] Canonical precedence policy tests.

---

## Phase 7: Ops, Safety, and Quality Gates (`P5`)

Goal: operationalize migrated memory system with measurable quality/safety controls.

`User-visible features`
- [ ] Reliable memory behavior with documented backup/export/restore operations.

`Internal engineering tasks`
- [ ] Extend eval suites for migrated stack:
  - [ ] restart continuity with persistent checkpointer
  - [ ] store-backed parity
  - [ ] policy redline memory write denial
  - [ ] prompt retrieval relevance
  - [ ] context compaction effectiveness on long transcripts
- [ ] Split eval governance:
  - [ ] capability eval lane for new memory behaviors
  - [ ] regression eval lane for frozen command/runtime contracts
  - [ ] multi-trial policy for stochastic eval scenarios
  - [ ] transcript review cadence for grader quality/drift
- [ ] Add `memory migration` CI gate target.
- [ ] Add backup/export/restore operational docs.
- [ ] Add memory schema migration playbook.
- [ ] Add observability metrics:
  - [ ] write counts
  - [ ] denied writes
  - [ ] retrieval hit rates
  - [ ] consolidation drift indicators
  - [ ] per-subdomain read/write rates (`persona_core`, `user_profile`, `working_rules`, `task_memory`)
  - [ ] `last_verified` freshness distribution

`Acceptance criteria`
- [ ] CI gates green across supported platforms.
- [ ] Operational runbook ready and reviewed.
- [ ] Observability dashboards/metrics available for migration decisions.

`Non-goals`
- No new product features unrelated to memory migration.
- No relaxation of deterministic contract requirements.

`Required tests and gates`
- [ ] Full memory migration CI gate green.
- [ ] Phase 7 quality suite green.
- [ ] Baseline-to-post-migration metric comparison report complete.

---

## Risks and Mitigations

- [ ] Risk: migration changes behavior unexpectedly.
  - [ ] Mitigation: adapter parity tests + frozen command contracts.
- [ ] Risk: performance regression from Store backend.
  - [ ] Mitigation: benchmark gate + bounded retrieval + compaction policy.
- [ ] Risk: policy bypass through new tooling.
  - [ ] Mitigation: enforce policy gate at repository and tool boundaries.
- [ ] Risk: command-surface confusion during three-level rollout.
  - [ ] Mitigation: keep legacy commands stable; add explicit docs/help for new families.

---

## Progress Log

- 2026-02-16: Plan created from V1 spec + LangGraph/LangMem + Anthropic best-practice synthesis.
- 2026-02-16: Plan restructured to AGENTS phase-contract format (fixed scope, acceptance criteria, non-goals, required tests/gates, feature/internal split).
- 2026-02-16: Gate M0 completed. Baseline eval/quality gates passed and observability baseline snapshot captured in `docs/dev/memory_m0_baseline_2026-02-16.md`.
- 2026-02-16: Phase 1 completed. Added global checkpointer config, SQLite-backed persistent checkpointer wiring, profile contract for production backend, and restart/history continuity tests.
- 2026-02-16: Phase 2 completed. Added store-backed memory repositories, repository-interface command wiring, compatibility command aliases, and initial `/memory short|long|evidence` command-family rollout with parity/isolation tests.
