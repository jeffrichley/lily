"""Unit tests for memory observability counters."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from importlib import import_module

import pytest

from lily.observability import memory_metrics

_FIXED_NOW = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)
_MEMORY_METRICS_MODULE = import_module("lily.observability.memory_metrics")


class _FrozenDateTime:
    """Deterministic datetime replacement for freshness bucket tests."""

    @staticmethod
    def now(tz: object) -> datetime:
        """Return fixed UTC timestamp for deterministic bucket boundaries."""
        del tz
        return _FIXED_NOW


@pytest.mark.unit
def test_memory_metrics_snapshot_includes_expected_counters() -> None:
    """Snapshot should include required counters and subdomain rates."""
    # Arrange - reset and record write/denied/read/retrieval/consolidation/verified
    memory_metrics.reset()
    memory_metrics.record_write(namespace="user_profile/workspace:x/persona:lily")
    memory_metrics.record_denied_write(
        namespace="working_rules/workspace:x/persona:lily"
    )
    memory_metrics.record_read(namespace="task_memory/task:alpha", hit_count=2)
    memory_metrics.record_retrieval(hit_count=1)
    memory_metrics.record_consolidation(proposed=4, written=3, skipped=1)
    memory_metrics.record_last_verified(last_verified=_FIXED_NOW)
    # Act - snapshot
    snapshot = memory_metrics.snapshot().to_dict()

    # Assert - expected counters and subdomains
    assert snapshot["write_counts"] == 1
    assert snapshot["denied_writes"] == 1
    assert snapshot["retrieval_hit_rate"] == 1.0
    assert snapshot["consolidation_drift_indicator"] == 0.25
    subdomain = snapshot["per_subdomain_read_write_rates"]
    assert "user_profile" in subdomain
    assert "task_memory" in subdomain


@pytest.mark.unit
def test_memory_metrics_last_verified_distribution_has_buckets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Snapshot should bucket last-verified ages deterministically."""
    # Arrange - reset and record never, 10d, 100d verified
    memory_metrics.reset()
    monkeypatch.setattr(_MEMORY_METRICS_MODULE, "datetime", _FrozenDateTime)
    memory_metrics.record_last_verified(last_verified=None)
    memory_metrics.record_last_verified(last_verified=_FIXED_NOW - timedelta(days=10))
    memory_metrics.record_last_verified(last_verified=_FIXED_NOW - timedelta(days=100))
    # Act - snapshot and get distribution
    distribution = memory_metrics.snapshot().to_dict()[
        "last_verified_freshness_distribution"
    ]
    # Assert - buckets populated
    assert distribution["never_verified"] == 1
    assert distribution["8_30_days"] == 1
    assert distribution["91_plus_days"] == 1
