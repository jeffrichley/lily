"""Unit tests for memory observability counters."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from lily.observability import memory_metrics


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
    memory_metrics.record_last_verified(last_verified=datetime.now(UTC))
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
def test_memory_metrics_last_verified_distribution_has_buckets() -> None:
    """Snapshot should bucket last-verified ages deterministically."""
    # Arrange - reset and record never, 10d, 100d verified
    memory_metrics.reset()
    memory_metrics.record_last_verified(last_verified=None)
    memory_metrics.record_last_verified(
        last_verified=datetime.now(UTC) - timedelta(days=10)
    )
    memory_metrics.record_last_verified(
        last_verified=datetime.now(UTC) - timedelta(days=100)
    )
    # Act - snapshot and get distribution
    distribution = memory_metrics.snapshot().to_dict()[
        "last_verified_freshness_distribution"
    ]
    # Assert - buckets populated
    assert distribution["never_verified"] == 1
    assert distribution["8_30_days"] == 1
    assert distribution["91_plus_days"] == 1
