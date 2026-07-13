"""Migration runner behavior against a real CockroachDB."""

import asyncpg
import pytest

from tejasri.infrastructure.db import Database
from tejasri.infrastructure.db.migrator import apply_migrations
from tests.integration.conftest import ADMIN_DSN

pytestmark = pytest.mark.integration


async def test_migrations_are_idempotent(db: Database) -> None:
    """A second run applies nothing — the schema is fully recorded."""
    conn = await asyncpg.connect(ADMIN_DSN)
    try:
        assert await apply_migrations(conn) == []
    finally:
        await conn.close()


async def test_memory_core_tables_exist(db: Database) -> None:
    expected = {
        "tenants",
        "users",
        "patients",
        "care_plans",
        "conversations",
        "clinical_notes",
        "tasks",
        "audit_log",
        "schema_migrations",
    }
    async with db.system_connection() as conn:
        rows = await conn.fetch(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )
    assert expected <= {r["table_name"] for r in rows}


async def test_clinical_notes_has_cspann_vector_index(db: Database) -> None:
    async with db.system_connection() as conn:
        ddl = await conn.fetchval("SELECT create_statement FROM [SHOW CREATE clinical_notes]")
    assert "VECTOR INDEX" in ddl
    assert "vector_l2_ops" in ddl
