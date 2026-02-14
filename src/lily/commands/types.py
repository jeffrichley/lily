"""Shared command-domain types."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

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
    message: str

    @classmethod
    def ok(cls, message: str) -> CommandResult:
        """Construct a successful command result.

        Args:
            message: User-facing output payload.

        Returns:
            Successful command result.
        """
        return cls(status=CommandStatus.OK, message=message)

    @classmethod
    def error(cls, message: str) -> CommandResult:
        """Construct an error command result.

        Args:
            message: User-facing error payload.

        Returns:
            Error command result.
        """
        return cls(status=CommandStatus.ERROR, message=message)


class CommandHandler(Protocol):
    """Protocol implemented by deterministic command handlers."""

    def execute(self, call: CommandCall, session: Session) -> CommandResult:
        """Execute command call against snapshot-bound session state.

        Args:
            call: Normalized slash command call.
            session: Session to read deterministic state from.
        """
