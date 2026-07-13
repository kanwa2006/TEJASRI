"""Operational CLI.

Usage:
    python -m tejasri.cli migrate            # apply pending schema migrations
    python -m tejasri.cli create-app-user    # create least-privilege runtime user
"""

import argparse
import asyncio
import sys

import asyncpg

from tejasri.core.config import get_settings
from tejasri.core.logging import configure_logging, get_logger
from tejasri.infrastructure.db.migrator import apply_migrations

log = get_logger(__name__)


async def _migrate() -> None:
    settings = get_settings()
    conn = await asyncpg.connect(settings.database_url)
    try:
        # C-SPANN prerequisite. Cluster-scoped, so it may be denied on some
        # managed tiers — migrations proceed and the CREATE VECTOR INDEX
        # statement itself is the real gate (see docs/BLUEPRINT.md, Part B).
        try:
            await conn.execute("SET CLUSTER SETTING feature.vector_index.enabled = true")
        except asyncpg.PostgresError as exc:
            log.warning("vector_index_setting_failed", error=str(exc))
        applied = await apply_migrations(conn)
        log.info("migrate_complete", applied=applied or "none")
    finally:
        await conn.close()


APP_USER = "tejasri_app"

# Admin (and root) members bypass Row-Level Security, so the application
# must run as a dedicated non-admin user for the tenant-isolation policies
# to bind. See docs/adr/0006-least-privilege-app-user.md.
_APP_USER_GRANTS = (
    f"CREATE USER IF NOT EXISTS {APP_USER}",
    f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {APP_USER}",
)


async def _create_app_user() -> None:
    settings = get_settings()
    conn = await asyncpg.connect(settings.database_url)
    try:
        for statement in _APP_USER_GRANTS:
            await conn.execute(statement)
        log.info("app_user_ready", user=APP_USER)
    finally:
        await conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tejasri", description="TEJASRI operations CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("migrate", help="apply pending schema migrations")
    subparsers.add_parser(
        "create-app-user",
        help="create the least-privilege runtime user (run as admin, after migrate)",
    )
    args = parser.parse_args(argv)

    configure_logging(get_settings().tejasri_log_level)
    if args.command == "migrate":
        asyncio.run(_migrate())
    elif args.command == "create-app-user":
        asyncio.run(_create_app_user())
    return 0


if __name__ == "__main__":
    sys.exit(main())
