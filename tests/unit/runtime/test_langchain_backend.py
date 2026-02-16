"""Unit tests for LangChain backend contract behavior."""

from __future__ import annotations

from lily.runtime.llm_backend import (
    BackendInvalidResponseError,
    BackendUnavailableError,
    LangChainBackend,
    LlmRunRequest,
)
from lily.runtime.llm_backend.langchain_adapter import _LangChainV1Invoker


class _SuccessInvoker:
    """Invoker that always succeeds with deterministic text."""

    def invoke(self, request: LlmRunRequest) -> str:
        """Return deterministic text output.

        Args:
            request: Normalized request payload.

        Returns:
            Deterministic output.
        """
        return f"ok:{request.skill_name}:{request.user_text}"


class _RetryThenSuccessInvoker:
    """Invoker that fails once then succeeds."""

    def __init__(self) -> None:
        """Initialize call counter."""
        self.calls = 0

    def invoke(self, request: LlmRunRequest) -> str:
        """Fail once with retryable error then succeed.

        Args:
            request: Normalized request payload.

        Returns:
            Deterministic output after first retry.
        """
        self.calls += 1
        if self.calls == 1:
            raise BackendUnavailableError("transient")
        return f"ok:{request.skill_name}:{request.user_text}"


class _InvalidResponseInvoker:
    """Invoker that returns empty payload to trigger validation error."""

    def invoke(self, request: LlmRunRequest) -> str:
        """Return invalid empty output.

        Args:
            request: Normalized request payload.

        Returns:
            Invalid output.
        """
        del request
        return "   "


def _request() -> LlmRunRequest:
    """Create shared request fixture.

    Returns:
        Normalized backend request.
    """
    return LlmRunRequest(
        session_id="session-test",
        skill_name="echo",
        skill_summary="Echo skill",
        user_text="hello",
        model_name="default",
    )


def test_langchain_backend_returns_response_on_success() -> None:
    """Backend should return valid response for successful invocations."""
    backend = LangChainBackend(invoker=_SuccessInvoker())

    response = backend.run(_request())

    assert response.text == "ok:echo:hello"


def test_langchain_backend_retries_retryable_error_then_succeeds() -> None:
    """Backend should retry retryable errors based on configured policy."""
    sleeps: list[float] = []
    invoker = _RetryThenSuccessInvoker()
    backend = LangChainBackend(
        invoker=invoker,
        sleep_fn=sleeps.append,
        max_attempts=2,
        backoff_seconds=0.25,
    )

    response = backend.run(_request())

    assert response.text == "ok:echo:hello"
    assert invoker.calls == 2
    assert sleeps == [0.25]


def test_langchain_backend_fails_fast_on_invalid_response() -> None:
    """Backend should not retry invalid-response failures."""
    backend = LangChainBackend(invoker=_InvalidResponseInvoker(), max_attempts=2)

    try:
        backend.run(_request())
    except BackendInvalidResponseError as exc:
        assert "empty output" in str(exc)
    else:  # pragma: no cover - safety assertion
        raise AssertionError("Expected BackendInvalidResponseError")


def test_system_prompt_uses_skill_instructions_without_skill_name_hardcoding() -> None:
    """Prompt construction should use instructions generically with no echo branch."""
    request = LlmRunRequest(
        session_id="session-test",
        skill_name="echo",
        skill_summary="Echo skill",
        skill_instructions="Return the text in lowercase.",
        user_text="HELLO",
        model_name="default",
    )

    prompt = _LangChainV1Invoker._build_system_prompt(request)

    assert "Skill instructions:\nReturn the text in lowercase." in prompt
    assert "user payload transformed to uppercase" not in prompt


def test_extract_text_supports_structured_response_payload() -> None:
    """Structured response payload should be accepted when messages are absent."""
    result = {"structured_response": {"text": "structured hello"}}

    text = _LangChainV1Invoker._extract_text(result)

    assert text == "structured hello"
