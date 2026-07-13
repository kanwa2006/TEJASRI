"""Integration fixtures — require a reachable CockroachDB (see docs/DEVELOPMENT.md).

The admin DSN (root) applies migrations and provisions the runtime user;
the application itself always connects as the least-privilege user, because
admin members bypass Row-Level Security (ADR 0006).
"""

import os
from collections.abc import AsyncIterator, Iterator
from urllib.parse import urlsplit, urlunsplit

import asyncpg
import pytest

from tejasri.cli import _APP_USER_GRANTS, APP_USER
from tejasri.core.config import get_settings
from tejasri.infrastructure.db import Database
from tejasri.infrastructure.db.migrator import apply_migrations

ADMIN_DSN = os.getenv("DATABASE_URL", "postgresql://root@localhost:26257/defaultdb?sslmode=disable")


def _with_user(dsn: str, user: str) -> str:
    parts = urlsplit(dsn)
    hostport = parts.hostname or "localhost"
    if parts.port:
        hostport = f"{hostport}:{parts.port}"
    return urlunsplit((parts.scheme, f"{user}@{hostport}", parts.path, parts.query, ""))


APP_DSN = _with_user(ADMIN_DSN, APP_USER)


@pytest.fixture
async def db() -> AsyncIterator[Database]:
    """Migrated database gateway, connected as the least-privilege app user."""
    conn = await asyncpg.connect(ADMIN_DSN)
    try:
        await conn.execute("SET CLUSTER SETTING feature.vector_index.enabled = true")
        await apply_migrations(conn)
        for statement in _APP_USER_GRANTS:
            await conn.execute(statement)
    finally:
        await conn.close()

    database = Database(APP_DSN)
    await database.connect()
    yield database
    await database.close()


@pytest.fixture
def configured_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Provide required runtime configuration (JWT secret) to the app."""
    monkeypatch.setenv("JWT_SECRET_KEY", "integration-test-secret-key-with-length")
    monkeypatch.setenv("DATABASE_URL", APP_DSN)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
