"""Handler for /memory subcommands."""

from __future__ import annotations

from lily.commands.handlers._memory_support import resolve_memory_root
from lily.commands.parser import CommandCall
from lily.commands.types import CommandResult
from lily.memory import FileBackedPersonalityMemoryRepository, MemoryError, MemoryQuery
from lily.session.models import Session


class MemoryCommand:
    """Deterministic `/memory` command handler."""

    def execute(self, call: CommandCall, session: Session) -> CommandResult:
        """Execute `/memory show [query]` subcommand.

        Args:
            call: Parsed command call.
            session: Active session.

        Returns:
            Deterministic success/error envelope.
        """
        if not call.args:
            return CommandResult.error(
                "Error: /memory requires subcommand 'show'.",
                code="invalid_args",
                data={"command": "memory"},
            )
        if call.args[0] != "show":
            return CommandResult.error(
                f"Error: unsupported /memory subcommand '{call.args[0]}'.",
                code="invalid_args",
                data={"command": "memory", "subcommand": call.args[0]},
            )
        return self._show(session, call.args[1:])

    def _show(self, session: Session, args: tuple[str, ...]) -> CommandResult:
        """Render personality memory records for query.

        Args:
            session: Active session.
            args: Remaining show arguments.

        Returns:
            Deterministic success/error envelope.
        """
        root = resolve_memory_root(session)
        if root is None:
            return CommandResult.error(
                "Error: /memory show is unavailable for this session.",
                code="memory_unavailable",
            )
        query = " ".join(args).strip() or "*"
        repository = FileBackedPersonalityMemoryRepository(root_dir=root)
        try:
            records = repository.query(
                MemoryQuery(query=query, namespace="global", limit=10)
            )
        except MemoryError as exc:
            return CommandResult.error(
                f"Error: {exc}",
                code=exc.code.value,
            )
        if not records:
            return CommandResult.ok(
                "No personality memory records found.",
                code="memory_empty",
                data={"count": 0, "query": query},
            )
        lines = [f"- {record.id}: {record.content}" for record in records]
        return CommandResult.ok(
            "\n".join(lines),
            code="memory_listed",
            data={"count": len(records), "query": query},
        )
