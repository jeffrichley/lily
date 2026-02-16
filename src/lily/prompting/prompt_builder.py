"""Prompt assembly primitives for PersonaContext-driven conversation runs."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class PromptMode(StrEnum):
    """Prompt rendering mode for conversation execution."""

    FULL = "full"
    MINIMAL = "minimal"


class PersonaStyleLevel(StrEnum):
    """User-facing persona style intensity."""

    FOCUS = "focus"
    BALANCED = "balanced"
    PLAYFUL = "playful"


class PersonaContext(BaseModel):
    """Persona context passed through LangChain runtime context."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    active_persona_id: str = Field(min_length=1)
    style_level: PersonaStyleLevel = PersonaStyleLevel.BALANCED
    persona_summary: str = ""
    persona_instructions: str = ""
    user_preference_summary: str = ""
    session_hints: tuple[str, ...] = ()
    task_hints: tuple[str, ...] = ()


class PromptBuildContext(BaseModel):
    """Input contract for deterministic prompt assembly."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    persona: PersonaContext
    mode: PromptMode = PromptMode.FULL
    session_id: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    skill_names: tuple[str, ...] = ()
    memory_summary: str = ""


class PromptSection(Protocol):
    """Protocol for individual prompt sections."""

    def render(self, context: PromptBuildContext, *, max_chars: int) -> str:
        """Render one prompt section string for provided context.

        Args:
            context: Prompt build context.
            max_chars: Maximum section chars before deterministic truncation.
        """


def truncate_with_marker(text: str, *, max_chars: int, label: str) -> str:
    """Deterministically truncate long text with a stable marker.

    Args:
        text: Source text.
        max_chars: Max characters to keep before truncation marker.
        label: Stable field label used in marker output.

    Returns:
        Original or truncated text with deterministic marker.
    """
    cleaned = text.strip()
    if max_chars < 1 or len(cleaned) <= max_chars:
        return cleaned
    keep_head = max(1, int(max_chars * 0.7))
    keep_tail = max(1, max_chars - keep_head)
    marker = (
        f"[...truncated {label}: kept {keep_head}+{keep_tail} chars of "
        f"{len(cleaned)} total...]"
    )
    return f"{cleaned[:keep_head]}\n{marker}\n{cleaned[-keep_tail:]}"


class IdentitySection:
    """Prompt section describing active Lily identity profile."""

    def render(self, context: PromptBuildContext, *, max_chars: int) -> str:
        """Render identity section.

        Args:
            context: Prompt build context.
            max_chars: Maximum section chars (unused for identity section).

        Returns:
            Rendered identity section text.
        """
        del max_chars
        persona = context.persona
        return "\n".join(
            (
                "## Identity",
                f"Persona: {persona.active_persona_id}",
                f"Style: {persona.style_level.value}",
            )
        )


class SafetySection:
    """Prompt section with minimal behavior guardrails."""

    def render(self, context: PromptBuildContext, *, max_chars: int) -> str:
        """Render safety section.

        Args:
            context: Prompt build context.
            max_chars: Maximum section chars (unused for safety section).

        Returns:
            Rendered safety section text.
        """
        del context
        del max_chars
        return "\n".join(
            (
                "## Safety",
                "Do not manipulate the user or encourage emotional dependency.",
                "If uncertain, state uncertainty and ask for missing context.",
            )
        )


class PersonaSection:
    """Prompt section with active persona directives."""

    def render(self, context: PromptBuildContext, *, max_chars: int) -> str:
        """Render bounded persona summary/instructions section.

        Args:
            context: Prompt build context.
            max_chars: Maximum section chars before truncation.

        Returns:
            Rendered persona section or empty string.
        """
        summary = context.persona.persona_summary.strip()
        instructions = context.persona.persona_instructions.strip()
        if not summary and not instructions:
            return ""
        blocks: list[str] = ["## Persona"]
        if summary:
            blocks.append(f"Summary: {summary}")
        if instructions:
            bounded = truncate_with_marker(
                instructions,
                max_chars=max_chars,
                label="persona_instructions",
            )
            blocks.append(bounded)
        return "\n".join(blocks)


class SkillsSection:
    """Prompt section listing currently available skill names."""

    def render(self, context: PromptBuildContext, *, max_chars: int) -> str:
        """Render skills section for full prompt mode.

        Args:
            context: Prompt build context.
            max_chars: Maximum section chars (unused for skills section).

        Returns:
            Rendered skills section or empty string.
        """
        del max_chars
        if context.mode != PromptMode.FULL:
            return ""
        if not context.skill_names:
            return ""
        lines = "\n".join(f"- {name}" for name in context.skill_names)
        return f"## Skills\n{lines}"


class MemorySection:
    """Prompt section injecting bounded memory and preference context."""

    def render(self, context: PromptBuildContext, *, max_chars: int) -> str:
        """Render memory section in full prompt mode with deterministic bounds.

        Args:
            context: Prompt build context.
            max_chars: Maximum section chars before truncation.

        Returns:
            Rendered memory section or empty string.
        """
        if context.mode != PromptMode.FULL:
            return ""
        memory_summary = (
            context.memory_summary or context.persona.user_preference_summary
        )
        if not memory_summary:
            return ""
        bounded = truncate_with_marker(
            memory_summary,
            max_chars=max_chars,
            label="memory_summary",
        )
        return f"## Memory\n{bounded}"


class RuntimeSection:
    """Prompt section for stable runtime metadata and hints."""

    def render(self, context: PromptBuildContext, *, max_chars: int) -> str:
        """Render runtime metadata and bounded hints.

        Args:
            context: Prompt build context.
            max_chars: Maximum chars for bounded hint injection.

        Returns:
            Rendered runtime section text.
        """
        hints = (*context.persona.session_hints, *context.persona.task_hints)
        hints_text = ""
        if hints:
            joined = "\n".join(f"- {hint}" for hint in hints)
            bounded_hints = truncate_with_marker(
                joined,
                max_chars=max_chars,
                label="runtime_hints",
            )
            hints_text = f"\nHints:\n{bounded_hints}"
        return (
            "## Runtime\n"
            f"Session ID: {context.session_id}\n"
            f"Model: {context.model_name}{hints_text}"
        )


class PromptBuilder:
    """Deterministic prompt builder using ordered section providers."""

    def __init__(
        self,
        *,
        sections: tuple[PromptSection, ...] | None = None,
        section_max_chars: int = 600,
    ) -> None:
        """Create prompt builder with ordered sections.

        Args:
            sections: Optional section provider override.
            section_max_chars: Max chars per section before truncation.
        """
        self._sections = sections or (
            IdentitySection(),
            PersonaSection(),
            SafetySection(),
            SkillsSection(),
            MemorySection(),
            RuntimeSection(),
        )
        self._section_max_chars = section_max_chars

    def build(self, context: PromptBuildContext) -> str:
        """Build stable prompt text for provided context.

        Args:
            context: Prompt build context.

        Returns:
            Fully rendered prompt text.
        """
        blocks: list[str] = []
        for section in self._sections:
            rendered = section.render(
                context, max_chars=self._section_max_chars
            ).strip()
            if rendered:
                blocks.append(rendered)
        return "\n\n".join(blocks).strip()
