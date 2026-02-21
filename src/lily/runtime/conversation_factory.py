"""Composition root for conversation execution runtime."""

from __future__ import annotations

from lily.runtime.conversation import (
    ConversationExecutor,
    LangChainConversationExecutor,
)
from lily.runtime.runtime_dependencies import ConversationRuntimeSpec


class ConversationRuntimeFactory:
    """Compose conversation execution dependency for runtime facade."""

    def build(self, spec: ConversationRuntimeSpec) -> ConversationExecutor:
        """Build conversation executor from composition spec.

        Args:
            spec: Conversation composition spec.

        Returns:
            Conversation executor for runtime orchestration.
        """
        if spec.conversation_executor is not None:
            return spec.conversation_executor
        return LangChainConversationExecutor(
            checkpointer=spec.conversation_checkpointer
        )
