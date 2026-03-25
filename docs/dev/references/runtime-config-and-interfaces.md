---
owner: "@jeffrichley"
last_updated: "2026-03-05"
status: "active"
source_of_truth: true
---

# Runtime Config And Interfaces

This document defines the active runtime configuration contract and user-facing interfaces for the reboot kernel.

## Scope

Covers:
- YAML/TOML runtime configuration schema
- Tool catalog (`tools.yaml` / `tools.toml`) and runtime allowlist boundary (`agent.yaml` / `agent.toml`)
- CLI interfaces (`lily run`, `lily tui`)
- Textual TUI behavior
- Runtime policy surfaces currently enforced

Does not cover:
- Skill registry/discovery beyond static catalog entries
- Sub-agent orchestration framework
- Autonomous skill evolution/logging engine

## Config Files

Primary runtime config:
- `.lily/config/agent.yaml` or `.lily/config/agent.toml`

Tool catalog config:
- `.lily/config/tools.yaml` or `.lily/config/tools.toml`

Default pairing behavior:
- when runtime config is `agent.yaml`/`agent.yml`, supervisor defaults to `tools.yaml` in the same directory
- when runtime config is `agent.toml`, supervisor defaults to `tools.toml` in the same directory

## Config Schema (YAML/TOML)

Top-level keys in `agent.*`:
- `schema_version`
- `agent`
- `models`
- `tools`
- `mcp_servers` (optional)
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
- `allowlist`: ordered list of tool IDs bound into runtime invocation

### `mcp_servers` (optional)
- Mapping of server name to server config.
- Supported transports:
  - `transport: streamable_http`
    - `url`: MCP streamable HTTP endpoint
    - `headers` (optional): request headers mapping
    - `timeout_seconds` (optional): request and stream timeout
  - `transport: test` (fixture-only deterministic local path)
    - `tool_targets`: mapping of remote MCP tool name -> Python import target (`module.path:attribute`)

### `policies`
- `max_iterations`: recursion limit for LangChain graph invoke
- `max_model_calls`: enforced via LangChain `ModelCallLimitMiddleware`
- `max_tool_calls`: enforced via LangChain `ToolCallLimitMiddleware`

### `logging`
- `level`: `DEBUG|INFO|WARNING|ERROR`

## Tool Catalog Contract (`tools.*`)

Top-level keys:
- `definitions`

Definition variants:
- Python definition:
  - `id`
  - `source: python`
  - `target` (`module.path:attribute`)
- MCP definition:
  - `id`
  - `source: mcp`
  - `server`
  - `remote_tool`

Validation constraints:
- `id` values must be snake_case and unique across all definitions.
- Unknown fields are rejected.
- Invalid catalog files fail fast with deterministic field-specific errors.

## Runtime Behavior

Runtime path:
1. `agent.*` load + pydantic validation
2. `tools.*` load + catalog validation
3. catalog definition resolution to tool objects (Python/MCP resolver layer)
4. model profile construction (`ModelFactory`)
5. dynamic model middleware wiring (`DynamicModelRouter`)
6. tool registration + `agent.yaml` allowlist filtering (`ToolRegistry.allowlisted`)
7. LangChain `create_agent` execution (`AgentRuntime`)

Policy boundary:
- `tools.*` defines what exists in the catalog.
- `agent.*` `tools.allowlist` defines what gets bound for execution.
- `agent.*` `mcp_servers` defines MCP server providers used to resolve catalog MCP tools.

Example real MCP server config (`agent.yaml`):
```yaml
mcp_servers:
  langgraph_docs:
    transport: streamable_http
    url: https://gitmcp.io/langchain-ai/langgraph
```

Equivalent TOML config (`agent.toml`):
```toml
[mcp_servers.langgraph_docs]
transport = "streamable_http"
url = "https://gitmcp.io/langchain-ai/langgraph"
```

Single prompt contract:
- Input: prompt text
- Output: deterministic result object with:
  - `final_output`
  - `message_count`

## CLI Interfaces

### `lily run`

Runs a single prompt through supervisor runtime.

Example (YAML):
```bash
uv run lily run --prompt "hello" --config .lily/config/agent.yaml
```

Example (TOML):
```bash
uv run lily run --prompt "hello" --config .lily/config/agent.toml
```

Options:
- `--prompt` (required)
- `--config` (defaults to `.lily/config/agent.toml`)
- `--override` (optional runtime override)

### `lily tui`

Launches Textual app with transcript + input.

Example (YAML):
```bash
uv run lily tui --config .lily/config/agent.yaml
```

Example (TOML):
```bash
uv run lily tui --config .lily/config/agent.toml
```

Exit keys in TUI:
- `Ctrl+Q`
- `Esc`
- `Ctrl+C`

## Test Surfaces

- Unit: `tests/unit/runtime/test_config_loader.py`
- Unit: `tests/unit/runtime/test_tool_catalog.py`
- Unit: `tests/unit/runtime/test_tool_resolvers.py`
- Integration: `tests/integration/test_agent_runtime.py`
- Integration: `tests/integration/test_lily_supervisor.py`
- E2E CLI: `tests/e2e/test_cli_agent_run.py`
- E2E TUI: `tests/e2e/test_tui_app.py`

## Deferred Boundaries

Explicitly deferred from current implementation slice:
- dynamic capability/skill discovery selection beyond static catalog entries
- sub-agent runtime and delegation graph
- autonomous evolution/reflection pipelines
