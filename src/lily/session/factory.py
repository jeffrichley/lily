"""Session factory."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from lily.session.models import ModelConfig, Session, SkillSnapshotConfig
from lily.skills.loader import SkillSnapshotRequest, build_skill_snapshot


class SessionFactoryConfig(BaseModel):
    """Configuration used by ``SessionFactory`` when creating snapshots."""

    model_config = ConfigDict(extra="forbid")

    bundled_dir: Path
    workspace_dir: Path
    user_dir: Path | None = None
    reserved_commands: set[str] = Field(default_factory=set)
    available_tools: set[str] | None = None
    platform: str | None = None
    env: dict[str, str] | None = None


class SessionFactory:
    """Construct session objects with deterministic skill snapshots."""

    def __init__(self, config: SessionFactoryConfig) -> None:
        """Store immutable configuration used to create future sessions.

        Args:
            config: Static settings for discovery roots and eligibility context.
        """
        self._config = config

    def create(
        self,
        *,
        active_agent: str = "default",
        model_config: ModelConfig | None = None,
        session_id: str | None = None,
    ) -> Session:
        """Create a new session with a stable skills snapshot.

        Args:
            active_agent: Initial active agent identifier.
            model_config: Optional model behavior override for this session.
            session_id: Optional explicit session ID.

        Returns:
            A fully initialized session with an immutable skill snapshot.
        """
        snapshot = build_skill_snapshot(
            SkillSnapshotRequest(
                bundled_dir=self._config.bundled_dir,
                workspace_dir=self._config.workspace_dir,
                user_dir=self._config.user_dir,
                reserved_commands=self._config.reserved_commands,
                available_tools=self._config.available_tools,
                platform=self._config.platform,
                env=self._config.env,
            )
        )

        payload: dict[str, object] = {
            "active_agent": active_agent,
            "skill_snapshot": snapshot,
            "model_config": model_config or ModelConfig(),
            "skill_snapshot_config": SkillSnapshotConfig(
                bundled_dir=self._config.bundled_dir,
                workspace_dir=self._config.workspace_dir,
                user_dir=self._config.user_dir,
                reserved_commands=tuple(sorted(self._config.reserved_commands)),
                available_tools=(
                    tuple(sorted(self._config.available_tools))
                    if self._config.available_tools is not None
                    else None
                ),
                platform=self._config.platform,
                env=self._config.env,
            ),
        }
        if session_id is not None:
            payload["session_id"] = session_id

        return Session(**payload)
