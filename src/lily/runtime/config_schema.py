"""Typed YAML schema contracts for Lily runtime configuration."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from lily.runtime.skill_types import SkillValidationError, normalize_skill_name

_SKILL_SCOPE_NAMES = frozenset({"repository", "user", "system"})
_TOOL_ID_PATTERN = re.compile(r"^[a-z0-9_]+$")
_PACK_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

_ScopePrecedence = list[Literal["repository", "user", "system"]]


def _default_scopes_precedence() -> _ScopePrecedence:
    """Return default scope ordering (lowest to highest precedence).

    Returns:
        Scope names from repository through user to system.
    """
    return ["repository", "user", "system"]


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
    skill_telemetry_log: str | None = Field(
        default=None,
        description=(
            "Optional path for skill F7 JSON telemetry (JSONL). "
            "Relative paths resolve against the runtime config file directory. "
            "When omitted, defaults to ../logs/skill-telemetry.jsonl "
            "from that directory."
        ),
    )


def _validate_skills_tools_packs_entries(packs: dict[str, list[str]]) -> None:
    """Validate pack ids and nested tool id lists.

    Args:
        packs: Map of pack id to ordered tool id list.

    Raises:
        ValueError: If a pack id or tool id is malformed or a pack is empty.
    """
    for pack_id, tool_ids in packs.items():
        if not _PACK_ID_PATTERN.fullmatch(pack_id):
            msg = f"skills.tools.packs has invalid pack id '{pack_id}'"
            raise ValueError(msg)
        if not tool_ids:
            msg = f"skills.tools.packs['{pack_id}'] must list at least one tool id"
            raise ValueError(msg)
        for tid in tool_ids:
            if not _TOOL_ID_PATTERN.fullmatch(tid):
                msg = f"skills.tools.packs['{pack_id}'] has invalid tool id '{tid}'"
                raise ValueError(msg)


class SkillsToolsConfig(BaseModel):
    """Tool-pack policy for skills (intersected with runtime tool allowlists)."""

    model_config = ConfigDict(extra="forbid")

    default_policy: Literal[
        "inherit_runtime",
        "deny_unless_allowed",
        "use_default_packs",
    ] = "inherit_runtime"
    default_packs: list[str] = Field(default_factory=list)
    packs: dict[str, list[str]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_packs_and_policy(self) -> SkillsToolsConfig:
        """Ensure pack references resolve and tool ids are well-formed.

        Returns:
            Validated model instance.

        Raises:
            ValueError: If pack references or tool ids are invalid.
        """
        for pack_id in self.default_packs:
            if pack_id not in self.packs:
                msg = (
                    f"skills.tools.default_packs references unknown pack id '{pack_id}'"
                )
                raise ValueError(msg)
        if self.default_policy == "use_default_packs" and not self.default_packs:
            msg = (
                "skills.tools.default_policy 'use_default_packs' requires a "
                "non-empty skills.tools.default_packs list"
            )
            raise ValueError(msg)
        _validate_skills_tools_packs_entries(self.packs)
        return self


class SkillsRetrievalConfig(BaseModel):
    """Gates for progressive disclosure (tool-based ``SKILL.md`` / linked files)."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    scopes_allowlist: list[Literal["repository", "user", "system"]] = Field(
        default_factory=list,
        description=(
            "When non-empty, only skills whose winning scope is listed here may be "
            "retrieved. When empty, no extra scope restriction applies."
        ),
    )


class SkillsConfig(BaseModel):
    """Skill discovery roots, precedence, and policy lists."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    roots: dict[str, list[str]] = Field(default_factory=dict)
    scopes_precedence: list[Literal["repository", "user", "system"]] = Field(
        default_factory=_default_scopes_precedence,
    )
    allowlist: list[str] = Field(default_factory=list)
    denylist: list[str] = Field(default_factory=list)
    tools: SkillsToolsConfig = Field(default_factory=SkillsToolsConfig)
    retrieval: SkillsRetrievalConfig = Field(default_factory=SkillsRetrievalConfig)

    @field_validator("allowlist", "denylist", mode="before")
    @classmethod
    def _normalize_skill_policy_lists(cls, value: object) -> list[str]:
        """Normalize allow/deny entries to canonical skill keys.

        Args:
            value: Raw list from YAML/TOML.

        Returns:
            List of normalized keys suitable for policy membership checks.

        Raises:
            ValueError: If the value is not a list of normalizable skill name strings.
        """
        if not isinstance(value, list):
            msg = "skills allowlist and denylist must be lists of skill name strings"
            raise ValueError(msg)

        out: list[str] = []
        for raw in value:
            s = str(raw).strip()
            if not s:
                msg = "skills allowlist/denylist entries must be non-empty strings"
                raise ValueError(msg)
            try:
                out.append(normalize_skill_name(s))
            except SkillValidationError as exc:
                msg = f"invalid skill name in policy list: {exc}"
                raise ValueError(msg) from exc
        return out

    @field_validator("roots", mode="before")
    @classmethod
    def _normalize_roots(cls, value: object) -> dict[str, list[str]]:
        """Accept YAML list of paths as repository-scoped roots.

        Args:
            value: Raw ``skills.roots`` value from YAML/TOML.

        Returns:
            Mapping of scope name to a list of root path strings.

        Raises:
            ValueError: If ``value`` is not a list or dict of lists.
        """
        if isinstance(value, list):
            return {"repository": [str(p) for p in value]}
        if isinstance(value, dict):
            out: dict[str, list[str]] = {}
            for raw_key, raw_value in value.items():
                key = str(raw_key)
                if isinstance(raw_value, list):
                    out[key] = [str(p) for p in raw_value]
                else:
                    msg = f"skills.roots['{key}'] must be a list of path strings"
                    raise ValueError(msg)
            return out
        msg = "skills.roots must be a list of paths or a mapping of scope -> paths"
        raise ValueError(msg)

    @model_validator(mode="after")
    def _validate_scopes_and_roots(self) -> SkillsConfig:
        """Validate scope keys and precedence ordering.

        Returns:
            Validated skills configuration.

        Raises:
            ValueError: If a scope key is unknown or precedence has duplicates.
        """
        for scope in self.roots:
            if scope not in _SKILL_SCOPE_NAMES:
                msg = f"skills.roots has unknown scope key '{scope}'"
                raise ValueError(msg)
        seen: set[str] = set()
        for scope in self.scopes_precedence:
            if scope not in _SKILL_SCOPE_NAMES:
                msg = f"skills.scopes_precedence has unknown scope '{scope}'"
                raise ValueError(msg)
            if scope in seen:
                msg = (
                    "skills.scopes_precedence must not contain duplicate scope entries"
                )
                raise ValueError(msg)
            seen.add(scope)
        return self


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
    skills: SkillsConfig | None = None
