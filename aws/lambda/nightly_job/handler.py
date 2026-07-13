"""TEJASRI nightly job — AWS Lambda handler.

Runs on an EventBridge cron (see aws/lambda/nightly_job/README.md). For every
tenant it:

1. Creates today's `adherence_check` task for each patient with an active
   care plan (idempotent — skips patients that already have one open).
2. Archives the previous day's audit log to S3 as a JSON document.

The function connects as the least-privilege `tejasri_app` user and sets the
RLS tenant context per tenant, exactly like the API does — the same memory
layer, the same isolation guarantees, no side channel.

Environment: DATABASE_URL, S3_BUCKET, AWS_REGION (implicit in Lambda).
Keep the function OUT of any VPC: CockroachDB Cloud and S3 are reached over
public HTTPS, which avoids NAT-gateway costs entirely.
"""

import asyncio
import datetime
import json
import os
from typing import Any

import asyncpg
import boto3


async def _run() -> dict[str, int]:
    dsn = os.environ["DATABASE_URL"]
    bucket = os.environ.get("S3_BUCKET", "")
    stats = {"tenants": 0, "tasks_created": 0, "audit_rows_archived": 0}

    conn = await asyncpg.connect(dsn)
    try:
        tenants = await conn.fetch("SELECT tenant_id FROM tenants")
        for tenant in tenants:
            tenant_id = tenant["tenant_id"]
            stats["tenants"] += 1
            await conn.execute(
                "SELECT set_config('app.tenant_id', $1, false)", str(tenant_id)
            )

            # 1. Due adherence checks (idempotent per patient per open task).
            created = await conn.fetch(
                """
                INSERT INTO tasks (tenant_id, patient_id, kind, state, payload)
                SELECT cp.tenant_id, cp.patient_id, 'adherence_check', 'open',
                       json_build_object('scheduled_by', 'nightly_lambda')
                FROM care_plans AS cp
                WHERE cp.status = 'active'
                  AND NOT EXISTS (
                    SELECT 1 FROM tasks t
                    WHERE t.patient_id = cp.patient_id
                      AND t.kind = 'adherence_check' AND t.state = 'open'
                  )
                RETURNING task_id
                """
            )
            stats["tasks_created"] += len(created)

            # 2. Archive yesterday's audit log to S3.
            if bucket:
                yesterday = datetime.date.today() - datetime.timedelta(days=1)
                rows = await conn.fetch(
                    """
                    SELECT audit_id, patient_id, actor, action, detail, created_at
                    FROM audit_log
                    WHERE created_at >= $1 AND created_at < $2
                    ORDER BY created_at
                    """,
                    datetime.datetime.combine(yesterday, datetime.time.min, datetime.UTC),
                    datetime.datetime.combine(
                        yesterday + datetime.timedelta(days=1), datetime.time.min, datetime.UTC
                    ),
                )
                if rows:
                    key = f"audit-archive/{tenant_id}/{yesterday.isoformat()}.json"
                    body = json.dumps([dict(r) for r in rows], default=str).encode()
                    boto3.client("s3").put_object(
                        Bucket=bucket, Key=key, Body=body, ContentType="application/json"
                    )
                    stats["audit_rows_archived"] += len(rows)

            await conn.execute("SELECT set_config('app.tenant_id', '', false)")
    finally:
        await conn.close()
    return stats


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    stats = asyncio.run(_run())
    print(json.dumps({"event": "nightly_job_complete", **stats}))
    return {"statusCode": 200, "body": stats}


if __name__ == "__main__":
    # Local dry run: python handler.py (needs DATABASE_URL; S3 optional)
    print(lambda_handler({}, None))
