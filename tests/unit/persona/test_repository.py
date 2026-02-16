"""Unit tests for file-backed persona repository."""

from __future__ import annotations

from pathlib import Path

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


def test_repository_loads_sorted_catalog_and_get(tmp_path: Path) -> None:
    """Repository should return deterministic sorted catalog and exact get."""
    root = tmp_path / "personas"
    _write_persona(root, name="chad", style="playful")
    _write_persona(root, name="barbie", style="playful")
    _write_persona(root, name="lily", style="focus")

    repository = FilePersonaRepository(root_dir=root)
    catalog = repository.load_catalog()

    assert [profile.persona_id for profile in catalog.personas] == [
        "barbie",
        "chad",
        "lily",
    ]
    lily = repository.get("lily")
    assert lily is not None
    assert lily.default_style.value == "focus"


def test_repository_returns_empty_catalog_when_root_missing(tmp_path: Path) -> None:
    """Missing persona root should return empty deterministic catalog."""
    repository = FilePersonaRepository(root_dir=tmp_path / "missing")

    catalog = repository.load_catalog()

    assert catalog.personas == ()


def test_repository_reload_refreshes_cached_catalog(tmp_path: Path) -> None:
    """Repository should keep cache stable until explicit reload."""
    root = tmp_path / "personas"
    _write_persona(root, name="lily", style="focus")
    repository = FilePersonaRepository(root_dir=root)

    first = repository.load_catalog()
    _write_persona(root, name="chad", style="playful")
    still_cached = repository.load_catalog()
    reloaded = repository.reload_catalog()

    assert [profile.persona_id for profile in first.personas] == ["lily"]
    assert [profile.persona_id for profile in still_cached.personas] == ["lily"]
    assert [profile.persona_id for profile in reloaded.personas] == ["chad", "lily"]


def test_repository_export_and_import_roundtrip(tmp_path: Path) -> None:
    """Repository should export and import personas deterministically."""
    root = tmp_path / "personas"
    _write_persona(root, name="lily", style="focus")
    repository = FilePersonaRepository(root_dir=root)
    export_path = tmp_path / "exports" / "lily.md"

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

    assert imported.persona_id == "zen"
    assert (root / "zen.md").exists()
