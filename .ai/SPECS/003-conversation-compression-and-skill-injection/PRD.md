# PRD
#
# Feature: Conversation Compression + Skill Injection Modes
#

**Author:** Jeff + Lily Runtime
**Audience:** Internal engineering
**Status:** Draft v1

---

# 1. Overview
Lily currently preserves conversation continuity via LangGraph checkpointing (`thread_id`), but long sessions can grow token usage as the full message history is repeatedly provided to the model.

Separately, Lily injects the enabled skill catalog into the system prompt during runtime agent construction. While this works, it limits experimentation with alternative, more deterministic injection points (for example via LangChain middleware).

This PRD defines an MVP engineering slice that:
1. Adds configurable conversation compression/summarization to reduce token growth in long sessions.
2. Adds an experimental mode for skill catalog injection that can be implemented via LangChain middleware (while keeping the current pre-build injection as default).

---

# 2. Mission
Provide a deterministic, configuration-driven way to:
1. Keep long sessions within practical token budgets via summarization of older context.
2. Allow the system prompt skill catalog injection to be implemented either at agent construction time or right before model execution via middleware, without changing the higher-level runtime/tool contracts.

---

# 3. Target Users
1. Lily operator
   - Needs: stable behavior in long-running conversations, lower cost/latency.
   - Comfort: intermediate CLI/TOML usage.
2. Lily runtime maintainer / engineer
   - Needs: an easy-to-extend injection strategy boundary and safe configuration toggles.
   - Comfort: advanced Python, LangChain/LangGraph middleware patterns.

---

# 4. MVP Scope

## In Scope
### Conversation compression (BL-001)
- ✅ Add `SummarizationMiddleware`-backed compression (or equivalent) that triggers when a configured token/message threshold is met.
- ✅ Preserve recent messages verbatim and summarize older messages into a single replacement context item.
- ✅ Ensure the compression modifies persisted agent state for checkpoint continuity (so the summary is reused on subsequent turns).
- ✅ Add config surfaces to enable/disable and set trigger/keep policy.

### Skill injection strategy (BL-002)
- ✅ Introduce a configuration-controlled injection strategy for the enabled skill catalog:
  - `middleware` (only): append catalog by mutating the model request system message right before model invocation.
- ✅ Preserve the existing `skill_catalog_injected` telemetry event semantics in both strategies.
- ✅ Keep the existing `skill_retrieve` retrieval tool behavior unchanged.

## Out of Scope
- ❌ Autonomous long-term memory systems beyond checkpointed conversation continuity.
- ❌ Semantic ranking/re-ranking of skills.
- ❌ UI/TUI changes beyond any necessary configuration documentation.
- ❌ New external dependencies (must use existing LangChain/LangGraph capabilities).

---

# 5. User Stories
1. As a Lily operator, I want long conversations to stay within token budgets so my runs remain fast and affordable.
2. As a Lily maintainer, I want configurable conversation compression with predictable behavior so I can debug context changes.
3. As a Lily maintainer, I want an injection strategy boundary for the skill catalog so I can experiment with deterministic middleware-based injection.
4. As a Lily operator, I want skill catalog injection to remain transparent via existing telemetry so I can verify which catalog was applied.

---

# 6. Core Architecture & Patterns
## Conversation compression
- Use `langchain.agents.middleware.summarization.SummarizationMiddleware`.
- The middleware operates on `AgentState["messages"]` in `before_model` / `abefore_model`.
- The middleware replaces older messages with a single summary and keeps a configured number of most recent messages.

## Skill injection strategy
- Implement middleware-only skill catalog injection by rewriting the model request
  system message right before model invocation (via a dedicated `AgentMiddleware`).
- Keep the higher-level runtime contracts (tool registry allowlist, retrieval tool binding, etc.) unchanged.

---

# 7. Tools / Features
### F1: ConversationCompressionConfig
- New config fields to enable/disable summarization and select trigger/keep policy.

### F2: SkillCatalogInjectionStrategy
- No additional config surface: when skills are enabled, catalog injection is
  performed via middleware.

### F3: Runtime integration
- Update `AgentRuntime._build_agent` to attach SummarizationMiddleware (when enabled)
  and to always attach the catalog injection middleware when a non-empty skill catalog exists.

---

# 8. Technology Stack
- Python 3.14+
- LangChain agents middleware
  - `SummarizationMiddleware`
- LangGraph checkpointing via `AsyncSqliteSaver`
- Existing Lily runtime components:
  - `src/lily/runtime/agent_runtime.py`
  - `src/lily/runtime/skill_loader.py`
  - `src/lily/runtime/skill_prompt_injector.py`

---

# 9. Security & Configuration
- Config must remain strictly validated (`pydantic`, `extra="forbid"`).
- The summarization pipeline must not exfiltrate secrets; it summarizes existing conversation text only.
- Compression must not alter tool allowlist or retrieval policy; it only compresses message history.

---

# 10. API Specification
No new external API endpoints are introduced. This feature adds configuration fields only.

---

# 11. Success Criteria
## MVP success definition
1. When compression is enabled, long sessions trigger summarization and the persisted message history becomes compact.
2. Skill catalog injection remains correct and telemetry remains emitted for the middleware path.

## Quality indicators
- Tests cover:
  - trigger/no-trigger behavior for summarization
  - that the summary replacement is persisted for subsequent turns
  - that middleware injection modifies the model request system message
- Final gates run warning-clean:
  - `just quality && just test`

---

# 12. Implementation Phases

### Phase 1: Config contracts and middleware wiring surface
- Goal: define strict config schema for compression + injection strategy.
- Deliverables:
  - Add config models / fields under `PoliciesConfig` and `SkillsConfig`.
  - Decide default values (compression disabled by default; middleware injection is always used).
- Validation:
  - `just types` and unit tests for config parsing/validation.

### Phase 2: Conversation compression implementation
- Goal: integrate `SummarizationMiddleware` when enabled.
- Deliverables:
  - attach `SummarizationMiddleware` to runtime middleware list based on config.
  - ensure summary replacement modifies persisted state across turns.
- Validation:
  - unit + integration tests verifying reduced message counts/contents across runs.

### Phase 3: Skill catalog middleware injection
- Goal: ensure middleware-based catalog injection is the only supported path.
- Deliverables:
  - new `AgentMiddleware` for system prompt skill catalog injection.
- Validation:
  - unit tests ensuring request system message includes catalog in middleware mode.

### Phase 4: Test hardening and docs/status sync
- Goal: final quality gates and operator documentation.
- Deliverables:
  - update runtime config docs for new fields.
  - add/extend tests and run `just quality && just test`.
- Validation:
  - `just docs-check`, `just status`, and final gates.

---

# 13. Future Considerations
- Per-skill compression summaries (avoid summarizing away retrieved content semantics).
- Advanced policy controls (e.g., summarization cooldown, separate triggers for tool calls).
- More injection strategies (middleware variants, prompt chunking).

---

# 14. Risks & Mitigations
1. Risk: Summarization increases model calls unexpectedly.
   - Mitigation: provide configuration defaults and add tests measuring calls; keep summarization trigger conservative.
2. Risk: Middleware ordering breaks determinism or changes behavior.
   - Mitigation: codify middleware ordering and add tests for injection + compression interaction.
3. Risk: Telemetry event duplicates or missing in middleware mode.
   - Mitigation: define and test event emission policy (emit once per runtime build).

