"""LangChain v1-backed LLM adapter (isolated behind Lily backend interface)."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Protocol

from langchain.agents import create_agent
from pydantic import BaseModel, ConfigDict, Field

from lily.runtime.llm_backend.base import (
    BackendInvalidResponseError,
    BackendTimeoutError,
    BackendUnavailableError,
    LlmBackendError,
    LlmRunRequest,
    LlmRunResponse,
)

_LOGGER = logging.getLogger(__name__)


class _StructuredSkillResponse(BaseModel):
    """Structured output contract for LLM-orchestrated skill responses."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str = Field(min_length=1)


class AgentInvoker(Protocol):
    """Internal agent invoker port used by LangChain adapter."""

    def invoke(self, request: LlmRunRequest) -> str:
        """Execute one LLM invocation for a normalized request.

        Args:
            request: Normalized run request payload.
        """


class _LangChainV1Invoker:
    """Default invoker using LangChain v1 `create_agent` APIs."""

    def invoke(self, request: LlmRunRequest) -> str:
        """Execute a single turn via LangChain v1 high-level agent API.

        Args:
            request: Normalized run request payload.

        Returns:
            Final text response.
        """
        system_prompt = self._build_system_prompt(request)
        agent = create_agent(
            model=request.model_name,
            tools=[],
            system_prompt=system_prompt,
            response_format=_StructuredSkillResponse,
        )
        result = agent.invoke(
            {"messages": [{"role": "user", "content": request.user_text}]}
        )
        return self._extract_text(result)

    @staticmethod
    def _build_system_prompt(request: LlmRunRequest) -> str:
        """Build stable system prompt from request metadata.

        Args:
            request: Normalized request payload.

        Returns:
            System prompt string.
        """
        base = (
            "You are Lily executing a specific skill.\n"
            f"Skill name: {request.skill_name}\n"
            f"Skill summary: {request.skill_summary or 'No summary provided.'}\n"
            "Follow the skill intent precisely and respond directly.\n"
        )
        instructions = request.skill_instructions.strip()
        if not instructions:
            return base
        return f"{base}Skill instructions:\n{instructions}"

    @staticmethod
    def _extract_text(result: object) -> str:
        """Extract text from LangChain agent response payload.

        Args:
            result: Raw agent invocation result object.

        Returns:
            Extracted assistant text.

        Raises:
            BackendInvalidResponseError: If response payload is malformed.
        """
        if not isinstance(result, dict):
            raise BackendInvalidResponseError(
                "LangChain response was not a dictionary."
            )
        structured_text = _LangChainV1Invoker._extract_structured_text(result)
        if structured_text is not None:
            return structured_text

        messages = result.get("messages")
        if not isinstance(messages, list) or not messages:
            raise BackendInvalidResponseError(
                "LangChain response did not include messages."
            )
        return _LangChainV1Invoker._extract_message_text(messages[-1])

    @staticmethod
    def _extract_message_text(message: object) -> str:
        """Extract text from the last response message object.

        Args:
            message: Last message object from LangChain response.

        Returns:
            Extracted text string.

        Raises:
            BackendInvalidResponseError: If message content is malformed.
        """
        content = getattr(message, "content", None)
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            text_chunks = [
                str(item.get("text", "")).strip()
                for item in content
                if isinstance(item, dict)
            ]
            return "\n".join(chunk for chunk in text_chunks if chunk)
        raise BackendInvalidResponseError(
            "LangChain response message content was invalid."
        )

    @staticmethod
    def _extract_structured_text(result: dict[str, object]) -> str | None:
        """Extract text from structured response payload when present.

        Args:
            result: Raw invocation result dictionary.

        Returns:
            Structured response text when available, else None.
        """
        structured = result.get("structured_response")
        if isinstance(structured, _StructuredSkillResponse):
            return structured.text.strip()
        if isinstance(structured, dict):
            maybe_text = structured.get("text")
            if isinstance(maybe_text, str):
                return maybe_text.strip()
        return None


class LangChainBackend:
    """Concrete backend implementation using LangChain v1 high-level APIs."""

    def __init__(
        self,
        invoker: AgentInvoker | None = None,
        *,
        sleep_fn: Callable[[float], None] = time.sleep,
        max_attempts: int = 2,
        backoff_seconds: float = 0.25,
    ) -> None:
        """Create LangChain backend implementation.

        Args:
            invoker: Optional invoker for provider-specific model execution.
            sleep_fn: Injectable sleep function for retries/tests.
            max_attempts: Total attempts (initial + retries).
            backoff_seconds: Fixed sleep between retryable attempts.

        Raises:
            ValueError: If `max_attempts` is less than 1.
        """
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        self._invoker = invoker or _LangChainV1Invoker()
        self._sleep_fn = sleep_fn
        self._max_attempts = max_attempts
        self._backoff_seconds = backoff_seconds

    def run(self, request: LlmRunRequest) -> LlmRunResponse:
        """Run a LangChain v1 workflow for the request.

        Args:
            request: Normalized run request.

        Returns:
            Normalized response payload.

        Raises:
            BackendInvalidResponseError: If output validation fails.
            BackendTimeoutError: If timeout is reached and retries are exhausted.
            BackendUnavailableError: If backend is unavailable after retries.
            LlmBackendError: If execution fails after retry policy is applied.
        """
        request = self._normalize_request(request)
        last_error: LlmBackendError | None = None

        for attempt in range(1, self._max_attempts + 1):
            started = time.perf_counter()
            try:
                response_text = self._invoker.invoke(request).strip()
                if not response_text:
                    raise BackendInvalidResponseError("Model returned empty output.")
                self._emit_event(
                    request=request,
                    attempt=attempt,
                    duration_ms=self._duration_ms(started),
                    status="ok",
                )
                return LlmRunResponse(text=response_text)
            except LlmBackendError as exc:
                last_error = exc
                self._emit_event(
                    request=request,
                    attempt=attempt,
                    duration_ms=self._duration_ms(started),
                    status="error",
                    error_code=exc.code.value,
                )
                if not self._should_retry(exc, attempt):
                    raise
                self._sleep_fn(self._backoff_seconds)
            except TimeoutError as exc:
                timeout_error = BackendTimeoutError(str(exc))
                last_error = timeout_error
                self._emit_event(
                    request=request,
                    attempt=attempt,
                    duration_ms=self._duration_ms(started),
                    status="error",
                    error_code=timeout_error.code.value,
                )
                if not self._should_retry(timeout_error, attempt):
                    raise BackendTimeoutError(str(exc)) from exc
                self._sleep_fn(self._backoff_seconds)
            except Exception as exc:
                unavailable = BackendUnavailableError(str(exc))
                last_error = unavailable
                self._emit_event(
                    request=request,
                    attempt=attempt,
                    duration_ms=self._duration_ms(started),
                    status="error",
                    error_code=unavailable.code.value,
                )
                if not self._should_retry(unavailable, attempt):
                    raise BackendUnavailableError(str(exc)) from exc
                self._sleep_fn(self._backoff_seconds)

        if last_error is not None:
            raise LlmBackendError(
                last_error.code,
                str(last_error),
                retryable=last_error.retryable,
            )
        raise BackendUnavailableError("Unexpected adapter state.")

    @staticmethod
    def _normalize_request(request: LlmRunRequest) -> LlmRunRequest:
        """Normalize input request fields.

        Args:
            request: Original request payload.

        Returns:
            Normalized request payload.
        """
        return LlmRunRequest(
            session_id=request.session_id,
            skill_name=request.skill_name,
            skill_summary=request.skill_summary.strip(),
            skill_instructions=request.skill_instructions.strip(),
            user_text=request.user_text.strip(),
            model_name=request.model_name,
        )

    def _should_retry(self, error: LlmBackendError, attempt: int) -> bool:
        """Decide whether to retry a failed attempt.

        Args:
            error: Caught backend error.
            attempt: Current attempt number.

        Returns:
            Whether one more attempt should be made.
        """
        if attempt >= self._max_attempts:
            return False
        return error.retryable

    def _emit_event(
        self,
        *,
        request: LlmRunRequest,
        attempt: int,
        duration_ms: int,
        status: str,
        error_code: str | None = None,
    ) -> None:
        """Emit structured runtime event for backend execution.

        Args:
            request: Normalized run request.
            attempt: Current attempt number.
            duration_ms: Attempt duration in milliseconds.
            status: Attempt status.
            error_code: Optional stable error code.
        """
        _LOGGER.info(
            "llm_backend_event",
            extra={
                "session_id": request.session_id,
                "skill_name": request.skill_name,
                "invocation_mode": "llm_orchestration",
                "model_name": request.model_name,
                "attempt": attempt,
                "duration_ms": duration_ms,
                "status": status,
                "error_code": error_code,
            },
        )

    @staticmethod
    def _duration_ms(started: float) -> int:
        """Compute elapsed duration in milliseconds.

        Args:
            started: Start time from ``time.perf_counter``.

        Returns:
            Elapsed duration in milliseconds.
        """
        return int((time.perf_counter() - started) * 1000)
