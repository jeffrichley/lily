---
owner: "@team"
last_updated: "2026-02-17"
status: "active"
source_of_truth: true
---

# Skills Tool Authoring Workflow

Purpose: keep tiny tool adds/changes lightweight while preserving typed contracts.

## Tiny Change Path

1. Change tool logic in one file.
2. Run `just contract-conformance`.
3. If envelope shape changed, run `just contract-snapshots`.
4. Run `just quality-check`.
5. Commit.

## Tiny Tool Add Path

1. Generate scaffold:
   - `just scaffold-tool <tool_name>`
2. Register tool in provider wiring.
3. Add/adjust skill `SKILL.md`:
   - `invocation_mode: tool_dispatch`
   - `command_tool_provider: builtin|mcp|plugin`
   - `command_tool: <tool_name>`
   - `capabilities.declared_tools: [provider:tool_name]`
4. Run:
   - `just contract-conformance`
   - `just contract-snapshots` (if envelope fixture updates are expected)
   - `just quality-check`

## Optional Base Class

- Use `BaseToolContract` when defaults are enough:
  - default `parse_payload`: raw text -> `{payload: <text>}`
  - default `render_output`: prefer `display`, fallback to stable JSON
- Direct `ToolContract` implementations remain supported.

## LangChain Interop

- `LangChainToLilyTool`: wraps LangChain tools for Lily tool-dispatch use.
- `LilyToLangChainTool`: exposes Lily tools as LangChain `StructuredTool`.
- Wrapper failures map to deterministic Lily codes:
  - `langchain_wrapper_invalid`
  - `langchain_wrapper_invoke_failed`
