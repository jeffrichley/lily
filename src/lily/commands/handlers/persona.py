"""Handler for /persona subcommands."""

from __future__ import annotations

from typing import Protocol

from lily.commands.parser import CommandCall
from lily.commands.types import CommandResult
from lily.persona import PersonaCatalog, PersonaProfile
from lily.session.models import Session


class PersonaRepositoryPort(Protocol):
    """Persona repository interface used by command layer."""

    def load_catalog(self) -> PersonaCatalog:
        """Load deterministic persona catalog."""

    def get(self, persona_id: str) -> PersonaProfile | None:
        """Resolve one persona by exact id.

        Args:
            persona_id: Persona identifier.
        """


class PersonaCommand:
    """Deterministic `/persona` command handler."""

    def __init__(self, repository: PersonaRepositoryPort) -> None:
        """Create handler with persona repository dependency.

        Args:
            repository: Persona repository implementation.
        """
        self._repository = repository

    def execute(self, call: CommandCall, session: Session) -> CommandResult:
        """Execute `/persona list|use|show` against session state.

        Args:
            call: Parsed command call.
            session: Active session.

        Returns:
            Deterministic success/error envelope.
        """
        if not call.args:
            return self._invalid_subcommand_error(None)

        subcommand = call.args[0]
        return self._dispatch_subcommand(
            session=session,
            subcommand=subcommand,
            args=call.args[1:],
        )

    def _dispatch_subcommand(
        self,
        *,
        session: Session,
        subcommand: str,
        args: tuple[str, ...],
    ) -> CommandResult:
        """Dispatch validated subcommand to concrete handler path.

        Args:
            session: Active session.
            subcommand: Persona subcommand token.
            args: Remaining command arguments.

        Returns:
            Deterministic command result.
        """
        if subcommand == "list":
            return self._handle_list(session, args)
        if subcommand == "use":
            return self._handle_use(session, args)
        if subcommand == "show":
            return self._handle_show(session, args)
        return self._invalid_subcommand_error(subcommand)

    def _handle_list(self, session: Session, args: tuple[str, ...]) -> CommandResult:
        """Validate and execute `/persona list`.

        Args:
            session: Active session.
            args: Remaining arguments.

        Returns:
            Deterministic command result.
        """
        if args:
            return CommandResult.error(
                "Error: /persona list does not accept arguments.",
                code="invalid_args",
                data={"command": "persona"},
            )
        return self._list_personas(session)

    def _handle_use(self, session: Session, args: tuple[str, ...]) -> CommandResult:
        """Validate and execute `/persona use <name>`.

        Args:
            session: Active session.
            args: Remaining arguments.

        Returns:
            Deterministic command result.
        """
        if len(args) != 1:
            return CommandResult.error(
                "Error: /persona use requires exactly one persona name.",
                code="invalid_args",
                data={"command": "persona"},
            )
        return self._use_persona(session, args[0])

    def _handle_show(self, session: Session, args: tuple[str, ...]) -> CommandResult:
        """Validate and execute `/persona show`.

        Args:
            session: Active session.
            args: Remaining arguments.

        Returns:
            Deterministic command result.
        """
        if args:
            return CommandResult.error(
                "Error: /persona show does not accept arguments.",
                code="invalid_args",
                data={"command": "persona"},
            )
        return self._show_persona(session)

    @staticmethod
    def _invalid_subcommand_error(subcommand: str | None) -> CommandResult:
        """Build deterministic invalid-subcommand error result.

        Args:
            subcommand: Optional invalid subcommand token.

        Returns:
            Deterministic command error envelope.
        """
        if subcommand is None:
            message = "Error: /persona requires one subcommand: list|use|show."
            data = {"command": "persona"}
        else:
            message = f"Error: unsupported /persona subcommand '{subcommand}'."
            data = {"command": "persona", "subcommand": subcommand}
        return CommandResult.error(message, code="invalid_args", data=data)

    def _list_personas(self, session: Session) -> CommandResult:
        """Render deterministic persona list with active marker.

        Args:
            session: Active session.

        Returns:
            Formatted persona list result.
        """
        catalog = self._repository.load_catalog()
        if not catalog.personas:
            return CommandResult.error(
                "Error: no persona profiles are available.",
                code="persona_not_found",
            )
        lines = []
        for profile in catalog.personas:
            marker = "*" if profile.persona_id == session.active_agent else " "
            lines.append(f"{marker} {profile.persona_id} - {profile.summary}")
        return CommandResult.ok(
            "\n".join(lines),
            code="persona_listed",
            data={"count": len(catalog.personas), "active": session.active_agent},
        )

    def _use_persona(self, session: Session, persona_id: str) -> CommandResult:
        """Switch active persona in current session.

        Args:
            session: Active session.
            persona_id: Requested persona identifier.

        Returns:
            Success/error result.
        """
        normalized = persona_id.strip().lower()
        profile = self._repository.get(normalized)
        if profile is None:
            return CommandResult.error(
                f"Error: persona '{normalized}' was not found.",
                code="persona_not_found",
                data={"persona": normalized},
            )
        session.active_agent = profile.persona_id
        session.active_style = None
        return CommandResult.ok(
            (
                f"Active persona set to '{profile.persona_id}' "
                f"(default style: {profile.default_style.value})."
            ),
            code="persona_set",
            data={
                "persona": profile.persona_id,
                "style": profile.default_style.value,
            },
        )

    def _show_persona(self, session: Session) -> CommandResult:
        """Show current active persona profile.

        Args:
            session: Active session.

        Returns:
            Success/error result.
        """
        profile = self._repository.get(session.active_agent)
        if profile is None:
            return CommandResult.error(
                (
                    f"Error: active persona '{session.active_agent}' "
                    "is missing from persona catalog."
                ),
                code="persona_not_found",
                data={"persona": session.active_agent},
            )
        effective_style = session.active_style or profile.default_style
        lines = [
            f"# Persona: {profile.persona_id}",
            "",
            f"- `summary`: {profile.summary}",
            f"- `default_style`: {profile.default_style.value}",
            f"- `effective_style`: {effective_style.value}",
            "",
            "## Instructions",
            profile.instructions,
        ]
        return CommandResult.ok(
            "\n".join(lines),
            code="persona_shown",
            data={
                "persona": profile.persona_id,
                "default_style": profile.default_style.value,
                "effective_style": effective_style.value,
            },
        )
