"""Memory summary provider for conversation prompt injection."""

from __future__ import annotations

from lily.commands.handlers._memory_support import (
    build_personality_namespace,
    build_personality_repository,
    build_task_namespace,
    build_task_repository,
)
from lily.memory import PromptMemoryRetrievalService
from lily.memory.repository import PersonalityMemoryRepository, TaskMemoryRepository
from lily.session.models import Session


class MemorySummaryProvider:
    """Build repository-backed memory summary for one conversation turn."""

    def build(self, *, session: Session, user_text: str) -> str:
        """Build memory summary string for prompt context.

        Args:
            session: Active session state.
            user_text: Current user turn text.

        Returns:
            Retrieved memory summary string, or empty when unavailable.
        """
        repositories = self._resolve_repositories(session=session)
        if repositories is None:
            return ""
        personality_repository, task_repository = repositories
        retrieval = PromptMemoryRetrievalService(
            personality_repository=personality_repository,
            task_repository=task_repository,
        )
        personality_namespaces = self._personality_namespaces(session=session)
        task_namespaces = self._task_namespaces(session=session)
        try:
            return retrieval.build_memory_summary(
                user_text=user_text,
                personality_namespaces=personality_namespaces,
                task_namespaces=task_namespaces,
            )
        except Exception:  # pragma: no cover - defensive fallback
            return ""

    @staticmethod
    def _resolve_repositories(
        *,
        session: Session,
    ) -> tuple[PersonalityMemoryRepository, TaskMemoryRepository] | None:
        """Resolve personality/task repositories from session memory config.

        Args:
            session: Active session state.

        Returns:
            Tuple of personality and task repositories when both are available.
        """
        personality_repository = build_personality_repository(session)
        task_repository = build_task_repository(session)
        if personality_repository is None or task_repository is None:
            return None
        return personality_repository, task_repository

    @staticmethod
    def _personality_namespaces(*, session: Session) -> dict[str, str]:
        """Build personality namespace mapping used by prompt retrieval.

        Args:
            session: Active session state.

        Returns:
            Domain-to-namespace mapping.
        """
        return {
            domain: build_personality_namespace(session=session, domain=domain)
            for domain in ("working_rules", "persona_core", "user_profile")
        }

    @staticmethod
    def _task_namespaces(*, session: Session) -> tuple[str, ...]:
        """Build task namespace tuple used by prompt retrieval.

        Args:
            session: Active session state.

        Returns:
            Task namespaces tuple.
        """
        return (build_task_namespace(task=session.session_id),)
