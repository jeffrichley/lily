"""Handler for /help <skill>."""

from __future__ import annotations

from lily.commands.parser import CommandCall
from lily.commands.types import CommandResult
from lily.session.models import Session
from lily.skills.types import SkillEntry


def _format_list(values: tuple[str, ...]) -> str:
    """Render deterministic comma-separated list with fallback."""
    if not values:
        return "(none)"
    return ", ".join(values)


def _format_help(entry: SkillEntry) -> str:
    """Build deterministic human-readable help output for a snapshot skill."""
    lines = [
        f"# /help {entry.name}",
        "",
        f"- `name`: {entry.name}",
        f"- `summary`: {entry.summary or '(none)'}",
        f"- `source`: {entry.source.value}",
        f"- `invocation_mode`: {entry.invocation_mode.value}",
        f"- `command_alias`: {entry.command or '(none)'}",
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
        """Render snapshot metadata for one skill without executing it."""
        if len(call.args) != 1:
            return CommandResult.error("Error: /help requires exactly one skill name.")

        skill_name = call.args[0]
        target = self._find_skill(session, skill_name)
        if target is None:
            return CommandResult.error(
                f"Error: skill '{skill_name}' not found in snapshot."
            )
        return CommandResult.ok(_format_help(target))

    @staticmethod
    def _find_skill(session: Session, skill_name: str) -> SkillEntry | None:
        """Look up exact skill name from current session snapshot."""
        for entry in session.skill_snapshot.skills:
            if entry.name == skill_name:
                return entry
        return None
