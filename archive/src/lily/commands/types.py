"""Shared command-domain types."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict

from lily.commands.parser import CommandCall
from lily.session.models import Session


class CommandStatus(StrEnum):
    """Normalized command execution status."""

    OK = "ok"
    ERROR = "error"


class CommandResult(BaseModel):
    """Deterministic command execution result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: CommandStatus
    code: str
    message: str
    data: dict[str, Any] | None = None

    @classmethod
    def ok(
        cls,
        message: str,
        *,
        code: str = "ok",
        data: dict[str, Any] | None = None,
    ) -> CommandResult:
        """Construct a successful command result.

        Args:
            message: User-facing output payload.
            code: Stable machine-readable success code.
            data: Optional structured payload for downstream consumers.

        Returns:
            Successful command result.
        """
        return cls(status=CommandStatus.OK, code=code, message=message, data=data)

    @classmethod
    def error(
        cls,
        message: str,
        *,
        code: str = "error",
        data: dict[str, Any] | None = None,
    ) -> CommandResult:
        """Construct an error command result.

        Args:
            message: User-facing error payload.
            code: Stable machine-readable error code.
            data: Optional structured payload for downstream consumers.

        Returns:
            Error command result.
        """
        return cls(status=CommandStatus.ERROR, code=code, message=message, data=data)


class CommandHandler(Protocol):
    """Protocol implemented by deterministic command handlers."""

    def execute(self, call: CommandCall, session: Session) -> CommandResult:
        """Execute command call against snapshot-bound session state.

        Args:
            call: Normalized slash command call.
            session: Session to read deterministic state from.
        """
