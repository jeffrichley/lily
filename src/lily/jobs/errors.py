"""Deterministic job error contracts."""

from __future__ import annotations

from enum import StrEnum


class JobErrorCode(StrEnum):
    """Stable job runtime/repository error codes."""

    NOT_FOUND = "job_not_found"
    INVALID_SPEC = "job_invalid_spec"
    TRIGGER_INVALID = "job_trigger_invalid"
    TARGET_UNRESOLVED = "job_target_unresolved"
    BINDINGS_INVALID = "job_bindings_invalid"
    EXECUTION_FAILED = "job_execution_failed"
    POLICY_DENIED = "job_policy_denied"


class JobError(RuntimeError):
    """Job failure with stable deterministic code."""

    def __init__(
        self,
        code: JobErrorCode,
        message: str,
        *,
        data: dict[str, object] | None = None,
    ) -> None:
        """Create job failure.

        Args:
            code: Stable job error code.
            message: Human-readable error message.
            data: Optional structured payload for diagnostics.
        """
        super().__init__(message)
        self.code = code
        self.data = data or {}
