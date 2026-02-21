"""Unit tests for jobs composition root."""

from __future__ import annotations

from pathlib import Path

import pytest

from lily.runtime.jobs_factory import JobsFactory
from lily.runtime.runtime_dependencies import JobsSpec


@pytest.mark.unit
def test_jobs_factory_build_without_scheduler(tmp_path: Path) -> None:
    """Jobs factory should build executor paths without scheduler runtime."""
    # Arrange - factory and disabled scheduler spec
    factory = JobsFactory()
    spec = JobsSpec(workspace_root=tmp_path, scheduler_enabled=False)

    # Act - build jobs bundle
    bundle = factory.build(spec)

    # Assert - runs root and scheduler fields are deterministic
    assert bundle.runs_root == tmp_path / "runs"
    assert bundle.scheduler_control is None
    assert bundle.scheduler_runtime is None


@pytest.mark.unit
def test_jobs_factory_build_with_scheduler(tmp_path: Path) -> None:
    """Jobs factory should optionally build/start scheduler runtime."""
    # Arrange - factory with enabled scheduler spec
    factory = JobsFactory()
    spec = JobsSpec(workspace_root=tmp_path, scheduler_enabled=True)

    # Act - build jobs bundle
    bundle = factory.build(spec)

    # Assert - scheduler is present and can be shutdown cleanly
    try:
        assert bundle.scheduler_runtime is not None
        assert bundle.scheduler_control is bundle.scheduler_runtime
        assert (tmp_path / "runs") == bundle.runs_root
    finally:
        if bundle.scheduler_runtime is not None:
            bundle.scheduler_runtime.shutdown()
