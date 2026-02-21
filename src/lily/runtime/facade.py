"""Runtime facade for command vs conversational routing."""

from __future__ import annotations

from pathlib import Path

from langgraph.checkpoint.base import BaseCheckpointSaver

from lily.commands.parser import CommandParseError, ParsedInputKind, parse_input
from lily.commands.registry import CommandRegistry
from lily.commands.types import CommandResult
from lily.config import SecuritySettings
from lily.memory import ConsolidationBackend, EvidenceChunkingSettings
from lily.persona import FilePersonaRepository, default_persona_root
from lily.runtime.consolidation_scheduler import ConsolidationScheduler
from lily.runtime.conversation import ConversationExecutor
from lily.runtime.conversation_factory import ConversationRuntimeFactory
from lily.runtime.conversation_orchestrator import ConversationOrchestrator
from lily.runtime.jobs_factory import JobsFactory
from lily.runtime.memory_summary_provider import MemorySummaryProvider
from lily.runtime.runtime_dependencies import (
    ConversationRuntimeSpec,
    JobsSpec,
    RuntimeDependencies,
    ToolingSpec,
)
from lily.runtime.security import SecurityPrompt
from lily.runtime.session_lanes import run_in_session_lane
from lily.runtime.tooling_factory import ToolingFactory
from lily.session.models import HistoryCompactionBackend, Message, MessageRole, Session


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
        self._persona_repository = persona_repository or FilePersonaRepository(
            root_dir=default_persona_root()
        )
        self._memory_summary_provider = MemorySummaryProvider()
        self._consolidation_scheduler = ConsolidationScheduler(
            enabled=consolidation_enabled,
            backend=consolidation_backend,
            llm_assisted_enabled=consolidation_llm_assisted_enabled,
            auto_run_every_n_turns=consolidation_auto_run_every_n_turns,
        )

        if dependencies is not None:
            self._command_registry = dependencies.command_registry
            self._conversation_executor = dependencies.conversation_executor
            self._jobs_scheduler_runtime = dependencies.jobs_scheduler_runtime
        else:
            effective_security = security or SecuritySettings()
            effective_project_root = project_root or Path.cwd()
            effective_workspace_root = workspace_root or Path.cwd() / ".lily"
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
                conversation_factory=conversation_factory
                or ConversationRuntimeFactory(),
            )
            self._command_registry = resolved.command_registry
            self._conversation_executor = resolved.conversation_executor
            self._jobs_scheduler_runtime = resolved.jobs_scheduler_runtime

        self._conversation_orchestrator = ConversationOrchestrator(
            conversation_executor=self._conversation_executor,
            persona_repository=self._persona_repository,
            memory_summary_provider=self._memory_summary_provider,
            compaction_backend=compaction_backend,
            compaction_max_tokens=compaction_max_tokens,
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

        result = self._conversation_orchestrator.run_turn(text=text, session=session)
        self._record_turn(session, user_text=text, assistant_text=result.message)
        self._consolidation_scheduler.maybe_run(session)
        return result

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
