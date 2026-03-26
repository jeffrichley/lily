---
owner: "@jeffrichley"
last_updated: "2026-03-26"
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

Named-agent runtime config (primary contract):
- `.lily/agents/<agent-name>/agent.yaml` or `.lily/agents/<agent-name>/agent.toml`

Named-agent tool catalog config:
- `.lily/agents/<agent-name>/tools.yaml` or `.lily/agents/<agent-name>/tools.toml`

Default named agent:
- `.lily/agents/default/` is selected when `--agent` is omitted.

Default pairing behavior:
- when runtime config is `agent.yaml`/`agent.yml`, supervisor defaults to `tools.yaml` in the same directory
- when runtime config is `agent.toml`, supervisor defaults to `tools.toml` in the same directory

Legacy explicit config mode:
- `--config` still accepts any explicit `agent.*` path.
- In this mode, session scoping remains rooted at process cwd.
- `--config` and `--agent` are mutually exclusive.

## Named-Agent Workspace Contract

Each named agent directory under `.lily/agents/<agent-name>/` must contain:

- Required files:
  - `agent.toml` (or `agent.yaml` / `agent.yml`)
  - paired `tools.toml` (or `tools.yaml`)
  - `AGENTS.md`
  - `IDENTITY.md`
  - `SOUL.md`
  - `USER.md`
  - `TOOLS.md`
- Required directories:
  - `skills/`
  - `memory/`

Validation behavior:
- Missing required file/dir fails fast with deterministic CLI/runtime error.
- Agent names are directory identifiers and support values like `pepper-potts`.

Session/memory scoping:
- In `--agent` mode, conversation sessions are isolated per selected agent workspace
  (session DB path is rooted under that agent directory).

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
  - `transport: sse`
    - `url`: MCP SSE endpoint
    - `headers` (optional): request headers mapping
    - `timeout_seconds` (optional): request and SSE read timeout
  - `transport: stdio`
    - `command`: executable used to start local MCP server
    - `args`: command arguments list
    - `env` (optional): environment variables mapping
    - `cwd` (optional): process working directory
    - `encoding` (optional): stdio encoding
    - `encoding_error_handler` (optional): `strict|ignore|replace`
  - `transport: websocket`
    - `url`: MCP websocket endpoint
  - `transport: test` (fixture-only deterministic local path)
    - `tool_targets`: mapping of remote MCP tool name -> Python import target (`module.path:attribute`)

### `policies`
- `max_iterations`: recursion limit for LangChain graph invoke
- `max_model_calls`: enforced via LangChain `ModelCallLimitMiddleware`
- `max_tool_calls`: enforced via LangChain `ToolCallLimitMiddleware`

### `logging`
- `level`: `DEBUG|INFO|WARNING|ERROR` — applied at process startup (when the supervisor loads config) to the stdlib logger **`lily`** and therefore all descendant loggers **`lily.*`** that do not set their own level. A single **Rich** `RichHandler` on stderr is attached to **`lily`** (idempotent) so package logs render with Rich styling. Third-party libraries (e.g. LangChain) are **not** controlled by this field.
- `skill_telemetry_log` (optional): relative path (from the runtime config file’s directory) or absolute path for skill F7 JSONL telemetry. When omitted, defaults to `../logs/skill-telemetry.jsonl` from that directory (e.g. `.lily/logs/skill-telemetry.jsonl` when config lives under `.lily/config/`).

**Skill telemetry:** logger `lily.skill.telemetry` uses dedicated handlers (append-only **plain** JSONL file by default; optional stderr mirror via `--show-skill-telemetry` on `lily run` / `lily tui` using **Rich**). That logger does **not** propagate to the parent `lily` logger (avoids duplicate Rich lines). It is explicitly held at **INFO** for emission so F7 JSON lines still record when `level` is `WARNING` or `ERROR`.

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
1. `agent.*` load + pydantic validation; `[logging].level` → `lily` package logger (`configure_lily_package_logging`)
2. `tools.*` load + catalog validation
3. catalog definition resolution to tool objects (Python/MCP resolver layer)
4. model profile construction (`ModelFactory`)
5. dynamic model middleware wiring (`DynamicModelRouter`)
6. agent identity context load from required markdown files (`AGENTS.md`, `IDENTITY.md`, `SOUL.md`, `USER.md`, `TOOLS.md`) when `--agent` mode is active
7. middleware injection of identity/personality context (`SystemPromptAgentIdentityMiddleware`) right before model invocation
8. tool registration + `agent.yaml` allowlist filtering (`ToolRegistry.allowlisted`)
9. LangChain `create_agent` execution (`AgentRuntime`)

### Special Markdown Context Injection Contract

When runtime is launched via named-agent mode (`--agent` or default `default`):

- Required sources:
  - `AGENTS.md`
  - `IDENTITY.md`
  - `SOUL.md`
  - `USER.md`
  - `TOOLS.md`
- Injection order (fixed):
  1. `AGENTS.md`
  2. `IDENTITY.md`
  3. `SOUL.md`
  4. `USER.md`
  5. `TOOLS.md`
- Injection mechanism:
  - middleware-only via `SystemPromptAgentIdentityMiddleware`
  - appended to request `system_message` at model-call time
- Failure semantics:
  - missing required file -> fail fast
  - no silent skipping
  - no nondeterministic filesystem ordering

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

Example (named-agent default):
```bash
uv run lily run --prompt "hello"
```

Example (named agent):
```bash
uv run lily run --agent pepper-potts --prompt "hello"
```

Example (explicit config YAML):
```bash
uv run lily run --prompt "hello" --config .lily/agents/default/agent.yaml
```

Example (explicit config TOML):
```bash
uv run lily run --prompt "hello" --config .lily/agents/default/agent.toml
```

Options:
- `--prompt` (required)
- `--agent` (optional, defaults to `default` when `--config` is omitted)
- `--config` (optional explicit runtime config path; mutually exclusive with `--agent`)
- `--override` (optional runtime override)

### `lily tui`

Launches Textual app with transcript + input.

Example (named-agent default):
```bash
uv run lily tui
```

Example (named agent):
```bash
uv run lily tui --agent pepper-potts
```

Example (explicit config YAML):
```bash
uv run lily tui --config .lily/agents/default/agent.yaml
```

Example (explicit config TOML):
```bash
uv run lily tui --config .lily/agents/default/agent.toml
```

Exit keys in TUI:
- `Ctrl+Q`
- `Esc`
- `Ctrl+C`

## Migration: Legacy `.lily/config/*` -> Named Agents

Recommended migration:

1. Create default agent workspace:
   - `.lily/agents/default/`
2. Move config/catalog files:
   - `.lily/config/agent.toml` -> `.lily/agents/default/agent.toml`
   - `.lily/config/tools.toml` -> `.lily/agents/default/tools.toml`
   - or YAML equivalents
3. Add required identity markdown files:
   - `AGENTS.md`, `IDENTITY.md`, `SOUL.md`, `USER.md`, `TOOLS.md`
4. Add required directories:
   - `skills/`, `memory/`
5. Run named-agent default mode:
   - `uv run lily run --prompt "hello"`

Compatibility:
- You can still run legacy-style explicit config path with `--config`.
- New default behavior prefers named-agent mode and `default` agent.

## Test Surfaces

- Unit: `tests/unit/runtime/test_config_loader.py`
- Unit: `tests/unit/runtime/test_tool_catalog.py`
- Unit: `tests/unit/runtime/test_tool_resolvers.py`
- Unit: `tests/unit/runtime/test_test_guardrails.py`
- Integration: `tests/integration/test_agent_runtime.py`
- Integration: `tests/integration/test_lily_supervisor.py`
- E2E CLI: `tests/e2e/test_cli_agent_run.py`
- E2E TUI: `tests/e2e/test_tui_app.py`

### Test-Time Live-Call Guardrails

- Default test behavior blocks outbound sockets and `init_chat_model` calls via `tests/conftest.py` autouse fixtures.
- Live-provider environment variables (`OPENAI_API_KEY`, etc.) are scrubbed during non-network tests to prevent accidental paid-provider use.
- Tests that intentionally call live services must opt in with `@pytest.mark.allows_network`.
- Strict local/CI mode can enforce fail-fast on detected live-provider env vars by setting `LILY_TEST_STRICT_PROVIDER_ENV=1`.

## Deferred Boundaries

Explicitly deferred from current implementation slice:
- dynamic capability/skill discovery selection beyond static catalog entries
- sub-agent runtime and delegation graph
- autonomous evolution/reflection pipelines
