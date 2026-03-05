"""Top-level `/memory` command router."""

from __future__ import annotations

from collections.abc import Callable

from lily.commands.handlers._memory_support import (
    build_evidence_namespace,
    build_evidence_repository,
    build_personality_namespace,
    build_personality_repository,
)
from lily.commands.handlers.memory_evidence import (
    run_evidence_ingest,
    run_evidence_show,
)
from lily.commands.handlers.memory_long import MemoryLongCommand
from lily.commands.handlers.memory_ops import query_personality, render_records
from lily.commands.parser import CommandCall
from lily.commands.types import CommandResult
from lily.memory import ConsolidationBackend, EvidenceChunkingSettings
from lily.session.models import Session

RouteHandler = Callable[[Session, tuple[str, ...]], CommandResult]


class MemoryCommand:
    """Deterministic `/memory` command handler."""

    def __init__(  # noqa: PLR0913
        self,
        *,
        tooling_enabled: bool = False,
        tooling_auto_apply: bool = False,
        consolidation_enabled: bool = False,
        consolidation_backend: ConsolidationBackend = ConsolidationBackend.RULE_BASED,
        consolidation_llm_assisted_enabled: bool = False,
        evidence_chunking: EvidenceChunkingSettings | None = None,
    ) -> None:
        """Create memory command router with delegated long-memory handler.

        Args:
            tooling_enabled: Whether LangMem tooling routes are enabled.
            tooling_auto_apply: Whether standard long-show paths use LangMem search.
            consolidation_enabled: Whether consolidation pipeline is enabled.
            consolidation_backend: Consolidation backend selection.
            consolidation_llm_assisted_enabled: LLM-assisted path toggle.
            evidence_chunking: Evidence chunking settings.
        """
        self._evidence_chunking = evidence_chunking or EvidenceChunkingSettings()
        self._long_command = MemoryLongCommand(
            tooling_enabled=tooling_enabled,
            tooling_auto_apply=tooling_auto_apply,
            consolidation_enabled=consolidation_enabled,
            consolidation_backend=consolidation_backend,
            consolidation_llm_assisted_enabled=consolidation_llm_assisted_enabled,
        )

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
        handlers: dict[str, RouteHandler] = {
            "show": self._legacy_show,
            "short": self._run_short,
            "long": self._run_long,
            "evidence": self._run_evidence,
        }
        handler = handlers.get(head)
        if handler is None:
            return CommandResult.error(
                f"Error: unsupported /memory subcommand '{head}'.",
                code="invalid_args",
                data={"command": "memory", "subcommand": head},
            )
        return handler(session, call.args[1:])

    def _legacy_show(self, session: Session, args: tuple[str, ...]) -> CommandResult:
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
        records, error = query_personality(
            repository=repository,
            namespace=namespace,
            query=query,
        )
        if error is not None:
            return error
        assert records is not None
        return render_records(
            query=query,
            records=records,
            empty_message="No personality memory records found.",
        )

    def _run_short(self, session: Session, args: tuple[str, ...]) -> CommandResult:
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

    def _run_long(self, session: Session, args: tuple[str, ...]) -> CommandResult:
        """Delegate `/memory long ...` routes to long-memory strategy handler.

        Args:
            session: Active session.
            args: Long-memory tokens.

        Returns:
            Deterministic command result.
        """
        return self._long_command.run(session=session, args=args)

    def _run_evidence(self, session: Session, args: tuple[str, ...]) -> CommandResult:
        """Execute `/memory evidence show|ingest` command family.

        Args:
            session: Active session.
            args: Evidence-memory tokens.

        Returns:
            Deterministic command result.
        """
        repository = build_evidence_repository(
            session,
            chunking=self._evidence_chunking,
        )
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
        handlers: dict[str, RouteHandler] = {
            "ingest": lambda _session, route_args: run_evidence_ingest(
                repository=repository,
                namespace=namespace,
                args=route_args,
            ),
            "show": lambda _session, route_args: run_evidence_show(
                repository=repository,
                namespace=namespace,
                args=route_args,
            ),
        }
        handler = handlers.get(head)
        if handler is None:
            return CommandResult.error(
                f"Error: unsupported /memory evidence subcommand '{head}'.",
                code="invalid_args",
                data={"command": "memory", "subcommand": "evidence"},
            )
        return handler(session, args[1:])
