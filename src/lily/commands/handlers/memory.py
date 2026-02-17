"""Handler for /memory subcommands."""

from __future__ import annotations

from lily.commands.handlers._memory_support import (
    build_personality_namespace,
    build_personality_repository,
    build_task_namespace,
    build_task_repository,
)
from lily.commands.parser import CommandCall
from lily.commands.types import CommandResult
from lily.memory import (
    MemoryError,
    MemoryQuery,
    MemoryRecord,
    PersonalityMemoryRepository,
    TaskMemoryRepository,
)
from lily.session.models import Session

_PERSONALITY_DOMAINS = {"persona_core", "user_profile", "working_rules"}


class MemoryCommand:
    """Deterministic `/memory` command handler."""

    def execute(self, call: CommandCall, session: Session) -> CommandResult:
        """Execute `/memory ...` command family.

        Args:
            call: Parsed command call.
            session: Active session.

        Returns:
            Deterministic success/error envelope.
        """
        if not call.args:
            return CommandResult.error(
                "Error: /memory requires a subcommand.",
                code="invalid_args",
                data={"command": "memory"},
            )
        head = call.args[0]
        if head == "show":
            return self._legacy_show(session=session, args=call.args[1:])
        if head == "short":
            return self._run_short(session=session, args=call.args[1:])
        if head == "long":
            return self._run_long(session=session, args=call.args[1:])
        if head == "evidence":
            return self._run_evidence(args=call.args[1:])
        return CommandResult.error(
            f"Error: unsupported /memory subcommand '{head}'.",
            code="invalid_args",
            data={"command": "memory", "subcommand": head},
        )

    def _legacy_show(self, *, session: Session, args: tuple[str, ...]) -> CommandResult:
        """Execute legacy `/memory show [query]` compatibility path.

        Args:
            session: Active session.
            args: Query tokens.

        Returns:
            Deterministic command result.
        """
        repository = build_personality_repository(session)
        if repository is None:
            return CommandResult.error(
                "Error: /memory show is unavailable for this session.",
                code="memory_unavailable",
            )
        namespace = build_personality_namespace(session=session, domain="user_profile")
        query = " ".join(args).strip() or "*"
        records, error = self._query_personality(
            repository=repository,
            namespace=namespace,
            query=query,
        )
        if error is not None:
            return error
        assert records is not None
        return self._render_records(
            query=query,
            records=records,
            empty_message="No personality memory records found.",
        )

    def _run_short(self, *, session: Session, args: tuple[str, ...]) -> CommandResult:
        """Execute `/memory short ...` command family.

        Args:
            session: Active session.
            args: Short-memory tokens.

        Returns:
            Deterministic success/error envelope.
        """
        if not args:
            return CommandResult.error(
                "Error: /memory short requires subcommand show|checkpoints.",
                code="invalid_args",
                data={"command": "memory", "subcommand": "short"},
            )
        subcommand = args[0]
        if subcommand not in {"show", "checkpoints"}:
            return CommandResult.error(
                f"Error: unsupported /memory short subcommand '{subcommand}'.",
                code="invalid_args",
                data={"command": "memory", "subcommand": "short"},
            )
        return CommandResult.ok(
            (
                "Short-term memory is checkpoint-managed for thread "
                f"'{session.session_id}'."
            ),
            code="memory_short_shown",
            data={"thread_id": session.session_id, "route": "checkpointer"},
        )

    def _run_long(self, *, session: Session, args: tuple[str, ...]) -> CommandResult:
        """Execute `/memory long ...` command family.

        Args:
            session: Active session.
            args: Long-memory tokens.

        Returns:
            Deterministic command result.
        """
        if not args:
            return CommandResult.error(
                "Error: /memory long requires subcommand show|task.",
                code="invalid_args",
                data={"command": "memory", "subcommand": "long"},
            )
        head = args[0]
        if head == "show":
            return self._run_long_show(session=session, args=args[1:])
        if head == "task":
            return self._run_long_task(session=session, args=args[1:])
        return CommandResult.error(
            f"Error: unsupported /memory long subcommand '{head}'.",
            code="invalid_args",
            data={"command": "memory", "subcommand": "long"},
        )

    def _run_long_show(
        self,
        *,
        session: Session,
        args: tuple[str, ...],
    ) -> CommandResult:
        """Execute `/memory long show [--domain <domain>] [query]`.

        Args:
            session: Active session.
            args: Long-show tokens.

        Returns:
            Deterministic command result.
        """
        repository = build_personality_repository(session)
        if repository is None:
            return CommandResult.error(
                "Error: /memory long show is unavailable for this session.",
                code="memory_unavailable",
            )
        domain, remaining, error = _parse_optional_flag(args=args, flag="--domain")
        if error is not None:
            return error
        effective_domain = domain or "user_profile"
        if effective_domain not in _PERSONALITY_DOMAINS:
            return CommandResult.error(
                (
                    "Error: /memory long show --domain must be one of "
                    "persona_core|user_profile|working_rules."
                ),
                code="invalid_args",
                data={"domain": effective_domain},
            )
        query = " ".join(remaining).strip() or "*"
        namespace = build_personality_namespace(
            session=session,
            domain=effective_domain,
        )
        records, query_error = self._query_personality(
            repository=repository,
            namespace=namespace,
            query=query,
        )
        if query_error is not None:
            return query_error
        assert records is not None
        return self._render_records(
            query=query,
            records=records,
            empty_message="No long-term personality memory records found.",
        )

    def _run_long_task(
        self,
        *,
        session: Session,
        args: tuple[str, ...],
    ) -> CommandResult:
        """Execute `/memory long task show --namespace <task> [query]`.

        Args:
            session: Active session.
            args: Task-memory tokens.

        Returns:
            Deterministic command result.
        """
        repository = build_task_repository(session)
        if repository is None:
            return CommandResult.error(
                "Error: /memory long task is unavailable for this session.",
                code="memory_unavailable",
            )
        if not args or args[0] != "show":
            return CommandResult.error(
                "Error: /memory long task requires subcommand 'show'.",
                code="invalid_args",
                data={"command": "memory", "subcommand": "long task"},
            )
        namespace, remaining, error = _parse_required_flag(
            args=args[1:],
            flag="--namespace",
        )
        if error is not None:
            return error
        assert namespace is not None
        query = " ".join(remaining).strip() or "*"
        records, query_error = self._query_task(
            repository=repository,
            namespace=build_task_namespace(task=namespace),
            query=query,
        )
        if query_error is not None:
            return query_error
        assert records is not None
        return self._render_records(
            query=query,
            records=records,
            empty_message="No long-term task memory records found.",
        )

    @staticmethod
    def _run_evidence(args: tuple[str, ...]) -> CommandResult:
        """Execute `/memory evidence ...` placeholder path.

        Args:
            args: Evidence-memory tokens.

        Returns:
            Deterministic placeholder result.
        """
        if not args or args[0] != "show":
            return CommandResult.error(
                "Error: /memory evidence currently supports only 'show'.",
                code="invalid_args",
                data={"command": "memory", "subcommand": "evidence"},
            )
        return CommandResult.ok(
            "Semantic evidence memory is not enabled yet.",
            code="memory_evidence_unavailable",
            data={"route": "placeholder"},
        )

    @staticmethod
    def _query_personality(
        *,
        repository: PersonalityMemoryRepository,
        namespace: str,
        query: str,
    ) -> tuple[tuple[MemoryRecord, ...] | None, CommandResult | None]:
        """Query one personality namespace with deterministic error mapping.

        Args:
            repository: Personality repository.
            namespace: Target namespace token.
            query: Query text.

        Returns:
            Tuple of records-or-none and error-or-none.
        """
        try:
            records = repository.query(
                MemoryQuery(query=query, namespace=namespace, limit=10)
            )
        except MemoryError as exc:
            return None, CommandResult.error(f"Error: {exc}", code=exc.code.value)
        return records, None

    @staticmethod
    def _query_task(
        *,
        repository: TaskMemoryRepository,
        namespace: str,
        query: str,
    ) -> tuple[tuple[MemoryRecord, ...] | None, CommandResult | None]:
        """Query task namespace with deterministic error mapping.

        Args:
            repository: Task repository.
            namespace: Target task namespace.
            query: Query text.

        Returns:
            Tuple of records-or-none and error-or-none.
        """
        try:
            records = repository.query(
                MemoryQuery(query=query, namespace=namespace, limit=10)
            )
        except MemoryError as exc:
            return None, CommandResult.error(f"Error: {exc}", code=exc.code.value)
        return records, None

    @staticmethod
    def _render_records(
        *,
        query: str,
        records: tuple[MemoryRecord, ...],
        empty_message: str,
    ) -> CommandResult:
        """Render query results into deterministic command envelope.

        Args:
            query: Query text.
            records: Memory records tuple.
            empty_message: Message used when no records are present.

        Returns:
            Success result with empty/listed variant.
        """
        if not records:
            return CommandResult.ok(
                empty_message,
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


def _parse_optional_flag(
    *,
    args: tuple[str, ...],
    flag: str,
) -> tuple[str | None, tuple[str, ...], CommandResult | None]:
    """Parse one optional `--flag value` pair from command tokens.

    Args:
        args: Command token tuple.
        flag: Flag token.

    Returns:
        Tuple of value-or-none, remaining tokens, and optional validation error.
    """
    tokens = list(args)
    if flag not in tokens:
        return None, tuple(tokens), None
    index = tokens.index(flag)
    if index + 1 >= len(tokens):
        return (
            None,
            tuple(tokens),
            CommandResult.error(
                f"Error: {flag} requires a value.",
                code="invalid_args",
            ),
        )
    value = tokens[index + 1].strip()
    if not value:
        return (
            None,
            tuple(tokens),
            CommandResult.error(
                f"Error: {flag} requires a value.",
                code="invalid_args",
            ),
        )
    del tokens[index : index + 2]
    return value, tuple(tokens), None


def _parse_required_flag(
    *,
    args: tuple[str, ...],
    flag: str,
) -> tuple[str | None, tuple[str, ...], CommandResult | None]:
    """Parse one required `--flag value` pair from command tokens.

    Args:
        args: Command token tuple.
        flag: Flag token.

    Returns:
        Tuple of parsed value-or-none, remaining tokens, and optional error.
    """
    value, remaining, error = _parse_optional_flag(args=args, flag=flag)
    if error is not None:
        return None, remaining, error
    if value is not None:
        return value, remaining, None
    return (
        None,
        remaining,
        CommandResult.error(
            f"Error: {flag} is required.",
            code="invalid_args",
        ),
    )
