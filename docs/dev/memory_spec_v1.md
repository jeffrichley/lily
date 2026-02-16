# LILY MEMORY SPECIFICATION (V1)

Status: Proposed  
Date: 2026-02-16  
Supersedes: `docs/dev/memory_spec_v0.md` (conceptual draft)  
Scope: Short-term + long-term memory architecture and migration strategy

---

## 1. Why V1 Exists

Lily currently has:

- Deterministic session persistence for conversation state.
- Split long-term memory stores (`personality_memory`, `task_memory`) with policy checks.
- Strong command UX (`/remember`, `/memory show`, `/forget`) and deterministic envelopes.

But we are still carrying custom memory plumbing that LangGraph/LangMem can provide with less maintenance burden.

V1 defines:

- What we keep (product behavior/contracts).
- What we replace (infrastructure internals).
- How we migrate safely in phases.

---

## 2. Design Principles (Locked)

1. Local-first by default.
2. Deterministic contracts at command/runtime boundaries.
3. Explicit separation:
   - short-term execution state
   - long-term cross-thread memory
   - optional semantic retrieval evidence
4. Eval-driven changes; no silent memory behavior changes.
5. Structured store is canonical truth; semantic retrieval is supporting context.
6. Minimize custom code where LangGraph/LangMem already solves the problem.

---

## 3. Out-of-the-Box Platform Capabilities We Will Use

### LangGraph

- Checkpointer persistence keyed by `thread_id` for resume/time-travel/fault tolerance.
- Store API for cross-thread memory with namespace organization.
- Semantic search in Store when embeddings/indexing are configured.

### LangMem

- Memory management tools:
  - `create_manage_memory_tool`
  - `create_search_memory_tool`
- Memory manager patterns for consolidation/reflection workflows.

### Anthropic best-practice alignment

- Eval-driven iteration for agent behavior changes.
- Tool ergonomics:
  - clear purpose
  - strong namespacing
  - meaningful, token-efficient responses
- Context management for long-running tasks:
  - context editing/compaction
  - memory tool usage instead of transcript bloat

---

## 4. Current vs Target Architecture

## Current (implemented)

- Short-term:
  - Session JSON persistence (`conversation_state`) is canonical.
  - LangGraph checkpointer is `InMemorySaver`.
- Long-term:
  - Custom JSON file repositories for personality/task memory.
  - Command writes/reads routed directly to custom repositories.
- Prompt memory:
  - Memory section is present, but repository-backed retrieval is limited/manual.

## Target (V1)

- Short-term:
  - Persistent LangGraph checkpointer backend (SQLite first).
  - `thread_id = session_id` remains stable.
  - Session JSON remains as outer session metadata/state envelope; graph checkpoints become execution source of truth.
- Long-term:
  - LangGraph Store backend for durable cross-thread memory.
  - Keep split-store semantics via namespace policy:
    - personality namespaces
    - task namespaces
  - Existing command contracts stay stable while internals move to Store adapters.
- Retrieval:
  - Structured store query first.
  - Optional semantic store/search as evidence layer.
- Automation:
  - Controlled LangMem memory tools (opt-in paths first).
  - Background consolidation pipeline added after deterministic baseline is stable.

---

## 5. Canonical Memory Domains

### 5.1 Short-Term (Thread Scoped)

Purpose:
- Turn-by-turn execution continuity and resumability.

Canonical backend:
- LangGraph checkpointer.

Key invariants:
- Always invoke with `thread_id`.
- No large artifact blobs in checkpoint state.
- Keep checkpoint state execution-focused.

### 5.2 Long-Term (Cross-Thread)

Purpose:
- Durable preferences, identity constraints, project/task facts.

Canonical backend:
- LangGraph Store.

Namespace model:
- Personality memory:
  - `("memory", "personality", <user_or_workspace>, <scope>)`
- Task memory:
  - `("memory", "task", <task_or_project>, <scope>)`

Rule:
- No implicit cross-domain retrieval in default command/runtime path.

### 5.3 Semantic Evidence (Optional)

Purpose:
- Similarity retrieval for large artifacts and historical context.

Rule:
- Never treated as canonical truth.

---

## 6. Data Contract Requirements

All long-term records should retain equivalent metadata fields currently used in Lily:

- `schema_version`
- `source` (command/inference/import/system)
- `confidence`
- `created_at`, `updated_at`
- `session_id` / source thread reference
- optional stability/expiry/task linkage fields

Additional V1 fields:

- `last_verified` (nullable)
- `conflict_group` (nullable, for reconciliation)

Notes:
- These remain logical fields; physical representation may differ by Store backend.

---

## 7. Policy, Safety, and Precedence

Memory writes remain policy-gated:

- blocked sensitive content => deterministic `memory_policy_denied`

Precedence for style/personality remains unchanged:

- `safety > user style > persona default > stochastic expression`

No auto-write behavior without explicit policy and eval coverage.

---

## 8. Command Surface Compatibility (Must Preserve)

The following commands remain behaviorally stable while internals migrate:

- `/remember <text>`
- `/memory show [query]`
- `/forget <memory_id>`
- `/persona ...` and `/style ...` (where relevant memory/profile interactions exist)

Contract constraints:

- deterministic `code` values remain stable
- CLI UX remains human-first (tables/panels)
- no forced user migration for basic workflows

---

## 9. Migration Strategy (Summary)

1. Replace short-term checkpointer internals first.
2. Introduce Store-backed long-term adapters behind existing repository interfaces.
3. Switch command handlers/runtime retrieval to adapters.
4. Add selective prompt-memory retrieval wiring.
5. Add LangMem tooling in controlled opt-in mode.
6. Add consolidation/background memory management.
7. Add optional semantic retrieval.

This order keeps user-visible behavior stable while reducing custom infra code early.

---

## 10. Non-Goals (for V1 Delivery)

- Full autonomous memory writing from all conversation turns by default.
- Replacing deterministic command envelopes with opaque tool outputs.
- Treating semantic search results as authoritative memory facts.
- Full multi-agent memory orchestration beyond current compatibility surface.

---

## 11. Acceptance Criteria

V1 is considered successful when:

1. Short-term conversation execution survives restart via persistent checkpointer.
2. Long-term memory commands use Store-backed adapters with unchanged public behavior.
3. Phase 7 eval suites remain green after migration.
4. Memory provenance remains inspectable and deterministic.
5. Total custom memory infrastructure code is reduced without losing functionality.

---

## 12. Source References

- LangGraph persistence docs:
  - https://docs.langchain.com/oss/python/langgraph/persistence
- LangGraph memory/store docs:
  - https://docs.langchain.com/oss/python/langgraph/add-memory
- LangMem tools/reference:
  - https://langchain-ai.github.io/langmem/reference/tools/
  - https://langchain-ai.github.io/langmem/reference/
- Anthropic context management:
  - https://www.anthropic.com/news/context-management
- Anthropic tool design best practices:
  - https://www.anthropic.com/engineering/writing-tools-for-agents
- Anthropic eval best practices:
  - https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
