"""Layer 6: Load pack definitions from local Python modules."""

from __future__ import annotations

import importlib
import re
from typing import NoReturn

from lily.kernel.pack_models import PackDefinition
from lily.kernel.run import KERNEL_VERSION


def _parse_version(version: str) -> tuple[int, ...]:
    """Parse a version string into a tuple of integers for comparison. Handles 0.1.0, 0.1.0-dev, etc."""
    # Take the first part that looks like semver (digits and dots)
    match = re.match(r"^(\d+(?:\.\d+)*)", version.strip())
    if not match:
        return (0,)
    parts = match.group(1).split(".")
    return tuple(int(p) for p in parts)


def _kernel_satisfies(minimum_kernel_version: str) -> bool:
    """Return True if current kernel version >= pack's minimum_kernel_version."""
    current = _parse_version(KERNEL_VERSION)
    required = _parse_version(minimum_kernel_version)
    # Pad with zeros so (0, 1) vs (0, 1, 0) compares correctly
    n = max(len(current), len(required))
    current_padded = current + (0,) * (n - len(current))
    required_padded = required + (0,) * (n - len(required))
    return current_padded >= required_padded


def _fail(message: str) -> NoReturn:
    raise ValueError(message)


def load_pack(module_path: str) -> PackDefinition:
    """
    Load a pack definition from a Python module.
    The module must export PACK_DEFINITION (a PackDefinition instance).
    Validates minimum_kernel_version and structure; fails fast on error.
    """
    try:
        mod = importlib.import_module(module_path)
    except Exception as e:
        _fail(f"Failed to import pack module {module_path!r}: {e}")

    if not hasattr(mod, "PACK_DEFINITION"):
        _fail(f"Pack module {module_path!r} has no PACK_DEFINITION export")

    raw = getattr(mod, "PACK_DEFINITION")
    if not isinstance(raw, PackDefinition):
        _fail(
            f"PACK_DEFINITION in {module_path!r} must be a PackDefinition instance, got {type(raw).__name__}"
        )

    if not _kernel_satisfies(raw.minimum_kernel_version):
        _fail(
            f"Pack {raw.name!r} requires minimum_kernel_version {raw.minimum_kernel_version!r}; "
            f"current kernel is {KERNEL_VERSION!r}"
        )

    return raw


def load_packs(module_paths: list[str]) -> list[PackDefinition]:
    """Load multiple pack definitions from Python modules. Order preserved; fails fast on first error."""
    return [load_pack(path) for path in module_paths]
