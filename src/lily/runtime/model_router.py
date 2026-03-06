"""Dynamic model selection middleware for LangChain agents."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents.middleware import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
)
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, ConfigDict

from lily.runtime.config_schema import DynamicModelRoutingConfig


def _message_text_size(message: object) -> int:
    """Estimate message complexity as text length.

    Args:
        message: Message-like object from LangChain request state.

    Returns:
        Integer complexity estimate based on content length.
    """
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return len(content)
    if isinstance(content, list):
        return len("".join(str(item) for item in content))
    return len(str(content))


class DynamicModelRouter(BaseModel):
    """Selects an appropriate model profile per request."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    models: dict[str, BaseChatModel]
    routing: DynamicModelRoutingConfig

    def _select_profile_name(self, request: ModelRequest[None]) -> str:
        """Pick the configured model profile name for one model call.

        Args:
            request: Current LangChain model call request.

        Returns:
            Selected model profile name.
        """
        if not self.routing.enabled:
            return self.routing.default_profile

        complexity = sum(_message_text_size(message) for message in request.messages)
        if complexity >= self.routing.complexity_threshold:
            return self.routing.long_context_profile
        return self.routing.default_profile

    def build_middleware(self) -> AgentMiddleware[Any, Any]:
        """Create LangChain middleware that rewrites request.model.

        Returns:
            Agent middleware that swaps request model based on routing policy.
        """
        router = self

        class _DynamicModelRoutingMiddleware(AgentMiddleware[Any, Any]):
            """Model selection middleware with sync and async handler support."""

            def wrap_model_call(
                self,
                request: ModelRequest[None],
                handler: Callable[[ModelRequest[None]], ModelResponse[Any]],
            ) -> ModelResponse[Any]:
                """Select model profile for sync model invocation.

                Args:
                    request: Current model call request.
                    handler: Downstream sync model-call handler.

                Returns:
                    Model response from downstream handler.
                """
                selected_profile = router._select_profile_name(request)
                selected_model = router.models[selected_profile]
                return handler(request.override(model=selected_model))

            async def awrap_model_call(
                self,
                request: ModelRequest[None],
                handler: Callable[
                    [ModelRequest[None]],
                    Awaitable[ModelResponse[Any]],
                ],
            ) -> ModelResponse[Any]:
                """Select model profile for async model invocation.

                Args:
                    request: Current model call request.
                    handler: Downstream async model-call handler.

                Returns:
                    Model response from downstream handler.
                """
                selected_profile = router._select_profile_name(request)
                selected_model = router.models[selected_profile]
                return await handler(request.override(model=selected_model))

        return _DynamicModelRoutingMiddleware()
