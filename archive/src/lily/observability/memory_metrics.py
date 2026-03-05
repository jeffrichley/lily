"""In-process observability counters for memory migration metrics."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock
from typing import Any

_FRESHNESS_7_DAYS = 7
_FRESHNESS_30_DAYS = 30
_FRESHNESS_90_DAYS = 90


@dataclass(frozen=True)
class MemoryMetricsSnapshot:
    """Immutable memory observability snapshot."""

    total_writes: int
    total_denied_writes: int
    total_reads: int
    total_read_hits: int
    retrieval_queries: int
    retrieval_hits: int
    consolidation_runs: int
    consolidation_proposed_total: int
    consolidation_written_total: int
    consolidation_skipped_total: int
    per_subdomain_write_counts: dict[str, int]
    per_subdomain_read_counts: dict[str, int]
    per_subdomain_write_rates: dict[str, float]
    per_subdomain_read_rates: dict[str, float]
    last_verified_freshness_distribution: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        """Convert snapshot to deterministic mapping.

        Returns:
            Snapshot mapping for reports.
        """
        drift_ratio = 0.0
        if self.consolidation_proposed_total > 0:
            drift_ratio = self.consolidation_skipped_total / float(
                self.consolidation_proposed_total
            )
        retrieval_hit_rate = 0.0
        if self.retrieval_queries > 0:
            retrieval_hit_rate = self.retrieval_hits / float(self.retrieval_queries)
        return {
            "write_counts": self.total_writes,
            "denied_writes": self.total_denied_writes,
            "retrieval_hit_rate": round(retrieval_hit_rate, 4),
            "retrieval_hits": self.total_read_hits,
            "consolidation_drift_indicator": round(drift_ratio, 4),
            "consolidation_runs": self.consolidation_runs,
            "per_subdomain_read_write_rates": {
                key: {
                    "read_rate": self.per_subdomain_read_rates.get(key, 0.0),
                    "write_rate": self.per_subdomain_write_rates.get(key, 0.0),
                    "read_count": self.per_subdomain_read_counts.get(key, 0),
                    "write_count": self.per_subdomain_write_counts.get(key, 0),
                }
                for key in sorted(
                    {
                        *self.per_subdomain_read_counts.keys(),
                        *self.per_subdomain_write_counts.keys(),
                    }
                )
            },
            "last_verified_freshness_distribution": dict(
                self.last_verified_freshness_distribution
            ),
        }


class MemoryMetricsCollector:
    """Thread-safe in-process counters for memory observability."""

    def __init__(self) -> None:
        """Initialize empty counters."""
        self._lock = Lock()
        self._reset_state()

    def reset(self) -> None:
        """Reset counters for deterministic test isolation."""
        with self._lock:
            self._reset_state()

    def record_write(self, *, namespace: str) -> None:
        """Record one successful memory write.

        Args:
            namespace: Memory namespace token.
        """
        with self._lock:
            self._total_writes += 1
            self._subdomain_writes[_subdomain(namespace)] += 1

    def record_denied_write(self, *, namespace: str) -> None:
        """Record one policy-denied write attempt.

        Args:
            namespace: Memory namespace token.
        """
        with self._lock:
            self._total_denied_writes += 1
            self._subdomain_denied_writes[_subdomain(namespace)] += 1

    def record_read(self, *, namespace: str, hit_count: int) -> None:
        """Record one read operation and resulting hit count.

        Args:
            namespace: Memory namespace token.
            hit_count: Number of rows returned.
        """
        with self._lock:
            self._total_reads += 1
            self._total_read_hits += max(hit_count, 0)
            self._subdomain_reads[_subdomain(namespace)] += 1

    def record_retrieval(self, *, hit_count: int) -> None:
        """Record one prompt-memory retrieval event.

        Args:
            hit_count: Number of selected retrieval rows.
        """
        with self._lock:
            self._retrieval_queries += 1
            if hit_count > 0:
                self._retrieval_hits += 1

    def record_consolidation(
        self,
        *,
        proposed: int,
        written: int,
        skipped: int,
    ) -> None:
        """Record one consolidation run summary.

        Args:
            proposed: Proposed record count.
            written: Written record count.
            skipped: Skipped record count.
        """
        with self._lock:
            self._consolidation_runs += 1
            self._consolidation_proposed_total += max(proposed, 0)
            self._consolidation_written_total += max(written, 0)
            self._consolidation_skipped_total += max(skipped, 0)

    def record_last_verified(self, *, last_verified: datetime | None) -> None:
        """Record one last-verified freshness datapoint.

        Args:
            last_verified: Last verification timestamp, if present.
        """
        with self._lock:
            self._freshness[_freshness_bucket(last_verified)] += 1

    def snapshot(self) -> MemoryMetricsSnapshot:
        """Build immutable snapshot of current counters.

        Returns:
            Immutable metrics snapshot.
        """
        with self._lock:
            write_rates = _rates(self._subdomain_writes, self._total_writes)
            read_rates = _rates(self._subdomain_reads, self._total_reads)
            return MemoryMetricsSnapshot(
                total_writes=self._total_writes,
                total_denied_writes=self._total_denied_writes,
                total_reads=self._total_reads,
                total_read_hits=self._total_read_hits,
                retrieval_queries=self._retrieval_queries,
                retrieval_hits=self._retrieval_hits,
                consolidation_runs=self._consolidation_runs,
                consolidation_proposed_total=self._consolidation_proposed_total,
                consolidation_written_total=self._consolidation_written_total,
                consolidation_skipped_total=self._consolidation_skipped_total,
                per_subdomain_write_counts=dict(self._subdomain_writes),
                per_subdomain_read_counts=dict(self._subdomain_reads),
                per_subdomain_write_rates=write_rates,
                per_subdomain_read_rates=read_rates,
                last_verified_freshness_distribution=dict(self._freshness),
            )

    def _reset_state(self) -> None:
        """Reset mutable counter state."""
        self._total_writes = 0
        self._total_denied_writes = 0
        self._total_reads = 0
        self._total_read_hits = 0
        self._retrieval_queries = 0
        self._retrieval_hits = 0
        self._consolidation_runs = 0
        self._consolidation_proposed_total = 0
        self._consolidation_written_total = 0
        self._consolidation_skipped_total = 0
        self._subdomain_writes: defaultdict[str, int] = defaultdict(int)
        self._subdomain_denied_writes: defaultdict[str, int] = defaultdict(int)
        self._subdomain_reads: defaultdict[str, int] = defaultdict(int)
        self._freshness: defaultdict[str, int] = defaultdict(int)


memory_metrics = MemoryMetricsCollector()


def _subdomain(namespace: str) -> str:
    """Extract stable subdomain identifier from namespace.

    Args:
        namespace: Memory namespace token.

    Returns:
        Stable subdomain identifier.
    """
    normalized = namespace.strip().lower()
    if not normalized:
        return "unknown"
    for key in ("persona_core", "user_profile", "working_rules", "task_memory"):
        if normalized.startswith(f"{key}/") or normalized == key:
            return key
    if normalized.startswith("evidence/"):
        return "evidence"
    return "unknown"


def _freshness_bucket(last_verified: datetime | None) -> str:
    """Map last-verified timestamp to freshness bucket.

    Args:
        last_verified: Last verification timestamp, if present.

    Returns:
        Freshness bucket key.
    """
    if last_verified is None:
        return "never_verified"
    now = datetime.now(UTC)
    age_days = max((now - last_verified).days, 0)
    if age_days <= _FRESHNESS_7_DAYS:
        return "0_7_days"
    if age_days <= _FRESHNESS_30_DAYS:
        return "8_30_days"
    if age_days <= _FRESHNESS_90_DAYS:
        return "31_90_days"
    return "91_plus_days"


def _rates(counts: dict[str, int], total: int) -> dict[str, float]:
    """Compute normalized rates map from counts.

    Args:
        counts: Counter map by key.
        total: Total denominator.

    Returns:
        Normalized rate map.
    """
    if total <= 0:
        return {key: 0.0 for key in counts}
    return {key: round(value / float(total), 4) for key, value in counts.items()}
