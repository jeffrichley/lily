"""Shared fixtures for command-surface unit tests."""

from __future__ import annotations

from pathlib import Path

from lily.runtime.conversation import ConversationRequest, ConversationResponse
from lily.session.models import ModelConfig, Session
from lily.skills.types import (
    InvocationMode,
    SkillCapabilitySpec,
    SkillEntry,
    SkillSnapshot,
    SkillSource,
)


class _ConversationCaptureExecutor:
    """Conversation executor fixture that captures last request."""

    def __init__(self) -> None:
        """Initialize capture slots."""
        self.last_request: ConversationRequest | None = None

    def run(self, request: ConversationRequest) -> ConversationResponse:
        """Capture request and return deterministic reply."""
        self.last_request = request
        return ConversationResponse(text="ok")


def _make_session(skills: tuple[SkillEntry, ...]) -> Session:
    """Create a minimal session fixture with a supplied skill snapshot.

    Args:
        skills: Snapshot skill entries.

    Returns:
        Session configured for command-surface unit tests.
    """
    snapshot = SkillSnapshot(version="v-test", skills=skills)
    return Session(
        session_id="session-test",
        active_agent="default",
        skill_snapshot=snapshot,
        model_config=ModelConfig(),
    )


def _make_skill(
    name: str,
    summary: str = "",
    *,
    mode: InvocationMode = InvocationMode.LLM_ORCHESTRATION,
    command_tool: str | None = None,
    command: str | None = None,
) -> SkillEntry:
    """Create a deterministic skill entry fixture.

    Args:
        name: Skill name.
        summary: Skill summary text.
        mode: Invocation mode for the skill fixture.
        command_tool: Optional tool name for tool_dispatch fixtures.
        command: Optional alias command exposed by the skill.

    Returns:
        Skill entry fixture.
    """
    capabilities = SkillCapabilitySpec()
    if mode == InvocationMode.TOOL_DISPATCH and command_tool is not None:
        capabilities = SkillCapabilitySpec(declared_tools=(command_tool,))
    return SkillEntry(
        name=name,
        source=SkillSource.BUNDLED,
        path=Path(f"/skills/{name}/SKILL.md"),
        summary=summary,
        invocation_mode=mode,
        command=command,
        command_tool=command_tool,
        capabilities=capabilities,
        capabilities_declared=(mode == InvocationMode.TOOL_DISPATCH),
    )


def _write_persona(root: Path, name: str, summary: str, default_style: str) -> None:
    """Write one persona markdown fixture.

    Args:
        root: Persona directory root.
        name: Persona identifier and filename stem.
        summary: Persona summary.
        default_style: Persona default style value.
    """
    root.mkdir(parents=True, exist_ok=True)
    (root / f"{name}.md").write_text(
        (
            "---\n"
            f"id: {name}\n"
            f"summary: {summary}\n"
            f"default_style: {default_style}\n"
            "---\n"
            f"You are {name}.\n"
        ),
        encoding="utf-8",
    )


def _write_agent(root: Path, name: str, summary: str) -> None:
    """Write one structured agent contract fixture."""
    root.mkdir(parents=True, exist_ok=True)
    (root / f"{name}.agent.yaml").write_text(
        (f"id: {name}\nsummary: {summary}\npolicy: safe_eval\ndeclared_tools: []\n"),
        encoding="utf-8",
    )
