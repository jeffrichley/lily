"""Unit tests for Layer 6 pack loader."""

from __future__ import annotations

import pytest

from lily.kernel.pack_loader import load_pack, load_packs

_FIXTURE_MODULE = "tests.unit.pack_fixtures.sample_pack_for_loader"
_OLD_KERNEL_MODULE = "tests.unit.pack_fixtures.sample_pack_old_kernel"
_NO_EXPORT_MODULE = "tests.unit.pack_fixtures.sample_pack_no_export"
_WRONG_TYPE_MODULE = "tests.unit.pack_fixtures.sample_pack_wrong_type"


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


@pytest.mark.parametrize(
    "module_path,match",
    [
        (_NO_EXPORT_MODULE, "no PACK_DEFINITION export"),
        (_OLD_KERNEL_MODULE, r"requires minimum_kernel_version.*99\.0\.0"),
        (_WRONG_TYPE_MODULE, "must be a PackDefinition instance"),
        ("nonexistent.module.path.that.does.not.exist", "Failed to import pack module"),
    ],
    ids=[
        "missing_pack_definition",
        "version_mismatch",
        "invalid_structure",
        "nonexistent_module",
    ],
)
def test_load_pack_fails(module_path: str, match: str) -> None:
    """load_pack raises ValueError with expected message for invalid or missing modules."""
    with pytest.raises(ValueError, match=match):
        load_pack(module_path)
