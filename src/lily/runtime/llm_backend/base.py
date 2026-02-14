"""Private LLM backend contracts for runtime executors."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class LlmRunRequest(BaseModel):
    """Normalized request payload for LLM orchestration backends."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: str = Field(min_length=1)
    skill_name: str = Field(min_length=1)
    skill_summary: str
    user_text: str
    model_name: str = Field(min_length=1)


class LlmRunResponse(BaseModel):
    """Normalized response payload from LLM orchestration backends."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str = Field(min_length=1)


class LlmBackendErrorCode(StrEnum):
    """Stable backend failure categories."""

    BACKEND_UNAVAILABLE = "backend_unavailable"
    BACKEND_TIMEOUT = "backend_timeout"
    BACKEND_INVALID_RESPONSE = "backend_invalid_response"
    BACKEND_POLICY_BLOCKED = "backend_policy_blocked"


class LlmBackendError(RuntimeError):
    """Base error for backend failures with stable machine-readable code."""

    def __init__(
        self,
        code: LlmBackendErrorCode,
        message: str,
        *,
        retryable: bool,
    ) -> None:
        """Create backend error.

        Args:
            code: Stable backend error category.
            message: Human-readable error message.
            retryable: Whether error category is retryable.
        """
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class BackendUnavailableError(LlmBackendError):
    """Raised when backend/provider runtime is unavailable."""

    def __init__(self, message: str = "Backend unavailable.") -> None:
        """Create backend unavailable error.

        Args:
            message: Human-readable error message.
        """
        super().__init__(
            LlmBackendErrorCode.BACKEND_UNAVAILABLE,
            message,
            retryable=True,
        )


class BackendTimeoutError(LlmBackendError):
    """Raised when backend processing exceeds timeout."""

    def __init__(self, message: str = "Backend timeout.") -> None:
        """Create backend timeout error.

        Args:
            message: Human-readable error message.
        """
        super().__init__(
            LlmBackendErrorCode.BACKEND_TIMEOUT,
            message,
            retryable=True,
        )


class BackendInvalidResponseError(LlmBackendError):
    """Raised when backend returns an invalid response payload."""

    def __init__(self, message: str = "Backend invalid response.") -> None:
        """Create backend invalid-response error.

        Args:
            message: Human-readable error message.
        """
        super().__init__(
            LlmBackendErrorCode.BACKEND_INVALID_RESPONSE,
            message,
            retryable=False,
        )


class BackendPolicyBlockedError(LlmBackendError):
    """Raised when policy blocks output."""

    def __init__(self, message: str = "Backend policy blocked.") -> None:
        """Create backend policy-blocked error.

        Args:
            message: Human-readable error message.
        """
        super().__init__(
            LlmBackendErrorCode.BACKEND_POLICY_BLOCKED,
            message,
            retryable=False,
        )


class LlmBackend(Protocol):
    """Backend contract hidden behind Lily runtime seams."""

    def run(self, request: LlmRunRequest) -> LlmRunResponse:
        """Execute one model run for an orchestration request.

        Args:
            request: Normalized run request.
        """
