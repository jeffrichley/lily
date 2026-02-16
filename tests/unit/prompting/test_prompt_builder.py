"""Unit tests for persona-aware prompt builder behavior."""

from __future__ import annotations

from lily.prompting import (
    PersonaContext,
    PersonaStyleLevel,
    PromptBuildContext,
    PromptBuilder,
    PromptMode,
    truncate_with_marker,
)


def _context(*, mode: PromptMode = PromptMode.FULL) -> PromptBuildContext:
    """Create prompt-build context fixture."""
    return PromptBuildContext(
        persona=PersonaContext(
            active_persona_id="architect",
            style_level=PersonaStyleLevel.BALANCED,
            persona_summary="Structured architecture persona.",
            persona_instructions="Lead with architecture constraints and decisions.",
            user_preference_summary="User likes concise output.",
            session_hints=("channel=repl",),
            task_hints=("phase=2",),
        ),
        mode=mode,
        session_id="session-test",
        model_name="ollama:llama3.2",
        skill_names=("add", "echo"),
        memory_summary="Remember prior architecture decisions.",
    )


def test_prompt_builder_full_mode_renders_all_core_sections() -> None:
    """Full mode should include identity/safety/skills/memory/runtime sections."""
    builder = PromptBuilder(section_max_chars=200)

    prompt = builder.build(_context(mode=PromptMode.FULL))

    assert "## Identity" in prompt
    assert "## Persona" in prompt
    assert "## Safety" in prompt
    assert "## Skills" in prompt
    assert "## Memory" in prompt
    assert "## Runtime" in prompt


def test_prompt_builder_minimal_mode_skips_skills_and_memory() -> None:
    """Minimal mode should omit skills and memory sections."""
    builder = PromptBuilder(section_max_chars=200)

    prompt = builder.build(_context(mode=PromptMode.MINIMAL))

    assert "## Identity" in prompt
    assert "## Persona" in prompt
    assert "## Safety" in prompt
    assert "## Runtime" in prompt
    assert "## Skills" not in prompt
    assert "## Memory" not in prompt


def test_truncate_with_marker_emits_deterministic_marker() -> None:
    """Truncation should include stable marker with kept/original lengths."""
    source = "a" * 80

    truncated = truncate_with_marker(source, max_chars=20, label="memory_summary")

    assert "[...truncated memory_summary: kept" in truncated
    assert "80 total" in truncated
