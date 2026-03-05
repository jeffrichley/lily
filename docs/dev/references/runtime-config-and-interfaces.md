---
owner: "@team"
last_updated: "2026-03-05"
status: "active"
source_of_truth: true
---

# Runtime Config And Interfaces

This document defines the active runtime configuration contract and user-facing interfaces for the reboot kernel.

## Scope

Covers:
- YAML runtime configuration schema
- CLI interfaces (`lily run`, `lily tui`)
- Textual TUI behavior
- Runtime policy surfaces currently enforced

Does not cover:
- Skill registry/discovery
- Sub-agent orchestration framework
- Autonomous skill evolution/logging engine

## Config Files

Primary runtime config:
- `.lily/config/agent.yaml`

Tool allowlist-only config (optional override source):
- `.lily/config/tools.yaml`

## YAML Schema (Current)

Top-level keys:
- `schema_version`
- `agent`
- `models`
- `tools`
- `policies`
- `logging`

### `agent`
- `name`: supervisor/agent runtime name
- `system_prompt`: system prompt passed to LangChain `create_agent`

### `models`
- `profiles`: named model profiles with:
  - `provider` (`openai` | `ollama`)
  - `model`
  - `temperature`
  - `timeout_seconds` (model-level timeout)
- `routing`: dynamic model policy with:
  - `enabled`
  - `default_profile`
  - `long_context_profile`
  - `complexity_threshold`

### `tools`
- `allowlist`: ordered list of tool names enabled for runtime invocation

### `policies`
- `max_iterations`: recursion limit for LangChain graph invoke
- `max_model_calls`: enforced via LangChain `ModelCallLimitMiddleware`
- `max_tool_calls`: enforced via LangChain `ToolCallLimitMiddleware`

### `logging`
- `level`: `DEBUG|INFO|WARNING|ERROR`

## Runtime Behavior

Runtime path:
1. YAML load + pydantic validation
2. model profile construction (`ModelFactory`)
3. dynamic model middleware wiring (`DynamicModelRouter`)
4. tool registration + allowlist filtering (`ToolRegistry`)
5. LangChain `create_agent` execution (`AgentRuntime`)

Single prompt contract:
- Input: prompt text
- Output: deterministic result object with:
  - `final_output`
  - `message_count`

## CLI Interfaces

### `lily run`

Runs a single prompt through supervisor runtime.

Example:
```bash
uv run lily run --prompt "hello" --config .lily/config/agent.yaml
```

Options:
- `--prompt` (required)
- `--config` (defaults to `.lily/config/agent.yaml`)
- `--override` (optional YAML override)

### `lily tui`

Launches Textual app with transcript + input.

Example:
```bash
uv run lily tui --config .lily/config/agent.yaml
```

Exit keys in TUI:
- `Ctrl+Q`
- `Esc`
- `Ctrl+C`

## Test Surfaces

- Unit: `tests/unit/runtime/test_config_loader.py`
- Integration: `tests/integration/test_agent_runtime.py`
- E2E CLI: `tests/e2e/test_cli_agent_run.py`
- E2E TUI: `tests/e2e/test_tui_app.py`

## Deferred Boundaries

Explicitly deferred from current implementation slice:
- capability/skill registry selection surfaces
- sub-agent runtime and delegation graph
- autonomous evolution/reflection pipelines
