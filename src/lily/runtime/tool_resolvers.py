"""Resolvers that map tool catalog definitions to runtime tool objects."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable, Coroutine, Mapping
from datetime import timedelta
from importlib import import_module
from typing import Any, Protocol, cast

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.sessions import StreamableHttpConnection
from pydantic import PrivateAttr

from lily.runtime.config_schema import (
    McpServerConfig,
    McpServerStreamableHttpConfig,
    McpServerTestConfig,
)
from lily.runtime.tool_catalog import (
    McpToolDefinition,
    PythonToolDefinition,
    ToolCatalog,
    ToolDefinition,
    ToolSource,
)
from lily.runtime.tool_registry import ToolLike, ToolRegistry

type _ResolverCallable = Callable[[ToolDefinition], ToolLike]


class ToolResolverError(ValueError):
    """Raised when resolving configured tools fails."""


class PythonToolResolveError(ToolResolverError):
    """Raised when a Python tool target cannot be resolved."""


class McpToolResolveError(ToolResolverError):
    """Raised when an MCP tool target cannot be resolved."""


class McpServerToolProvider(Protocol):
    """Protocol for server-scoped MCP remote-tool resolution."""

    def resolve_tool(self, remote_tool: str) -> ToolLike:
        """Resolve one remote MCP tool into a LangChain-compatible tool.

        Args:
            remote_tool: Remote tool identifier exposed by MCP server.
        """


class McpServerConfigError(ToolResolverError):
    """Raised when MCP server provider config cannot be built."""


def _tool_name(tool: ToolLike) -> str:
    """Resolve tool name from a BaseTool or callable.

    Args:
        tool: Tool object to name.

    Returns:
        Stable tool name.
    """
    if isinstance(tool, BaseTool):
        return tool.name
    return tool.__name__


def _validate_tool_like(value: object, *, context: str) -> ToolLike:
    """Ensure one resolved object is a BaseTool/callable tool value.

    Args:
        value: Candidate resolved object.
        context: Resolution context for deterministic error messages.

    Returns:
        Validated tool object.

    Raises:
        ToolResolverError: If value is not BaseTool/callable.
    """
    if isinstance(value, BaseTool):
        return value
    if callable(value):
        return cast(ToolLike, value)
    msg = f"{context} resolved to non-tool value of type '{type(value).__name__}'."
    raise ToolResolverError(msg)


def _run_async[T](coro: Coroutine[Any, Any, T]) -> T:
    """Execute one coroutine from sync code in or out of an event loop.

    Args:
        coro: Awaitable coroutine to execute.

    Returns:
        Coroutine result.

    Raises:
        RuntimeError: If coroutine execution fails or returns no result.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: list[T] = []
    error: list[BaseException] = []

    def _worker() -> None:
        try:
            result.append(asyncio.run(coro))
        except BaseException as exc:  # pragma: no cover - defensive thread bridge
            error.append(exc)

    worker = threading.Thread(target=_worker, daemon=True)
    worker.start()
    worker.join()

    if error:
        msg = "Async execution failed."
        raise RuntimeError(msg) from error[0]

    if not result:
        msg = "Async execution did not produce a result."
        raise RuntimeError(msg)

    return result[0]


class _AsyncMcpToolSyncBridge(BaseTool):
    """Bridge async-only MCP tools so sync agent invoke can execute them."""

    _delegate: BaseTool = PrivateAttr()

    def __init__(self, delegate: BaseTool) -> None:
        """Capture delegate metadata and store async MCP tool reference.

        Args:
            delegate: MCP adapter tool that exposes `ainvoke(...)`.
        """
        super().__init__(
            name=delegate.name,
            description=delegate.description,
            args_schema=delegate.args_schema,
            return_direct=delegate.return_direct,
        )
        self._delegate = delegate

    def _normalize_tool_input(
        self,
        args: tuple[object, ...],
        kwargs: dict[str, object],
    ) -> str | dict[str, Any]:
        """Normalize BaseTool call args/kwargs into MCP tool input payload.

        Args:
            args: Positional arguments from BaseTool sync/async entrypoints.
            kwargs: Keyword arguments from BaseTool sync/async entrypoints.

        Returns:
            Tool input accepted by `BaseTool.ainvoke(...)`.
        """
        filtered_kwargs = {
            key: value
            for key, value in kwargs.items()
            if key not in {"run_manager", "config"}
        }
        if filtered_kwargs:
            return filtered_kwargs
        if len(args) == 1:
            raw = args[0]
            if isinstance(raw, str):
                return raw
            if isinstance(raw, dict):
                return cast(dict[str, Any], raw)
            return {"input": raw}
        if args:
            return {"args": list(args)}
        return {}

    def _run(self, *args: object, **kwargs: object) -> object:
        """Bridge sync invocation into delegate async invoke path.

        Args:
            *args: Positional tool arguments.
            **kwargs: Keyword tool arguments.

        Returns:
            Delegate tool response payload.
        """
        tool_input = self._normalize_tool_input(args, kwargs)
        return _run_async(self._delegate.ainvoke(tool_input))

    async def _arun(self, *args: object, **kwargs: object) -> object:
        """Pass through async invocation into delegate async invoke path.

        Args:
            *args: Positional tool arguments.
            **kwargs: Keyword tool arguments.

        Returns:
            Delegate tool response payload.
        """
        tool_input = self._normalize_tool_input(args, kwargs)
        return await self._delegate.ainvoke(tool_input)


class ToolResolvers:
    """Resolver registry that dispatches by tool source type."""

    def __init__(
        self,
        mcp_servers: Mapping[str, McpServerToolProvider] | None = None,
    ) -> None:
        """Initialize source dispatch map and optional MCP server providers.

        Args:
            mcp_servers: Mapping of configured MCP server name to tool provider.
        """
        self._mcp_servers = dict(mcp_servers or {})
        self._resolvers: dict[ToolSource, _ResolverCallable] = {
            ToolSource.PYTHON: self._resolve_python,
            ToolSource.MCP: self._resolve_mcp,
        }

    def resolve(self, definition: ToolDefinition) -> ToolLike:
        """Resolve one typed catalog definition into a runtime tool object.

        Args:
            definition: One parsed catalog definition.

        Returns:
            LangChain-compatible tool object.

        Raises:
            ToolResolverError: If dispatch or resolution validation fails.
        """
        resolver = self._resolvers.get(definition.source)
        if resolver is None:
            msg = f"No resolver registered for tool source '{definition.source.value}'."
            raise ToolResolverError(msg)

        resolved = resolver(definition)
        return _validate_tool_like(
            resolved,
            context=(
                f"Tool id '{definition.id}' from source '{definition.source.value}'"
            ),
        )

    def resolve_catalog(self, catalog: ToolCatalog) -> list[ToolLike]:
        """Resolve all catalog definitions to tool objects in catalog order.

        Args:
            catalog: Parsed tool catalog.

        Returns:
            Tool objects suitable for `ToolRegistry.from_tools(...)`.
        """
        return [self.resolve(definition) for definition in catalog.definitions]

    def resolve_catalog_registry(self, catalog: ToolCatalog) -> ToolRegistry:
        """Resolve catalog and construct runtime ToolRegistry.

        Args:
            catalog: Parsed tool catalog.

        Returns:
            Tool registry built from resolved catalog definitions.
        """
        return ToolRegistry.from_tools(self.resolve_catalog(catalog))

    def _resolve_python(self, definition: ToolDefinition) -> ToolLike:
        """Resolve a Python target (`module:attribute`) into a tool object.

        Args:
            definition: Catalog definition expected to be Python type.

        Returns:
            Resolved Python tool object.

        Raises:
            ToolResolverError: If definition type mismatches source.
            PythonToolResolveError: If import/attribute/name validation fails.
        """
        if not isinstance(definition, PythonToolDefinition):
            msg = (
                "Resolver/source mismatch for source 'python': expected "
                "PythonToolDefinition."
            )
            raise ToolResolverError(msg)

        module_path, separator, attribute_name = definition.target.partition(":")
        if not separator or not module_path or not attribute_name:
            msg = (
                f"Invalid Python tool target for id '{definition.id}': "
                f"'{definition.target}'. Expected 'module.path:attribute'."
            )
            raise PythonToolResolveError(msg)

        try:
            module = import_module(module_path)
        except Exception as exc:
            msg = (
                f"Unable to import module '{module_path}' for tool id "
                f"'{definition.id}': {exc}"
            )
            raise PythonToolResolveError(msg) from exc

        try:
            value = getattr(module, attribute_name)
        except AttributeError as exc:
            msg = (
                f"Unable to resolve attribute '{attribute_name}' from module "
                f"'{module_path}' for tool id '{definition.id}'."
            )
            raise PythonToolResolveError(msg) from exc

        tool = _validate_tool_like(
            value,
            context=(
                f"Python target '{definition.target}' for tool id '{definition.id}'"
            ),
        )
        resolved_name = _tool_name(tool)
        if resolved_name != definition.id:
            msg = (
                f"Resolved Python tool name mismatch for id '{definition.id}': "
                f"got '{resolved_name}'."
            )
            raise PythonToolResolveError(msg)
        return tool

    def _resolve_mcp(self, definition: ToolDefinition) -> ToolLike:
        """Resolve MCP definition via configured server provider.

        Args:
            definition: Catalog definition expected to be MCP type.

        Returns:
            Resolved MCP-backed tool object.

        Raises:
            ToolResolverError: If definition type mismatches source.
            McpToolResolveError: If server lookup/discovery/name validation fails.
        """
        if not isinstance(definition, McpToolDefinition):
            msg = (
                "Resolver/source mismatch for source 'mcp': expected McpToolDefinition."
            )
            raise ToolResolverError(msg)

        provider = self._mcp_servers.get(definition.server)
        if provider is None:
            msg = (
                f"MCP server '{definition.server}' is not configured for "
                f"tool id '{definition.id}'."
            )
            raise McpToolResolveError(msg)

        try:
            resolved = provider.resolve_tool(definition.remote_tool)
        except Exception as exc:
            msg = (
                f"Unable to resolve remote MCP tool '{definition.remote_tool}' "
                f"from server '{definition.server}' for tool id '{definition.id}': "
                f"{exc}"
            )
            raise McpToolResolveError(msg) from exc

        tool = _validate_tool_like(
            resolved,
            context=(
                f"MCP tool '{definition.remote_tool}' from server "
                f"'{definition.server}' for tool id '{definition.id}'"
            ),
        )
        resolved_name = _tool_name(tool)
        if resolved_name != definition.id:
            msg = (
                f"Resolved MCP tool name mismatch for id '{definition.id}': "
                f"got '{resolved_name}'."
            )
            raise McpToolResolveError(msg)
        return tool


class _TestMcpServerProvider:
    """Deterministic local MCP provider used for runtime wiring and tests."""

    def __init__(self, tool_targets: Mapping[str, str]) -> None:
        """Initialize remote-tool to Python import target map.

        Args:
            tool_targets: Mapping of remote tool id to `module:attribute` target.
        """
        self._tool_targets = dict(tool_targets)

    def resolve_tool(self, remote_tool: str) -> ToolLike:
        """Resolve one remote tool by importing configured Python target.

        Args:
            remote_tool: Remote MCP tool name requested by catalog definition.

        Returns:
            Resolved tool-like object.

        Raises:
            McpServerConfigError: If remote tool mapping/import/attribute fails.
        """
        target = self._tool_targets.get(remote_tool)
        if target is None:
            msg = f"Remote MCP tool '{remote_tool}' is not configured."
            raise McpServerConfigError(msg)

        module_path, separator, attribute_name = target.partition(":")
        if not separator or not module_path or not attribute_name:
            msg = (
                f"Invalid MCP tool target '{target}' for remote tool "
                f"'{remote_tool}'. Expected 'module.path:attribute'."
            )
            raise McpServerConfigError(msg)

        try:
            module = import_module(module_path)
        except Exception as exc:
            msg = (
                f"Unable to import module '{module_path}' for remote tool "
                f"'{remote_tool}': {exc}"
            )
            raise McpServerConfigError(msg) from exc

        try:
            value = getattr(module, attribute_name)
        except AttributeError as exc:
            msg = (
                f"Unable to resolve attribute '{attribute_name}' from module "
                f"'{module_path}' for remote tool '{remote_tool}'."
            )
            raise McpServerConfigError(msg) from exc

        return _validate_tool_like(
            value,
            context=f"MCP remote tool '{remote_tool}' target '{target}'",
        )


class _AdapterMcpServerProvider:
    """Real MCP provider backed by LangChain MCP adapters client."""

    def __init__(self, server_name: str, client: MultiServerMCPClient) -> None:
        """Store one server-bound adapter client wrapper.

        Args:
            server_name: Configured MCP server name.
            client: MultiServerMCPClient instance.
        """
        self._server_name = server_name
        self._client = client
        self._tools_by_name: dict[str, ToolLike] | None = None

    def _load_tools(self) -> dict[str, ToolLike]:
        """Fetch and cache server tools from MCP adapter client.

        Returns:
            Mapping of remote tool name to LangChain tool object.
        """
        if self._tools_by_name is not None:
            return self._tools_by_name

        tools = _run_async(self._client.get_tools(server_name=self._server_name))
        tools_by_name: dict[str, ToolLike] = {}
        for tool in tools:
            wrapped: ToolLike = tool
            if getattr(tool, "func", None) is None and getattr(tool, "coroutine", None):
                wrapped = _AsyncMcpToolSyncBridge(tool)
            tools_by_name[tool.name] = wrapped
        self._tools_by_name = tools_by_name
        return self._tools_by_name

    def resolve_tool(self, remote_tool: str) -> ToolLike:
        """Resolve one remote tool from cached MCP adapter tool list.

        Args:
            remote_tool: Remote MCP tool identifier.

        Returns:
            LangChain-compatible resolved tool.

        Raises:
            McpServerConfigError: If remote tool is not present on server.
        """
        tools_by_name = self._load_tools()
        resolved = tools_by_name.get(remote_tool)
        if resolved is None:
            available = ", ".join(sorted(tools_by_name))
            msg = (
                f"Remote MCP tool '{remote_tool}' not found on server "
                f"'{self._server_name}'. Available: {available}"
            )
            raise McpServerConfigError(msg)
        return resolved


def build_mcp_server_providers(
    mcp_servers: Mapping[str, McpServerConfig],
) -> dict[str, McpServerToolProvider]:
    """Build MCP server provider objects from runtime config mapping.

    Args:
        mcp_servers: Runtime config `mcp_servers` mapping.

    Returns:
        Mapping of server name to MCP server provider instance.

    Raises:
        McpServerConfigError: If a server config transport is unsupported.
    """
    providers: dict[str, McpServerToolProvider] = {}
    for server_name, server_config in mcp_servers.items():
        if isinstance(server_config, McpServerTestConfig):
            providers[server_name] = _TestMcpServerProvider(server_config.tool_targets)
            continue

        if isinstance(server_config, McpServerStreamableHttpConfig):
            connection: StreamableHttpConnection = {
                "transport": "streamable_http",
                "url": server_config.url,
            }
            if server_config.headers:
                connection["headers"] = server_config.headers
            if server_config.timeout_seconds is not None:
                timeout = timedelta(seconds=server_config.timeout_seconds)
                connection["timeout"] = timeout
                connection["sse_read_timeout"] = timeout

            client = MultiServerMCPClient({server_name: connection})
            providers[server_name] = _AdapterMcpServerProvider(server_name, client)
            continue

        msg = (
            f"Unsupported MCP transport for server '{server_name}': "
            f"'{server_config.transport}'."
        )
        raise McpServerConfigError(msg)

    return providers
