"""Skill registry: collision resolution, allow/deny filtering, and lookup APIs."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from packaging.version import InvalidVersion, Version

from lily.runtime.config_schema import SkillsConfig
from lily.runtime.skill_discovery import SkillCandidate, SkillDiscoveryEvent
from lily.runtime.skill_policies import candidate_allowed_by_lists
from lily.runtime.skill_types import SkillSummary


@dataclass(frozen=True, slots=True)
class SkillRegistryEntry:
    """Winning skill record after precedence and policy filters."""

    summary: SkillSummary
    scope: str
    skill_dir: Path
    skill_md_path: Path
    version: str | None


class SkillRegistry:
    """Deterministic lookup of skills by canonical key."""

    def __init__(
        self,
        entries: dict[str, SkillRegistryEntry],
        events: list[SkillDiscoveryEvent],
    ) -> None:
        """Store resolved entries and merge diagnostics.

        Args:
            entries: Winning entries keyed by canonical skill id.
            events: Discovery and shadowing events from merge.
        """
        self._entries = entries
        self.events = events

    def get(self, canonical_key: str) -> SkillRegistryEntry | None:
        """Return the registry entry for ``canonical_key`` if present.

        Args:
            canonical_key: Stable skill identifier.

        Returns:
            Registry entry when found, otherwise ``None``.
        """
        return self._entries.get(canonical_key)

    def canonical_keys(self) -> list[str]:
        """Return sorted canonical keys for stable iteration.

        Returns:
            Sorted list of canonical skill ids present in the registry.
        """
        return sorted(self._entries)


def build_skill_registry(
    candidates: Sequence[SkillCandidate],
    skills_config: SkillsConfig,
) -> SkillRegistry:
    """Apply allow/deny filters, resolve collisions, and emit shadow events.

    Collision resolution order per ``canonical_key``:
    1. Higher scope rank (later in ``scopes_precedence`` wins).
    2. Higher semantic version when both declare ``metadata.version`` strings.
    3. Lexicographic tie-break on resolved ``skill_dir`` path string.

    Args:
        candidates: Discovered candidates (from ``discover_skill_candidates``).
        skills_config: Skills policy configuration.

    Returns:
        Registry with deterministic winner map and merged diagnostic events.
    """
    events: list[SkillDiscoveryEvent] = []
    if not skills_config.enabled:
        return SkillRegistry({}, events)

    filtered: list[SkillCandidate] = []
    for cand in candidates:
        key = cand.summary.canonical_key
        if not candidate_allowed_by_lists(key, skills_config):
            continue
        filtered.append(cand)

    by_key: dict[str, list[SkillCandidate]] = defaultdict(list)
    for cand in filtered:
        by_key[cand.summary.canonical_key].append(cand)

    winners: dict[str, SkillRegistryEntry] = {}
    for canonical_key in sorted(by_key.keys()):
        group = by_key[canonical_key]
        winner = _pick_winner(group, skills_config.scopes_precedence)
        winners[canonical_key] = SkillRegistryEntry(
            summary=winner.summary,
            scope=winner.scope,
            skill_dir=winner.skill_dir,
            skill_md_path=winner.skill_md_path,
            version=winner.version,
        )
        events.append(
            SkillDiscoveryEvent(
                kind="discovered",
                canonical_key=canonical_key,
                scope=winner.scope,
                path=winner.skill_md_path,
            ),
        )
        for loser in group:
            if loser.skill_md_path == winner.skill_md_path:
                continue
            events.append(
                SkillDiscoveryEvent(
                    kind="shadowed",
                    canonical_key=canonical_key,
                    scope=loser.scope,
                    path=loser.skill_md_path,
                    superseded_by=winner.skill_md_path,
                ),
            )

    return SkillRegistry(winners, events)


def _pick_winner(
    group: list[SkillCandidate],
    scopes_precedence: Sequence[str],
) -> SkillCandidate:
    """Return the winning candidate using scope, semver, then lexical path order.

    Args:
        group: Candidates that share the same canonical key.
        scopes_precedence: Scope ordering from lowest to highest precedence.

    Returns:
        Single winning candidate after pairwise comparison.
    """
    best = group[0]
    for cand in group[1:]:
        best = _prefer_candidate(best, cand, scopes_precedence)
    return best


def _prefer_candidate(
    a: SkillCandidate,
    b: SkillCandidate,
    scopes_precedence: Sequence[str],
) -> SkillCandidate:
    """Return the preferred candidate for ``scopes_precedence`` (later wins).

    Args:
        a: First candidate.
        b: Second candidate.
        scopes_precedence: Scope ordering from lowest to highest precedence.

    Returns:
        Preferred candidate between ``a`` and ``b``.
    """
    ra = _scope_rank(a.scope, scopes_precedence)
    rb = _scope_rank(b.scope, scopes_precedence)
    if ra != rb:
        return a if ra > rb else b
    cmp_ver = _compare_versions(a.version, b.version)
    if cmp_ver != 0:
        return a if cmp_ver > 0 else b
    sa = str(a.skill_dir)
    sb = str(b.skill_dir)
    return a if sa > sb else b


def _scope_rank(scope: str, order: Sequence[str]) -> int:
    try:
        return order.index(scope)
    except ValueError:
        return -1


def _compare_versions(a: str | None, b: str | None) -> int:
    """Compare optional PEP 440-ish version strings for tie-breaking.

    Args:
        a: Optional version string from skill metadata.
        b: Optional version string from skill metadata.

    Returns:
        Positive if ``a`` is newer than ``b``, negative if older, zero if equal.
    """
    if a is None and b is None:
        return 0
    if a is None:
        return -1
    if b is None:
        return 1
    try:
        va, vb = Version(a), Version(b)
        return int(va > vb) - int(va < vb)
    except InvalidVersion:
        return int(a > b) - int(a < b)
