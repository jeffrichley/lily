"""Filesystem discovery of skill packages under configured scope roots."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from lily.runtime.config_schema import SkillsConfig
from lily.runtime.skill_catalog import load_skill_md
from lily.runtime.skill_types import SkillSummary, SkillValidationError

_SKILL_MD = "SKILL.md"


@dataclass(frozen=True, slots=True)
class SkillCandidate:
    """One parsed skill package discovered on disk before registry merge."""

    scope: str
    skill_dir: Path
    skill_md_path: Path
    summary: SkillSummary
    version: str | None


SkillDiscoveryKind = Literal["discovered", "shadowed", "skipped_invalid"]


@dataclass(frozen=True, slots=True)
class SkillDiscoveryEvent:
    """Diagnostics for discovery and collision resolution."""

    kind: SkillDiscoveryKind
    canonical_key: str
    scope: str
    path: Path
    detail: str | None = None
    superseded_by: Path | None = None


def _sorted_child_dir_names(root: Path) -> list[str]:
    """Return sorted names of non-hidden child directories under ``root``.

    Args:
        root: Directory whose immediate children are inspected.

    Returns:
        Sorted subdirectory names (non-hidden only).
    """
    child_dirs = [
        p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")
    ]
    return sorted(p.name for p in child_dirs)


def _parse_skill_package_or_skip(
    scope: str,
    skill_dir: Path,
    skill_md: Path,
) -> SkillCandidate | SkillDiscoveryEvent:
    """Parse one SKILL.md into a candidate, or return a skip event on failure.

    Args:
        scope: Configured scope name for this root.
        skill_dir: Directory containing ``SKILL.md``.
        skill_md: Path to ``SKILL.md``.

    Returns:
        Parsed candidate on success, or a ``skipped_invalid`` event on failure.
    """
    try:
        parsed = load_skill_md(skill_md)
    except (OSError, SkillValidationError) as exc:
        return SkillDiscoveryEvent(
            kind="skipped_invalid",
            canonical_key="",
            scope=scope,
            path=skill_md,
            detail=str(exc),
        )
    summary = parsed.metadata.to_summary()
    version = None
    if parsed.metadata.metadata and "version" in parsed.metadata.metadata:
        raw_ver = parsed.metadata.metadata["version"]
        if isinstance(raw_ver, str):
            version = raw_ver
    return SkillCandidate(
        scope=scope,
        skill_dir=skill_dir.resolve(),
        skill_md_path=skill_md.resolve(),
        summary=summary,
        version=version,
    )


def discover_skill_candidates(
    skills_config: SkillsConfig,
    *,
    base_path: Path,
) -> tuple[list[SkillCandidate], list[SkillDiscoveryEvent]]:
    """Walk configured roots and collect valid skill packages in deterministic order.

    Directory iteration is explicitly sorted; roots are visited in ``scopes_precedence``
    order and paths within each scope are sorted lexically.

    Args:
        skills_config: Validated skills configuration.
        base_path: Base directory used to resolve relative root paths (typically the
            config file directory).

    Returns:
        Parsed candidates plus diagnostic events (including skipped invalid packages).
    """
    if not skills_config.enabled:
        return [], []

    events: list[SkillDiscoveryEvent] = []
    candidates: list[SkillCandidate] = []

    for scope in skills_config.scopes_precedence:
        root_paths = skills_config.roots.get(scope, [])
        for root_str in sorted(root_paths):
            root = _resolve_root_path(base_path, root_str)
            if not root.is_dir():
                events.append(
                    SkillDiscoveryEvent(
                        kind="skipped_invalid",
                        canonical_key="",
                        scope=scope,
                        path=root,
                        detail=f"skill root is not a directory: {root}",
                    ),
                )
                continue
            for child_name in _sorted_child_dir_names(root):
                skill_dir = root / child_name
                skill_md = skill_dir / _SKILL_MD
                if not skill_md.is_file():
                    continue
                outcome = _parse_skill_package_or_skip(scope, skill_dir, skill_md)
                if isinstance(outcome, SkillDiscoveryEvent):
                    events.append(outcome)
                    continue
                candidates.append(outcome)

    return candidates, events


def _resolve_root_path(base_path: Path, root_str: str) -> Path:
    """Resolve a configured root string against the config base path.

    Args:
        base_path: Directory used to resolve relative roots.
        root_str: Root path from configuration (absolute or relative).

    Returns:
        Absolute, resolved filesystem path for the skill root.
    """
    raw = Path(root_str)
    if raw.is_absolute():
        return raw
    return (base_path / raw).resolve()
