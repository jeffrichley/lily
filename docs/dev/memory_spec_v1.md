---
owner: "TBD"
last_updated: "TBD"
status: "reference"
source_of_truth: false
---

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
- Production-grade persistence via database-backed checkpointers/stores (for example, Postgres-backed savers/stores), with local-first development defaults.
- Checkpoint inspection APIs (`get_state`, `get_state_history`) and replay (`checkpoint_id`) for auditability/debugging.
- Explicit memory-store indexing controls per write (index specific fields vs `index=False` for non-searchable payloads).
- Built-in state/context management primitives for long runs (trim, delete, summarize message history) to prevent context-window failure modes.

### LangMem

- Memory management tools:
  - `create_manage_memory_tool`
  - `create_search_memory_tool`
- Memory manager patterns for consolidation/reflection workflows.
- Store-backed manager utilities:
  - `create_memory_manager`
  - `create_memory_store_manager`
- Reflection/background execution utilities (for deferred memory consolidation) via `ReflectionExecutor`.

### Anthropic best-practice alignment

- Eval-driven iteration for agent behavior changes.
- Tool ergonomics:
  - clear purpose
  - strong namespacing
  - meaningful, token-efficient responses
- Context management for long-running tasks:
  - context editing/compaction
  - memory tool usage instead of transcript bloat
- Evaluation discipline:
  - split capability evals vs regression evals
  - run multiple trials for stochastic tasks
  - inspect transcripts regularly to validate grader quality

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
  - Global Lily config controls checkpointer backend/path with local default:
    - backend: `sqlite`
    - sqlite path: `.lily/checkpoints/checkpointer.sqlite`
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
- Default persistence path is controlled by global Lily config (`.lily/checkpoints/checkpointer.sqlite` in local mode).

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
- Task memory is classified as long-term scoped memory (never short-term execution state).

Long-term subdomains:

- `persona_core`
  - Purpose: stable identity, persona voice, enduring behavioral traits.
  - Examples: tone anchors, non-negotiable persona constraints.
- `user_profile`
  - Purpose: durable user preferences and recurring user-specific patterns.
  - Examples: preferred response format, cadence, constraint preferences.
- `working_rules`
  - Purpose: durable "how Lily should operate" execution/playbook guidance.
  - Examples: preferred planning style, escalation rules, reporting defaults.
- `task_memory`
  - Purpose: project/task facts and decisions that persist beyond one thread.
  - Examples: accepted requirements, architecture choices, deferred items.

Suggested namespace mapping:

- `("memory", "personality", "persona_core", <user_or_workspace>, <scope>)`
- `("memory", "personality", "user_profile", <user_or_workspace>, <scope>)`
- `("memory", "personality", "working_rules", <user_or_workspace>, <scope>)`
- `("memory", "task", "task_memory", <task_or_project>, <scope>)`

### 5.3 Semantic Evidence (Optional)

Purpose:
- Similarity retrieval for large artifacts and historical context.

Rule:
- Never treated as canonical truth.

### 5.4 Context Working Set (Short-Term Control Plane)

Purpose:
- Keep active prompt context bounded and high-signal during long-running tasks.

Primary mechanisms:
- deterministic transcript compaction (summarize/trim stale tool outputs)
- deletion of low-value historical tool payloads from active context
- externalization of durable facts to long-term memory stores

Rule:
- If short-term context pressure rises, compact first and persist durable facts; do not silently drop high-value memory facts.

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

### 6.1 Lifecycle and Retention Policy (Default)

| Subdomain | Stability default | Expiry metadata | Reverification |
|---|---|---|---|
| `persona_core` | high | none | only on explicit user/persona update |
| `working_rules` | high | none | scheduled review or explicit correction |
| `user_profile` | medium-high | optional | periodic re-verification using `last_verified` |
| `task_memory` | medium | optional namespace expiry/archive markers | per task lifecycle milestone |

Rules:
- Expiry and archival are metadata states in V1; they are not automatic hard-delete actions.
- Canonical memory records are never automatically deleted by lifecycle jobs in V1.
- Expired/archived records are excluded from default retrieval unless explicitly requested.
- `last_verified` should be updated on explicit confirmation events, not inferred silently from weak signals.

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

### 8.1 Three-Level Memory Command Model (V1 Additive)

V1 introduces explicit command families aligned to memory layers (while keeping legacy commands):

- Short-term memory (thread/checkpointer scope):
  - `/memory short show`
  - `/memory short checkpoints [--limit N]`
- Long-term structured memory (canonical cross-thread facts):
  - `/memory long show [query]`
  - `/memory long show --domain persona_core [query]`
  - `/memory long show --domain user_profile [query]`
  - `/memory long show --domain working_rules [query]`
  - `/memory long task show --namespace <task_or_project> [query]`
  - `/remember` and `/forget` remain compatibility aliases for long-term personality memory.
- Semantic evidence memory (non-canonical similarity evidence):
  - `/memory evidence show [query]`
  - `/memory evidence ingest <path_or_ref>`

Rules:

- Structured long-term memory remains canonical source of truth.
- Evidence commands must always label results as non-canonical evidence/citation context.
- Default interactive output uses Rich tables/panels, not raw JSON panels.

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
- Automatic hard-deletion lifecycle pipelines for memory storage.

---

## 11. Acceptance Criteria

V1 is considered successful when:

1. Short-term conversation execution survives restart via persistent checkpointer.
2. Long-term memory commands use Store-backed adapters with unchanged public behavior.
3. Phase 7 eval suites remain green after migration.
4. Memory provenance remains inspectable and deterministic.
5. Total custom memory infrastructure code is reduced without losing functionality.
6. Long-running runs have deterministic context-compaction behavior that prevents unbounded prompt growth.
7. Evaluation suite includes both:
   - capability coverage for new memory behavior
   - high-pass regression coverage protecting existing contracts.

---

## 12. Source References

- LangGraph persistence docs:
  - https://docs.langchain.com/oss/python/langgraph/persistence
- LangGraph memory/store docs:
  - https://docs.langchain.com/oss/python/langgraph/add-memory
  - https://docs.langchain.com/langgraph-platform/semantic-search
- LangMem tools/reference:
  - https://langchain-ai.github.io/langmem/reference/tools/
  - https://langchain-ai.github.io/langmem/reference/
- Anthropic context management:
  - https://www.anthropic.com/news/context-management
- Anthropic tool design best practices:
  - https://www.anthropic.com/engineering/writing-tools-for-agents
- Anthropic eval best practices:
  - https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- Anthropic long-running agent practices:
  - https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk
  - https://www.anthropic.com/engineering/built-multi-agent-research-system
