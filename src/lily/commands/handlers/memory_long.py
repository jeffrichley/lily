"""Long-memory command strategies for `/memory long ...` routes."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from lily.commands.handlers._memory_support import (
    build_personality_namespace,
    build_personality_repository,
    build_task_namespace,
    build_task_repository,
)
from lily.commands.handlers.memory_flags import (
    consume_bool_flag,
    parse_optional_flag,
    parse_required_flag,
)
from lily.commands.handlers.memory_ops import (
    build_langmem_adapter,
    find_personality_record,
    query_personality,
    query_task,
    render_consolidation_result,
    render_records,
    render_tool_rows,
)
from lily.commands.types import CommandResult
from lily.memory import (
    ConsolidationBackend,
    ConsolidationRequest,
    MemoryError,
    MemorySource,
    MemoryWriteRequest,
    RuleBasedConsolidationEngine,
)
from lily.memory.consolidation import LangMemManagerConsolidationEngine
from lily.session.models import Session

_PERSONALITY_DOMAINS = {"persona_core", "user_profile", "working_rules"}


class MemoryLongCommand:
    """Strategy router for `/memory long` command surface."""

    def __init__(
        self,
        *,
        tooling_enabled: bool,
        tooling_auto_apply: bool,
        consolidation_enabled: bool,
        consolidation_backend: ConsolidationBackend,
        consolidation_llm_assisted_enabled: bool,
    ) -> None:
        """Store long-memory feature flags and backend selection.

        Args:
            tooling_enabled: Whether LangMem tooling routes are enabled.
            tooling_auto_apply: Whether standard long-show paths use LangMem search.
            consolidation_enabled: Whether consolidation pipeline is enabled.
            consolidation_backend: Consolidation backend selection.
            consolidation_llm_assisted_enabled: LLM-assisted path toggle.
        """
        self._tooling_enabled = tooling_enabled
        self._tooling_auto_apply = tooling_auto_apply
        self._consolidation_enabled = consolidation_enabled
        self._consolidation_backend = consolidation_backend
        self._consolidation_llm_assisted_enabled = consolidation_llm_assisted_enabled

    def run(self, *, session: Session, args: tuple[str, ...]) -> CommandResult:
        """Execute `/memory long ...` command family.

        Args:
            session: Active session.
            args: Long-memory tokens.

        Returns:
            Deterministic command result.
        """
        if not args:
            return CommandResult.error(
                (
                    "Error: /memory long requires subcommand "
                    "show|task|tool|consolidate|verify."
                ),
                code="invalid_args",
                data={"command": "memory", "subcommand": "long"},
            )
        head = args[0]
        handlers: dict[str, Callable[..., CommandResult]] = {
            "show": self._run_show,
            "task": self._run_task,
            "tool": self._run_tool,
            "consolidate": self._run_consolidate,
            "verify": self._run_verify,
        }
        handler = handlers.get(head)
        if handler is None:
            return CommandResult.error(
                f"Error: unsupported /memory long subcommand '{head}'.",
                code="invalid_args",
                data={"command": "memory", "subcommand": "long"},
            )
        return handler(session=session, args=args[1:])

    def _run_consolidate(
        self,
        *,
        session: Session,
        args: tuple[str, ...],
    ) -> CommandResult:
        dry_run = "--dry-run" in args
        namespace = build_personality_namespace(session=session, domain="user_profile")
        request = ConsolidationRequest(
            session_id=session.session_id,
            history=tuple(session.conversation_state),
            personality_namespace=namespace,
            enabled=self._consolidation_enabled,
            backend=self._consolidation_backend,
            llm_assisted_enabled=self._consolidation_llm_assisted_enabled,
            dry_run=dry_run,
        )
        if self._consolidation_backend == ConsolidationBackend.RULE_BASED:
            repository = build_personality_repository(session)
            task_repository = build_task_repository(session)
            if repository is None:
                return CommandResult.error(
                    "Error: memory consolidation is unavailable for this session.",
                    code="memory_unavailable",
                )
            result = RuleBasedConsolidationEngine(
                personality_repository=repository,
                task_repository=task_repository,
            ).run(request)
            return render_consolidation_result(result)

        adapter, error = build_langmem_adapter(session)
        if error is not None:
            return error
        assert adapter is not None
        result = LangMemManagerConsolidationEngine(tooling_adapter=adapter).run(request)
        return render_consolidation_result(result)

    def _run_verify(
        self,
        *,
        session: Session,
        args: tuple[str, ...],
    ) -> CommandResult:
        repository = build_personality_repository(session)
        if repository is None:
            return CommandResult.error(
                "Error: /memory long verify is unavailable for this session.",
                code="memory_unavailable",
            )
        parsed = self._parse_verify_args(args=args)
        if isinstance(parsed, CommandResult):
            return parsed
        effective_domain, memory_id = parsed
        namespace = build_personality_namespace(
            session=session,
            domain=effective_domain,
        )
        record, query_error = find_personality_record(
            repository=repository,
            namespace=namespace,
            memory_id=memory_id,
        )
        if query_error is not None:
            return query_error
        assert record is not None
        updated = repository.remember(
            MemoryWriteRequest(
                namespace=record.namespace,
                content=record.content,
                source=MemorySource.COMMAND,
                confidence=record.confidence,
                tags=record.tags,
                preference_type=record.preference_type,
                stability=record.stability,
                task_id=record.task_id,
                session_id=session.session_id,
                status="verified",
                expires_at=record.expires_at,
                last_verified=datetime.now(UTC),
                conflict_group=record.conflict_group,
            )
        )
        return CommandResult.ok(
            f"Verified memory record '{memory_id}'.",
            code="memory_verified",
            data={"id": updated.id, "namespace": updated.namespace},
        )

    @staticmethod
    def _parse_verify_args(
        *,
        args: tuple[str, ...],
    ) -> tuple[str, str] | CommandResult:
        domain, remaining, error = parse_optional_flag(args=args, flag="--domain")
        if error is not None:
            return error
        effective_domain = domain or "user_profile"
        if effective_domain not in _PERSONALITY_DOMAINS:
            return CommandResult.error(
                (
                    "Error: /memory long verify --domain must be one of "
                    "persona_core|user_profile|working_rules."
                ),
                code="invalid_args",
                data={"domain": effective_domain},
            )
        if len(remaining) != 1 or not remaining[0].strip():
            return CommandResult.error(
                "Error: /memory long verify requires exactly one memory id.",
                code="invalid_args",
            )
        return effective_domain, remaining[0].strip()

    def _run_show(self, *, session: Session, args: tuple[str, ...]) -> CommandResult:
        repository = build_personality_repository(session)
        if repository is None:
            return CommandResult.error(
                "Error: /memory long show is unavailable for this session.",
                code="memory_unavailable",
            )
        parsed = self._parse_show_args(args=args)
        if isinstance(parsed, CommandResult):
            return parsed
        (
            effective_domain,
            query,
            include_archived,
            include_expired,
            include_conflicted,
        ) = parsed
        if self._tooling_enabled and self._tooling_auto_apply:
            return self._run_tool_show(
                session=session,
                domain=effective_domain,
                query=query,
            )
        namespace = build_personality_namespace(
            session=session,
            domain=effective_domain,
        )
        records, query_error = query_personality(
            repository=repository,
            namespace=namespace,
            query=query,
            include_archived=include_archived,
            include_expired=include_expired,
            include_conflicted=include_conflicted,
        )
        if query_error is not None:
            return query_error
        assert records is not None
        return render_records(
            query=query,
            records=records,
            empty_message="No long-term personality memory records found.",
        )

    @staticmethod
    def _parse_show_args(
        *,
        args: tuple[str, ...],
    ) -> tuple[str, str, bool, bool, bool] | CommandResult:
        """Parse args for `/memory long show [--domain <domain>] [query]`.

        Args:
            args: Raw long-show args.

        Returns:
            Parsed domain, query, include flags, or deterministic arg error.
        """
        domain, remaining, error = parse_optional_flag(args=args, flag="--domain")
        if error is not None:
            return error
        include_archived, remaining = consume_bool_flag(
            args=remaining, flag="--include-archived"
        )
        include_expired, remaining = consume_bool_flag(
            args=remaining, flag="--include-expired"
        )
        include_conflicted, remaining = consume_bool_flag(
            args=remaining, flag="--include-conflicted"
        )
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
        return (
            effective_domain,
            (" ".join(remaining).strip() or "*"),
            include_archived,
            include_expired,
            include_conflicted,
        )

    def _run_task(self, *, session: Session, args: tuple[str, ...]) -> CommandResult:
        repository = build_task_repository(session)
        if repository is None:
            return CommandResult.error(
                "Error: /memory long task is unavailable for this session.",
                code="memory_unavailable",
            )
        parsed = self._parse_long_task_show_args(args=args)
        if isinstance(parsed, CommandResult):
            return parsed
        namespace, query, include_archived, include_expired, include_conflicted = parsed
        if self._tooling_enabled and self._tooling_auto_apply:
            return self._run_tool_task_show(
                session=session,
                namespace=namespace,
                query=query,
            )
        records, query_error = query_task(
            repository=repository,
            namespace=build_task_namespace(task=namespace),
            query=query,
            include_archived=include_archived,
            include_expired=include_expired,
            include_conflicted=include_conflicted,
        )
        if query_error is not None:
            return query_error
        assert records is not None
        return render_records(
            query=query,
            records=records,
            empty_message="No long-term task memory records found.",
        )

    @staticmethod
    def _parse_long_task_show_args(
        *,
        args: tuple[str, ...],
    ) -> tuple[str, str, bool, bool, bool] | CommandResult:
        if not args or args[0] != "show":
            return CommandResult.error(
                "Error: /memory long task requires subcommand 'show'.",
                code="invalid_args",
                data={"command": "memory", "subcommand": "long task"},
            )
        namespace, remaining, error = parse_required_flag(
            args=args[1:],
            flag="--namespace",
        )
        if error is not None:
            return error
        assert namespace is not None
        include_archived, remaining = consume_bool_flag(
            args=remaining, flag="--include-archived"
        )
        include_expired, remaining = consume_bool_flag(
            args=remaining, flag="--include-expired"
        )
        include_conflicted, remaining = consume_bool_flag(
            args=remaining, flag="--include-conflicted"
        )
        return (
            namespace,
            (" ".join(remaining).strip() or "*"),
            include_archived,
            include_expired,
            include_conflicted,
        )

    def _run_tool(self, *, session: Session, args: tuple[str, ...]) -> CommandResult:
        if not self._tooling_enabled:
            return CommandResult.error(
                "Error: memory tooling is disabled. Enable it in global config.",
                code="memory_tooling_disabled",
            )
        if not args:
            return CommandResult.error(
                "Error: /memory long tool requires subcommand show|remember|task.",
                code="invalid_args",
                data={"command": "memory", "subcommand": "long tool"},
            )
        head = args[0]
        handlers: dict[str, Callable[..., CommandResult]] = {
            "show": self._run_tool_show_route,
            "remember": self._run_tool_remember_route,
            "task": self._run_tool_task_route,
        }
        handler = handlers.get(head)
        if handler is None:
            return CommandResult.error(
                f"Error: unsupported /memory long tool subcommand '{head}'.",
                code="invalid_args",
                data={"command": "memory", "subcommand": "long tool"},
            )
        return handler(session=session, args=args[1:])

    def _run_tool_show_route(
        self,
        *,
        session: Session,
        args: tuple[str, ...],
    ) -> CommandResult:
        domain, remaining, error = parse_optional_flag(args=args, flag="--domain")
        if error is not None:
            return error
        effective_domain = domain or "user_profile"
        if effective_domain not in _PERSONALITY_DOMAINS:
            return CommandResult.error(
                (
                    "Error: /memory long tool show --domain must be one of "
                    "persona_core|user_profile|working_rules."
                ),
                code="invalid_args",
                data={"domain": effective_domain},
            )
        query = " ".join(remaining).strip() or "*"
        return self._run_tool_show(
            session=session,
            domain=effective_domain,
            query=query,
        )

    def _run_tool_remember_route(
        self,
        *,
        session: Session,
        args: tuple[str, ...],
    ) -> CommandResult:
        domain, remaining, error = parse_optional_flag(args=args, flag="--domain")
        if error is not None:
            return error
        effective_domain = domain or "user_profile"
        if effective_domain not in _PERSONALITY_DOMAINS:
            return CommandResult.error(
                (
                    "Error: /memory long tool remember --domain must be one of "
                    "persona_core|user_profile|working_rules."
                ),
                code="invalid_args",
                data={"domain": effective_domain},
            )
        content = " ".join(remaining).strip()
        if not content:
            return CommandResult.error(
                "Error: /memory long tool remember requires memory content.",
                code="invalid_args",
                data={"command": "memory", "subcommand": "long tool remember"},
            )
        return self._run_tool_remember(
            session=session,
            domain=effective_domain,
            content=content,
        )

    def _run_tool_task_route(
        self,
        *,
        session: Session,
        args: tuple[str, ...],
    ) -> CommandResult:
        if not args or args[0] != "show":
            return CommandResult.error(
                "Error: /memory long tool task requires subcommand 'show'.",
                code="invalid_args",
                data={"command": "memory", "subcommand": "long tool task"},
            )
        namespace, remaining, error = parse_required_flag(
            args=args[1:],
            flag="--namespace",
        )
        if error is not None:
            return error
        assert namespace is not None
        query = " ".join(remaining).strip() or "*"
        return self._run_tool_task_show(
            session=session,
            namespace=namespace,
            query=query,
        )

    def _run_tool_show(
        self,
        *,
        session: Session,
        domain: str,
        query: str,
    ) -> CommandResult:
        adapter, error = build_langmem_adapter(session)
        if error is not None:
            return error
        assert adapter is not None
        namespace = build_personality_namespace(session=session, domain=domain)
        try:
            rows = adapter.search(
                namespace=namespace,
                query=query,
                tool_name=f"lily_memory_search_{domain}",
            )
        except MemoryError as exc:
            return CommandResult.error(f"Error: {exc}", code=exc.code.value)
        return render_tool_rows(
            query=query,
            rows=rows,
            route="langmem_search_tool",
        )

    def _run_tool_task_show(
        self,
        *,
        session: Session,
        namespace: str,
        query: str,
    ) -> CommandResult:
        adapter, error = build_langmem_adapter(session)
        if error is not None:
            return error
        assert adapter is not None
        try:
            rows = adapter.search(
                namespace=build_task_namespace(task=namespace),
                query=query,
                tool_name="lily_memory_search_task_memory",
            )
        except MemoryError as exc:
            return CommandResult.error(f"Error: {exc}", code=exc.code.value)
        return render_tool_rows(
            query=query,
            rows=rows,
            route="langmem_search_tool",
        )

    def _run_tool_remember(
        self,
        *,
        session: Session,
        domain: str,
        content: str,
    ) -> CommandResult:
        adapter, error = build_langmem_adapter(session)
        if error is not None:
            return error
        assert adapter is not None
        namespace = build_personality_namespace(session=session, domain=domain)
        try:
            key = adapter.remember(
                namespace=namespace,
                content=content,
                tool_name=f"lily_memory_manage_{domain}",
            )
        except MemoryError as exc:
            return CommandResult.error(f"Error: {exc}", code=exc.code.value)
        return CommandResult.ok(
            f"Remembered via tool ({key}): {content}",
            code="memory_langmem_saved",
            data={
                "id": key,
                "namespace": namespace,
                "route": "langmem_manage_tool",
            },
        )
