"""Handler for /reload_persona."""

from __future__ import annotations

from lily.commands.parser import CommandCall
from lily.commands.types import CommandResult
from lily.persona import FilePersonaRepository, PersonaRepositoryError
from lily.session.models import Session


class ReloadPersonaCommand:
    """Deterministic `/reload_persona` command handler."""

    def __init__(self, repository: FilePersonaRepository) -> None:
        """Create handler with persona repository dependency.

        Args:
            repository: Persona repository implementation.
        """
        self._repository = repository

    def execute(self, call: CommandCall, session: Session) -> CommandResult:
        """Reload persona catalog and validate active persona.

        Args:
            call: Parsed command call.
            session: Active session.

        Returns:
            Deterministic success/error envelope.
        """
        if call.args:
            return CommandResult.error(
                "Error: /reload_persona does not accept arguments.",
                code="invalid_args",
                data={"command": "reload_persona"},
            )
        try:
            catalog = self._repository.reload_catalog()
        except PersonaRepositoryError as exc:
            return CommandResult.error(
                f"Error: {exc}",
                code="persona_reload_failed",
            )
        if not catalog.personas:
            return CommandResult.error(
                "Error: no persona profiles are available after reload.",
                code="persona_not_found",
            )

        active_exists = catalog.get(session.active_agent) is not None
        switched = False
        if not active_exists:
            session.active_agent = catalog.personas[0].persona_id
            session.active_style = None
            switched = True

        return CommandResult.ok(
            (
                f"Reloaded personas. active={session.active_agent} "
                f"count={len(catalog.personas)} switched={str(switched).lower()}"
            ),
            code="persona_reloaded",
            data={
                "active": session.active_agent,
                "count": len(catalog.personas),
                "switched": switched,
            },
        )
