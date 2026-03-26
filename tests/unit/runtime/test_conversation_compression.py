"""Unit tests for conversation compression middleware wiring."""

from __future__ import annotations

from typing import Any

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage

from lily.runtime.config_schema import (
    ConversationCompressionConfig,
    ConversationCompressionKeepConfig,
    ConversationCompressionTriggerConfig,
)
from lily.runtime.conversation_compression import (
    build_conversation_compression_middleware,
)

pytestmark = pytest.mark.unit


def _state(messages: list[Any]) -> dict[str, Any]:
    return {"messages": messages}


def test_conversation_compression_no_trigger_returns_none() -> None:
    """When below the configured threshold, middleware does not mutate state."""
    # Arrange - build config, model, and middleware.
    cfg = ConversationCompressionConfig(
        enabled=True,
        trigger=ConversationCompressionTriggerConfig(
            kind="messages",
            threshold=10,
        ),
        keep=ConversationCompressionKeepConfig(
            kind="messages",
            value=1,
        ),
    )
    model = FakeMessagesListChatModel(responses=[AIMessage(content="SUMMARY")])
    middleware = build_conversation_compression_middleware(cfg, model=model)

    state = _state([HumanMessage(content="h1")])

    # SummarizationMiddleware.before_model ignores runtime, so a sentinel is fine.
    # Act - execute compression middleware.
    result = middleware.before_model(state, runtime=object())

    # Assert - state was not mutated.
    assert result is None


def test_conversation_compression_trigger_replaces_old_messages_preserves_tail() -> (
    None
):
    """When threshold is met, older messages are replaced with a summary."""
    # Arrange - build config, model, and middleware.
    cfg = ConversationCompressionConfig(
        enabled=True,
        trigger=ConversationCompressionTriggerConfig(
            kind="messages",
            threshold=4,
        ),
        keep=ConversationCompressionKeepConfig(
            kind="messages",
            value=1,
        ),
    )
    model = FakeMessagesListChatModel(responses=[AIMessage(content="SUMMARY")])
    middleware = build_conversation_compression_middleware(cfg, model=model)

    # len(messages) == 5, so with threshold=4 summarization should run.
    messages = [
        HumanMessage(content="h1"),
        AIMessage(content="a1"),
        HumanMessage(content="h2"),
        AIMessage(content="a2"),
        HumanMessage(content="h3"),
    ]
    state = _state(messages)

    # Act - execute compression middleware (should trigger summarization).
    result = middleware.before_model(state, runtime=object())

    # Assert - older messages are replaced with a summary plus preserved tail.
    assert result is not None
    updated_messages = result["messages"]
    assert isinstance(updated_messages, list)
    assert len(updated_messages) == 3  # RemoveMessage + summary + 1 kept message
    assert isinstance(updated_messages[0], RemoveMessage)

    # First concrete new message is a HumanMessage summary.
    summary_msg = updated_messages[1]
    assert isinstance(summary_msg, HumanMessage)
    assert "Here is a summary of the conversation to date" in summary_msg.content
    assert "SUMMARY" in summary_msg.content

    # Tail verbatim message is preserved.
    tail_msg = updated_messages[2]
    assert isinstance(tail_msg, HumanMessage)
    assert tail_msg.content == "h3"
