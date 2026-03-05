"""Top-level Lily supervisor bound to runtime and config loaders."""

from __future__ import annotations

from pathlib import Path

from langchain_core.tools import tool

from lily.runtime.agent_runtime import AgentRunResult, AgentRuntime
from lily.runtime.config_loader import load_runtime_config


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
    ) -> LilySupervisor:
        """Build supervisor from YAML config files.

        Args:
            config_path: Base YAML config path.
            override_config_path: Optional override YAML config path.

        Returns:
            Supervisor with runtime and built-in tools configured.
        """
        config = load_runtime_config(config_path, override_config_path)
        runtime = AgentRuntime(config=config, tools=[echo_tool, ping_tool])
        return cls(runtime=runtime)

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
