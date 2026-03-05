"""File-backed agent registry loader.

Primary format is schema-first `*.agent.yaml` / `*.agent.yml`.
Legacy markdown with YAML frontmatter remains supported during migration.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from lily.agents.models import AgentCatalog, AgentProfile

_FRONTMATTER_DELIMITER = "---"
_AGENT_YAML_GLOBS = ("*.agent.yaml", "*.agent.yml")


class AgentRepositoryError(RuntimeError):
    """Raised when agent files cannot be loaded deterministically."""


class _AgentFrontmatter(BaseModel):
    """Validated agent frontmatter fields."""

    model_config = ConfigDict(extra="forbid")

    summary: str = ""
    policy: str = "safe_eval"
    agent_id: str = Field(alias="id", min_length=1)
    declared_tools: tuple[str, ...] = ()


class FileAgentRepository:
    """Load agent profiles from markdown files in one root directory."""

    def __init__(self, *, root_dir: Path) -> None:
        """Create repository for one agent root.

        Args:
            root_dir: Agent markdown directory.
        """
        self._root_dir = root_dir
        self._catalog_cache: AgentCatalog | None = None

    def load_catalog(self) -> AgentCatalog:
        """Load all agent profiles into a deterministic catalog.

        Returns:
            Sorted agent catalog.
        """
        if self._catalog_cache is None:
            return self.reload_catalog()
        return self._catalog_cache

    def reload_catalog(self) -> AgentCatalog:
        """Reload agent catalog from disk and refresh in-memory cache.

        Returns:
            Reloaded sorted agent catalog.

        Raises:
            AgentRepositoryError: If one or more agent files are invalid.
        """
        if not self._root_dir.exists():
            self._catalog_cache = AgentCatalog(agents=())
            return self._catalog_cache
        if not self._root_dir.is_dir():
            raise AgentRepositoryError(
                f"Agent root is not a directory: {self._root_dir}"
            )

        files = self._iter_agent_files()
        profiles = [_parse_agent_file(path) for path in files]
        _validate_unique_agent_ids(profiles)
        ordered = tuple(sorted(profiles, key=lambda profile: profile.agent_id))
        self._catalog_cache = AgentCatalog(agents=ordered)
        return self._catalog_cache

    def get(self, agent_id: str) -> AgentProfile | None:
        """Resolve one agent by id from the current catalog.

        Args:
            agent_id: Agent identifier.

        Returns:
            Matching profile when available.
        """
        return self.load_catalog().get(agent_id)

    def _iter_agent_files(self) -> tuple[Path, ...]:
        """Return deterministic ordered agent definition files.

        Returns:
            Ordered list of YAML and legacy markdown files.
        """
        yaml_files: list[Path] = []
        for pattern in _AGENT_YAML_GLOBS:
            yaml_files.extend(self._root_dir.glob(pattern))
        markdown_files = list(self._root_dir.glob("*.md"))
        return tuple(sorted([*yaml_files, *markdown_files]))


def _parse_agent_file(path: Path) -> AgentProfile:
    """Parse one agent markdown file into profile model.

    Args:
        path: Agent markdown path.

    Returns:
        Parsed agent profile.

    Raises:
        AgentRepositoryError: If frontmatter/body is malformed.
    """
    if path.suffix in {".yaml", ".yml"}:
        metadata = _parse_agent_yaml(path)
    else:
        metadata = _parse_agent_markdown(path)
    agent_id = metadata.agent_id.strip().lower()
    try:
        return AgentProfile(
            agent_id=agent_id,
            summary=metadata.summary.strip(),
            policy=metadata.policy.strip().lower(),
            declared_tools=tuple(
                sorted(tool.strip() for tool in metadata.declared_tools)
            ),
        )
    except ValidationError as exc:
        raise AgentRepositoryError(
            f"Invalid agent profile '{path.name}': {exc}"
        ) from exc


def _validate_unique_agent_ids(profiles: list[AgentProfile]) -> None:
    """Validate there are no duplicate agent identifiers.

    Args:
        profiles: Parsed profiles from disk.

    Raises:
        AgentRepositoryError: If duplicate ids are present.
    """
    counts: dict[str, int] = {}
    for profile in profiles:
        counts[profile.agent_id] = counts.get(profile.agent_id, 0) + 1
    duplicates = sorted(agent_id for agent_id, count in counts.items() if count > 1)
    if duplicates:
        joined = ", ".join(duplicates)
        raise AgentRepositoryError(f"Duplicate agent id(s) detected: {joined}.")


def _parse_agent_markdown(path: Path) -> _AgentFrontmatter:
    """Parse legacy markdown frontmatter into agent metadata.

    Args:
        path: Legacy markdown agent path.

    Returns:
        Parsed metadata.

    Raises:
        AgentRepositoryError: If markdown payload is malformed.
    """
    raw = path.read_text(encoding="utf-8")
    frontmatter, body = _extract_frontmatter(raw)
    if not body.strip():
        raise AgentRepositoryError(
            f"Agent '{path.name}' must include body text describing execution role."
        )
    return _parse_frontmatter(frontmatter, path)


def _parse_agent_yaml(path: Path) -> _AgentFrontmatter:
    """Parse schema-first agent YAML payload.

    Args:
        path: YAML agent contract path.

    Returns:
        Parsed metadata.

    Raises:
        AgentRepositoryError: If YAML is malformed or schema-invalid.
    """
    try:
        parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise AgentRepositoryError(
            f"Invalid agent YAML in '{path.name}': {exc}"
        ) from exc
    if parsed is None:
        parsed = {}
    if not isinstance(parsed, dict):
        raise AgentRepositoryError(
            f"Invalid agent YAML in '{path.name}': expected mapping payload."
        )
    try:
        return _AgentFrontmatter.model_validate(cast(dict[str, Any], parsed))
    except ValidationError as exc:
        raise AgentRepositoryError(
            f"Invalid agent YAML in '{path.name}': {exc}"
        ) from exc


def _extract_frontmatter(raw: str) -> tuple[str | None, str]:
    """Split markdown into optional frontmatter and body.

    Args:
        raw: Raw markdown text.

    Returns:
        Optional frontmatter YAML and markdown body.

    Raises:
        AgentRepositoryError: If frontmatter start is missing a close delimiter.
    """
    lines = raw.splitlines()
    if not lines or lines[0].strip() != _FRONTMATTER_DELIMITER:
        return None, raw
    end_idx = -1
    for idx in range(1, len(lines)):
        if lines[idx].strip() == _FRONTMATTER_DELIMITER:
            end_idx = idx
            break
    if end_idx == -1:
        raise AgentRepositoryError(
            "Invalid agent frontmatter: missing closing delimiter."
        )
    frontmatter = "\n".join(lines[1:end_idx])
    body = "\n".join(lines[end_idx + 1 :]).lstrip("\n")
    return frontmatter, body


def _parse_frontmatter(frontmatter: str | None, path: Path) -> _AgentFrontmatter:
    """Validate agent frontmatter mapping.

    Args:
        frontmatter: Optional YAML frontmatter text.
        path: Source path for error context.

    Returns:
        Validated metadata.

    Raises:
        AgentRepositoryError: If YAML or schema is invalid.
    """
    parsed = {} if frontmatter is None else yaml.safe_load(frontmatter)
    if parsed is None:
        parsed = {}
    if not isinstance(parsed, dict):
        raise AgentRepositoryError(
            f"Invalid agent frontmatter in '{path.name}': expected mapping."
        )
    try:
        return _AgentFrontmatter.model_validate(cast(dict[str, Any], parsed))
    except ValidationError as exc:
        raise AgentRepositoryError(
            f"Invalid agent frontmatter in '{path.name}': {exc}"
        ) from exc
