---
owner: "@team"
last_updated: "2026-02-19"
status: "active"
source_of_truth: true
---

# Blueprints + Jobs: GoF Patterns with LangChain/LangGraph

Purpose: document how Lily should implement Blueprints + Jobs using LangChain/LangGraph primitives first, with GoF patterns applied where custom code is still needed.

Scope:
- Blueprint runtime substrate (B1+)
- Jobs runtime (J0+)
- Run Contract alignment

## 1. Guiding Rule

Default to framework primitives first:
- Use LangChain/LangGraph for orchestration/runtime mechanics.
- Add custom Lily code only for domain policy, contracts, and operator UX.

Avoid re-implementing:
- tool-call loops
- middleware hook systems
- graph state progression
- checkpoint persistence semantics

## 2. LangChain/LangGraph Patterns to Use Directly

### 2.1 Agents Runtime

Use `create_agent` for graph-backed tool agents when a node is an agentic worker:
- built-in tool loop and stop conditions
- middleware hook points (`before_model`, `after_model`, `wrap_tool_call`, dynamic prompts)
- structured response support via `response_format`
- context injection via `context_schema` + runtime context

### 2.2 Chain Construction (LCEL)

Use LCEL as the default composition layer inside blueprint nodes:
- `RunnableSequence` for ordered pipelines
- `RunnableParallel` for map/reduce fan-out
- shared runnable methods such as `with_retry`, `bind`, `assign`, `get_graph`

### 2.3 Graph Orchestration

Use LangGraph `StateGraph` for blueprint compile targets:
- node functions for work units
- edges/conditional edges for deterministic routing
- explicit compile step for structural checks + runtime args

### 2.4 Persistence and Resume

Use LangGraph checkpointers for run continuity:
- thread-based state using `thread_id`
- checkpoint history, replay, fault-tolerance semantics
- SQLite for local dev, Postgres-class backends for production profile

### 2.5 Human-in-the-Loop

Use interrupts/HITL mechanisms for approval boundaries:
- `interrupt()` + `Command(resume=...)` for run pauses
- enforce side-effect approvals before irreversible operations

## 3. GoF Pattern Mapping (Lily-Specific)

| Concern | GoF Pattern | LangChain/LangGraph Primitive | Lily Custom Layer |
|---|---|---|---|
| Blueprint execution shape (council, pipeline, pex) | `Strategy` | `StateGraph` + LCEL building blocks | `BlueprintCompiler` strategy map by blueprint id |
| Runtime creation by id | `Abstract Factory` | n/a (framework-neutral) | Factory for runnable/tool/provider adapters from registry ids |
| Blueprint compile entrypoint | `Factory Method` | `compile()` in blueprint implementation | `Blueprint.compile(bindings)` returns compiled graph/runnable |
| Job run lifecycle | `Template Method` | invoke/stream APIs | fixed sequence: load -> validate -> resolve -> policy -> execute -> persist |
| Job operation requests | `Command` | `Command` objects (LangGraph), CLI commands | `RunJobCommand`, `TailJobCommand`, `ReplayRunCommand` |
| Validation/policy gates | `Chain of Responsibility` | middleware + validators | ordered handlers for spec, bindings, capability, approval |
| Run lifecycle tracking | `State` | graph state + checkpoint state | job/run status model: pending/running/succeeded/failed/blocked |
| Eventing/tailing | `Observer` | stream APIs | subscribers for CLI tail, metrics, artifact event sink |
| Cross-cutting runtime concerns | `Decorator` | runnable wrappers / middleware | timeout, retry, metrics, tracing, policy audit wrappers |
| Legacy and provider integration | `Adapter` | tool/model abstractions | wrap skills/tools/providers into unified runnable contract |
| Simpler public API | `Facade` | n/a (framework-neutral) | `BlueprintsFacade`, `JobsFacade` for CLI + Director |

## 4. Build vs Borrow Decisions

### 4.1 Borrow (Do not rebuild)

- Agent loop mechanics: LangChain `create_agent`
- Middleware lifecycle hooks: LangChain middleware
- Typed structured output enforcement: `response_format` strategies
- Graph state progression: LangGraph `StateGraph`
- Checkpoint persistence and resume: LangGraph checkpointers
- Human approval pause/resume transport: LangGraph interrupts/HITL
- Sequence/parallel composition mechanics: LCEL runnables

### 4.2 Build (Lily-specific value)

- Run Contract R0 envelope and stable error codes
- Blueprint registry ids, deterministic resolution, and contract diagnostics
- Job spec model (`.lily/jobs/*.job.yaml`) and deterministic validation errors
- Capability/approval policy mapping for side effects
- Artifact contract and run receipt conventions
- Operator-facing CLI rendering and troubleshooting UX

## 5. Blueprint + Job Integration Shape

## 5.1 Blueprint side

- Blueprints remain code-defined in V0.
- Each blueprint defines:
  - stable `id` and `version`
  - typed bindings/input/output schemas
  - `compile(bindings)` returning executable graph/runnable

## 5.2 Job side

- Jobs are concrete invocations bound to blueprint ids.
- Job runner resolves blueprint -> validates bindings -> compiles -> executes.
- Job execution writes deterministic artifacts:
  - `run_receipt.json`
  - `summary.md`
  - `events.jsonl`

## 6. Pattern-Level Anti-Patterns to Avoid

- Re-implementing a custom agent loop instead of `create_agent`.
- Building custom parallel orchestration where LCEL/StateGraph already fits.
- Encoding policy checks only in prompts (must be enforced in code/middleware).
- Maintaining two execution truths (template DSL + code graph) in V0.
- Letting job flows bypass compile/validation/policy boundaries.

## 7. Immediate Application to Current Plans

For `docs/dev/blueprints_execution_plan.md`:
- B1 should implement `council.v1` as:
  - compile-time strategy selection
  - LCEL or StateGraph map/reduce execution
  - structured specialist outputs before synthesis

For `docs/dev/jobs_execution_plan.md`:
- J0 should implement:
  - Template Method job runner lifecycle
  - Chain-of-Responsibility validation/policy handlers
  - Observer-style event publishing to tail + artifacts

## 8. Source References (Official)

- LangChain Agents:
  - https://docs.langchain.com/oss/python/langchain/agents
- LangChain Structured Output:
  - https://docs.langchain.com/oss/python/langchain/structured-output
- LangChain Runtime (context/store/stream writer):
  - https://docs.langchain.com/oss/python/langchain/runtime
- LangChain Middleware:
  - https://docs.langchain.com/oss/python/langchain/middleware/custom
- LangChain Multi-agent (handoffs/subagents):
  - https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs
  - https://docs.langchain.com/oss/python/langchain/multi-agent/subagents
- LangGraph Graph API:
  - https://docs.langchain.com/oss/python/langgraph/graph-api
- LangGraph Persistence:
  - https://docs.langchain.com/oss/python/langgraph/persistence
- LangGraph Interrupts:
  - https://docs.langchain.com/oss/python/langgraph/interrupts
- LCEL Runnable composition:
  - https://api.python.langchain.com/en/latest/core/runnables/langchain_core.runnables.base.Runnable.html
  - https://api.python.langchain.com/en/latest/core/runnables/langchain_core.runnables.base.RunnableSequence.html
  - https://api.python.langchain.com/en/latest/core/runnables/langchain_core.runnables.base.RunnableParallel.html
