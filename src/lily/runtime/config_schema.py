"""Typed YAML schema contracts for Lily runtime configuration."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelProvider(StrEnum):
    """Supported model providers."""

    OPENAI = "openai"
    OLLAMA = "ollama"


class AgentConfig(BaseModel):
    """Top-level agent behavior settings."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    system_prompt: str = Field(min_length=1)


class ModelProfileConfig(BaseModel):
    """One concrete model definition for a provider."""

    model_config = ConfigDict(extra="forbid")

    provider: ModelProvider
    model: str = Field(min_length=1)
    temperature: float = Field(ge=0.0, le=2.0)
    timeout_seconds: float = Field(gt=0.0)


class DynamicModelRoutingConfig(BaseModel):
    """Dynamic model routing policy used by runtime middleware."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    default_profile: str = Field(min_length=1)
    long_context_profile: str = Field(min_length=1)
    complexity_threshold: int = Field(ge=1)


class ModelsConfig(BaseModel):
    """Container for available model profiles and routing policy."""

    model_config = ConfigDict(extra="forbid")

    profiles: dict[str, ModelProfileConfig] = Field(min_length=1)
    routing: DynamicModelRoutingConfig

    @model_validator(mode="after")
    def _validate_profile_references(self) -> ModelsConfig:
        """Ensure routing references only known model profiles.

        Returns:
            Self after successful post-validation checks.

        Raises:
            ValueError: If routing references unknown profile keys.
        """
        profile_names = set(self.profiles)
        if self.routing.default_profile not in profile_names:
            msg = "routing.default_profile must reference a key from models.profiles"
            raise ValueError(msg)
        if self.routing.long_context_profile not in profile_names:
            msg = (
                "routing.long_context_profile must reference a key from models.profiles"
            )
            raise ValueError(msg)
        return self


class ToolsConfig(BaseModel):
    """Tool registry enablement and allowlist constraints."""

    model_config = ConfigDict(extra="forbid")

    allowlist: list[str] = Field(min_length=1)


class McpServerConfig(BaseModel):
    """Base marker type for runtime MCP server config variants."""

    model_config = ConfigDict(extra="forbid")

    transport: str


class McpServerTestConfig(McpServerConfig):
    """Deterministic local MCP transport used for test fixtures."""

    transport: Literal["test"]
    tool_targets: dict[str, str] = Field(min_length=1)


class McpServerStreamableHttpConfig(McpServerConfig):
    """Real streamable HTTP MCP transport configuration."""

    transport: Literal["streamable_http"]
    url: str = Field(min_length=1)
    headers: dict[str, str] = Field(default_factory=dict)
    timeout_seconds: float | None = Field(default=None, gt=0.0)


class PoliciesConfig(BaseModel):
    """Runtime safety and loop policies."""

    model_config = ConfigDict(extra="forbid")

    max_iterations: int = Field(ge=1, le=100)
    max_model_calls: int = Field(ge=1, le=1000)
    max_tool_calls: int = Field(ge=1, le=1000)


class LoggingConfig(BaseModel):
    """Logging behavior controls."""

    model_config = ConfigDict(extra="forbid")

    level: str = Field(pattern="^(DEBUG|INFO|WARNING|ERROR)$")


class RuntimeConfig(BaseModel):
    """Root runtime configuration loaded from YAML."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(ge=1)
    agent: AgentConfig
    models: ModelsConfig
    tools: ToolsConfig
    mcp_servers: dict[
        str,
        Annotated[
            McpServerTestConfig | McpServerStreamableHttpConfig,
            Field(discriminator="transport"),
        ],
    ] = Field(default_factory=dict)
    policies: PoliciesConfig
    logging: LoggingConfig
