"""LLM orchestration skill executor."""

from __future__ import annotations

from lily.commands.types import CommandResult
from lily.runtime.llm_backend import (
    LlmBackend,
    LlmBackendError,
    LlmBackendErrorCode,
    LlmRunRequest,
)
from lily.session.models import Session
from lily.skills.types import InvocationMode, SkillEntry


class LlmOrchestrationExecutor:
    """Execute `llm_orchestration` skills via private LLM backend port."""

    mode = InvocationMode.LLM_ORCHESTRATION

    def __init__(self, backend: LlmBackend) -> None:
        """Store backend implementation.

        Args:
            backend: Private LLM backend adapter.
        """
        self._backend = backend

    def execute(
        self, entry: SkillEntry, session: Session, user_text: str
    ) -> CommandResult:
        """Run one LLM-orchestrated skill.

        Args:
            entry: Skill entry selected from snapshot.
            session: Active session with model settings.
            user_text: User payload for skill execution.

        Returns:
            Command result with backend response text.
        """
        request = LlmRunRequest(
            session_id=session.session_id,
            skill_name=entry.name,
            skill_summary=entry.summary,
            user_text=user_text,
            model_name=session.model_settings.model_name,
        )
        try:
            response = self._backend.run(request)
            return CommandResult.ok(response.text)
        except LlmBackendError as exc:
            return CommandResult.error(self._map_backend_error(exc.code))

    @staticmethod
    def _map_backend_error(code: LlmBackendErrorCode) -> str:
        """Map backend failure code to deterministic user-facing message.

        Args:
            code: Stable backend failure code.

        Returns:
            Deterministic user-facing error message.
        """
        messages = {
            LlmBackendErrorCode.BACKEND_UNAVAILABLE: (
                "Error: LLM backend is unavailable."
            ),
            LlmBackendErrorCode.BACKEND_TIMEOUT: ("Error: LLM backend timed out."),
            LlmBackendErrorCode.BACKEND_INVALID_RESPONSE: (
                "Error: LLM backend returned invalid response."
            ),
            LlmBackendErrorCode.BACKEND_POLICY_BLOCKED: (
                "Error: response blocked by LLM policy."
            ),
        }
        return messages.get(code, "Error: LLM backend failed.")
