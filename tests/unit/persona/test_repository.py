"""Unit tests for file-backed persona repository."""

from __future__ import annotations

from pathlib import Path

import pytest

from lily.persona import FilePersonaRepository


def _write_persona(root: Path, *, name: str, style: str) -> None:
    """Write one persona markdown fixture.

    Args:
        root: Persona root directory.
        name: Persona id and filename stem.
        style: Default style string.
    """
    root.mkdir(parents=True, exist_ok=True)
    (root / f"{name}.md").write_text(
        (
            "---\n"
            f"id: {name}\n"
            f"summary: {name} summary\n"
            f"default_style: {style}\n"
            "---\n"
            f"You are {name}.\n"
        ),
        encoding="utf-8",
    )


@pytest.mark.unit
def test_repository_loads_sorted_catalog_and_get(tmp_path: Path) -> None:
    """Repository should return deterministic sorted catalog and exact get."""
    # Arrange - persona dir with chad, barbie, lily
    root = tmp_path / "personas"
    _write_persona(root, name="chad", style="playful")
    _write_persona(root, name="barbie", style="playful")
    _write_persona(root, name="lily", style="focus")

    repository = FilePersonaRepository(root_dir=root)
    # Act - load catalog and get lily
    catalog = repository.load_catalog()

    # Assert - sorted catalog and get returns lily with focus
    assert [profile.persona_id for profile in catalog.personas] == [
        "barbie",
        "chad",
        "lily",
    ]
    lily = repository.get("lily")
    assert lily is not None
    assert lily.default_style.value == "focus"


@pytest.mark.unit
def test_repository_returns_empty_catalog_when_root_missing(tmp_path: Path) -> None:
    """Missing persona root should return empty deterministic catalog."""
    # Arrange - repository with missing root
    repository = FilePersonaRepository(root_dir=tmp_path / "missing")

    # Act - load catalog
    catalog = repository.load_catalog()

    # Assert - empty catalog
    assert catalog.personas == ()


@pytest.mark.unit
def test_repository_reload_refreshes_cached_catalog(tmp_path: Path) -> None:
    """Repository should keep cache stable until explicit reload."""
    # Arrange - root with lily, repository
    root = tmp_path / "personas"
    _write_persona(root, name="lily", style="focus")
    repository = FilePersonaRepository(root_dir=root)

    # Act - load, add chad on disk, load again, reload
    first = repository.load_catalog()
    _write_persona(root, name="chad", style="playful")
    still_cached = repository.load_catalog()
    reloaded = repository.reload_catalog()

    # Assert - first and still_cached show lily only; reloaded shows both
    assert [profile.persona_id for profile in first.personas] == ["lily"]
    assert [profile.persona_id for profile in still_cached.personas] == ["lily"]
    assert [profile.persona_id for profile in reloaded.personas] == ["chad", "lily"]


@pytest.mark.unit
def test_repository_export_and_import_roundtrip(tmp_path: Path) -> None:
    """Repository should export and import personas deterministically."""
    # Arrange - root with lily, repository, export path, incoming zen file
    root = tmp_path / "personas"
    _write_persona(root, name="lily", style="focus")
    repository = FilePersonaRepository(root_dir=root)
    export_path = tmp_path / "exports" / "lily.md"

    # Act - export lily then import zen
    written = repository.export_persona(persona_id="lily", destination=export_path)
    assert written == export_path
    assert export_path.exists()

    imported_source = tmp_path / "incoming" / "zen.md"
    imported_source.parent.mkdir(parents=True, exist_ok=True)
    imported_source.write_text(
        (
            "---\n"
            "id: zen\n"
            "summary: Calm and focused helper\n"
            "default_style: balanced\n"
            "---\n"
            "You are zen.\n"
        ),
        encoding="utf-8",
    )
    imported = repository.import_persona(source=imported_source)

    # Assert - zen imported and file exists
    assert imported.persona_id == "zen"
    assert (root / "zen.md").exists()
