"""Connection pool with tenant-scoped sessions and serializable retry.

Two invariants live here so no repository can get them wrong:

1. Every tenant-scoped connection runs ``SET app.tenant_id`` before use,
   which is what the Row-Level Security policies key on — and resets it
   on release, so pooled connections never leak tenant context.
2. Write transactions run SERIALIZABLE (CockroachDB's default) with
   automatic retry on serialization conflicts (SQLSTATE 40001).
"""

import asyncio
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import asyncpg

from tejasri.core.logging import get_logger

log = get_logger(__name__)

_SERIALIZATION_FAILURE = "40001"
_MAX_RETRIES = 5


class Database:
    """Async CockroachDB gateway. One instance per application process."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=10)
            log.info("db_pool_created")

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            log.info("db_pool_closed")

    async def ping(self) -> bool:
        """Readiness check: can we reach the database right now?"""
        pool = await self._require_pool()
        value = await pool.fetchval("SELECT 1")
        return bool(value == 1)

    @asynccontextmanager
    async def tenant_connection(self, tenant_id: uuid.UUID) -> AsyncIterator[asyncpg.Connection]:
        """A connection scoped to one tenant via RLS session variable."""
        pool = await self._require_pool()
        conn = await pool.acquire()
        try:
            # set_config is the parameterized form of SET — no SQL built from strings.
            await conn.execute("SELECT set_config('app.tenant_id', $1, false)", str(tenant_id))
            yield conn
        finally:
            # Clear tenant context so pooled connections never leak it. The
            # RLS policies treat '' as "no tenant" (NULLIF), matching unset.
            await conn.execute("SELECT set_config('app.tenant_id', '', false)")
            await pool.release(conn)

    @asynccontextmanager
    async def system_connection(self) -> AsyncIterator[asyncpg.Connection]:
        """A connection WITHOUT tenant context.

        RLS-forced tables yield no rows on it; use only for the auth
        directory (tenants/users), migrations, and readiness checks.
        """
        pool = await self._require_pool()
        conn = await pool.acquire()
        try:
            yield conn
        finally:
            await pool.release(conn)

    async def run_serializable[T](
        self,
        tenant_id: uuid.UUID,
        fn: Callable[[asyncpg.Connection], Awaitable[T]],
    ) -> T:
        """Run ``fn`` in a SERIALIZABLE transaction, retrying on 40001.

        CockroachDB aborts one side of conflicting transactions instead of
        corrupting state; the correct client behavior is to retry with
        backoff. This is what lets concurrent agents share one patient's
        memory safely.
        """
        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                async with self.tenant_connection(tenant_id) as conn, conn.transaction():
                    return await fn(conn)
            except asyncpg.PostgresError as exc:
                if getattr(exc, "sqlstate", None) != _SERIALIZATION_FAILURE:
                    raise
                last_error = exc
                delay = 0.05 * (2**attempt)
                log.warning("serializable_retry", attempt=attempt + 1, delay=delay)
                await asyncio.sleep(delay)
        raise RuntimeError("serializable transaction retries exhausted") from last_error

    async def _require_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            await self.connect()
        assert self._pool is not None  # noqa: S101 — connect() either sets it or raises
        return self._pool
