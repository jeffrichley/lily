"""Handler for /persona subcommands."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from lily.commands.parser import CommandCall
from lily.commands.types import CommandResult
from lily.persona import PersonaCatalog, PersonaProfile, PersonaRepositoryError
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

    def export_persona(self, *, persona_id: str, destination: Path) -> Path:
        """Export one persona profile to destination path.

        Args:
            persona_id: Persona identifier.
            destination: Output file path.
        """

    def import_persona(self, *, source: Path) -> PersonaProfile:
        """Import one persona profile from source path.

        Args:
            source: Persona markdown file path.
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
        """Execute `/persona list|use|show|export|import` against session state.

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
        if subcommand == "export":
            return self._handle_export(args)
        if subcommand == "import":
            return self._handle_import(args)
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

    def _handle_export(self, args: tuple[str, ...]) -> CommandResult:
        """Validate and execute `/persona export <name> [path]`.

        Args:
            args: Remaining arguments.

        Returns:
            Deterministic command result.
        """
        if len(args) not in {1, 2}:
            return CommandResult.error(
                "Error: /persona export requires <name> and optional <path>.",
                code="invalid_args",
                data={"command": "persona"},
            )
        persona_id = args[0].strip().lower()
        with_path_arg_count = 2
        destination = (
            Path(args[1]).expanduser()
            if len(args) == with_path_arg_count
            else Path(f"{persona_id}.persona.md")
        )
        try:
            written = self._repository.export_persona(
                persona_id=persona_id,
                destination=destination,
            )
        except PersonaRepositoryError as exc:
            return CommandResult.error(
                f"Error: {exc}",
                code="persona_export_failed",
            )
        return CommandResult.ok(
            f"Exported persona '{persona_id}' to {written}.",
            code="persona_exported",
            data={"persona": persona_id, "path": str(written)},
        )

    def _handle_import(self, args: tuple[str, ...]) -> CommandResult:
        """Validate and execute `/persona import <path>`.

        Args:
            args: Remaining arguments.

        Returns:
            Deterministic command result.
        """
        if len(args) != 1:
            return CommandResult.error(
                "Error: /persona import requires exactly one file path.",
                code="invalid_args",
                data={"command": "persona"},
            )
        source = Path(args[0]).expanduser()
        try:
            imported = self._repository.import_persona(source=source)
        except PersonaRepositoryError as exc:
            return CommandResult.error(
                f"Error: {exc}",
                code="persona_import_failed",
            )
        return CommandResult.ok(
            f"Imported persona '{imported.persona_id}' from {source}.",
            code="persona_imported",
            data={
                "persona": imported.persona_id,
                "summary": imported.summary,
                "style": imported.default_style.value,
                "source": str(source),
            },
        )

    @staticmethod
    def _invalid_subcommand_error(subcommand: str | None) -> CommandResult:
        """Build deterministic invalid-subcommand error result.

        Args:
            subcommand: Optional invalid subcommand token.

        Returns:
            Deterministic command error envelope.
        """
        if subcommand is None:
            message = (
                "Error: /persona requires one subcommand: list|use|show|export|import."
            )
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
        rows = []
        for profile in catalog.personas:
            marker = "*" if profile.persona_id == session.active_agent else " "
            lines.append(f"{marker} {profile.persona_id} - {profile.summary}")
            rows.append(
                {
                    "persona": profile.persona_id,
                    "summary": profile.summary,
                    "default_style": profile.default_style.value,
                    "active": profile.persona_id == session.active_agent,
                }
            )
        return CommandResult.ok(
            "\n".join(lines),
            code="persona_listed",
            data={
                "count": len(catalog.personas),
                "active": session.active_agent,
                "personas": rows,
            },
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
                "summary": profile.summary,
                "instructions": profile.instructions,
            },
        )
