"""Tenant and user repositories.

These operate on the auth directory (no RLS — see migration 0001) and
therefore use system connections. Everything PHI-shaped goes through
tenant-scoped connections instead (see patients.py).
"""

import uuid
from typing import Any

import asyncpg

from tejasri.core.errors import ConflictError
from tejasri.domain.entities import Tenant, User, UserRole
from tejasri.infrastructure.db import Database

_UNIQUE_VIOLATION = "23505"


def _tenant_from_row(row: Any) -> Tenant:
    return Tenant(
        tenant_id=row["tenant_id"],
        name=row["name"],
        created_at=row["created_at"],
    )


def _user_from_row(row: Any) -> User:
    return User(
        user_id=row["user_id"],
        tenant_id=row["tenant_id"],
        email=row["email"],
        password_hash=row["password_hash"],
        role=UserRole(row["role"]),
        display_name=row["display_name"],
        created_at=row["created_at"],
    )


class CockroachTenantRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def create(self, name: str) -> Tenant:
        async with self._db.system_connection() as conn:
            try:
                row = await conn.fetchrow(
                    "INSERT INTO tenants (name) VALUES ($1) RETURNING *", name
                )
            except asyncpg.PostgresError as exc:
                if getattr(exc, "sqlstate", None) == _UNIQUE_VIOLATION:
                    raise ConflictError(f"tenant name already exists: {name}") from exc
                raise
        return _tenant_from_row(row)

    async def get(self, tenant_id: uuid.UUID) -> Tenant | None:
        async with self._db.system_connection() as conn:
            row = await conn.fetchrow("SELECT * FROM tenants WHERE tenant_id = $1", tenant_id)
        return _tenant_from_row(row) if row else None


class CockroachUserRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def create(
        self,
        tenant_id: uuid.UUID,
        email: str,
        password_hash: str,
        role: UserRole,
        display_name: str,
    ) -> User:
        async with self._db.system_connection() as conn:
            try:
                row = await conn.fetchrow(
                    """
                    INSERT INTO users (tenant_id, email, password_hash, role, display_name)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING *
                    """,
                    tenant_id,
                    email.lower(),
                    password_hash,
                    role.value,
                    display_name,
                )
            except asyncpg.PostgresError as exc:
                if getattr(exc, "sqlstate", None) == _UNIQUE_VIOLATION:
                    raise ConflictError(f"email already registered: {email}") from exc
                raise
        return _user_from_row(row)

    async def get_by_email(self, email: str) -> User | None:
        async with self._db.system_connection() as conn:
            row = await conn.fetchrow("SELECT * FROM users WHERE email = $1", email.lower())
        return _user_from_row(row) if row else None
