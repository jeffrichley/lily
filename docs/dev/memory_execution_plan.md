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
- [x] Optional command/agent paths backed by LangMem manage/search tools.
- [x] No change to deterministic command envelope format.

`Internal engineering tasks`
- [x] Introduce manage/search memory tools in experimental mode.
- [x] Restrict tool usage to explicit paths first.
- [x] Keep deterministic output envelope adapter on top of tool results.
- [x] Enforce tool UX quality contract:
  - [x] concise/high-signal tool outputs
  - [x] stable, namespaced tool naming conventions
- [x] Add opt-in config flag for automatic memory tooling.
- [x] Add safety/policy interceptors around tool writes.

`Acceptance criteria`
- [x] LangMem tools are usable without breaking deterministic command outputs.
- [x] Policy-denied behavior remains unchanged.

`Non-goals`
- No default-on autonomous memory tooling.
- No replacement of canonical structured memory with tool-native outputs.

`Required tests and gates`
- [x] Deterministic envelope regression tests.
- [x] Policy redline tests around tool writes.
- [x] Opt-in flag behavior tests.

---

## Phase 5: Background Consolidation Pipeline (`P4`)

Goal: add post-run memory consolidation and profile merging.

`User-visible features`
- [x] More coherent long-term profile/task memory over time (when enabled).

`Internal engineering tasks`
- [x] Define consolidation input/output schema.
- [x] Implement deterministic rule-based consolidation backend.
- [x] Implement LangMem-manager consolidation backend.
- [x] Add backend selection config (`consolidation.backend = rule_based|langmem_manager`).
- [x] Add per-backend opt-in controls (`consolidation.enabled`, `consolidation.llm_assisted_enabled`).
- [x] Add optional LLM-assisted extraction path (guarded, disabled by default).
- [x] Implement lifecycle/retention policy from spec:
  - [x] `persona_core`: high stability, no expiry by default
  - [x] `working_rules`: high stability, no expiry by default
  - [x] `user_profile`: periodic reverification with `last_verified`
  - [x] `task_memory`: optional namespace expiry/archive metadata
  - [x] lifecycle state is metadata-only (no automatic hard deletion)
- [x] Add merge/conflict policy:
  - [x] provenance preserved
  - [x] confidence updates controlled
  - [x] stale/conflicting memory handling
- [x] Add scheduled/triggered execution path.
  - [x] Triggered command path (`/memory long consolidate [--dry-run]`).
  - [x] Scheduled/background runner.

`Acceptance criteria`
- [x] Consolidation produces stable, auditable profile updates.
- [x] No uncontrolled writes without explicit configuration.
- [x] Rule-based and LangMem-manager backends can each be enabled/disabled by config.
- [x] Backend selection is deterministic and explicit in runtime metadata/logging.
- [x] Expired/archived task memory is excluded from default retrieval unless explicitly requested.
- [x] `last_verified` is updated only on explicit confirmation events.
- [x] Lifecycle processing performs no automatic hard deletion.

`Non-goals`
- No fully autonomous always-on consolidation by default.
- No hidden mutation of canonical records without provenance.
- No automatic hard-deletion behavior from lifecycle processing.

`Required tests and gates`
- [x] Consolidation determinism tests.
- [x] Provenance/conflict resolution tests.
- [x] Configuration guard tests (disabled means no writes).
- [x] Backend selection tests (`rule_based` vs `langmem_manager`).
- [x] Per-backend opt-in/out behavior tests.
- [x] Lifecycle policy tests (expiry/archive/reverification behavior, no-delete guarantee).

---

## Phase 6: Optional Semantic Evidence Layer (`P3`)

Goal: add semantic retrieval for large artifacts while preserving structured truth.

`User-visible features`
- [x] Evidence retrieval for large artifacts with citations.
- [x] Explicitly labeled evidence outputs (`non-canonical`).

`Internal engineering tasks`
- [x] Add vector/evidence store abstraction.
- [x] Add ingestion path for long artifacts (transcripts/notes/logs).
- [x] Add retrieval API returning evidence citations.
- [x] Keep structured memory as canonical in resolver policy.
- [x] Complete `/memory evidence ...` command functionality.

`Acceptance criteria`
- [x] Semantic retrieval improves recall without overriding canonical records.
- [x] Evidence outputs include citation/provenance metadata.

`Non-goals`
- No semantic-results-only decision path for canonical memory facts.
- No silent override of structured memory by similarity hits.

`Required tests and gates`
- [x] Contradiction handling tests (structured vs semantic evidence).
- [x] Evidence citation integrity tests.
- [x] Canonical precedence policy tests.

---

## Phase 7: Ops, Safety, and Quality Gates (`P5`)

Goal: operationalize migrated memory system with measurable quality/safety controls.

`User-visible features`
- [x] Reliable memory behavior with documented backup/export/restore operations.

`Internal engineering tasks`
- [x] Extend eval suites for migrated stack:
  - [x] restart continuity with persistent checkpointer
  - [x] store-backed parity
  - [x] policy redline memory write denial
  - [x] prompt retrieval relevance
  - [x] context compaction effectiveness on long transcripts
- [x] Split eval governance:
  - [x] capability eval lane for new memory behaviors
  - [x] regression eval lane for frozen command/runtime contracts
  - [x] multi-trial policy for stochastic eval scenarios
  - [x] transcript review cadence for grader quality/drift
- [x] Add `memory migration` CI gate target.
- [x] Add backup/export/restore operational docs.
- [x] Add memory schema migration playbook.
- [x] Add observability metrics:
  - [x] write counts
  - [x] denied writes
  - [x] retrieval hit rates
  - [x] consolidation drift indicators
  - [x] per-subdomain read/write rates (`persona_core`, `user_profile`, `working_rules`, `task_memory`)
  - [x] `last_verified` freshness distribution

`Acceptance criteria`
- [x] CI gates green across supported platforms.
- [x] Operational runbook ready and reviewed.
- [x] Observability dashboards/metrics available for migration decisions.

`Non-goals`
- No new product features unrelated to memory migration.
- No relaxation of deterministic contract requirements.

`Required tests and gates`
- [x] Full memory migration CI gate green.
- [x] Phase 7 quality suite green.
- [x] Baseline-to-post-migration metric comparison report complete.

---

## Phase 8: Compaction Backend Migration (`P4`)

Goal: replace custom rule-based history compaction with LangGraph-native state/context compaction once parity is proven.

`User-visible features`
- [ ] Same or better long-thread response quality with lower maintenance burden.

`Internal engineering tasks`
- [ ] Add feature-flagged compaction backend (`rule_based` vs `langgraph_native`).
- [ ] Implement LangGraph-native state/context compaction path.
- [ ] Run parity + eval comparison (`rule_based` vs `langgraph_native`).
- [ ] Flip default to `langgraph_native` after quality/eval metrics pass.

`Acceptance criteria`
- [ ] Deterministic command/runtime contracts are unchanged.
- [ ] `langgraph_native` compaction matches or improves current quality metrics.
- [ ] Legacy `rule_based` path remains as fallback until full confidence window passes.

`Non-goals`
- No command-surface changes.
- No forced removal of fallback path in first rollout.

`Required tests and gates`
- [ ] Parity test matrix between both compaction backends.
- [ ] Long-transcript compaction effectiveness tests for both backends.
- [ ] Retrieval relevance regression checks under both backends.

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
- 2026-02-17: Phase 3 completed. Added repository-backed retrieval service, deterministic ranking and memory-summary prompt injection, and deterministic context compaction with long-transcript tests.
- 2026-02-17: Phase 4 completed. Added controlled LangMem manage/search tool routes, global opt-in tooling flags (`enabled`, `auto_apply`), deterministic envelope adapters for tool outputs, and policy/flag regression tests.
- 2026-02-17: Phase 5 started. Added dual-backend consolidation pipeline (`rule_based` + `langmem_manager`), opt-in backend/config toggles, triggered command path (`/memory long consolidate [--dry-run]`), and deterministic backend selection/behavior tests.
- 2026-02-17: Phase 5 completed. Added lifecycle visibility controls (`include_archived|include_expired|include_conflicted`), `/memory long verify` reverification path, conflict-group reconciliation behavior, scheduled auto-consolidation (`auto_run_every_n_turns`), and corresponding command/repository/consolidation test coverage.
- 2026-02-17: Phase 6 completed. Replaced evidence placeholder with working semantic evidence layer (`/memory evidence ingest|show`), added evidence repository abstraction, citation-bearing retrieval output, explicit non-canonical policy labeling, contradiction/precedence command tests, and CLI evidence table rendering.
- 2026-02-17: Phase 7 completed. Added memory migration eval harness/suite (`tests/unit/evals/test_memory_migration_quality.py`), split eval lanes (`eval-regression`, `eval-capability`), `memory-migration-gates` CI target, operational runbooks (`docs/ops/...`), in-process memory observability counters + snapshot artifact generation, and baseline-to-post metrics comparison report.
