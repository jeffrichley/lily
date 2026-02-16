"""Handler for /memory subcommands."""

from __future__ import annotations

from pathlib import Path

from lily.commands.handlers._memory_support import resolve_memory_root
from lily.commands.parser import CommandCall
from lily.commands.types import CommandResult
from lily.memory import (
    FileBackedPersonalityMemoryRepository,
    MemoryError,
    MemoryQuery,
    MemoryRecord,
)
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
        validation_error = self._validate_subcommand(call.args)
        if validation_error is not None:
            return validation_error
        return self._show(session, call.args[1:])

    @staticmethod
    def _validate_subcommand(args: tuple[str, ...]) -> CommandResult | None:
        """Validate `/memory` subcommand token.

        Args:
            args: Parsed command arguments.

        Returns:
            Validation error result when invalid, else None.
        """
        if not args:
            return CommandResult.error(
                "Error: /memory requires subcommand 'show'.",
                code="invalid_args",
                data={"command": "memory"},
            )
        if args[0] == "show":
            return None
        return CommandResult.error(
            f"Error: unsupported /memory subcommand '{args[0]}'.",
            code="invalid_args",
            data={"command": "memory", "subcommand": args[0]},
        )

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
        records, error = self._query_records(root_dir=root, query=query)
        if error is not None:
            return error
        assert records is not None
        return self._render_records(query=query, records=records)

    @staticmethod
    def _query_records(
        *,
        root_dir: Path,
        query: str,
    ) -> tuple[tuple[MemoryRecord, ...] | None, CommandResult | None]:
        """Query personality memory records with deterministic error mapping.

        Args:
            root_dir: Memory store root directory.
            query: Query text.

        Returns:
            Tuple of records-or-none and error-or-none.
        """
        repository = FileBackedPersonalityMemoryRepository(root_dir=root_dir)
        try:
            records = repository.query(
                MemoryQuery(query=query, namespace="global", limit=10)
            )
        except MemoryError as exc:
            return None, CommandResult.error(f"Error: {exc}", code=exc.code.value)
        return records, None

    @staticmethod
    def _render_records(query: str, records: tuple[MemoryRecord, ...]) -> CommandResult:
        """Render query results into command envelope.

        Args:
            query: Query text.
            records: Memory records tuple.

        Returns:
            Success result with empty/listed variant.
        """
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
            data={
                "count": len(records),
                "query": query,
                "records": [
                    {
                        "id": record.id,
                        "namespace": record.namespace,
                        "content": record.content,
                        "updated_at": record.updated_at.isoformat(),
                    }
                    for record in records
                ],
            },
        )
