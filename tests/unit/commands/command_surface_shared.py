"""Shared fixtures for command-surface unit tests."""

from __future__ import annotations

from lily.runtime.conversation import ConversationRequest, ConversationResponse


class _ConversationCaptureExecutor:
    """Conversation executor fixture that captures last request."""

    def __init__(self) -> None:
        """Initialize capture slots."""
        self.last_request: ConversationRequest | None = None

    def run(self, request: ConversationRequest) -> ConversationResponse:
        """Capture request and return deterministic reply."""
        self.last_request = request
        return ConversationResponse(text="ok")
