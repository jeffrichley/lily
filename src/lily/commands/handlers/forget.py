"""Handler for /forget."""

from __future__ import annotations

from lily.commands.handlers._memory_support import build_personality_repository
from lily.commands.parser import CommandCall
from lily.commands.types import CommandResult
from lily.memory import MemoryError
from lily.session.models import Session


class ForgetCommand:
    """Deterministic `/forget` command handler."""

    def execute(self, call: CommandCall, session: Session) -> CommandResult:
        """Delete one personality-memory record by id.

        Args:
            call: Parsed command call.
            session: Active session.

        Returns:
            Deterministic success/error envelope.
        """
        if len(call.args) != 1:
            return CommandResult.error(
                "Error: /forget requires exactly one memory id.",
                code="invalid_args",
                data={"command": "forget"},
            )
        repository = build_personality_repository(session)
        if repository is None:
            return CommandResult.error(
                "Error: /forget is unavailable for this session.",
                code="memory_unavailable",
            )
        memory_id = call.args[0].strip()
        try:
            repository.forget(memory_id)
        except MemoryError as exc:
            return CommandResult.error(
                f"Error: {exc}",
                code=exc.code.value,
            )
        return CommandResult.ok(
            f"Forgot memory record '{memory_id}'.",
            code="memory_deleted",
            data={"id": memory_id},
        )
