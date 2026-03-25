"""Top-level Lily supervisor bound to runtime and config loaders."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from langchain_core.tools import tool

from lily.runtime.agent_runtime import AgentRunResult, AgentRuntime
from lily.runtime.config_loader import load_runtime_config
from lily.runtime.config_schema import McpServerConfig
from lily.runtime.skill_loader import SkillBundle, build_skill_bundle
from lily.runtime.tool_catalog import load_tool_catalog
from lily.runtime.tool_registry import ToolLike
from lily.runtime.tool_resolvers import ToolResolvers, build_mcp_server_providers


@tool
def echo_tool(text: str) -> str:
    """Echo user text with a stable prefix.

    Args:
        text: Input text payload.

    Returns:
        Echo output with stable prefix.
    """
    return f"echo: {text}"


@tool
def ping_tool() -> str:
    """Return a simple liveness response.

    Returns:
        Static health string.
    """
    return "pong"


@tool
def mcp_ping_tool() -> str:
    """Return deterministic MCP test response.

    Returns:
        Static string used for MCP test-path verification.
    """
    return "mcp-pong"


class LilySupervisor:
    """Single supervisor surface for runtime-backed prompt execution."""

    def __init__(self, runtime: AgentRuntime) -> None:
        """Initialize supervisor with an already configured runtime.

        Args:
            runtime: Pre-configured runtime instance.
        """
        self._runtime = runtime

    @classmethod
    def from_config_paths(
        cls,
        config_path: str | Path,
        override_config_path: str | Path | None = None,
        tools_config_path: str | Path | None = None,
    ) -> LilySupervisor:
        """Build supervisor from config files.

        Args:
            config_path: Base runtime config path (.yaml/.yml/.toml).
            override_config_path: Optional override runtime config path.
            tools_config_path: Optional explicit tool catalog config path.
                When omitted, `.toml` runtime configs infer `tools.toml`
                in the same directory; otherwise `tools.yaml`.

        Returns:
            Supervisor with runtime and catalog-resolved tools configured.
        """
        resolved_tools_config_path = (
            Path(tools_config_path)
            if tools_config_path is not None
            else cls._default_tools_config_path(config_path)
        )
        config = load_runtime_config(config_path, override_config_path)
        resolved_tools = cls._load_tools_from_catalog(
            resolved_tools_config_path,
            mcp_servers=config.mcp_servers,
        )
        skill_bundle: SkillBundle | None = None
        if config.skills is not None and config.skills.enabled:
            skill_bundle = build_skill_bundle(
                config.skills,
                Path(config_path).resolve().parent,
            )
        runtime = AgentRuntime(
            config=config,
            tools=resolved_tools,
            skill_bundle=skill_bundle,
        )
        return cls(runtime=runtime)

    @staticmethod
    def _default_tools_config_path(config_path: str | Path) -> Path:
        """Infer default tools config path from runtime config extension.

        Args:
            config_path: Runtime config file path.

        Returns:
            Inferred tool catalog path in same directory as runtime config.
        """
        resolved = Path(config_path)
        if resolved.suffix.lower() == ".toml":
            return resolved.with_name("tools.toml")
        return resolved.with_name("tools.yaml")

    @staticmethod
    def _load_tools_from_catalog(
        tools_config_path: str | Path,
        mcp_servers: Mapping[str, McpServerConfig],
    ) -> list[ToolLike]:
        """Load and resolve runtime tools from one catalog config file.

        Args:
            tools_config_path: Tool catalog config path (.yaml/.yml/.toml).
            mcp_servers: Runtime MCP server configuration mapping.

        Returns:
            Resolved runtime tools in catalog order.
        """
        tool_catalog = load_tool_catalog(tools_config_path)
        providers = build_mcp_server_providers(mcp_servers)
        resolvers = ToolResolvers(mcp_servers=providers)
        return resolvers.resolve_catalog(tool_catalog)

    def run_prompt(
        self,
        prompt: str,
        conversation_id: str | None = None,
    ) -> AgentRunResult:
        """Execute one prompt through runtime and return normalized result.

        Args:
            prompt: Prompt text to execute.
            conversation_id: Optional conversation/thread id for resume continuity.

        Returns:
            Normalized run result contract.
        """
        return self._runtime.run(prompt, conversation_id=conversation_id)
