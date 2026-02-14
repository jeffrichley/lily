"""Command registry and dispatch."""

from __future__ import annotations

from lily.commands.handlers.help_skill import HelpSkillCommand
from lily.commands.handlers.reload_skills import ReloadSkillsCommand
from lily.commands.handlers.skill_invoke import SkillInvokeCommand
from lily.commands.handlers.skills_list import SkillsListCommand
from lily.commands.parser import CommandCall
from lily.commands.types import CommandHandler, CommandResult
from lily.runtime.skill_invoker import SkillInvoker
from lily.session.models import Session


class CommandRegistry:
    """Deterministic command handler registry."""

    def __init__(
        self,
        *,
        skill_invoker: SkillInvoker,
        handlers: dict[str, CommandHandler] | None = None,
    ) -> None:
        """Construct registry with built-in handlers plus optional overrides.

        Args:
            skill_invoker: Invoker dependency for `/skill` command execution.
            handlers: Optional custom handlers keyed by command name.
        """
        self._handlers: dict[str, CommandHandler] = {
            "skills": SkillsListCommand(),
            "skill": SkillInvokeCommand(skill_invoker),
            "help": HelpSkillCommand(),
            "reload_skills": ReloadSkillsCommand(),
        }
        if handlers:
            self._handlers.update(handlers)

    def dispatch(self, call: CommandCall, session: Session) -> CommandResult:
        """Dispatch parsed command call to exact-match handler.

        Args:
            call: Parsed command call.
            session: Active session for command evaluation.

        Returns:
            Command execution result.
        """
        handler = self._handlers.get(call.name)
        if handler is None:
            return CommandResult.error(f"Error: unknown command '/{call.name}'.")
        return handler.execute(call, session)
