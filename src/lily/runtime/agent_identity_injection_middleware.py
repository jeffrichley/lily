"""Middleware-based injection for agent identity/personality markdown context."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents.middleware import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
)
from langchain_core.messages import SystemMessage


class SystemPromptAgentIdentityMiddleware(AgentMiddleware[Any, Any]):
    """Append agent identity context to the request system message."""

    def __init__(self, *, identity_markdown: str) -> None:
        """Initialize middleware with one deterministic identity block.

        Args:
            identity_markdown: Pre-formatted identity/personality markdown context.
        """
        super().__init__()
        self._identity_markdown = identity_markdown

    def wrap_model_call(
        self,
        request: ModelRequest[Any],
        handler: Callable[[ModelRequest[Any]], ModelResponse[Any]],
    ) -> ModelResponse[Any]:
        """Inject identity markdown into the outgoing model request.

        Args:
            request: Current model request.
            handler: Downstream handler to call with rewritten request.

        Returns:
            Downstream model response after injection.
        """
        base_obj = request.system_message.content if request.system_message else ""
        base = base_obj if isinstance(base_obj, str) else str(base_obj)
        content = f"{base.rstrip()}\n\n{self._identity_markdown}"
        updated = request.override(system_message=SystemMessage(content=content))
        return handler(updated)

    async def awrap_model_call(
        self,
        request: ModelRequest[Any],
        handler: Callable[[ModelRequest[Any]], Awaitable[ModelResponse[Any]]],
    ) -> ModelResponse[Any]:
        """Async injection variant for model-call wrapping.

        Args:
            request: Current model request.
            handler: Downstream async handler for rewritten request.

        Returns:
            Downstream model response after injection.
        """
        base_obj = request.system_message.content if request.system_message else ""
        base = base_obj if isinstance(base_obj, str) else str(base_obj)
        content = f"{base.rstrip()}\n\n{self._identity_markdown}"
        updated = request.override(system_message=SystemMessage(content=content))
        return await handler(updated)
