"""Minimal in-process metrics with a Prometheus text exposition endpoint.

Deliberately dependency-free: counters and a duration histogram are enough
to demonstrate real observability (rate, errors, duration) without pulling
a metrics stack into the free-tier deployment. The format is Prometheus-
compatible, so a real Prometheus can scrape /metrics unchanged.
"""

import threading
from collections import defaultdict

_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests: dict[tuple[str, str, int], int] = defaultdict(int)
        self._duration_buckets: dict[float, int] = dict.fromkeys(_BUCKETS, 0)
        self._duration_sum = 0.0
        self._duration_count = 0
        self._agent_turns: dict[tuple[str, bool], int] = defaultdict(int)
        self._safety_flags = 0

    def observe_request(self, method: str, path: str, status: int, seconds: float) -> None:
        with self._lock:
            self._requests[(method, path, status)] += 1
            self._duration_sum += seconds
            self._duration_count += 1
            for bucket in _BUCKETS:
                if seconds <= bucket:
                    self._duration_buckets[bucket] += 1

    def observe_agent_turn(self, provider: str, degraded: bool, flags: int) -> None:
        with self._lock:
            self._agent_turns[(provider, degraded)] += 1
            self._safety_flags += flags

    def render(self) -> str:
        with self._lock:
            lines = [
                "# HELP tejasri_requests_total HTTP requests by method, path, status",
                "# TYPE tejasri_requests_total counter",
            ]
            lines += [
                f'tejasri_requests_total{{method="{m}",path="{p}",status="{s}"}} {count}'
                for (m, p, s), count in sorted(self._requests.items())
            ]
            lines += [
                "# HELP tejasri_request_duration_seconds Request latency",
                "# TYPE tejasri_request_duration_seconds histogram",
            ]
            lines += [
                f'tejasri_request_duration_seconds_bucket{{le="{b}"}} {count}'
                for b, count in self._duration_buckets.items()
            ]
            lines += [
                f'tejasri_request_duration_seconds_bucket{{le="+Inf"}} {self._duration_count}',
                f"tejasri_request_duration_seconds_sum {self._duration_sum:.6f}",
                f"tejasri_request_duration_seconds_count {self._duration_count}",
                "# HELP tejasri_agent_turns_total Agent turns by provider and degradation",
                "# TYPE tejasri_agent_turns_total counter",
            ]
            lines += [
                f'tejasri_agent_turns_total{{provider="{prov}",degraded="{str(deg).lower()}"}} {c}'
                for (prov, deg), c in sorted(self._agent_turns.items())
            ]
            lines += [
                "# HELP tejasri_safety_flags_total Safety flags raised by the engine",
                "# TYPE tejasri_safety_flags_total counter",
                f"tejasri_safety_flags_total {self._safety_flags}",
            ]
            return "\n".join(lines) + "\n"


metrics = MetricsRegistry()
