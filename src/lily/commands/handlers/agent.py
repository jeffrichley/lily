"""Handler for /agent subcommands (persona-backed compatibility surface)."""

from __future__ import annotations

from typing import Protocol

from lily.commands.parser import CommandCall
from lily.commands.types import CommandResult
from lily.persona import PersonaCatalog, PersonaProfile
from lily.session.models import Session


class AgentRepositoryPort(Protocol):
    """Persona repository subset required by `/agent` compatibility command."""

    def load_catalog(self) -> PersonaCatalog:
        """Load deterministic persona catalog."""

    def get(self, persona_id: str) -> PersonaProfile | None:
        """Resolve one persona by id.

        Args:
            persona_id: Persona identifier.
        """


class AgentCommand:
    """Deterministic `/agent list|use|show` command handler."""

    def __init__(self, repository: AgentRepositoryPort) -> None:
        """Create handler with shared persona repository dependency.

        Args:
            repository: Persona repository implementation.
        """
        self._repository = repository

    def execute(self, call: CommandCall, session: Session) -> CommandResult:
        """Execute `/agent` subcommands.

        Args:
            call: Parsed command call.
            session: Active session.

        Returns:
            Deterministic success/error envelope.
        """
        if not call.args:
            return CommandResult.error(
                "Error: /agent requires one subcommand: list|use|show.",
                code="invalid_args",
                data={"command": "agent"},
            )
        subcommand = call.args[0]
        if subcommand == "list":
            return self._list_agents(call.args[1:], session)
        if subcommand == "use":
            return self._use_agent(call.args[1:], session)
        if subcommand == "show":
            return self._show_agent(call.args[1:], session)
        return CommandResult.error(
            f"Error: unsupported /agent subcommand '{subcommand}'.",
            code="invalid_args",
            data={"command": "agent", "subcommand": subcommand},
        )

    def _list_agents(self, args: tuple[str, ...], session: Session) -> CommandResult:
        """Render deterministic agent list.

        Args:
            args: Remaining command args.
            session: Active session.

        Returns:
            Command result.
        """
        if args:
            return CommandResult.error(
                "Error: /agent list does not accept arguments.",
                code="invalid_args",
                data={"command": "agent"},
            )
        catalog = self._repository.load_catalog()
        rows = [
            {
                "agent": profile.persona_id,
                "summary": profile.summary,
                "active": profile.persona_id == session.active_agent,
            }
            for profile in catalog.personas
        ]
        lines = [
            f"{'*' if row['active'] else ' '} {row['agent']} - {row['summary']}"
            for row in rows
        ]
        return CommandResult.ok(
            "\n".join(lines) if lines else "No agents available.",
            code="agent_listed",
            data={"active": session.active_agent, "count": len(rows), "agents": rows},
        )

    def _use_agent(self, args: tuple[str, ...], session: Session) -> CommandResult:
        """Switch active agent (persona-backed).

        Args:
            args: Remaining command args.
            session: Active session.

        Returns:
            Command result.
        """
        if len(args) != 1:
            return CommandResult.error(
                "Error: /agent use requires exactly one agent name.",
                code="invalid_args",
                data={"command": "agent"},
            )
        agent_id = args[0].strip().lower()
        profile = self._repository.get(agent_id)
        if profile is None:
            return CommandResult.error(
                f"Error: agent '{agent_id}' was not found.",
                code="agent_not_found",
                data={"agent": agent_id},
            )
        session.active_agent = profile.persona_id
        session.active_style = None
        return CommandResult.ok(
            (
                f"Active agent set to '{profile.persona_id}' "
                "(persona-backed compatibility mode)."
            ),
            code="agent_set",
            data={"agent": profile.persona_id},
        )

    def _show_agent(self, args: tuple[str, ...], session: Session) -> CommandResult:
        """Show active agent details.

        Args:
            args: Remaining command args.
            session: Active session.

        Returns:
            Command result.
        """
        if args:
            return CommandResult.error(
                "Error: /agent show does not accept arguments.",
                code="invalid_args",
                data={"command": "agent"},
            )
        profile = self._repository.get(session.active_agent)
        if profile is None:
            return CommandResult.error(
                f"Error: active agent '{session.active_agent}' is missing.",
                code="agent_not_found",
                data={"agent": session.active_agent},
            )
        return CommandResult.ok(
            f"Agent: {profile.persona_id}\nSummary: {profile.summary}",
            code="agent_shown",
            data={"agent": profile.persona_id, "summary": profile.summary},
        )
