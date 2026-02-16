"""File-backed persona catalog loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from lily.persona.models import PersonaCatalog, PersonaProfile

_FRONTMATTER_DELIMITER = "---"


class PersonaRepositoryError(RuntimeError):
    """Raised when persona files cannot be loaded deterministically."""


class _PersonaFrontmatter(BaseModel):
    """Validated persona frontmatter fields."""

    model_config = ConfigDict(extra="forbid")

    summary: str = ""
    default_style: str = "balanced"
    persona_id: str | None = Field(default=None, alias="id")


class FilePersonaRepository:
    """Load persona profiles from markdown files in one root directory."""

    def __init__(self, *, root_dir: Path) -> None:
        """Create repository for one persona root.

        Args:
            root_dir: Persona markdown directory.
        """
        self._root_dir = root_dir

    def load_catalog(self) -> PersonaCatalog:
        """Load all persona profiles into a deterministic catalog.

        Returns:
            Sorted persona catalog.

        Raises:
            PersonaRepositoryError: If one or more persona files are invalid.
        """
        if not self._root_dir.exists():
            return PersonaCatalog(personas=())
        if not self._root_dir.is_dir():
            raise PersonaRepositoryError(
                f"Persona root is not a directory: {self._root_dir}"
            )

        profiles = [
            _parse_persona_file(path) for path in sorted(self._root_dir.glob("*.md"))
        ]
        ordered = tuple(sorted(profiles, key=lambda profile: profile.persona_id))
        return PersonaCatalog(personas=ordered)

    def get(self, persona_id: str) -> PersonaProfile | None:
        """Resolve one persona by id from the current catalog.

        Args:
            persona_id: Persona identifier.

        Returns:
            Matching profile when available.
        """
        return self.load_catalog().get(persona_id)


def default_persona_root() -> Path:
    """Return default bundled persona directory.

    Returns:
        Repository root for bundled persona profiles.
    """
    return Path(__file__).resolve().parents[3] / "personas"


def _parse_persona_file(path: Path) -> PersonaProfile:
    """Parse one persona markdown file into profile model.

    Args:
        path: Persona markdown path.

    Returns:
        Parsed persona profile.

    Raises:
        PersonaRepositoryError: If frontmatter/body is malformed.
    """
    raw = path.read_text(encoding="utf-8")
    frontmatter, body = _extract_frontmatter(raw)
    metadata = _parse_frontmatter(frontmatter, path)
    persona_id = (metadata.persona_id or path.stem).strip().lower()
    instructions = body.strip()
    if not instructions:
        raise PersonaRepositoryError(
            f"Persona '{path.name}' must include instruction body text."
        )
    try:
        return PersonaProfile(
            persona_id=persona_id,
            summary=metadata.summary.strip(),
            default_style=metadata.default_style.strip().lower(),
            instructions=instructions,
        )
    except ValidationError as exc:
        raise PersonaRepositoryError(
            f"Invalid persona profile '{path.name}': {exc}"
        ) from exc


def _extract_frontmatter(raw: str) -> tuple[str | None, str]:
    """Split markdown into optional frontmatter and body.

    Args:
        raw: Raw markdown text.

    Returns:
        Optional frontmatter YAML and markdown body.

    Raises:
        PersonaRepositoryError: If frontmatter start is missing a close delimiter.
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
        raise PersonaRepositoryError(
            "Invalid persona frontmatter: missing closing delimiter."
        )
    frontmatter = "\n".join(lines[1:end_idx])
    body = "\n".join(lines[end_idx + 1 :]).lstrip("\n")
    return frontmatter, body


def _parse_frontmatter(frontmatter: str | None, path: Path) -> _PersonaFrontmatter:
    """Validate persona frontmatter mapping.

    Args:
        frontmatter: Optional YAML frontmatter text.
        path: Source path for error context.

    Returns:
        Validated metadata.

    Raises:
        PersonaRepositoryError: If YAML or schema is invalid.
    """
    if frontmatter is None:
        return _PersonaFrontmatter()
    parsed = yaml.safe_load(frontmatter)
    if parsed is None:
        parsed = {}
    if not isinstance(parsed, dict):
        raise PersonaRepositoryError(
            f"Invalid persona frontmatter in '{path.name}': expected mapping."
        )
    try:
        return _PersonaFrontmatter.model_validate(cast(dict[str, Any], parsed))
    except ValidationError as exc:
        raise PersonaRepositoryError(
            f"Invalid persona frontmatter in '{path.name}': {exc}"
        ) from exc
