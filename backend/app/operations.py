"""Small dependency-free operational telemetry and abuse controls."""

from __future__ import annotations

import threading
import time
from collections import Counter, defaultdict, deque
from typing import Any


class OperationsMonitor:
    def __init__(self) -> None:
        self.started_at = time.time()
        self._lock = threading.RLock()
        self._requests = 0
        self._latency_ms = 0.0
        self._statuses: Counter[int] = Counter()
        self._paths: Counter[str] = Counter()

    def observe(self, path: str, status: int, latency_ms: float) -> None:
        with self._lock:
            self._requests += 1
            self._latency_ms += latency_ms
            self._statuses[status] += 1
            self._paths[path] += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "uptime_seconds": round(time.time() - self.started_at, 3),
                "requests_total": self._requests,
                "average_latency_ms": round(self._latency_ms / self._requests, 3) if self._requests else 0.0,
                "status_counts": {str(key): value for key, value in sorted(self._statuses.items())},
                "top_api_paths": [
                    {"path": path, "requests": count}
                    for path, count in self._paths.most_common(12)
                ],
            }

    def prometheus(self) -> str:
        value = self.snapshot()
        lines = [
            "# HELP sentinel_uptime_seconds Process uptime.",
            "# TYPE sentinel_uptime_seconds gauge",
            f"sentinel_uptime_seconds {value['uptime_seconds']}",
            "# HELP sentinel_http_requests_total HTTP requests by status.",
            "# TYPE sentinel_http_requests_total counter",
        ]
        lines.extend(
            f'sentinel_http_requests_total{{status="{status}"}} {count}'
            for status, count in value["status_counts"].items()
        )
        lines.extend(
            [
                "# HELP sentinel_http_latency_average_ms Mean observed HTTP latency.",
                "# TYPE sentinel_http_latency_average_ms gauge",
                f"sentinel_http_latency_average_ms {value['average_latency_ms']}",
            ]
        )
        return "\n".join(lines) + "\n"


class SlidingWindowRateLimiter:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        if limit <= 0:
            return True
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            bucket = self._requests[key]
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                return False
            bucket.append(now)
            return True


operations_monitor = OperationsMonitor()
rate_limiter = SlidingWindowRateLimiter()
