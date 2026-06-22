"""Metrics for Laputa governance operations.

Translated from agent-diva-laputa/src/metrics.rs
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class LaputaMetricsSnapshot:
    """Point-in-time snapshot of Laputa metrics."""

    writes: int = 0
    write_errors: int = 0
    rollbacks: int = 0
    governance_failures: int = 0


class LaputaMetrics:
    """Thread-safe metrics counters for Laputa operations."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._writes = 0
        self._write_errors = 0
        self._rollbacks = 0
        self._governance_failures = 0

    def record_write(self) -> None:
        with self._lock:
            self._writes += 1

    def record_write_error(self) -> None:
        with self._lock:
            self._write_errors += 1

    def record_rollback(self) -> None:
        with self._lock:
            self._rollbacks += 1

    def record_governance_failure(self) -> None:
        with self._lock:
            self._governance_failures += 1

    def snapshot(self) -> LaputaMetricsSnapshot:
        with self._lock:
            return LaputaMetricsSnapshot(
                writes=self._writes,
                write_errors=self._write_errors,
                rollbacks=self._rollbacks,
                governance_failures=self._governance_failures,
            )

    def reset(self) -> None:
        with self._lock:
            self._writes = 0
            self._write_errors = 0
            self._rollbacks = 0
            self._governance_failures = 0
