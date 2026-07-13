"""Versioned SQL migrations.

Plain .sql files in `migrations/`, applied in filename order, recorded in
`schema_migrations`. Statements execute individually (CockroachDB restricts
some DDL inside explicit transactions); files must therefore be written to
be safe if re-run after a partial failure (IF NOT EXISTS where possible).
"""

from importlib import resources

import asyncpg

from tejasri.core.logging import get_logger

log = get_logger(__name__)

_MIGRATIONS_PACKAGE = "tejasri.infrastructure.db.migrations"


def _split_statements(sql: str) -> list[str]:
    """Split a migration file into statements on top-level semicolons.

    Migration SQL is restricted by convention to plain DDL/DML without
    dollar-quoted bodies, so a line-based split is reliable.
    """
    statements: list[str] = []
    current: list[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        current.append(line)
        if stripped.endswith(";"):
            statements.append("\n".join(current).rstrip(";").strip())
            current = []
    if current:
        statements.append("\n".join(current).strip())
    return [s for s in statements if s]


def load_migrations() -> list[tuple[str, str]]:
    """Return (name, sql) pairs in application order."""
    root = resources.files(_MIGRATIONS_PACKAGE)
    return sorted(
        (entry.name, entry.read_text(encoding="utf-8"))
        for entry in root.iterdir()
        if entry.name.endswith(".sql")
    )


async def apply_migrations(conn: asyncpg.Connection) -> list[str]:
    """Apply all pending migrations; return the names applied."""
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
          name STRING PRIMARY KEY,
          applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    applied_rows = await conn.fetch("SELECT name FROM schema_migrations")
    already_applied = {row["name"] for row in applied_rows}

    newly_applied: list[str] = []
    for name, sql in load_migrations():
        if name in already_applied:
            continue
        log.info("migration_applying", name=name)
        for statement in _split_statements(sql):
            await conn.execute(statement)
        await conn.execute("INSERT INTO schema_migrations (name) VALUES ($1)", name)
        newly_applied.append(name)
        log.info("migration_applied", name=name)
    return newly_applied
