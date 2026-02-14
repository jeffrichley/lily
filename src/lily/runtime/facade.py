"""Runtime facade for command vs conversational routing."""

from __future__ import annotations

from lily.commands.parser import CommandParseError, ParsedInputKind, parse_input
from lily.commands.registry import CommandRegistry
from lily.commands.types import CommandResult
from lily.runtime.executors.llm_orchestration import LlmOrchestrationExecutor
from lily.runtime.session_lanes import run_in_session_lane
from lily.runtime.executors.tool_dispatch import AddTool, ToolDispatchExecutor
from lily.runtime.llm_backend import LangChainBackend
from lily.runtime.skill_invoker import SkillInvoker
from lily.session.models import Message, MessageRole, Session


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
        return run_in_session_lane(
            session.session_id,
            lambda: self._handle_input_serialized(text=text, session=session),
        )

    def _handle_input_serialized(self, *, text: str, session: Session) -> CommandResult:
        """Handle one input while holding per-session execution lane."""
        try:
            parsed = parse_input(text)
        except CommandParseError as exc:
            return CommandResult.error(str(exc))

        if parsed.kind == ParsedInputKind.COMMAND and parsed.command is not None:
            result = self._command_registry.dispatch(parsed.command, session)
            self._record_turn(session, user_text=text, assistant_text=result.message)
            return result

        result = CommandResult.error(
            "Error: non-command conversational routing is not implemented yet."
        )
        self._record_turn(session, user_text=text, assistant_text=result.message)
        return result

    @staticmethod
    def _build_default_registry() -> CommandRegistry:
        """Construct default command registry with hidden LLM backend wiring.

        Returns:
            Command registry with invoker and executor dependencies.
        """
        llm_backend = LangChainBackend()
        executors = (
            LlmOrchestrationExecutor(llm_backend),
            ToolDispatchExecutor(tools=(AddTool(),)),
        )
        invoker = SkillInvoker(executors=executors)
        return CommandRegistry(skill_invoker=invoker)

    @staticmethod
    def _record_turn(session: Session, *, user_text: str, assistant_text: str) -> None:
        """Append deterministic user/assistant events to conversation state."""
        session.conversation_state.append(
            Message(role=MessageRole.USER, content=user_text)
        )
        session.conversation_state.append(
            Message(role=MessageRole.ASSISTANT, content=assistant_text)
        )
