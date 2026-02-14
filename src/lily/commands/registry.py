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
from lily.skills.types import SkillEntry


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
        self._skill_invoker = skill_invoker
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
        if handler is not None:
            return handler.execute(call, session)

        alias_targets = self._find_alias_targets(session, call.name)
        if len(alias_targets) > 1:
            return CommandResult.error(
                f"Error: command alias '/{call.name}' is ambiguous in snapshot.",
                code="alias_ambiguous",
                data={"alias": call.name},
            )
        if len(alias_targets) == 1:
            user_text = " ".join(call.args)
            return self._skill_invoker.invoke(alias_targets[0], session, user_text)

        return CommandResult.error(
            f"Error: unknown command '/{call.name}'.",
            code="unknown_command",
            data={"command": call.name},
        )

    @staticmethod
    def _find_alias_targets(session: Session, alias_name: str) -> list[SkillEntry]:
        """Return skills in snapshot that expose matching command alias.

        Args:
            session: Active session whose snapshot should be queried.
            alias_name: Alias name from parsed slash command.

        Returns:
            Matching skill entries with same alias.
        """
        return [
            entry
            for entry in session.skill_snapshot.skills
            if entry.command is not None and entry.command == alias_name
        ]
