"""End-to-end API flow against a real CockroachDB: register → login → patients."""

import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from tejasri.infrastructure.db import Database
from tejasri.main import create_app

pytestmark = pytest.mark.integration

PASSWORD = "integration-test-password"


@pytest.fixture
async def client(db: Database, configured_settings: None) -> AsyncIterator[AsyncClient]:
    app = create_app()
    app.state.database = db  # lifespan does not run under ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _register(client: AsyncClient) -> tuple[str, dict[str, Any]]:
    """Register a fresh tenant; return (admin_email, auth_response_body)."""
    email = f"admin-{uuid.uuid4()}@clinic.example"
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "tenant_name": f"clinic-{uuid.uuid4()}",
            "admin_email": email,
            "admin_password": PASSWORD,
            "admin_display_name": "Dr. Admin",
        },
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return email, body


async def test_register_login_and_patient_lifecycle(client: AsyncClient) -> None:
    email, registration = await _register(client)

    login = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200, login.text
    assert login.json()["tenant_id"] == registration["tenant_id"]

    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    created = await client.post(
        "/api/v1/patients",
        headers=headers,
        json={
            "display_name": "Asha Rao",
            "conditions": ["type 2 diabetes"],
            "allergies": ["penicillin"],
        },
    )
    assert created.status_code == 201, created.text
    patient_id = created.json()["patient_id"]

    fetched = await client.get(f"/api/v1/patients/{patient_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["display_name"] == "Asha Rao"

    listed = await client.get("/api/v1/patients", headers=headers)
    assert listed.status_code == 200
    assert any(p["patient_id"] == patient_id for p in listed.json())


async def test_login_with_wrong_password_is_rejected(client: AsyncClient) -> None:
    email, _ = await _register(client)
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "wrong-password-value"}
    )
    assert login.status_code == 401


async def test_requests_without_token_are_unauthorized(client: AsyncClient) -> None:
    response = await client.get("/api/v1/patients")
    assert response.status_code == 401


async def test_patients_are_isolated_between_tenants_via_api(client: AsyncClient) -> None:
    _, tenant_a = await _register(client)
    _, tenant_b = await _register(client)
    headers_a = {"Authorization": f"Bearer {tenant_a['access_token']}"}
    headers_b = {"Authorization": f"Bearer {tenant_b['access_token']}"}

    created = await client.post(
        "/api/v1/patients", headers=headers_a, json={"display_name": "Only In A"}
    )
    assert created.status_code == 201
    patient_id = created.json()["patient_id"]

    cross_read = await client.get(f"/api/v1/patients/{patient_id}", headers=headers_b)
    assert cross_read.status_code == 404


async def test_readiness_reports_database_ok(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
