"""Health endpoint contract tests."""

from httpx import AsyncClient

from tejasri import __version__


async def test_health_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__
    assert body["environment"] in {"development", "test", "production"}


async def test_every_response_carries_a_trace_id(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.headers.get("x-request-id")


async def test_caller_supplied_trace_id_is_propagated(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health", headers={"x-request-id": "trace-abc-123"})
    assert response.headers["x-request-id"] == "trace-abc-123"
