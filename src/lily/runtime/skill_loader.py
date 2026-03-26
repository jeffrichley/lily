"""Progressive disclosure: load ``SKILL.md`` and other files under the skill dir."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lily.runtime.config_schema import SkillsConfig
from lily.runtime.skill_discovery import discover_skill_candidates
from lily.runtime.skill_events import emit_skill_discovery_events, emit_skill_loaded
from lily.runtime.skill_policies import (
    build_retrieval_blocked_keys,
    retrieval_config_denial_reason,
)
from lily.runtime.skill_prompt_injector import format_skill_catalog_block
from lily.runtime.skill_registry import (
    SkillRegistry,
    SkillRegistryEntry,
    build_skill_registry,
)
from lily.runtime.skill_types import normalize_skill_name


class SkillLoadError(ValueError):
    """Base error for skill retrieval failures."""


class SkillNotFoundError(SkillLoadError):
    """Raised when no registry entry matches the requested skill name."""


class SkillRetrievalDeniedError(SkillLoadError):
    """Raised when policy blocks retrieval before reading skill content."""


class SkillReferenceError(SkillLoadError):
    """Raised when a reference path is invalid, escapes bounds, or is missing."""


@dataclass(frozen=True, slots=True)
class SkillBundle:
    """Discovery output plus loader and catalog text for runtime wiring."""

    registry: SkillRegistry
    loader: SkillLoader
    catalog_markdown: str


class SkillLoader:
    """Load full skill files on demand with bounded path checks and memoization."""

    def __init__(
        self,
        registry: SkillRegistry,
        *,
        skills_config: SkillsConfig | None = None,
        retrieval_blocked_keys: dict[str, str] | None = None,
    ) -> None:
        """Store registry used to resolve skill names to on-disk paths.

        Args:
            registry: Merged registry from ``build_skill_registry``.
            skills_config: Skills policy configuration (required for retrieval gates).
            retrieval_blocked_keys: Canonical keys excluded from the registry by
                allow/deny lists, mapped to deterministic denial reasons.
        """
        self._registry = registry
        self._skills_config = skills_config or SkillsConfig(enabled=True)
        self._retrieval_blocked = dict(retrieval_blocked_keys or {})
        self._full_file_cache: dict[str, str] = {}
        self._reference_cache: dict[tuple[str, str], str] = {}
        self._last_retrieval_canonical_key: str | None = None

    @property
    def last_resolved_canonical_key(self) -> str | None:
        """Canonical key from the last successful ``retrieve``, if any.

        Returns:
            Registry key set after the most recent successful load, else ``None``.
        """
        return self._last_retrieval_canonical_key

    def retrieve(self, name: str, reference_subpath: str | None = None) -> str:
        """Load full ``SKILL.md`` text, or a UTF-8 file under the skill package root.

        Args:
            name: Skill name or canonical key (matched case-insensitively on name).
            reference_subpath: Path relative to the skill directory (no ``..``), e.g.
                ``references/notes.md``, ``assets/palette.json``, or ``SKILL.md``.

        Returns:
            Raw file contents.

        Raises:
            SkillRetrievalDeniedError: When allow/deny lists or ``skills.retrieval``
                policy blocks access before reading files.

        Note:
            Lookup and file reads may raise ``SkillNotFoundError``,
            ``SkillReferenceError``, or ``SkillLoadError``.
        """
        stripped = name.strip()
        key = normalize_skill_name(stripped)
        if key in self._retrieval_blocked:
            raise SkillRetrievalDeniedError(self._retrieval_blocked[key])
        entry = self._lookup_registry_entry(stripped, key)
        denied = retrieval_config_denial_reason(
            self._skills_config,
            skill_scope=entry.scope,
        )
        if denied:
            raise SkillRetrievalDeniedError(denied)
        if reference_subpath is None or not reference_subpath.strip():
            text = self._load_skill_md_file(entry.summary.canonical_key, entry)
            self._last_retrieval_canonical_key = entry.summary.canonical_key
            return text
        text = self._load_reference_file(
            entry.summary.canonical_key,
            entry,
            reference_subpath.strip(),
        )
        self._last_retrieval_canonical_key = entry.summary.canonical_key
        return text

    def _lookup_registry_entry(self, name: str, key: str) -> SkillRegistryEntry:
        """Find registry entry by normalized key or display name.

        Args:
            name: User-supplied skill label (trimmed).
            key: Normalized canonical key for ``name``.

        Returns:
            Matching registry entry.

        Raises:
            SkillNotFoundError: If no entry matches.
        """
        got = self._registry.get(key)
        if got is not None:
            return got
        lowered = name.strip().lower()
        for ck in self._registry.canonical_keys():
            entry = self._registry.get(ck)
            if entry is not None and entry.summary.name.strip().lower() == lowered:
                return entry
        msg = f"no skill matches name {name!r}"
        raise SkillNotFoundError(msg)

    def _load_skill_md_file(self, canonical_key: str, entry: SkillRegistryEntry) -> str:
        """Read and cache full ``SKILL.md`` text for one canonical key.

        Args:
            canonical_key: Stable registry key.
            entry: Registry row for the skill.

        Returns:
            Full file text (frontmatter + body).

        Raises:
            SkillLoadError: On read errors.
        """
        if canonical_key in self._full_file_cache:
            return self._full_file_cache[canonical_key]
        path = entry.skill_md_path
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            msg = f"unable to read SKILL.md at {path}: {exc}"
            raise SkillLoadError(msg) from exc
        self._full_file_cache[canonical_key] = text
        emit_skill_loaded(
            canonical_key=canonical_key,
            load_kind="skill_md",
            relative_path="SKILL.md",
            content_length=len(text),
        )
        return text

    def _load_reference_file(
        self,
        canonical_key: str,
        entry: SkillRegistryEntry,
        reference_subpath: str,
    ) -> str:
        """Read a UTF-8 file under ``skill_dir`` with path bounding.

        Args:
            canonical_key: Stable registry key (cache key).
            entry: Registry row for the skill.
            reference_subpath: Relative path inside the skill package directory.

        Returns:
            File contents.

        Raises:
            SkillLoadError: On read errors after path resolution.
        """
        cache_key = (canonical_key, reference_subpath)
        if cache_key in self._reference_cache:
            return self._reference_cache[cache_key]

        target = _safe_path_within_skill_dir(entry.skill_dir, reference_subpath)
        try:
            text = target.read_text(encoding="utf-8")
        except OSError as exc:
            msg = f"unable to read reference file {target}: {exc}"
            raise SkillLoadError(msg) from exc
        self._reference_cache[cache_key] = text
        emit_skill_loaded(
            canonical_key=canonical_key,
            load_kind="reference",
            relative_path=reference_subpath,
            content_length=len(text),
        )
        return text


def _safe_path_within_skill_dir(skill_dir: Path, reference_subpath: str) -> Path:
    """Resolve a path under ``skill_dir`` without parent-segment escapes.

    Args:
        skill_dir: Skill package root (contains ``SKILL.md``).
        reference_subpath: Relative path with no ``..`` segments.

    Returns:
        Absolute path to an existing file inside ``skill_dir``.

    Raises:
        SkillReferenceError: If the path is malformed, escapes the skill directory,
            is not a file, or is missing.
    """
    tail = Path(reference_subpath)
    if tail.is_absolute():
        msg = "reference_subpath must be a relative path"
        raise SkillReferenceError(msg)
    if ".." in tail.parts:
        msg = "reference_subpath must not contain '..' components"
        raise SkillReferenceError(msg)
    root = skill_dir.resolve()
    candidate = (root / tail).resolve()
    if not candidate.is_relative_to(root):
        msg = f"resolved path escapes skill directory: {reference_subpath!r}"
        raise SkillReferenceError(msg)
    if candidate.is_dir():
        msg = f"path is not a file: {reference_subpath!r}"
        raise SkillReferenceError(msg)
    if not candidate.is_file():
        msg = f"file not found: {reference_subpath!r}"
        raise SkillReferenceError(msg)
    return candidate


def build_skill_bundle(
    skills_config: SkillsConfig,
    base_path: Path,
) -> SkillBundle | None:
    """Discover and merge skills, then build a loader and catalog markdown.

    Args:
        skills_config: Validated ``skills`` section from runtime config.
        base_path: Directory used to resolve relative skill roots (config dir).

    Returns:
        Bundle when skills are enabled, otherwise ``None``.
    """
    if not skills_config.enabled:
        return None
    candidates, discovery_events = discover_skill_candidates(
        skills_config,
        base_path=base_path,
    )
    registry = build_skill_registry(candidates, skills_config)
    emit_skill_discovery_events(
        tuple((*discovery_events, *registry.events)),
    )
    catalog = format_skill_catalog_block(registry)
    blocked = build_retrieval_blocked_keys(candidates, skills_config)
    loader = SkillLoader(
        registry,
        skills_config=skills_config,
        retrieval_blocked_keys=blocked,
    )
    return SkillBundle(
        registry=registry,
        loader=loader,
        catalog_markdown=catalog,
    )
