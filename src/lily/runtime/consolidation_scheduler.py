"""Scheduled consolidation orchestration for runtime conversation flow."""

from __future__ import annotations

from lily.commands.handlers._memory_support import (
    build_personality_namespace,
    build_personality_repository,
    build_task_repository,
    resolve_store_file,
)
from lily.memory import (
    ConsolidationBackend,
    ConsolidationRequest,
    LangMemManagerConsolidationEngine,
    LangMemToolingAdapter,
    RuleBasedConsolidationEngine,
)
from lily.session.models import MessageRole, Session


class ConsolidationScheduler:
    """Run periodic consolidation when configured interval boundaries are met."""

    def __init__(
        self,
        *,
        enabled: bool,
        backend: ConsolidationBackend,
        llm_assisted_enabled: bool,
        auto_run_every_n_turns: int,
    ) -> None:
        """Store scheduler settings for deterministic periodic consolidation.

        Args:
            enabled: Whether scheduled consolidation is enabled.
            backend: Consolidation backend selection.
            llm_assisted_enabled: LLM-assisted consolidation toggle.
            auto_run_every_n_turns: Scheduled run interval.
        """
        self._enabled = enabled
        self._backend = backend
        self._llm_assisted_enabled = llm_assisted_enabled
        self._auto_run_every_n_turns = auto_run_every_n_turns

    def maybe_run(self, session: Session) -> None:
        """Run scheduled consolidation once when interval boundary is met.

        Args:
            session: Active session.
        """
        if not self._should_run(session):
            return
        self._run_once(session)

    def _should_run(self, session: Session) -> bool:
        """Check whether scheduled consolidation should run on this turn.

        Args:
            session: Active session.

        Returns:
            Whether scheduled consolidation should run now.
        """
        if not self._enabled:
            return False
        interval = self._auto_run_every_n_turns
        if interval < 1:
            return False
        user_turns = sum(
            1 for event in session.conversation_state if event.role == MessageRole.USER
        )
        return user_turns > 0 and user_turns % interval == 0

    def _run_once(self, session: Session) -> None:
        """Run one scheduled consolidation attempt.

        Args:
            session: Active session.
        """
        request = ConsolidationRequest(
            session_id=session.session_id,
            history=tuple(session.conversation_state),
            personality_namespace=build_personality_namespace(
                session=session,
                domain="user_profile",
            ),
            enabled=True,
            backend=self._backend,
            llm_assisted_enabled=self._llm_assisted_enabled,
            dry_run=False,
        )
        try:
            if self._backend == ConsolidationBackend.RULE_BASED:
                personality_repository = build_personality_repository(session)
                task_repository = build_task_repository(session)
                if personality_repository is None:
                    return
                RuleBasedConsolidationEngine(
                    personality_repository=personality_repository,
                    task_repository=task_repository,
                ).run(request)
                return
            store_file = resolve_store_file(session)
            if store_file is None:
                return
            LangMemManagerConsolidationEngine(
                tooling_adapter=LangMemToolingAdapter(store_file=store_file)
            ).run(request)
        except Exception:  # pragma: no cover - best effort scheduling
            return
