# Memory Execution Plan (V1)

Purpose: phased implementation plan for `docs/dev/memory_spec_v1.md` with deterministic gates.

---

## Gate M0: Alignment (Must Pass Before Migration Work)

- [ ] Spec accepted by team (`docs/dev/memory_spec_v1.md`)
- [ ] Current command contracts frozen for migration window:
  - [ ] `/remember`
  - [ ] `/memory show`
  - [ ] `/forget`
- [ ] Baseline eval snapshot captured before migration:
  - [ ] Gate B suite passing
  - [ ] Phase 7 quality suite passing

---

## Phase 1: Short-Term Memory Migration to Persistent Checkpointer (`P5`)

Goal: replace ephemeral `InMemorySaver` runtime behavior with persistent checkpointer backend.

- [ ] Add persistent checkpointer adapter selection (`sqlite` first).
- [ ] Keep `thread_id = session_id` invariant.
- [ ] Add config contract for checkpointer path/backend.
- [ ] Wire conversation runtime to use persistent backend by default in local mode.
- [ ] Add restart/resume tests for checkpointer continuity.
- [ ] Validate no regression in existing session JSON behavior.

Exit criteria:

- [ ] Conversation continuity proven after process restart using checkpointer-backed flow.
- [ ] Existing command/conversation tests pass unchanged.

---

## Phase 2: Long-Term Memory Store Adapter Layer (`P5`)

Goal: move custom file-repository internals to LangGraph Store-backed adapters while preserving external behavior.

- [ ] Define `StoreBackedPersonalityMemoryRepository`.
- [ ] Define `StoreBackedTaskMemoryRepository`.
- [ ] Preserve deterministic error mapping:
  - [ ] `memory_invalid_input`
  - [ ] `memory_not_found`
  - [ ] `memory_store_unavailable`
  - [ ] `memory_namespace_required`
  - [ ] `memory_schema_mismatch`
  - [ ] `memory_policy_denied`
- [ ] Preserve split-domain semantics via namespace policy.
- [ ] Add parity tests comparing file-backed vs store-backed behavior.

Exit criteria:

- [ ] Existing command handlers run against Store-backed repositories without contract change.
- [ ] File-backed implementation remains as fallback adapter (not primary).

---

## Phase 3: Runtime Retrieval Wiring (`P5`)

Goal: make prompt memory injection repository-backed and selective.

- [ ] Add retrieval service for prompt assembly:
  - [ ] personality query path
  - [ ] task query path (namespace constrained)
- [ ] Add deterministic ranking/filter policy:
  - [ ] confidence threshold
  - [ ] recency tie-break
  - [ ] bounded result count
- [ ] Inject retrieved summary into `PromptBuildContext.memory_summary`.
- [ ] Add prompt-size guards and truncation tests.

Exit criteria:

- [ ] Prompt memory section reflects retrieved records, not only manual summaries.
- [ ] Token bloat controls validated in tests.

---

## Phase 4: LangMem Tooling Integration (Controlled) (`P4`)

Goal: reduce custom write/search glue by integrating LangMem tooling in a controlled path.

- [ ] Introduce manage/search memory tools in experimental mode.
- [ ] Restrict tool usage to explicit command/agent paths first.
- [ ] Keep deterministic output envelope adapter on top of tool results.
- [ ] Add opt-in configuration flag for automatic memory tooling.
- [ ] Add safety and policy interceptors around tool writes.

Exit criteria:

- [ ] LangMem tools usable without breaking existing deterministic command outputs.
- [ ] Policy-denied behavior unchanged.

---

## Phase 5: Background Consolidation Pipeline (`P4`)

Goal: add post-run memory consolidation and profile merging.

- [ ] Define consolidation input/output schema.
- [ ] Implement deterministic rule-based extractor (phase 1).
- [ ] Add optional LLM-assisted extractor (phase 2, guarded).
- [ ] Add merge/conflict policy:
  - [ ] provenance preserved
  - [ ] confidence updates controlled
  - [ ] stale/conflicting memory handling
- [ ] Add scheduled/triggered execution path.

Exit criteria:

- [ ] Consolidation produces stable, auditable profile updates.
- [ ] No uncontrolled writes occur without explicit configuration.

---

## Phase 6: Optional Semantic Evidence Layer (`P3`)

Goal: add semantic retrieval for large artifacts while preserving structured truth.

- [ ] Add vector/evidence store abstraction.
- [ ] Add ingestion path for long artifacts (transcripts/notes/logs).
- [ ] Add retrieval API returning evidence citations.
- [ ] Keep structured memory as canonical in resolver policy.
- [ ] Add tests for contradiction handling (structured vs semantic evidence).

Exit criteria:

- [ ] Semantic retrieval improves recall without overriding canonical records.

---

## Phase 7: Ops, Safety, and Quality Gates (`P5`)

Goal: operationalize memory system changes with measurable safety/quality.

- [ ] Extend eval suites for migrated memory stack:
  - [ ] restart continuity with persistent checkpointer
  - [ ] store-backed parity
  - [ ] policy redline memory write denial
  - [ ] prompt retrieval relevance
- [ ] Add `memory migration` CI gate target.
- [ ] Add backup/export/restore operational docs.
- [ ] Add memory schema migration playbook.
- [ ] Add observability metrics:
  - [ ] write counts
  - [ ] denied writes
  - [ ] retrieval hit rates
  - [ ] consolidation drift indicators

Exit criteria:

- [ ] CI gates green across all supported platforms.
- [ ] Operational runbook ready for production use.

---

## Strong Additional Opportunities (From Research)

These are not blockers for V1 migration, but high-value next work.

- [ ] Context editing/compaction for long runs:
  - [ ] summarize/truncate policy
  - [ ] checkpoint-safe compaction
- [ ] Tool quality hardening:
  - [ ] enforce concise high-signal tool outputs
  - [ ] deterministic tool error taxonomy review
- [ ] Memory lifecycle policy:
  - [ ] TTL enforcement job
  - [ ] `last_verified` decay/revalidation
- [ ] Human review mode for high-impact memory writes.
- [ ] Memory explainability endpoint:
  - [ ] “why this memory was retrieved”
  - [ ] provenance trace display

---

## Risks and Mitigations

- [ ] Risk: migration changes behavior unexpectedly.
  - [ ] Mitigation: adapter parity tests + frozen command contracts.
- [ ] Risk: performance regression from Store backend.
  - [ ] Mitigation: benchmark gate + bounded retrieval.
- [ ] Risk: policy bypass through new tooling.
  - [ ] Mitigation: enforce policy gate at repository/tool boundary.

---

## Progress Log

- 2026-02-16: Plan created from V1 spec + LangGraph/LangMem + Anthropic best-practice synthesis.
