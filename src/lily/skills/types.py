"""Skills domain types."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class SkillSource(StrEnum):
    """Supported skill source roots."""

    BUNDLED = "bundled"
    WORKSPACE = "workspace"
    USER = "user"


class InvocationMode(StrEnum):
    """How a skill is executed once selected."""

    LLM_ORCHESTRATION = "llm_orchestration"
    TOOL_DISPATCH = "tool_dispatch"


class SkillEligibilitySpec(BaseModel):
    """Eligibility requirements declared by a skill."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    os: tuple[str, ...] = ()
    env: tuple[str, ...] = ()
    binaries: tuple[str, ...] = ()


class SkillCapabilitySpec(BaseModel):
    """Capability declarations enforced during skill invocation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    declared_tools: tuple[str, ...] = ()


class SkillMetadata(BaseModel):
    """Parsed metadata derived from SKILL.md frontmatter."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    summary: str = ""
    invocation_mode: InvocationMode = InvocationMode.LLM_ORCHESTRATION
    command: str | None = None
    command_tool_provider: str = "builtin"
    command_tool: str | None = None
    requires_tools: tuple[str, ...] = ()
    capabilities: SkillCapabilitySpec = Field(default_factory=SkillCapabilitySpec)
    capabilities_declared: bool = False
    eligibility: SkillEligibilitySpec = Field(default_factory=SkillEligibilitySpec)


class SkillDiagnostic(BaseModel):
    """Loader diagnostic record for malformed/ineligible skills."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    skill_name: str
    code: str
    message: str
    source: SkillSource | None = None
    path: Path | None = None


class SkillCandidate(BaseModel):
    """Discovered skill candidate before precedence resolution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    source: SkillSource
    path: Path


class SkillEntry(BaseModel):
    """Resolved, usable skill entry inside a snapshot."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    source: SkillSource
    path: Path
    summary: str = ""
    instructions: str = ""
    invocation_mode: InvocationMode = InvocationMode.LLM_ORCHESTRATION
    command: str | None = None
    command_tool_provider: str = "builtin"
    command_tool: str | None = None
    requires_tools: tuple[str, ...] = ()
    capabilities: SkillCapabilitySpec = Field(default_factory=SkillCapabilitySpec)
    capabilities_declared: bool = False
    eligibility: SkillEligibilitySpec = Field(default_factory=SkillEligibilitySpec)


class SkillSnapshot(BaseModel):
    """Immutable skills index used by a session."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: str
    skills: tuple[SkillEntry, ...]
    diagnostics: tuple[SkillDiagnostic, ...] = ()


class EligibilityContext(BaseModel):
    """Runtime context used for evaluating skill eligibility."""

    model_config = ConfigDict(extra="forbid")

    platform: str
    env: dict[str, str] = Field(default_factory=dict)
    available_tools: set[str] | None = None
