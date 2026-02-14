"""Handler for /reload_skills."""

from __future__ import annotations

from lily.commands.parser import CommandCall
from lily.commands.types import CommandResult
from lily.session.models import Session
from lily.skills.loader import SkillSnapshotRequest, build_skill_snapshot


class ReloadSkillsCommand:
    """Deterministic `/reload_skills` command handler."""

    def execute(self, call: CommandCall, session: Session) -> CommandResult:
        """Rebuild and replace the current session skill snapshot.

        Args:
            call: Parsed command call.
            session: Session containing current snapshot and reload config.

        Returns:
            Deterministic success/error result.
        """
        if call.args:
            return CommandResult.error(
                "Error: /reload_skills does not accept arguments."
            )

        config = session.skill_snapshot_config
        if config is None:
            return CommandResult.error(
                "Error: /reload_skills is unavailable for this session."
            )

        snapshot = build_skill_snapshot(
            SkillSnapshotRequest(
                bundled_dir=config.bundled_dir,
                workspace_dir=config.workspace_dir,
                user_dir=config.user_dir,
                reserved_commands=set(config.reserved_commands),
                available_tools=(
                    set(config.available_tools)
                    if config.available_tools is not None
                    else None
                ),
                platform=config.platform,
                env=config.env,
            )
        )
        session.skill_snapshot = snapshot
        return CommandResult.ok(
            
                f"Reloaded skills for current session. "
                f"version={snapshot.version} count={len(snapshot.skills)}"
            
        )
