"""Unit tests for conversation composition root."""

from __future__ import annotations

import pytest

from lily.runtime.conversation import ConversationRequest, ConversationResponse
from lily.runtime.conversation_factory import ConversationRuntimeFactory
from lily.runtime.runtime_dependencies import ConversationRuntimeSpec
from lily.session.models import HistoryCompactionBackend


class _StubConversationExecutor:
    """Conversation executor stub for composition override tests."""

    def run(self, request: ConversationRequest) -> ConversationResponse:
        """Return deterministic response."""
        del request
        return ConversationResponse(text="ok")


@pytest.mark.unit
def test_conversation_factory_uses_override_executor() -> None:
    """Factory should return provided conversation executor override."""
    # Arrange - factory and explicit executor override
    factory = ConversationRuntimeFactory()
    override = _StubConversationExecutor()
    spec = ConversationRuntimeSpec(
        conversation_executor=override,
        conversation_checkpointer=None,
        compaction_backend=HistoryCompactionBackend.LANGGRAPH_NATIVE,
        compaction_max_tokens=1000,
        evidence_chunking=None,
    )

    # Act - build
    built = factory.build(spec)

    # Assert - exact override instance reused
    assert built is override


@pytest.mark.unit
def test_conversation_factory_builds_default_executor_when_override_missing() -> None:
    """Factory should build default LangChain executor when no override exists."""
    # Arrange - factory and default spec
    factory = ConversationRuntimeFactory()
    spec = ConversationRuntimeSpec(
        conversation_executor=None,
        conversation_checkpointer=None,
        compaction_backend=HistoryCompactionBackend.LANGGRAPH_NATIVE,
        compaction_max_tokens=1000,
        evidence_chunking=None,
    )

    # Act - build
    built = factory.build(spec)

    # Assert - default executor exposes run interface
    assert callable(getattr(built, "run", None))
