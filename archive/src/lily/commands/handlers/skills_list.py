"""Handler for /skills."""

from __future__ import annotations

from lily.commands.parser import CommandCall
from lily.commands.types import CommandResult
from lily.session.models import Session
from lily.skills.types import SkillDiagnostic


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
        diagnostics = tuple(session.skill_snapshot.diagnostics)
        diagnostics_count = len(diagnostics)
        if not entries:
            message = self._empty_snapshot_message(diagnostics)
            return CommandResult.ok(
                message,
                code="skills_empty",
                data={"count": 0, "diagnostics_count": diagnostics_count},
            )

        lines = [_format_skill_line(entry.name, entry.summary) for entry in entries]
        lines.extend(self._diagnostics_lines(diagnostics))
        return CommandResult.ok(
            "\n".join(lines),
            code="skills_listed",
            data={"count": len(entries), "diagnostics_count": diagnostics_count},
        )

    @staticmethod
    def _diagnostics_lines(diagnostics: tuple[SkillDiagnostic, ...]) -> list[str]:
        """Render optional diagnostics section lines for `/skills` output.

        Args:
            diagnostics: Snapshot diagnostics to render.

        Returns:
            Deterministic diagnostics section lines.
        """
        if not diagnostics:
            return []
        lines = ["", "Diagnostics:"]
        lines.extend(
            f"- {diag.skill_name} [{diag.code}] {diag.message}" for diag in diagnostics
        )
        return lines

    @staticmethod
    def _empty_snapshot_message(diagnostics: tuple[SkillDiagnostic, ...]) -> str:
        """Build deterministic empty-snapshot message with optional diagnostics.

        Args:
            diagnostics: Snapshot diagnostics to render.

        Returns:
            Deterministic empty snapshot message.
        """
        if not diagnostics:
            return "No skills available in snapshot."
        return "No skills available in snapshot.\n\nDiagnostics:\n" + "\n".join(
            f"- {diag.skill_name} [{diag.code}] {diag.message}" for diag in diagnostics
        )
