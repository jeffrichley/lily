"""Top-level Lily supervisor bound to runtime and config loaders."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from langchain_core.tools import BaseTool, tool

from lily.runtime.agent_identity_context import load_agent_identity_context
from lily.runtime.agent_runtime import AgentRunResult, AgentRuntime
from lily.runtime.config_loader import ConfigLoadError, load_runtime_config
from lily.runtime.config_schema import McpServerConfig, RuntimeConfig
from lily.runtime.logging_setup import (
    clear_skill_telemetry_handlers,
    configure_lily_package_logging,
    configure_skill_telemetry_handlers,
    resolve_skill_telemetry_log_path,
)
from lily.runtime.skill_loader import SkillBundle, build_skill_bundle
from lily.runtime.skill_retrieve_tool import SKILL_RETRIEVE_TOOL_ID
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
        *,
        skill_telemetry_echo: bool = False,
        agent_workspace_dir: str | Path | None = None,
    ) -> LilySupervisor:
        """Build supervisor from config files.

        Args:
            config_path: Base runtime config path (.yaml/.yml/.toml).
            override_config_path: Optional override runtime config path.
            tools_config_path: Optional explicit tool catalog config path.
                When omitted, `.toml` runtime configs infer `tools.toml`
                in the same directory; otherwise `tools.yaml`.
            skill_telemetry_echo: When skills are enabled, mirror F7 JSON telemetry
                to stderr in addition to the configured log file.
            agent_workspace_dir: Optional named-agent workspace directory used to
                load required identity/personality markdown context for middleware
                injection.

        Returns:
            Supervisor with runtime and catalog-resolved tools configured.
        """
        resolved_tools_config_path = (
            Path(tools_config_path)
            if tools_config_path is not None
            else cls._default_tools_config_path(config_path)
        )
        config = load_runtime_config(config_path, override_config_path)
        configure_lily_package_logging(config.logging.level)
        skills_cfg = config.skills
        skills_enabled = skills_cfg is not None and skills_cfg.enabled
        if skills_enabled and skills_cfg is not None:
            telemetry_path = resolve_skill_telemetry_log_path(
                config_path,
                relative_override=config.logging.skill_telemetry_log,
            )
            configure_skill_telemetry_handlers(
                telemetry_path,
                echo_to_stderr=skill_telemetry_echo,
            )
        else:
            clear_skill_telemetry_handlers()
        resolved_tools = cls._load_tools_from_catalog(
            resolved_tools_config_path,
            mcp_servers=config.mcp_servers,
            skills_enabled=skills_enabled,
        )
        skill_bundle: SkillBundle | None = None
        if skills_enabled and skills_cfg is not None:
            skill_bundle = build_skill_bundle(
                skills_cfg,
                Path(config_path).resolve().parent,
            )
        identity_context_markdown = ""
        if agent_workspace_dir is not None:
            identity_context_markdown = load_agent_identity_context(
                Path(agent_workspace_dir)
            )
        runtime = AgentRuntime(
            config=cls._effective_runtime_config(config, skills_enabled=skills_enabled),
            tools=resolved_tools,
            skill_bundle=skill_bundle,
            agent_identity_context_markdown=identity_context_markdown,
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
    def _effective_runtime_config(
        config: RuntimeConfig,
        *,
        skills_enabled: bool,
    ) -> RuntimeConfig:
        """Drop ``skill_retrieve`` from the allowlist when skills are disabled.

        The catalog may still define the tool, but it is not registered; the allowlist
        must not reference a missing tool name.

        Args:
            config: Loaded runtime configuration.
            skills_enabled: Whether the skills subsystem is active.

        Returns:
            Config unchanged when skills are enabled, or with allowlist filtered.

        Raises:
            ConfigLoadError: When stripping ``skill_retrieve`` would leave an empty
                allowlist.
        """
        if skills_enabled:
            return config
        allow = config.tools.allowlist
        if SKILL_RETRIEVE_TOOL_ID not in allow:
            return config
        filtered = [tool_id for tool_id in allow if tool_id != SKILL_RETRIEVE_TOOL_ID]
        if not filtered:
            msg = (
                "tools.allowlist cannot include only 'skill_retrieve' when skills are "
                "disabled; add other tools or enable skills."
            )
            raise ConfigLoadError(msg)
        return config.model_copy(
            update={
                "tools": config.tools.model_copy(update={"allowlist": filtered}),
            }
        )

    @staticmethod
    def _resolved_tool_name(tool: ToolLike) -> str:
        """Stable tool id matching ``ToolRegistry`` naming rules.

        Args:
            tool: Resolved catalog tool object.

        Returns:
            Tool name string used for allowlist matching.
        """
        if isinstance(tool, BaseTool):
            return tool.name
        return tool.__name__

    @classmethod
    def _load_tools_from_catalog(
        cls,
        tools_config_path: str | Path,
        mcp_servers: Mapping[str, McpServerConfig],
        *,
        skills_enabled: bool,
    ) -> list[ToolLike]:
        """Load and resolve runtime tools from one catalog config file.

        Args:
            tools_config_path: Tool catalog config path (.yaml/.yml/.toml).
            mcp_servers: Runtime MCP server configuration mapping.
            skills_enabled: When false, ``skill_retrieve`` is omitted even if defined
                in the catalog so the tool registry matches the skills subsystem state.

        Returns:
            Resolved runtime tools in catalog order.
        """
        tool_catalog = load_tool_catalog(tools_config_path)
        providers = build_mcp_server_providers(mcp_servers)
        resolvers = ToolResolvers(mcp_servers=providers)
        resolved = resolvers.resolve_catalog(tool_catalog)
        if skills_enabled:
            return resolved
        return [
            tool
            for tool in resolved
            if cls._resolved_tool_name(tool) != SKILL_RETRIEVE_TOOL_ID
        ]

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
