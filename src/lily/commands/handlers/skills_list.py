"""Handler for /skills."""

from __future__ import annotations

from lily.commands.parser import CommandCall
from lily.commands.types import CommandResult
from lily.session.models import Session


def _format_skill_line(name: str, summary: str) -> str:
    """Format one skill line for deterministic output.

    Args:
        name: Skill name.
        summary: Skill summary text.

    Returns:
        Formatted display line.
    """
    if not summary:
        return name
    return f"{name} - {summary}"


class SkillsListCommand:
    """Deterministic `/skills` command handler."""

    def execute(self, call: CommandCall, session: Session) -> CommandResult:
        """Render snapshot skills in deterministic order.

        Args:
            call: Parsed command call.
            session: Session containing immutable skill snapshot.

        Returns:
            Command result with deterministic skill list output.
        """
        if call.args:
            return CommandResult.error(
                "Error: /skills does not accept arguments.",
                code="invalid_args",
                data={"command": "skills"},
            )

        entries = sorted(session.skill_snapshot.skills, key=lambda entry: entry.name)
        if not entries:
            return CommandResult.ok(
                "No skills available in snapshot.",
                code="skills_empty",
                data={"count": 0},
            )

        lines = [_format_skill_line(entry.name, entry.summary) for entry in entries]
        return CommandResult.ok(
            "\n".join(lines),
            code="skills_listed",
            data={"count": len(entries)},
        )
