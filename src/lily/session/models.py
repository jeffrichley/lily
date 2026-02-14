"""Session models."""

from __future__ import annotations

from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

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


class ModelConfig(BaseModel):
    """Session-scoped model behavior configuration."""

    model_config = ConfigDict(extra="forbid")

    model_name: str = "default"
    temperature: float = 0.0
    thinking_level: str | None = None
    verbose: bool = False


class Session(BaseModel):
    """Stable execution context for one conversation session."""

    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(default_factory=lambda: str(uuid4()))
    active_agent: str = "default"
    skill_snapshot: SkillSnapshot
    model_settings: ModelConfig = Field(alias="model_config")
    conversation_state: list[Message] = Field(default_factory=list)
