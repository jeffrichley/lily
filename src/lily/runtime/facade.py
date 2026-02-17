"""Runtime facade for command vs conversational routing."""

from __future__ import annotations

import re
from typing import cast

from langgraph.checkpoint.base import BaseCheckpointSaver

from lily.commands.handlers._memory_support import (
    build_personality_namespace,
    build_personality_repository,
    build_task_namespace,
    build_task_repository,
    resolve_store_file,
)
from lily.commands.parser import CommandParseError, ParsedInputKind, parse_input
from lily.commands.registry import CommandRegistry
from lily.commands.types import CommandResult
from lily.memory import (
    ConsolidationBackend,
    ConsolidationRequest,
    EvidenceChunkingSettings,
    LangMemManagerConsolidationEngine,
    LangMemToolingAdapter,
    PromptMemoryRetrievalService,
    RuleBasedConsolidationEngine,
)
from lily.persona import FilePersonaRepository, PersonaProfile, default_persona_root
from lily.prompting import PersonaContext, PersonaStyleLevel, PromptMode
from lily.runtime.conversation import (
    ConversationExecutionError,
    ConversationExecutor,
    ConversationRequest,
    ConversationResponse,
    LangChainConversationExecutor,
)
from lily.runtime.executors.llm_orchestration import LlmOrchestrationExecutor
from lily.runtime.executors.tool_dispatch import (
    AddTool,
    MultiplyTool,
    SubtractTool,
    ToolContract,
    ToolDispatchExecutor,
)
from lily.runtime.llm_backend import LangChainBackend
from lily.runtime.session_lanes import run_in_session_lane
from lily.runtime.skill_invoker import SkillInvoker
from lily.session.models import Message, MessageRole, Session

_FOCUS_HINT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(urgent|asap|critical|incident|prod|production|outage)\b", re.IGNORECASE
    ),
    re.compile(r"\b(error|failure|broken|fix now)\b", re.IGNORECASE),
)
_PLAYFUL_HINT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(fun|joke|playful|celebrate|party|lighten up)\b", re.IGNORECASE),
)


class RuntimeFacade:
    """Facade for deterministic command and conversational routing."""

    def __init__(  # noqa: PLR0913
        self,
        command_registry: CommandRegistry | None = None,
        conversation_executor: ConversationExecutor | None = None,
        persona_repository: FilePersonaRepository | None = None,
        conversation_checkpointer: BaseCheckpointSaver | None = None,
        memory_tooling_enabled: bool = False,
        memory_tooling_auto_apply: bool = False,
        consolidation_enabled: bool = False,
        consolidation_backend: ConsolidationBackend = ConsolidationBackend.RULE_BASED,
        consolidation_llm_assisted_enabled: bool = False,
        consolidation_auto_run_every_n_turns: int = 0,
        evidence_chunking: EvidenceChunkingSettings | None = None,
    ) -> None:
        """Create facade with command and conversation dependencies.

        Args:
            command_registry: Optional deterministic command registry.
            conversation_executor: Optional conversation execution adapter.
            persona_repository: Optional persona profile repository.
            conversation_checkpointer: Optional checkpointer for default conversation
                executor wiring.
            memory_tooling_enabled: Whether LangMem command routes are enabled.
            memory_tooling_auto_apply: Whether standard memory routes auto-use tools.
            consolidation_enabled: Whether consolidation pipeline is enabled.
            consolidation_backend: Consolidation backend selection.
            consolidation_llm_assisted_enabled: LLM-assisted consolidation toggle.
            consolidation_auto_run_every_n_turns: Scheduled consolidation interval.
            evidence_chunking: Evidence chunking settings.
        """
        self._consolidation_enabled = consolidation_enabled
        self._consolidation_backend = consolidation_backend
        self._consolidation_llm_assisted_enabled = consolidation_llm_assisted_enabled
        self._consolidation_auto_run_every_n_turns = (
            consolidation_auto_run_every_n_turns
        )
        self._persona_repository = persona_repository or FilePersonaRepository(
            root_dir=default_persona_root()
        )
        self._command_registry = command_registry or self._build_default_registry(
            memory_tooling_enabled=memory_tooling_enabled,
            memory_tooling_auto_apply=memory_tooling_auto_apply,
            consolidation_enabled=consolidation_enabled,
            consolidation_backend=consolidation_backend,
            consolidation_llm_assisted_enabled=consolidation_llm_assisted_enabled,
            evidence_chunking=evidence_chunking,
        )
        self._conversation_executor = (
            conversation_executor
            or LangChainConversationExecutor(checkpointer=conversation_checkpointer)
        )

    def handle_input(self, text: str, session: Session) -> CommandResult:
        """Route one user turn to command or conversational path.

        Args:
            text: Raw user text.
            session: Active session.

        Returns:
            Deterministic result for command/conversation routing.
        """
        return run_in_session_lane(
            session.session_id,
            lambda: self._handle_input_serialized(text=text, session=session),
        )

    def _handle_input_serialized(self, *, text: str, session: Session) -> CommandResult:
        """Handle one input while holding per-session execution lane.

        Args:
            text: Raw input text.
            session: Active session receiving the turn.

        Returns:
            Deterministic command result.
        """
        try:
            parsed = parse_input(text)
        except CommandParseError as exc:
            return CommandResult.error(
                str(exc),
                code="parse_error",
                data={"input": text},
            )

        if parsed.kind == ParsedInputKind.COMMAND and parsed.command is not None:
            result = self._command_registry.dispatch(parsed.command, session)
            self._record_turn(session, user_text=text, assistant_text=result.message)
            return result

        result = self._run_conversation(text=text, session=session)
        self._record_turn(session, user_text=text, assistant_text=result.message)
        self._maybe_run_scheduled_consolidation(session)
        return result

    def _run_conversation(self, *, text: str, session: Session) -> CommandResult:
        """Run non-command conversational turn through conversation executor.

        Args:
            text: Raw conversation input text.
            session: Active session context.

        Returns:
            Deterministic conversation command result envelope.
        """
        persona = self._resolve_persona(session.active_agent)
        style_level = (
            session.active_style or _derive_context_style(text) or persona.default_style
        )
        request = ConversationRequest(
            session_id=session.session_id,
            user_text=text,
            model_name=session.model_settings.model_name,
            history=tuple(session.conversation_state),
            limits=session.model_settings.conversation_limits,
            memory_summary=self._build_memory_summary(
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

    def _build_memory_summary(self, *, session: Session, user_text: str) -> str:
        """Build repository-backed memory summary for prompt injection.

        Args:
            session: Active session state.
            user_text: Current user turn text.

        Returns:
            Retrieved memory summary string, or empty when unavailable.
        """
        personality_repository = build_personality_repository(session)
        task_repository = build_task_repository(session)
        if personality_repository is None or task_repository is None:
            return ""
        retrieval = PromptMemoryRetrievalService(
            personality_repository=personality_repository,
            task_repository=task_repository,
        )
        personality_namespaces = {
            domain: build_personality_namespace(session=session, domain=domain)
            for domain in ("working_rules", "persona_core", "user_profile")
        }
        task_namespaces = (build_task_namespace(task=session.session_id),)
        try:
            return retrieval.build_memory_summary(
                user_text=user_text,
                personality_namespaces=personality_namespaces,
                task_namespaces=task_namespaces,
            )
        except Exception:  # pragma: no cover - defensive fallback
            return ""

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

    def _build_default_registry(  # noqa: PLR0913
        self,
        *,
        memory_tooling_enabled: bool,
        memory_tooling_auto_apply: bool,
        consolidation_enabled: bool,
        consolidation_backend: ConsolidationBackend,
        consolidation_llm_assisted_enabled: bool,
        evidence_chunking: EvidenceChunkingSettings | None,
    ) -> CommandRegistry:
        """Construct default command registry with hidden LLM backend wiring.

        Args:
            memory_tooling_enabled: Whether LangMem command routes are enabled.
            memory_tooling_auto_apply: Whether standard memory routes auto-use tools.
            consolidation_enabled: Whether consolidation pipeline is enabled.
            consolidation_backend: Consolidation backend selection.
            consolidation_llm_assisted_enabled: LLM-assisted consolidation toggle.
            evidence_chunking: Evidence chunking settings.

        Returns:
            Command registry with invoker and executor dependencies.
        """
        llm_backend = LangChainBackend()
        tools = cast(
            tuple[ToolContract, ...],
            (
                AddTool(),
                SubtractTool(),
                MultiplyTool(),
            ),
        )
        executors = (
            LlmOrchestrationExecutor(llm_backend),
            ToolDispatchExecutor(tools=tools),
        )
        invoker = SkillInvoker(executors=executors)
        return CommandRegistry(
            skill_invoker=invoker,
            persona_repository=self._persona_repository,
            memory_tooling_enabled=memory_tooling_enabled,
            memory_tooling_auto_apply=memory_tooling_auto_apply,
            consolidation_enabled=consolidation_enabled,
            consolidation_backend=consolidation_backend,
            consolidation_llm_assisted_enabled=consolidation_llm_assisted_enabled,
            evidence_chunking=evidence_chunking,
        )

    def _maybe_run_scheduled_consolidation(self, session: Session) -> None:
        """Run periodic consolidation when scheduled interval is met.

        Args:
            session: Active session.
        """
        if not self._should_run_scheduled_consolidation(session):
            return
        self._run_scheduled_consolidation(session)

    def _should_run_scheduled_consolidation(self, session: Session) -> bool:
        """Check whether scheduled consolidation should run for this turn.

        Args:
            session: Active session.

        Returns:
            Whether scheduled consolidation should run now.
        """
        if not self._consolidation_enabled:
            return False
        interval = self._consolidation_auto_run_every_n_turns
        if interval < 1:
            return False
        user_turns = sum(
            1 for event in session.conversation_state if event.role == MessageRole.USER
        )
        return user_turns > 0 and user_turns % interval == 0

    def _run_scheduled_consolidation(self, session: Session) -> None:
        """Run scheduled consolidation once for current session state.

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
            backend=self._consolidation_backend,
            llm_assisted_enabled=self._consolidation_llm_assisted_enabled,
            dry_run=False,
        )
        try:
            if self._consolidation_backend == ConsolidationBackend.RULE_BASED:
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

    @staticmethod
    def _record_turn(session: Session, *, user_text: str, assistant_text: str) -> None:
        """Append deterministic user/assistant events to conversation state.

        Args:
            session: Active session to mutate.
            user_text: User turn content.
            assistant_text: Assistant/result turn content.
        """
        session.conversation_state.append(
            Message(role=MessageRole.USER, content=user_text)
        )
        session.conversation_state.append(
            Message(role=MessageRole.ASSISTANT, content=assistant_text)
        )


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
