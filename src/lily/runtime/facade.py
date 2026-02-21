"""Runtime facade for command vs conversational routing."""

from __future__ import annotations

import re
from pathlib import Path

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
from lily.config import SecuritySettings
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
)
from lily.runtime.conversation_factory import ConversationRuntimeFactory
from lily.runtime.jobs_factory import JobsFactory
from lily.runtime.runtime_dependencies import (
    ConversationRuntimeSpec,
    JobsSpec,
    RuntimeDependencies,
    ToolingSpec,
)
from lily.runtime.security import SecurityPrompt
from lily.runtime.session_lanes import run_in_session_lane
from lily.runtime.tooling_factory import ToolingFactory
from lily.session.models import (
    HistoryCompactionBackend,
    HistoryCompactionConfig,
    Message,
    MessageRole,
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


class RuntimeFacade:
    """Facade for deterministic command and conversational routing."""

    def __init__(  # noqa: PLR0913
        self,
        command_registry: CommandRegistry | None = None,
        persona_repository: FilePersonaRepository | None = None,
        conversation_checkpointer: BaseCheckpointSaver | None = None,
        memory_tooling_enabled: bool = False,
        memory_tooling_auto_apply: bool = False,
        consolidation_enabled: bool = False,
        consolidation_backend: ConsolidationBackend = ConsolidationBackend.RULE_BASED,
        consolidation_llm_assisted_enabled: bool = False,
        consolidation_auto_run_every_n_turns: int = 0,
        evidence_chunking: EvidenceChunkingSettings | None = None,
        compaction_backend: HistoryCompactionBackend = (
            HistoryCompactionBackend.LANGGRAPH_NATIVE
        ),
        compaction_max_tokens: int = 1000,
        security: SecuritySettings | None = None,
        security_prompt: SecurityPrompt | None = None,
        project_root: Path | None = None,
        workspace_root: Path | None = None,
        jobs_scheduler_enabled: bool = False,
        dependencies: RuntimeDependencies | None = None,
        tooling_factory: ToolingFactory | None = None,
        jobs_factory: JobsFactory | None = None,
        conversation_factory: ConversationRuntimeFactory | None = None,
        conversation_executor: ConversationExecutor | None = None,
    ) -> None:
        """Create facade with command and conversation dependencies.

        Args:
            command_registry: Optional deterministic command registry.
            persona_repository: Optional persona profile repository.
            conversation_checkpointer: Optional checkpointer for conversation wiring.
            memory_tooling_enabled: Whether LangMem command routes are enabled.
            memory_tooling_auto_apply: Whether standard memory routes auto-use tools.
            consolidation_enabled: Whether consolidation pipeline is enabled.
            consolidation_backend: Consolidation backend selection.
            consolidation_llm_assisted_enabled: LLM-assisted consolidation toggle.
            consolidation_auto_run_every_n_turns: Scheduled consolidation interval.
            evidence_chunking: Evidence chunking settings.
            compaction_backend: Conversation compaction backend flag.
            compaction_max_tokens: Token budget for native compaction backend.
            security: Security settings for plugin-backed tool execution.
            security_prompt: Optional terminal prompt for HITL approvals.
            project_root: Optional project root for dependency lock hashing.
            workspace_root: Optional `.lily` workspace root for jobs/runs storage.
            jobs_scheduler_enabled: Whether cron scheduler runtime should start.
            dependencies: Optional pre-composed runtime dependencies.
            tooling_factory: Optional tooling composition root override.
            jobs_factory: Optional jobs composition root override.
            conversation_factory: Optional conversation composition root override.
            conversation_executor: Optional conversation executor override.
        """
        self._consolidation_enabled = consolidation_enabled
        self._consolidation_backend = consolidation_backend
        self._consolidation_llm_assisted_enabled = consolidation_llm_assisted_enabled
        self._consolidation_auto_run_every_n_turns = (
            consolidation_auto_run_every_n_turns
        )
        self._compaction_backend = compaction_backend
        self._compaction_max_tokens = compaction_max_tokens
        effective_security = security or SecuritySettings()
        effective_project_root = project_root or Path.cwd()
        effective_workspace_root = workspace_root or Path.cwd() / ".lily"
        self._persona_repository = persona_repository or FilePersonaRepository(
            root_dir=default_persona_root()
        )
        if dependencies is not None:
            self._command_registry = dependencies.command_registry
            self._conversation_executor = dependencies.conversation_executor
            self._jobs_scheduler_runtime = dependencies.jobs_scheduler_runtime
            return

        resolved = self._compose_dependencies(
            command_registry=command_registry,
            conversation_executor=conversation_executor,
            conversation_checkpointer=conversation_checkpointer,
            memory_tooling_enabled=memory_tooling_enabled,
            memory_tooling_auto_apply=memory_tooling_auto_apply,
            consolidation_enabled=consolidation_enabled,
            consolidation_backend=consolidation_backend,
            consolidation_llm_assisted_enabled=consolidation_llm_assisted_enabled,
            evidence_chunking=evidence_chunking,
            compaction_backend=compaction_backend,
            compaction_max_tokens=compaction_max_tokens,
            security=effective_security,
            security_prompt=security_prompt,
            project_root=effective_project_root,
            workspace_root=effective_workspace_root,
            jobs_scheduler_enabled=jobs_scheduler_enabled,
            tooling_factory=tooling_factory or ToolingFactory(),
            jobs_factory=jobs_factory or JobsFactory(),
            conversation_factory=conversation_factory or ConversationRuntimeFactory(),
        )
        self._command_registry = resolved.command_registry
        self._conversation_executor = resolved.conversation_executor
        self._jobs_scheduler_runtime = resolved.jobs_scheduler_runtime

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

    def close(self) -> None:
        """Release runtime resources (for example sqlite-backed checkpointers)."""
        if self._jobs_scheduler_runtime is not None:
            self._jobs_scheduler_runtime.shutdown()
        maybe_close = getattr(self._conversation_executor, "close", None)
        if callable(maybe_close):
            maybe_close()

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
            limits=session.model_settings.conversation_limits.model_copy(
                update={
                    "compaction": HistoryCompactionConfig(
                        backend=self._compaction_backend,
                        max_tokens=self._compaction_max_tokens,
                    )
                }
            ),
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

    def _compose_dependencies(  # noqa: PLR0913
        self,
        *,
        command_registry: CommandRegistry | None,
        conversation_executor: ConversationExecutor | None,
        conversation_checkpointer: BaseCheckpointSaver | None,
        memory_tooling_enabled: bool,
        memory_tooling_auto_apply: bool,
        consolidation_enabled: bool,
        consolidation_backend: ConsolidationBackend,
        consolidation_llm_assisted_enabled: bool,
        evidence_chunking: EvidenceChunkingSettings | None,
        compaction_backend: HistoryCompactionBackend,
        compaction_max_tokens: int,
        security: SecuritySettings,
        security_prompt: SecurityPrompt | None,
        project_root: Path,
        workspace_root: Path,
        jobs_scheduler_enabled: bool,
        tooling_factory: ToolingFactory,
        jobs_factory: JobsFactory,
        conversation_factory: ConversationRuntimeFactory,
    ) -> RuntimeDependencies:
        """Compose runtime dependencies from explicit composition roots.

        Args:
            command_registry: Optional externally provided command registry.
            conversation_executor: Optional externally provided conversation executor.
            conversation_checkpointer: Optional conversation checkpointer.
            memory_tooling_enabled: Whether memory tooling command routes are enabled.
            memory_tooling_auto_apply: Whether memory routes auto-use LangMem tools.
            consolidation_enabled: Whether consolidation pipeline is enabled.
            consolidation_backend: Consolidation backend selection.
            consolidation_llm_assisted_enabled: LLM-assisted consolidation toggle.
            evidence_chunking: Evidence chunking settings.
            compaction_backend: Conversation compaction backend.
            compaction_max_tokens: Conversation compaction token budget.
            security: Security settings for plugin-backed tool execution.
            security_prompt: Optional HITL security prompt.
            project_root: Project root path.
            workspace_root: Workspace root path.
            jobs_scheduler_enabled: Whether jobs scheduler is enabled.
            tooling_factory: Tooling composition root.
            jobs_factory: Jobs composition root.
            conversation_factory: Conversation composition root.

        Returns:
            Fully composed runtime dependencies.
        """
        jobs_bundle = None
        effective_registry = command_registry
        if effective_registry is None:
            jobs_bundle = jobs_factory.build(
                JobsSpec(
                    workspace_root=workspace_root,
                    scheduler_enabled=jobs_scheduler_enabled,
                )
            )
            tooling = tooling_factory.build(
                ToolingSpec(
                    security=security,
                    security_prompt=security_prompt,
                    project_root=project_root,
                )
            )
            effective_registry = CommandRegistry(
                skill_invoker=tooling.skill_invoker,
                persona_repository=self._persona_repository,
                memory_tooling_enabled=memory_tooling_enabled,
                memory_tooling_auto_apply=memory_tooling_auto_apply,
                consolidation_enabled=consolidation_enabled,
                consolidation_backend=consolidation_backend,
                consolidation_llm_assisted_enabled=consolidation_llm_assisted_enabled,
                evidence_chunking=evidence_chunking,
                jobs_executor=jobs_bundle.jobs_executor if jobs_bundle else None,
                jobs_runs_root=jobs_bundle.runs_root if jobs_bundle else None,
                jobs_scheduler_control=(
                    jobs_bundle.scheduler_control if jobs_bundle else None
                ),
            )
        effective_conversation_executor = conversation_factory.build(
            ConversationRuntimeSpec(
                conversation_executor=conversation_executor,
                conversation_checkpointer=conversation_checkpointer,
                compaction_backend=compaction_backend,
                compaction_max_tokens=compaction_max_tokens,
                evidence_chunking=evidence_chunking,
            )
        )
        scheduler_runtime = jobs_bundle.scheduler_runtime if jobs_bundle else None
        return RuntimeDependencies(
            command_registry=effective_registry,
            conversation_executor=effective_conversation_executor,
            jobs_scheduler_runtime=scheduler_runtime,
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
