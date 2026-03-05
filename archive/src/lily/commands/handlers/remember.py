"""Handler for /remember."""

from __future__ import annotations

from lily.commands.handlers._memory_support import (
    build_personality_namespace,
    build_personality_repository,
)
from lily.commands.parser import CommandCall
from lily.commands.types import CommandResult
from lily.memory import (
    MemoryError,
    MemorySource,
    MemoryWriteRequest,
)
from lily.session.models import Session


class RememberCommand:
    """Deterministic `/remember` command handler."""

    def execute(self, call: CommandCall, session: Session) -> CommandResult:
        """Persist one personality-memory fact from explicit user input.

        Args:
            call: Parsed command call.
            session: Active session.

        Returns:
            Deterministic success/error envelope.
        """
        content = " ".join(call.args).strip()
        if not content:
            return CommandResult.error(
                "Error: /remember requires memory content.",
                code="invalid_args",
                data={"command": "remember"},
            )
        repository = build_personality_repository(session)
        if repository is None:
            return CommandResult.error(
                "Error: /remember is unavailable for this session.",
                code="memory_unavailable",
            )
        namespace = build_personality_namespace(session=session, domain="user_profile")
        try:
            record = repository.remember(
                MemoryWriteRequest(
                    namespace=namespace,
                    content=content,
                    source=MemorySource.COMMAND,
                    session_id=session.session_id,
                )
            )
        except MemoryError as exc:
            return CommandResult.error(
                f"Error: {exc}",
                code=exc.code.value,
            )
        return CommandResult.ok(
            f"Remembered ({record.id}): {record.content}",
            code="memory_saved",
            data={"id": record.id, "namespace": record.namespace},
        )
