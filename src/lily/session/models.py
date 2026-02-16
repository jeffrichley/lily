"""Session models."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from lily.prompting import PersonaStyleLevel
from lily.skills.types import SkillSnapshot


class MessageRole(StrEnum):
    """Supported conversation roles."""

    USER = "user"
    SYSTEM = "system"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Message(BaseModel):
    """Single conversation event."""

    model_config = ConfigDict(extra="forbid")

    role: MessageRole
    content: str


class ToolLoopLimitConfig(BaseModel):
    """Tool-loop boundary settings for conversation turns."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    max_rounds: int = 8

    @model_validator(mode="after")
    def _validate_enabled_range(self) -> ToolLoopLimitConfig:
        """Validate max rounds when the limit is enabled.

        Returns:
            Validated config model.

        Raises:
            ValueError: If enabled but `max_rounds` is less than one.
        """
        if self.enabled and self.max_rounds < 1:
            raise ValueError("max_rounds must be >= 1 when enabled is true.")
        return self


class TurnTimeoutLimitConfig(BaseModel):
    """Turn timeout settings for conversation execution."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    timeout_ms: int = 30_000

    @model_validator(mode="after")
    def _validate_enabled_range(self) -> TurnTimeoutLimitConfig:
        """Validate timeout milliseconds when the limit is enabled.

        Returns:
            Validated config model.

        Raises:
            ValueError: If enabled but `timeout_ms` is less than one.
        """
        if self.enabled and self.timeout_ms < 1:
            raise ValueError("timeout_ms must be >= 1 when enabled is true.")
        return self


class RetryLimitConfig(BaseModel):
    """Retry-limit settings for conversation execution failures."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    max_retries: int = 1

    @model_validator(mode="after")
    def _validate_enabled_range(self) -> RetryLimitConfig:
        """Validate retry count when retries are enabled.

        Returns:
            Validated config model.

        Raises:
            ValueError: If enabled but `max_retries` is negative.
        """
        if self.enabled and self.max_retries < 0:
            raise ValueError("max_retries must be >= 0 when enabled is true.")
        return self


class ConversationLimitsConfig(BaseModel):
    """User-facing conversation/tool loop limit configuration."""

    model_config = ConfigDict(extra="forbid")

    tool_loop: ToolLoopLimitConfig = Field(default_factory=ToolLoopLimitConfig)
    timeout: TurnTimeoutLimitConfig = Field(default_factory=TurnTimeoutLimitConfig)
    retries: RetryLimitConfig = Field(default_factory=RetryLimitConfig)


class ModelConfig(BaseModel):
    """Session-scoped model behavior configuration."""

    model_config = ConfigDict(extra="forbid")

    model_name: str = "default"
    temperature: float = 0.0
    thinking_level: str | None = None
    verbose: bool = False
    conversation_limits: ConversationLimitsConfig = Field(
        default_factory=ConversationLimitsConfig
    )


class Session(BaseModel):
    """Stable execution context for one conversation session."""

    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(default_factory=lambda: str(uuid4()))
    active_agent: str = "default"
    active_style: PersonaStyleLevel | None = None
    skill_snapshot: SkillSnapshot
    model_settings: ModelConfig = Field(alias="model_config")
    conversation_state: list[Message] = Field(default_factory=list)
    skill_snapshot_config: SkillSnapshotConfig | None = None


class SkillSnapshotConfig(BaseModel):
    """Session-scoped config used to rebuild skill snapshots deterministically."""

    model_config = ConfigDict(extra="forbid")

    bundled_dir: Path
    workspace_dir: Path
    user_dir: Path | None = None
    reserved_commands: tuple[str, ...] = ()
    available_tools: tuple[str, ...] | None = None
    platform: str | None = None
    env: dict[str, str] | None = None
