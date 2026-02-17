"""Handler for /memory subcommands."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from lily.commands.handlers._memory_support import (
    build_evidence_namespace,
    build_evidence_repository,
    build_personality_namespace,
    build_personality_repository,
    build_task_namespace,
    build_task_repository,
    resolve_store_file,
)
from lily.commands.parser import CommandCall
from lily.commands.types import CommandResult
from lily.memory import (
    ConsolidationBackend,
    ConsolidationRequest,
    ConsolidationResult,
    FileBackedEvidenceRepository,
    LangMemManagerConsolidationEngine,
    MemoryError,
    MemoryQuery,
    MemoryRecord,
    MemorySource,
    MemoryWriteRequest,
    PersonalityMemoryRepository,
    RuleBasedConsolidationEngine,
    TaskMemoryRepository,
)
from lily.memory.langmem_tools import LangMemToolingAdapter
from lily.session.models import Session

_PERSONALITY_DOMAINS = {"persona_core", "user_profile", "working_rules"}


class MemoryCommand:
    """Deterministic `/memory` command handler."""

    def __init__(
        self,
        *,
        tooling_enabled: bool = False,
        tooling_auto_apply: bool = False,
        consolidation_enabled: bool = False,
        consolidation_backend: ConsolidationBackend = ConsolidationBackend.RULE_BASED,
        consolidation_llm_assisted_enabled: bool = False,
    ) -> None:
        """Create memory command handler.

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
            return self._run_evidence(session=session, args=call.args[1:])
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

    def _run_long(  # noqa: PLR0911
        self, *, session: Session, args: tuple[str, ...]
    ) -> CommandResult:
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
        if head == "show":
            return self._run_long_show(session=session, args=args[1:])
        if head == "task":
            return self._run_long_task(session=session, args=args[1:])
        if head == "tool":
            return self._run_long_tool(session=session, args=args[1:])
        if head == "consolidate":
            return self._run_long_consolidate(session=session, args=args[1:])
        if head == "verify":
            return self._run_long_verify(session=session, args=args[1:])
        return CommandResult.error(
            f"Error: unsupported /memory long subcommand '{head}'.",
            code="invalid_args",
            data={"command": "memory", "subcommand": "long"},
        )

    def _run_long_consolidate(
        self,
        *,
        session: Session,
        args: tuple[str, ...],
    ) -> CommandResult:
        """Execute `/memory long consolidate [--dry-run]`.

        Args:
            session: Active session.
            args: Consolidation args.

        Returns:
            Deterministic command result.
        """
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
            return self._render_consolidation_result(result)
        store_file = resolve_store_file(session)
        if store_file is None:
            return CommandResult.error(
                "Error: memory consolidation is unavailable for this session.",
                code="memory_unavailable",
            )
        result = LangMemManagerConsolidationEngine(
            tooling_adapter=LangMemToolingAdapter(store_file=store_file)
        ).run(request)
        return self._render_consolidation_result(result)

    def _run_long_verify(
        self,
        *,
        session: Session,
        args: tuple[str, ...],
    ) -> CommandResult:
        """Execute `/memory long verify [--domain <domain>] <memory_id>`.

        Args:
            session: Active session.
            args: Verify command args.

        Returns:
            Deterministic command result.
        """
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
        record, query_error = self._find_personality_record(
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
        """Parse verify command args.

        Args:
            args: Verify command args.

        Returns:
            Parsed domain and memory id, or deterministic arg error.
        """
        domain, remaining, error = _parse_optional_flag(args=args, flag="--domain")
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
        if len(remaining) != 1:
            return CommandResult.error(
                "Error: /memory long verify requires exactly one memory id.",
                code="invalid_args",
            )
        memory_id = remaining[0].strip()
        if not memory_id:
            return CommandResult.error(
                "Error: /memory long verify requires exactly one memory id.",
                code="invalid_args",
            )
        return effective_domain, memory_id

    def _find_personality_record(
        self,
        *,
        repository: PersonalityMemoryRepository,
        namespace: str,
        memory_id: str,
    ) -> tuple[MemoryRecord | None, CommandResult | None]:
        """Find one personality record by id.

        Args:
            repository: Personality repository.
            namespace: Namespace path.
            memory_id: Target record id.

        Returns:
            Record and optional error tuple.
        """
        records, query_error = self._query_personality(
            repository=repository,
            namespace=namespace,
            query="*",
            include_archived=True,
            include_expired=True,
            include_conflicted=True,
            limit=20,
        )
        if query_error is not None:
            return None, query_error
        assert records is not None
        target = next((record for record in records if record.id == memory_id), None)
        if target is None:
            return None, CommandResult.error(
                f"Error: Memory record '{memory_id}' was not found.",
                code="memory_not_found",
            )
        return target, None

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
        include_archived, remaining = _consume_bool_flag(
            args=remaining, flag="--include-archived"
        )
        include_expired, remaining = _consume_bool_flag(
            args=remaining, flag="--include-expired"
        )
        include_conflicted, remaining = _consume_bool_flag(
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
        query = " ".join(remaining).strip() or "*"
        if self._tooling_enabled and self._tooling_auto_apply:
            return self._run_long_tool_show(
                session=session,
                domain=effective_domain,
                query=query,
            )
        namespace = build_personality_namespace(
            session=session,
            domain=effective_domain,
        )
        records, query_error = self._query_personality(
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
        parsed = self._parse_long_task_show_args(args=args)
        if isinstance(parsed, CommandResult):
            return parsed
        namespace, query, include_archived, include_expired, include_conflicted = parsed
        if self._tooling_enabled and self._tooling_auto_apply:
            return self._run_long_tool_task_show(
                session=session,
                namespace=namespace,
                query=query,
            )
        records, query_error = self._query_task(
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
        return self._render_records(
            query=query,
            records=records,
            empty_message="No long-term task memory records found.",
        )

    @staticmethod
    def _parse_long_task_show_args(
        *,
        args: tuple[str, ...],
    ) -> tuple[str, str, bool, bool, bool] | CommandResult:
        """Parse `/memory long task show --namespace <task> [query]` args.

        Args:
            args: Long-task raw args.

        Returns:
            Parsed namespace+query tuple, or deterministic arg error.
        """
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
        include_archived, remaining = _consume_bool_flag(
            args=remaining, flag="--include-archived"
        )
        include_expired, remaining = _consume_bool_flag(
            args=remaining, flag="--include-expired"
        )
        include_conflicted, remaining = _consume_bool_flag(
            args=remaining, flag="--include-conflicted"
        )
        return (
            namespace,
            (" ".join(remaining).strip() or "*"),
            include_archived,
            include_expired,
            include_conflicted,
        )

    def _run_long_tool(
        self, *, session: Session, args: tuple[str, ...]
    ) -> CommandResult:
        """Execute `/memory long tool ...` explicit LangMem tooling routes.

        Args:
            session: Active session.
            args: Tool route arguments.

        Returns:
            Deterministic command result.
        """
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
        if head == "show":
            return self._run_long_tool_show_route(session=session, args=args[1:])
        if head == "remember":
            return self._run_long_tool_remember_route(session=session, args=args[1:])
        if head == "task":
            return self._run_long_tool_task_route(session=session, args=args[1:])
        return CommandResult.error(
            f"Error: unsupported /memory long tool subcommand '{head}'.",
            code="invalid_args",
            data={"command": "memory", "subcommand": "long tool"},
        )

    def _run_long_tool_show_route(
        self,
        *,
        session: Session,
        args: tuple[str, ...],
    ) -> CommandResult:
        """Execute `/memory long tool show [--domain <domain>] [query]`.

        Args:
            session: Active session.
            args: Tool-show args.

        Returns:
            Deterministic command result.
        """
        domain, remaining, error = _parse_optional_flag(args=args, flag="--domain")
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
        return self._run_long_tool_show(
            session=session,
            domain=effective_domain,
            query=query,
        )

    def _run_long_tool_remember_route(
        self,
        *,
        session: Session,
        args: tuple[str, ...],
    ) -> CommandResult:
        """Execute `/memory long tool remember [--domain <domain>] <content>`.

        Args:
            session: Active session.
            args: Tool-remember args.

        Returns:
            Deterministic command result.
        """
        domain, remaining, error = _parse_optional_flag(args=args, flag="--domain")
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
        return self._run_long_tool_remember(
            session=session,
            domain=effective_domain,
            content=content,
        )

    def _run_long_tool_task_route(
        self,
        *,
        session: Session,
        args: tuple[str, ...],
    ) -> CommandResult:
        """Execute `/memory long tool task show --namespace <task> [query]`.

        Args:
            session: Active session.
            args: Tool-task args.

        Returns:
            Deterministic command result.
        """
        if not args or args[0] != "show":
            return CommandResult.error(
                "Error: /memory long tool task requires subcommand 'show'.",
                code="invalid_args",
                data={"command": "memory", "subcommand": "long tool task"},
            )
        namespace, remaining, error = _parse_required_flag(
            args=args[1:],
            flag="--namespace",
        )
        if error is not None:
            return error
        assert namespace is not None
        query = " ".join(remaining).strip() or "*"
        return self._run_long_tool_task_show(
            session=session,
            namespace=namespace,
            query=query,
        )

    def _run_long_tool_show(
        self,
        *,
        session: Session,
        domain: str,
        query: str,
    ) -> CommandResult:
        """Search personality memory via LangMem search tool.

        Args:
            session: Active session.
            domain: Personality memory domain.
            query: Query string.

        Returns:
            Deterministic command result.
        """
        adapter, error = self._build_langmem_adapter(session)
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
        return self._render_tool_rows(
            query=query,
            rows=rows,
            route="langmem_search_tool",
        )

    def _run_long_tool_task_show(
        self,
        *,
        session: Session,
        namespace: str,
        query: str,
    ) -> CommandResult:
        """Search task memory via LangMem search tool.

        Args:
            session: Active session.
            namespace: Task namespace token.
            query: Query string.

        Returns:
            Deterministic command result.
        """
        adapter, error = self._build_langmem_adapter(session)
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
        return self._render_tool_rows(
            query=query,
            rows=rows,
            route="langmem_search_tool",
        )

    def _run_long_tool_remember(
        self,
        *,
        session: Session,
        domain: str,
        content: str,
    ) -> CommandResult:
        """Persist personality memory via LangMem manage tool.

        Args:
            session: Active session.
            domain: Personality memory domain.
            content: Memory content string.

        Returns:
            Deterministic command result.
        """
        adapter, error = self._build_langmem_adapter(session)
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

    @staticmethod
    def _build_langmem_adapter(
        session: Session,
    ) -> tuple[LangMemToolingAdapter | None, CommandResult | None]:
        """Build LangMem adapter from session memory storage roots.

        Args:
            session: Active session.

        Returns:
            Adapter or deterministic error.
        """
        store_file = resolve_store_file(session)
        if store_file is None:
            return None, CommandResult.error(
                "Error: memory tooling is unavailable for this session.",
                code="memory_unavailable",
            )
        return LangMemToolingAdapter(store_file=store_file), None

    def _run_evidence(
        self,
        *,
        session: Session,
        args: tuple[str, ...],
    ) -> CommandResult:
        """Execute `/memory evidence show|ingest` command family.

        Args:
            session: Active session.
            args: Evidence-memory tokens.

        Returns:
            Deterministic command result.
        """
        repository = build_evidence_repository(session)
        if repository is None:
            return CommandResult.error(
                "Error: /memory evidence is unavailable for this session.",
                code="memory_unavailable",
            )
        if not args:
            return CommandResult.error(
                "Error: /memory evidence requires subcommand show|ingest.",
                code="invalid_args",
                data={"command": "memory", "subcommand": "evidence"},
            )
        namespace = build_evidence_namespace(session=session)
        head = args[0]
        if head == "ingest":
            return self._run_evidence_ingest(
                repository=repository,
                namespace=namespace,
                args=args[1:],
            )
        if head == "show":
            return self._run_evidence_show(
                repository=repository,
                namespace=namespace,
                args=args[1:],
            )
        return CommandResult.error(
            f"Error: unsupported /memory evidence subcommand '{head}'.",
            code="invalid_args",
            data={"command": "memory", "subcommand": "evidence"},
        )

    @staticmethod
    def _run_evidence_ingest(
        *,
        repository: FileBackedEvidenceRepository,
        namespace: str,
        args: tuple[str, ...],
    ) -> CommandResult:
        """Execute `/memory evidence ingest <path_or_ref>`.

        Args:
            repository: Evidence repository implementation.
            namespace: Evidence namespace token.
            args: Ingest args.

        Returns:
            Deterministic command result.
        """
        path_or_ref = " ".join(args).strip()
        if not path_or_ref:
            return CommandResult.error(
                "Error: /memory evidence ingest requires a path.",
                code="invalid_args",
                data={"command": "memory", "subcommand": "evidence ingest"},
            )
        try:
            rows = repository.ingest(namespace=namespace, path_or_ref=path_or_ref)
        except MemoryError as exc:
            return CommandResult.error(f"Error: {exc}", code=exc.code.value)
        return CommandResult.ok(
            f"Ingested {len(rows)} evidence chunk(s).",
            code="memory_evidence_ingested",
            data={
                "route": "semantic_evidence",
                "namespace": namespace,
                "source": path_or_ref,
                "chunks": len(rows),
                "non_canonical": True,
            },
        )

    @staticmethod
    def _run_evidence_show(
        *,
        repository: FileBackedEvidenceRepository,
        namespace: str,
        args: tuple[str, ...],
    ) -> CommandResult:
        """Execute `/memory evidence show [query]`.

        Args:
            repository: Evidence repository implementation.
            namespace: Evidence namespace token.
            args: Show args.

        Returns:
            Deterministic command result.
        """
        query = " ".join(args).strip() or "*"
        try:
            hits = repository.query(namespace=namespace, query=query, limit=10)
        except MemoryError as exc:
            return CommandResult.error(f"Error: {exc}", code=exc.code.value)
        if not hits:
            return CommandResult.ok(
                "No semantic evidence hits found.",
                code="memory_evidence_empty",
                data={
                    "query": query,
                    "records": [],
                    "route": "semantic_evidence",
                    "non_canonical": True,
                    "canonical_precedence": "structured_long_term",
                },
            )
        lines = [
            f"{hit.snippet} [{hit.citation}] (score={hit.score:.3f})" for hit in hits
        ]
        return CommandResult.ok(
            "\n".join(lines),
            code="memory_evidence_listed",
            data={
                "query": query,
                "records": [
                    {
                        "id": hit.id,
                        "namespace": hit.namespace,
                        "source": hit.source_ref,
                        "citation": hit.citation,
                        "score": hit.score,
                        "content": hit.snippet,
                    }
                    for hit in hits
                ],
                "route": "semantic_evidence",
                "non_canonical": True,
                "canonical_precedence": "structured_long_term",
            },
        )

    @staticmethod
    def _query_personality(  # noqa: PLR0913
        *,
        repository: PersonalityMemoryRepository,
        namespace: str,
        query: str,
        include_archived: bool = False,
        include_expired: bool = False,
        include_conflicted: bool = False,
        limit: int = 10,
    ) -> tuple[tuple[MemoryRecord, ...] | None, CommandResult | None]:
        """Query one personality namespace with deterministic error mapping.

        Args:
            repository: Personality repository.
            namespace: Target namespace token.
            query: Query text.
            include_archived: Whether archived records should be included.
            include_expired: Whether expired records should be included.
            include_conflicted: Whether conflicted records should be included.
            limit: Maximum number of records to return.

        Returns:
            Tuple of records-or-none and error-or-none.
        """
        try:
            records = repository.query(
                MemoryQuery(
                    query=query,
                    namespace=namespace,
                    limit=limit,
                    include_archived=include_archived,
                    include_expired=include_expired,
                    include_conflicted=include_conflicted,
                )
            )
        except MemoryError as exc:
            return None, CommandResult.error(f"Error: {exc}", code=exc.code.value)
        return records, None

    @staticmethod
    def _query_task(  # noqa: PLR0913
        *,
        repository: TaskMemoryRepository,
        namespace: str,
        query: str,
        include_archived: bool = False,
        include_expired: bool = False,
        include_conflicted: bool = False,
        limit: int = 10,
    ) -> tuple[tuple[MemoryRecord, ...] | None, CommandResult | None]:
        """Query task namespace with deterministic error mapping.

        Args:
            repository: Task repository.
            namespace: Target task namespace.
            query: Query text.
            include_archived: Whether archived records should be included.
            include_expired: Whether expired records should be included.
            include_conflicted: Whether conflicted records should be included.
            limit: Maximum number of records to return.

        Returns:
            Tuple of records-or-none and error-or-none.
        """
        try:
            records = repository.query(
                MemoryQuery(
                    query=query,
                    namespace=namespace,
                    limit=limit,
                    include_archived=include_archived,
                    include_expired=include_expired,
                    include_conflicted=include_conflicted,
                )
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
                        "status": record.status,
                        "last_verified": (
                            record.last_verified.isoformat()
                            if record.last_verified is not None
                            else None
                        ),
                        "conflict_group": record.conflict_group,
                        "expires_at": (
                            record.expires_at.isoformat()
                            if record.expires_at is not None
                            else None
                        ),
                    }
                    for record in records
                ],
            },
        )

    @staticmethod
    def _render_tool_rows(
        *,
        query: str,
        rows: tuple[dict[str, Any], ...],
        route: str,
    ) -> CommandResult:
        """Render LangMem tool search rows with deterministic envelope.

        Args:
            query: Query text.
            rows: Tool-result rows.
            route: Stable route identifier.

        Returns:
            Deterministic command result.
        """
        if not rows:
            return CommandResult.ok(
                "No memory records found.",
                code="memory_empty",
                data={"count": 0, "query": query, "route": route},
            )
        normalized: list[dict[str, object]] = []
        lines: list[str] = []
        for row in rows:
            key = str(row.get("key", "")).strip()
            value = row.get("value", {})
            content = ""
            if isinstance(value, dict):
                content = str(value.get("content", "")).strip()
            if not content:
                continue
            lines.append(f"- {key}: {content}")
            normalized.append(
                {
                    "id": key,
                    "namespace": row.get("namespace"),
                    "content": content,
                    "updated_at": row.get("updated_at"),
                }
            )
        if not normalized:
            return CommandResult.ok(
                "No memory records found.",
                code="memory_empty",
                data={"count": 0, "query": query, "route": route},
            )
        return CommandResult.ok(
            "\n".join(lines),
            code="memory_langmem_listed",
            data={
                "count": len(normalized),
                "query": query,
                "route": route,
                "records": normalized,
            },
        )

    @staticmethod
    def _render_consolidation_result(result: ConsolidationResult) -> CommandResult:
        """Render consolidation engine result into command envelope.

        Args:
            result: Consolidation result object.

        Returns:
            Deterministic command output.
        """
        status = result.status
        backend = result.backend.value
        proposed = result.proposed
        written = result.written
        skipped = result.skipped
        notes = result.notes
        records = result.records
        if status == "disabled":
            return CommandResult.error(
                "Error: consolidation is disabled by config.",
                code="memory_consolidation_disabled",
                data={"backend": backend},
            )
        summary = (
            f"Consolidation [{backend}] status={status} "
            f"proposed={proposed} written={written} skipped={skipped}"
        )
        return CommandResult.ok(
            summary,
            code="memory_consolidation_ran",
            data={
                "backend": backend,
                "status": status,
                "proposed": proposed,
                "written": written,
                "skipped": skipped,
                "notes": notes,
                "records": records,
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


def _consume_bool_flag(
    *,
    args: tuple[str, ...],
    flag: str,
) -> tuple[bool, tuple[str, ...]]:
    """Consume boolean flag token when present.

    Args:
        args: Command token tuple.
        flag: Boolean flag token.

    Returns:
        Tuple of flag presence and remaining args.
    """
    tokens = list(args)
    if flag not in tokens:
        return False, tuple(tokens)
    tokens.remove(flag)
    return True, tuple(tokens)
