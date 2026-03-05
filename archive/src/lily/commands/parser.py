"""Deterministic slash command parser."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class CommandParseError(ValueError):
    """Raised when slash command syntax is invalid."""


class ParsedInputKind(StrEnum):
    """Input classification from the deterministic parser."""

    COMMAND = "command"
    CONVERSATION = "conversation"


class CommandCall(BaseModel):
    """Normalized slash command call."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    args: tuple[str, ...] = ()
    raw: str


class ParsedInput(BaseModel):
    """Result of parsing one line of user input."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: ParsedInputKind
    command: CommandCall | None = None


def parse_input(text: str) -> ParsedInput:
    """Parse input into deterministic command vs conversation routes.

    Args:
        text: Raw user input string.

    Returns:
        Parsed input classification with optional normalized command data.

    Raises:
        CommandParseError: If slash command syntax is invalid.
    """
    if not text.startswith("/"):
        return ParsedInput(kind=ParsedInputKind.CONVERSATION)

    stripped = text.strip()
    if stripped == "/":
        raise CommandParseError("Error: command name is required after '/'.")

    body = stripped[1:].strip()
    if not body:
        raise CommandParseError("Error: command name is required after '/'.")

    parts = body.split()
    command_name = parts[0]
    args = tuple(parts[1:])
    command = CommandCall(name=command_name, args=args, raw=text)
    return ParsedInput(kind=ParsedInputKind.COMMAND, command=command)
