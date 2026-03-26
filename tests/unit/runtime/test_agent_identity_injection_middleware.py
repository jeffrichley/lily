"""Unit tests for middleware-based agent identity context injection."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from langchain_core.messages import SystemMessage

from lily.runtime.agent_identity_injection_middleware import (
    SystemPromptAgentIdentityMiddleware,
)

pytestmark = pytest.mark.unit


@dataclass(frozen=True)
class _FakeModelRequest:
    """Minimal model request stub with `override` behavior."""

    system_message: SystemMessage | None

    def override(self, *, system_message: SystemMessage) -> _FakeModelRequest:
        """Return a new request object with overridden system message."""
        return _FakeModelRequest(system_message=system_message)


def test_identity_middleware_appends_context_to_existing_system_message() -> None:
    """Appends identity markdown below existing system instructions."""
    # Arrange - middleware with deterministic identity markdown block.
    middleware = SystemPromptAgentIdentityMiddleware(
        identity_markdown="## Agent identity context\n\n### IDENTITY.md\nName: Pepper",
    )
    request = _FakeModelRequest(system_message=SystemMessage(content="You are Lily."))
    captured: dict[str, _FakeModelRequest] = {}

    def _handler(updated: _FakeModelRequest) -> str:
        captured["request"] = updated
        return "ok"

    # Act - execute sync model-call wrapper.
    result = middleware.wrap_model_call(request, _handler)

    # Assert - outgoing system message includes base instructions and identity block.
    assert result == "ok"
    outgoing = captured["request"].system_message
    assert outgoing is not None
    assert "You are Lily." in str(outgoing.content)
    assert "## Agent identity context" in str(outgoing.content)


def test_identity_middleware_handles_missing_system_message() -> None:
    """Creates system message from identity markdown when base is missing."""
    # Arrange - middleware with identity markdown and empty incoming system message.
    middleware = SystemPromptAgentIdentityMiddleware(
        identity_markdown="## Agent identity context\n\n### SOUL.md\nPurpose: Help.",
    )
    request = _FakeModelRequest(system_message=None)
    captured: dict[str, _FakeModelRequest] = {}

    def _handler(updated: _FakeModelRequest) -> str:
        captured["request"] = updated
        return "ok"

    # Act - execute sync model-call wrapper.
    middleware.wrap_model_call(request, _handler)

    # Assert - outgoing request now includes middleware-provided system message.
    outgoing = captured["request"].system_message
    assert outgoing is not None
    assert "## Agent identity context" in str(outgoing.content)
