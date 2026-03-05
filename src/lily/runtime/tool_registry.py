"""Tool registration and allowlist filtering for runtime invocation."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict

type ToolLike = BaseTool | Callable[..., object]


class ToolRegistryError(ValueError):
    """Raised when tool registry operations fail validation."""


def _tool_name(tool: ToolLike) -> str:
    """Resolve a stable tool name from a BaseTool or callable.

    Args:
        tool: Tool object or callable tool function.

    Returns:
        Stable tool name for registry indexing.
    """
    if isinstance(tool, BaseTool):
        return tool.name
    return tool.__name__


class ToolRegistry(BaseModel):
    """Registry for configured runtime tools."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    tools_by_name: dict[str, ToolLike]

    @classmethod
    def from_tools(cls, tools: Sequence[ToolLike]) -> ToolRegistry:
        """Create registry from provided tools, rejecting duplicate names.

        Args:
            tools: Sequence of tools to register.

        Returns:
            Immutable tool registry instance.

        Raises:
            ToolRegistryError: If duplicate tool names are provided.
        """
        resolved: dict[str, ToolLike] = {}
        for tool in tools:
            name = _tool_name(tool)
            if name in resolved:
                msg = f"Duplicate tool registration for '{name}'."
                raise ToolRegistryError(msg)
            resolved[name] = tool
        return cls(tools_by_name=resolved)

    def names(self) -> list[str]:
        """Return sorted registered tool names.

        Returns:
            Sorted list of registered tool names.
        """
        return sorted(self.tools_by_name)

    def allowlisted(self, allowlist: Sequence[str]) -> list[ToolLike]:
        """Return tools restricted to an allowlist, preserving allowlist order.

        Args:
            allowlist: Ordered set of tool names to permit.

        Returns:
            Allowlisted tools in requested order.

        Raises:
            ToolRegistryError: If allowlist references unknown tool names.
        """
        missing = [
            tool_name for tool_name in allowlist if tool_name not in self.tools_by_name
        ]
        if missing:
            available = ", ".join(self.names())
            missing_list = ", ".join(sorted(missing))
            msg = (
                f"Tool allowlist references unknown tools: {missing_list}. "
                f"Available tools: {available}"
            )
            raise ToolRegistryError(msg)
        return [self.tools_by_name[tool_name] for tool_name in allowlist]
