"""Handler for /agent subcommands."""

from __future__ import annotations

from lily.agents import AgentNotFoundError, AgentService
from lily.agents.models import AgentProfile
from lily.commands.parser import CommandCall
from lily.commands.types import CommandResult
from lily.session.models import Session


class AgentCommand:
    """Deterministic `/agent list|use|show` command handler."""

    def __init__(self, service: AgentService) -> None:
        """Create handler with agent service dependency.

        Args:
            service: Agent service implementation.
        """
        self._service = service

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
        profiles = self._service.list_agents()
        rows = [
            {
                "agent": profile.agent_id,
                "summary": profile.summary,
                "active": profile.agent_id == session.active_agent,
            }
            for profile in profiles
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
        try:
            profile = self._service.set_active_agent(session, agent_id)
        except AgentNotFoundError:
            return CommandResult.error(
                f"Error: agent '{agent_id}' was not found.",
                code="agent_not_found",
                data={"agent": agent_id},
            )
        return CommandResult.ok(
            f"Active agent set to '{profile.agent_id}'.",
            code="agent_set",
            data={"agent": profile.agent_id},
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
        profile = self._service.get_agent(session.active_agent)
        if profile is None:
            return CommandResult.error(
                f"Error: active agent '{session.active_agent}' is missing.",
                code="agent_not_found",
                data={"agent": session.active_agent},
            )
        return CommandResult.ok(
            _render_agent_details(profile),
            code="agent_shown",
            data={"agent": profile.agent_id, "summary": profile.summary},
        )


def _render_agent_details(profile: AgentProfile) -> str:
    """Render one agent detail block.

    Args:
        profile: Resolved agent profile.

    Returns:
        Deterministic multi-line details.
    """
    return f"Agent: {profile.agent_id}\nSummary: {profile.summary}"
