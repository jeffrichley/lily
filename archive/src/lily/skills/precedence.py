"""Deterministic precedence resolution."""

from __future__ import annotations

from collections import defaultdict

from lily.skills.types import SkillCandidate, SkillDiagnostic, SkillSource

_PRECEDENCE: dict[SkillSource, int] = {
    SkillSource.BUNDLED: 1,
    SkillSource.USER: 2,
    SkillSource.WORKSPACE: 3,
}


def resolve_precedence(
    candidates: tuple[SkillCandidate, ...],
) -> tuple[tuple[SkillCandidate, ...], tuple[SkillDiagnostic, ...]]:
    """Resolve duplicate skill names using deterministic source precedence.

    Args:
        candidates: All discovered candidates across source roots.

    Returns:
        A tuple of selected winners and precedence diagnostics.
    """
    by_name: dict[str, list[SkillCandidate]] = defaultdict(list)
    for candidate in candidates:
        by_name[candidate.name].append(candidate)

    winners: list[SkillCandidate] = []
    diagnostics: list[SkillDiagnostic] = []

    for skill_name in sorted(by_name.keys()):
        name_candidates = sorted(
            by_name[skill_name],
            key=lambda c: (_PRECEDENCE[c.source], str(c.path)),
            reverse=True,
        )
        winner = name_candidates[0]
        winners.append(winner)

        if len(name_candidates) > 1:
            losers = [
                f"{candidate.source.value}:{candidate.path}"
                for candidate in name_candidates[1:]
            ]
            winner_label = f"{winner.source.value}:{winner.path}"
            losers_label = "; ".join(losers)
            diagnostics.append(
                SkillDiagnostic(
                    skill_name=skill_name,
                    code="precedence_conflict",
                    message=(
                        "Resolved by precedence. "
                        f"Winner={winner_label}; Losers={losers_label}"
                    ),
                    source=winner.source,
                    path=winner.path,
                ),
            )

    return tuple(winners), tuple(diagnostics)
