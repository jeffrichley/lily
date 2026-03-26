"""Middleware-based injection for the enabled skill catalog."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents.middleware import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
)
from langchain_core.messages import SystemMessage


class SystemPromptSkillCatalogMiddleware(AgentMiddleware[Any, Any]):
    """Append the skill catalog markdown to the request system message."""

    def __init__(self, *, catalog_markdown: str) -> None:
        """Initialize middleware with a deterministic catalog string.

        Args:
            catalog_markdown: Catalog markdown block to append to the system prompt.
        """
        super().__init__()
        self._catalog_markdown = catalog_markdown

    def wrap_model_call(
        self,
        request: ModelRequest[Any],
        handler: Callable[[ModelRequest[Any]], ModelResponse[Any]],
    ) -> ModelResponse[Any]:
        """Inject catalog markdown into the outgoing model request.

        Args:
            request: Current model request.
            handler: Downstream handler to call with the rewritten request.

        Returns:
            The downstream model response.
        """
        base_obj = request.system_message.content if request.system_message else ""
        base = base_obj if isinstance(base_obj, str) else str(base_obj)
        content = f"{base.rstrip()}\n\n{self._catalog_markdown}"
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
            handler: Downstream async handler to call with the rewritten request.

        Returns:
            The downstream model response.
        """
        base_obj = request.system_message.content if request.system_message else ""
        base = base_obj if isinstance(base_obj, str) else str(base_obj)
        content = f"{base.rstrip()}\n\n{self._catalog_markdown}"
        updated = request.override(system_message=SystemMessage(content=content))
        return await handler(updated)
