"""Pytest configuration and shared fixtures."""

from pathlib import Path

import pytest


@pytest.fixture
def workspace_root(tmp_path: Path) -> Path:
    """Temporary workspace root (e.g. project root). .iris will be created under it."""
    return tmp_path
