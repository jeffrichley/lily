"""Conversation orchestration helper for runtime facade."""

from __future__ import annotations

import re

from lily.commands.types import CommandResult
from lily.persona import FilePersonaRepository, PersonaProfile
from lily.prompting import PersonaContext, PersonaStyleLevel, PromptMode
from lily.runtime.conversation import (
    ConversationExecutionError,
    ConversationExecutor,
    ConversationRequest,
    ConversationResponse,
)
from lily.runtime.memory_summary_provider import MemorySummaryProvider
from lily.session.models import (
    HistoryCompactionBackend,
    HistoryCompactionConfig,
    Session,
)

_FOCUS_HINT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(urgent|asap|critical|incident|prod|production|outage)\b", re.IGNORECASE
    ),
    re.compile(r"\b(error|failure|broken|fix now)\b", re.IGNORECASE),
)
_PLAYFUL_HINT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(fun|joke|playful|celebrate|party|lighten up)\b", re.IGNORECASE),
)


class ConversationOrchestrator:
    """Build and execute deterministic conversation turns."""

    def __init__(
        self,
        *,
        conversation_executor: ConversationExecutor,
        persona_repository: FilePersonaRepository,
        memory_summary_provider: MemorySummaryProvider,
        compaction_backend: HistoryCompactionBackend,
        compaction_max_tokens: int,
    ) -> None:
        """Store collaborators used to run one conversation turn.

        Args:
            conversation_executor: Conversation executor adapter.
            persona_repository: Persona repository for active persona resolution.
            memory_summary_provider: Prompt-memory summary provider.
            compaction_backend: Conversation compaction backend.
            compaction_max_tokens: Conversation compaction token budget.
        """
        self._conversation_executor = conversation_executor
        self._persona_repository = persona_repository
        self._memory_summary_provider = memory_summary_provider
        self._compaction_backend = compaction_backend
        self._compaction_max_tokens = compaction_max_tokens

    def run_turn(self, *, text: str, session: Session) -> CommandResult:
        """Run non-command conversational turn through conversation executor.

        Args:
            text: Raw conversation input text.
            session: Active session context.

        Returns:
            Deterministic conversation command result envelope.
        """
        persona = self._resolve_persona(session.active_agent)
        style_level = (
            session.active_style
            or self._derive_context_style(text)
            or persona.default_style
        )
        request = ConversationRequest(
            session_id=session.session_id,
            user_text=text,
            model_name=session.model_settings.model_name,
            history=tuple(session.conversation_state),
            limits=session.model_settings.conversation_limits.model_copy(
                update={
                    "compaction": HistoryCompactionConfig(
                        backend=self._compaction_backend,
                        max_tokens=self._compaction_max_tokens,
                    )
                }
            ),
            memory_summary=self._memory_summary_provider.build(
                session=session,
                user_text=text,
            ),
            persona_context=PersonaContext(
                active_persona_id=persona.persona_id,
                style_level=style_level,
                persona_summary=persona.summary,
                persona_instructions=persona.instructions,
                session_hints=(
                    f"conversation_events={len(session.conversation_state)}",
                    f"style={style_level.value}",
                ),
            ),
            prompt_mode=PromptMode.FULL,
        )
        try:
            response = self._conversation_executor.run(request)
        except ConversationExecutionError as exc:
            return CommandResult.error(
                f"Error: {exc}",
                code=exc.code,
            )
        return self._conversation_result(response)

    @staticmethod
    def _conversation_result(response: ConversationResponse) -> CommandResult:
        """Convert conversation response to deterministic command envelope.

        Args:
            response: Normalized conversation response.

        Returns:
            Deterministic successful command result.
        """
        return CommandResult.ok(
            response.text,
            code="conversation_reply",
            data={"route": "conversation"},
        )

    def _resolve_persona(self, persona_id: str) -> PersonaProfile:
        """Resolve active persona profile with deterministic fallback.

        Args:
            persona_id: Session active persona identifier.

        Returns:
            Loaded persona profile or safe fallback profile.
        """
        profile = self._persona_repository.get(persona_id)
        if profile is not None:
            return profile
        return PersonaProfile(
            persona_id=persona_id,
            summary="Fallback persona profile.",
            default_style=PersonaStyleLevel.BALANCED,
            instructions="Provide clear, accurate, and concise assistance.",
        )

    @staticmethod
    def _derive_context_style(user_text: str) -> PersonaStyleLevel | None:
        """Derive style hint from user turn content.

        Args:
            user_text: Raw user input text.

        Returns:
            Suggested style level when a context marker is detected.
        """
        text = user_text.strip()
        for pattern in _FOCUS_HINT_PATTERNS:
            if pattern.search(text):
                return PersonaStyleLevel.FOCUS
        for pattern in _PLAYFUL_HINT_PATTERNS:
            if pattern.search(text):
                return PersonaStyleLevel.PLAYFUL
        return None
