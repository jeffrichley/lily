"""Runtime facade for command vs conversational routing."""

from __future__ import annotations

from lily.commands.parser import CommandParseError, ParsedInputKind, parse_input
from lily.commands.registry import CommandRegistry
from lily.commands.types import CommandResult
from lily.runtime.executors.llm_orchestration import LlmOrchestrationExecutor
from lily.runtime.executors.tool_dispatch import ToolDispatchExecutor
from lily.runtime.llm_backend import LangChainBackend
from lily.runtime.skill_invoker import SkillInvoker
from lily.session.models import Session


class RuntimeFacade:
    """Facade for deterministic command and conversational routing."""

    def __init__(self, command_registry: CommandRegistry | None = None) -> None:
        """Create facade with command registry dependency.

        Args:
            command_registry: Optional deterministic command registry.
        """
        self._command_registry = command_registry or self._build_default_registry()

    def handle_input(self, text: str, session: Session) -> CommandResult:
        """Route one user turn to command or conversational path.

        Args:
            text: Raw user text.
            session: Active session.

        Returns:
            Deterministic result for command/conversation routing.
        """
        try:
            parsed = parse_input(text)
        except CommandParseError as exc:
            return CommandResult.error(str(exc))

        if parsed.kind == ParsedInputKind.COMMAND and parsed.command is not None:
            return self._command_registry.dispatch(parsed.command, session)

        return CommandResult.error(
            "Error: non-command conversational routing is not implemented yet."
        )

    @staticmethod
    def _build_default_registry() -> CommandRegistry:
        """Construct default command registry with hidden LLM backend wiring.

        Returns:
            Command registry with invoker and executor dependencies.
        """
        llm_backend = LangChainBackend()
        executors = (
            LlmOrchestrationExecutor(llm_backend),
            ToolDispatchExecutor(),
        )
        invoker = SkillInvoker(executors=executors)
        return CommandRegistry(skill_invoker=invoker)
