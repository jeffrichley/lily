"""Skill discovery from configured roots."""

from __future__ import annotations

from pathlib import Path

from lily.skills.types import SkillCandidate, SkillDiagnostic, SkillSource

SKILL_FILENAME = "SKILL.md"


def discover_candidates(
    root: Path, source: SkillSource
) -> tuple[tuple[SkillCandidate, ...], tuple[SkillDiagnostic, ...]]:
    """Discover immediate-child skill directories for a single root.

    A directory qualifies as a skill candidate only if ``SKILL.md`` exists.

    Args:
        root: Source root directory to scan.
        source: Skill source label for produced candidates and diagnostics.

    Returns:
        A tuple of discovered candidates and discovery diagnostics.
    """
    candidates: list[SkillCandidate] = []
    diagnostics: list[SkillDiagnostic] = []

    children = sorted(
        (child for child in root.iterdir() if child.is_dir()), key=lambda p: p.name
    )
    for child in children:
        skill_name = child.name
        skill_md = child / SKILL_FILENAME
        if not skill_md.is_file():
            diagnostics.append(
                SkillDiagnostic(
                    skill_name=skill_name,
                    code="missing_skill_md",
                    message="Skill directory missing SKILL.md; excluded.",
                    source=source,
                    path=child,
                ),
            )
            continue

        candidates.append(
            SkillCandidate(
                name=skill_name,
                source=source,
                path=child,
            ),
        )

    return tuple(candidates), tuple(diagnostics)
