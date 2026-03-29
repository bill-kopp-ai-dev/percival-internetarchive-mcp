from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import threading
import time
from typing import Any


@dataclass
class ToolTelemetry:
    calls: int = 0
    errors: int = 0
    total_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    last_latency_ms: float = 0.0
    last_error_code: str | None = None

    def record(self, duration_ms: float, ok: bool, error_code: str | None = None) -> None:
        self.calls += 1
        self.total_latency_ms += duration_ms
        self.last_latency_ms = duration_ms
        if duration_ms > self.max_latency_ms:
            self.max_latency_ms = duration_ms
        if not ok:
            self.errors += 1
            self.last_error_code = error_code

    def to_dict(self) -> dict[str, Any]:
        avg_latency_ms = self.total_latency_ms / self.calls if self.calls else 0.0
        return {
            "calls": self.calls,
            "errors": self.errors,
            "avg_latency_ms": round(avg_latency_ms, 3),
            "max_latency_ms": round(self.max_latency_ms, 3),
            "last_latency_ms": round(self.last_latency_ms, 3),
            "last_error_code": self.last_error_code,
        }


class TelemetryRegistry:
    def __init__(self, server_name: str):
        self._server_name = server_name
        self._started_monotonic = time.monotonic()
        self._started_at_epoch = time.time()
        self._tool_metrics: dict[str, ToolTelemetry] = {}
        self._total_calls = 0
        self._total_errors = 0
        self._lock = threading.Lock()

    def record(
        self,
        tool_name: str,
        *,
        duration_ms: float,
        ok: bool,
        error_code: str | None,
    ) -> None:
        with self._lock:
            stats = self._tool_metrics.setdefault(tool_name, ToolTelemetry())
            stats.record(duration_ms=duration_ms, ok=ok, error_code=error_code)
            self._total_calls += 1
            if not ok:
                self._total_errors += 1

    def snapshot(self, **extra: Any) -> dict[str, Any]:
        with self._lock:
            uptime_seconds = time.monotonic() - self._started_monotonic
            started_at_utc = datetime.fromtimestamp(
                self._started_at_epoch,
                tz=timezone.utc,
            ).isoformat()
            tools_dict = {
                tool_name: stats.to_dict()
                for tool_name, stats in sorted(self._tool_metrics.items())
            }
            payload: dict[str, Any] = {
                "server": {
                    "name": self._server_name,
                    "started_at_utc": started_at_utc,
                    "uptime_seconds": round(uptime_seconds, 3),
                },
                "metrics": {
                    "total_calls": self._total_calls,
                    "total_errors": self._total_errors,
                    "tools": tools_dict,
                },
            }
            if extra:
                payload.update(extra)
            return payload
