"""Argument flag parsing helpers for `/memory` commands."""

from __future__ import annotations

from lily.commands.types import CommandResult


def parse_optional_flag(
    *,
    args: tuple[str, ...],
    flag: str,
) -> tuple[str | None, tuple[str, ...], CommandResult | None]:
    """Parse one optional `--flag value` pair from command tokens.

    Args:
        args: Raw command argument tuple.
        flag: Flag token to parse.

    Returns:
        Tuple of parsed value (or None), remaining args, and optional error result.
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


def parse_required_flag(
    *,
    args: tuple[str, ...],
    flag: str,
) -> tuple[str | None, tuple[str, ...], CommandResult | None]:
    """Parse one required `--flag value` pair from command tokens.

    Args:
        args: Raw command argument tuple.
        flag: Flag token to parse.

    Returns:
        Tuple of parsed value, remaining args, and optional error result.
    """
    value, remaining, error = parse_optional_flag(args=args, flag=flag)
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


def consume_bool_flag(
    *,
    args: tuple[str, ...],
    flag: str,
) -> tuple[bool, tuple[str, ...]]:
    """Consume boolean flag token when present.

    Args:
        args: Raw command argument tuple.
        flag: Boolean flag token.

    Returns:
        Tuple of presence flag and remaining args.
    """
    tokens = list(args)
    if flag not in tokens:
        return False, tuple(tokens)
    tokens.remove(flag)
    return True, tuple(tokens)
