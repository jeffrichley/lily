"""Handler for /help <skill>."""

from __future__ import annotations

from lily.commands.parser import CommandCall
from lily.commands.types import CommandResult
from lily.session.models import Session
from lily.skills.types import SkillEntry


def _format_list(values: tuple[str, ...]) -> str:
    """Render deterministic comma-separated list with fallback.

    Args:
        values: Tuple of string values to render.

    Returns:
        Comma-separated display string or `(none)`.
    """
    if not values:
        return "(none)"
    return ", ".join(values)


def _format_help(entry: SkillEntry) -> str:
    """Build deterministic human-readable help output for a snapshot skill.

    Args:
        entry: Snapshot skill entry to describe.

    Returns:
        Markdown text describing the skill.
    """
    lines = [
        f"# /help {entry.name}",
        "",
        f"- `name`: {entry.name}",
        f"- `summary`: {entry.summary or '(none)'}",
        f"- `source`: {entry.source.value}",
        f"- `invocation_mode`: {entry.invocation_mode.value}",
        f"- `command_alias`: {entry.command or '(none)'}",
        f"- `command_tool_provider`: {entry.command_tool_provider}",
        f"- `command_tool`: {entry.command_tool or '(none)'}",
        f"- `requires_tools`: {_format_list(entry.requires_tools)}",
        "- `eligibility`:",
        f"  - `os`: {_format_list(entry.eligibility.os)}",
        f"  - `env`: {_format_list(entry.eligibility.env)}",
        f"  - `binaries`: {_format_list(entry.eligibility.binaries)}",
    ]
    return "\n".join(lines)


class HelpSkillCommand:
    """Deterministic `/help <skill>` command handler."""

    def execute(self, call: CommandCall, session: Session) -> CommandResult:
        """Render snapshot metadata for one skill without executing it.

        Args:
            call: Parsed command call.
            session: Session containing the current skill snapshot.

        Returns:
            Deterministic success/error result.
        """
        if len(call.args) != 1:
            return CommandResult.error(
                "Error: /help requires exactly one skill name.",
                code="invalid_args",
                data={"command": "help"},
            )

        skill_name = call.args[0]
        target = self._find_skill(session, skill_name)
        if target is None:
            return CommandResult.error(
                f"Error: skill '{skill_name}' not found in snapshot.",
                code="skill_not_found",
                data={"skill": skill_name},
            )
        return CommandResult.ok(
            _format_help(target),
            code="skill_help",
            data={"skill": target.name},
        )

    @staticmethod
    def _find_skill(session: Session, skill_name: str) -> SkillEntry | None:
        """Look up exact skill name from current session snapshot.

        Args:
            session: Session to query.
            skill_name: Exact skill name.

        Returns:
            Matching skill entry or None.
        """
        for entry in session.skill_snapshot.skills:
            if entry.name == skill_name:
                return entry
        return None
