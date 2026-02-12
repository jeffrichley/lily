"""Unit tests for Layer 6 pack loader."""

from __future__ import annotations

import pytest

from lily.kernel.pack_loader import load_pack, load_packs

_FIXTURE_MODULE = "unit.pack_fixtures.sample_pack_for_loader"
_OLD_KERNEL_MODULE = "unit.pack_fixtures.sample_pack_old_kernel"
_NO_EXPORT_MODULE = "unit.pack_fixtures.sample_pack_no_export"
_WRONG_TYPE_MODULE = "unit.pack_fixtures.sample_pack_wrong_type"


def test_valid_pack_loads() -> None:
    """Valid pack module with PACK_DEFINITION loads successfully."""
    pack = load_pack(_FIXTURE_MODULE)
    assert pack.name == "sample_pack"
    assert pack.version == "1.0.0"
    assert pack.minimum_kernel_version == "0.1.0"


def test_load_packs_multiple() -> None:
    """load_packs loads multiple modules and preserves order."""
    packs = load_packs([_FIXTURE_MODULE, _FIXTURE_MODULE])
    assert len(packs) == 2
    assert packs[0].name == packs[1].name == "sample_pack"


def test_missing_pack_definition_fails() -> None:
    """Module without PACK_DEFINITION raises ValueError."""
    with pytest.raises(ValueError, match="no PACK_DEFINITION export"):
        load_pack(_NO_EXPORT_MODULE)


def test_version_mismatch_fails() -> None:
    """Pack requiring newer kernel than current raises ValueError."""
    with pytest.raises(ValueError, match="requires minimum_kernel_version.*99\\.0\\.0"):
        load_pack(_OLD_KERNEL_MODULE)


def test_invalid_structure_fails() -> None:
    """PACK_DEFINITION that is not a PackDefinition instance raises ValueError."""
    with pytest.raises(ValueError, match="must be a PackDefinition instance"):
        load_pack(_WRONG_TYPE_MODULE)


def test_nonexistent_module_fails() -> None:
    """Import of non-existent module raises ValueError (wrapping ImportError)."""
    with pytest.raises(ValueError, match="Failed to import pack module"):
        load_pack("nonexistent.module.path.that.does.not.exist")
