"""Rate limiter and metrics behavior."""

from tejasri.core.metrics import MetricsRegistry
from tejasri.core.ratelimit import TokenBucketLimiter


class TestTokenBucketLimiter:
    def test_allows_up_to_capacity_then_blocks(self) -> None:
        limiter = TokenBucketLimiter(capacity=3, refill_per_minute=60)
        assert [limiter.allow("ip1") for _ in range(4)] == [True, True, True, False]

    def test_keys_are_independent(self) -> None:
        limiter = TokenBucketLimiter(capacity=1, refill_per_minute=60)
        assert limiter.allow("ip1")
        assert limiter.allow("ip2")  # a different client is unaffected
        assert not limiter.allow("ip1")

    def test_reset_restores_capacity(self) -> None:
        limiter = TokenBucketLimiter(capacity=1, refill_per_minute=60)
        assert limiter.allow("ip1")
        limiter.reset()
        assert limiter.allow("ip1")


class TestMetricsRegistry:
    def test_prometheus_exposition_contains_observations(self) -> None:
        registry = MetricsRegistry()
        registry.observe_request("GET", "/api/v1/health", 200, 0.02)
        registry.observe_agent_turn("gemini", degraded=False, flags=2)

        text = registry.render()
        assert 'tejasri_requests_total{method="GET",path="/api/v1/health",status="200"} 1' in text
        assert 'tejasri_agent_turns_total{provider="gemini",degraded="false"} 1' in text
        assert "tejasri_safety_flags_total 2" in text
        assert "tejasri_request_duration_seconds_count 1" in text
