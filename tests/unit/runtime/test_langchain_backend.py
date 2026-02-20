"""Unit tests for LangChain backend contract behavior."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

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


@pytest.mark.unit
def test_langchain_backend_returns_response_on_success() -> None:
    """Backend should return valid response for successful invocations."""
    backend = LangChainBackend(invoker=_SuccessInvoker())

    response = backend.run(_request())

    assert response.text == "ok:echo:hello"


@pytest.mark.unit
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


@pytest.mark.unit
def test_langchain_backend_fails_fast_on_invalid_response() -> None:
    """Backend should not retry invalid-response failures."""
    backend = LangChainBackend(invoker=_InvalidResponseInvoker(), max_attempts=2)

    try:
        backend.run(_request())
    except BackendInvalidResponseError as exc:
        assert "empty output" in str(exc)
    else:  # pragma: no cover - safety assertion
        raise AssertionError("Expected BackendInvalidResponseError")


@pytest.mark.unit
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


@pytest.mark.unit
def test_extract_text_supports_structured_response_payload() -> None:
    """Structured response payload should be accepted when messages are absent."""
    result = {"structured_response": {"text": "structured hello"}}

    text = _LangChainV1Invoker._extract_text(result)

    assert text == "structured hello"


@pytest.mark.unit
def test_invoker_falls_back_when_structured_output_is_unsupported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invoker should retry without response_format on known vLLM error signature."""
    calls: list[dict[str, object]] = []

    class _FirstAgent:
        def invoke(self, payload: object) -> object:
            del payload
            message = (
                'Error code: 400 - tool_choice="required" requires '
                "--tool-call-parser to be set"
            )
            raise RuntimeError(message)

    class _SecondAgent:
        def invoke(self, payload: object) -> object:
            del payload
            return {"messages": [SimpleNamespace(content="fallback-ok")]}

    agents = [_FirstAgent(), _SecondAgent()]

    def _fake_create_agent(**kwargs: object) -> object:
        calls.append(kwargs)
        return agents[len(calls) - 1]

    monkeypatch.setattr(
        "lily.runtime.llm_backend.langchain_adapter.create_agent",
        _fake_create_agent,
    )
    request = LlmRunRequest(
        session_id="session-test",
        skill_name="echo",
        skill_summary="Echo skill",
        user_text="hello",
        model_name="openai:Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
    )

    result = _LangChainV1Invoker().invoke(request)

    assert result == "fallback-ok"
    assert len(calls) == 2
    assert "response_format" in calls[0]
    assert "response_format" not in calls[1]


@pytest.mark.unit
def test_invoker_does_not_fallback_for_unknown_structured_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invoker should bubble non-matching exceptions from structured path."""

    class _FailingAgent:
        def invoke(self, payload: object) -> object:
            del payload
            raise RuntimeError("some other provider error")

    monkeypatch.setattr(
        "lily.runtime.llm_backend.langchain_adapter.create_agent",
        lambda **_: _FailingAgent(),
    )
    request = LlmRunRequest(
        session_id="session-test",
        skill_name="echo",
        skill_summary="Echo skill",
        user_text="hello",
        model_name="openai:Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
    )

    with pytest.raises(RuntimeError, match="some other provider error"):
        _LangChainV1Invoker().invoke(request)
