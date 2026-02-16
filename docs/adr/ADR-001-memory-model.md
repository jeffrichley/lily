# ADR-001: Lily Memory Model (Split Personality + Task Stores)

- Status: Accepted
- Date: 2026-02-16
- Owners: Lily core runtime
- Related:
  - `docs/dev/personality_roadmap.md`
  - `docs/specs/agent_mode_v0/SESSION_MODEL_V0.md`

## Context

Lily is moving from command-only V0 behavior toward a personality-aware conversational runtime.  
Memory will become a core subsystem that affects tone consistency, task continuity, safety, and determinism.

The main decision is whether to keep one unified memory store or split memory by purpose.

## Decision

Use **two separate logical stores**:

1. `personality_memory`
- Long-lived user/assistant relationship facts and durable preferences.
- Example: preferred name, writing preferences, stable working style.

2. `task_memory`
- Work/task/session-scoped context and progress.
- Example: in-progress plan state, decisions made for a specific task, pending todos.

Task memory is additionally segmented by namespace (`task_id` and/or `session_id`) so unrelated work does not mix.

## Rationale

- Prevents preference/persona facts from contaminating task recall.
- Enables different retention strategies (durable personality vs expiring task data).
- Improves retrieval precision and debugability.
- Makes user controls clearer (`forget preference` vs `clear task context`).
- Lowers safety risk from over-personalized behavior in operational task context.

## Alternatives Considered

1. Single unified memory store with namespaces
- Pros: simpler storage operations, fewer components.
- Cons: easier leakage across memory types, harder ranking policy, ambiguous deletion semantics.
- Decision: rejected for v1 due to safety and consistency risks.

2. No long-term memory (session-only)
- Pros: simplest design.
- Cons: weak personality continuity and poor long-running task experience.
- Decision: rejected; does not meet roadmap goals.

## Memory Boundaries

### Personality Memory (Store A)

- Contains:
  - user preferences, communication style, stable relationship facts
  - high-signal durable constraints
- Must not contain:
  - secrets, credentials, unsafe personal inferences, high-risk regulated advice artifacts
- Default retention: long-lived, explicit delete on `/forget` or user privacy actions

### Task Memory (Store B)

- Contains:
  - task/project context, short-to-mid-term decisions, checkpoints, open loops
- Must not contain:
  - durable personal profile facts unless explicitly promoted
- Default retention: TTL-based plus archive/compaction policy

## Data Contracts

## Shared record envelope

```json
{
  "id": "mem_...",
  "schema_version": 1,
  "store": "personality_memory | task_memory",
  "namespace": "string",
  "content": "string",
  "source": "command|inference|import|system",
  "confidence": 0.0,
  "tags": ["string"],
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601"
}
```

## Personality extension fields

```json
{
  "preference_type": "name|tone|format|workflow|boundary",
  "stability": "high|medium|low"
}
```

## Task extension fields

```json
{
  "task_id": "string",
  "session_id": "string",
  "status": "active|paused|done|abandoned",
  "expires_at": "ISO-8601|null"
}
```

## Write Semantics

- Sources:
  - explicit command (`/remember`) is preferred for high-confidence writes
  - controlled auto-write paths can be added later with strict filters
- Upsert/dedup:
  - normalize content hash + namespace for duplicate suppression
  - update `updated_at` and confidence when reinforcing existing memory
- Promotions:
  - task facts can be promoted into personality memory only through explicit rule/command path

## Retrieval Contract

- Query shape:
  - `store`: required (`personality_memory` or `task_memory`)
  - `query`: required string
  - `namespace`: optional but recommended for task memory
  - `limit`: default 5, max 20
  - `min_confidence`: optional
- Ranking:
  - personality: preference stability + semantic similarity + recency tie-break
  - task: namespace match + semantic similarity + recency + active status boost
- Cross-store queries:
  - disabled by default in v1 to prevent accidental blending
  - optional explicit dual-query mode may be added later

## Retention and Deletion

- Personality:
  - no TTL by default
  - deleted only by explicit user/system action
- Task:
  - default TTL applied to inactive/done records
  - archival/compaction for old namespaces
- Deletion semantics:
  - `/forget` performs hard delete of targeted records
  - delete operations are idempotent

## Safety and Privacy Controls

- Blocklist categories for storage:
  - secrets/tokens/passwords
  - sensitive data disallowed by policy
  - manipulative or dependency-seeking reinforcement content
- Memory writes pass policy filter before persist.
- Memory reads can be filtered by policy context (future extension).

## Deterministic Error Model

All memory operations return stable envelope fields:

- `status`: `ok | error`
- `code`: machine-readable code
- `message`: human-readable summary
- `data`: optional structured payload

Initial memory error codes:

- `memory_invalid_input`
- `memory_not_found`
- `memory_policy_denied`
- `memory_store_unavailable`
- `memory_namespace_required`
- `memory_schema_mismatch`

## Versioning and Migration

- Each record includes `schema_version`.
- v1 starts at `schema_version = 1`.
- Migration strategy:
  - read path supports known prior versions via adapter
  - write path always emits latest version
  - corrupt/unknown versions return `memory_schema_mismatch` with deterministic message

## Operational Notes

- Storage backend can start file-based, with repository interfaces to allow SQLite/Postgres later.
- Keep store interfaces isolated from prompt/policy layer via repository contracts.
- Emit memory events (created/updated/deleted) for future eval and observability.

## Test Plan (Required Before “Accepted”)

1. Unit tests
- create/read/update/delete for each store
- namespace isolation behavior
- dedup/upsert semantics
- deterministic errors for invalid inputs and missing records

2. Integration tests
- no cross-store leakage in retrieval
- task TTL expiration behavior
- restart/restore continuity

3. Policy tests
- blocked content categories do not persist
- `/forget` hard delete behavior is deterministic

4. Drift tests
- retrieval stability under unrelated filesystem/store mutations

## Rollout Plan

1. Add repository interfaces + file adapters for both stores.
2. Add command-level memory operations with deterministic envelopes.
3. Integrate retrieval into prompt assembly via explicit store-scoped calls.
4. Enable controlled auto-write only after policy + eval coverage is in place.

## Acceptance Criteria

- Split-store behavior is enforced and tested.
- No implicit cross-store reads in default runtime path.
- Deterministic memory error envelopes are stable.
- Migration path for `schema_version` is implemented (at least stub + tests).

## Open Questions

- Default task TTL duration by task status (`active`, `done`, `abandoned`).
- Whether task memory namespace should require `task_id` always, or allow `session_id` fallback.
- Whether explicit “promote to personality” should be command-only in v1.
