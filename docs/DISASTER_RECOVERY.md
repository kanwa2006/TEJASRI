# Disaster Recovery

The platform's recovery posture is simple because the design is simple:
**one system of record, stateless everything else.**

## What can be lost, and what cannot

| Component | State | Recovery |
|---|---|---|
| CockroachDB | ALL memory (plans, conversations, vectors, tasks, audit) | Backups + replication (below) |
| API processes | None (stateless; in-memory rate buckets reset harmlessly) | Redeploy/restart |
| Frontend | None (static bundle) | Redeploy |
| Lambda | None (idempotent job) | Redeploy; safe to re-run |
| S3 archives | Copies of audit history + datasets | Versioning enabled; source of truth remains the DB |

## Backup strategy

- **CockroachDB Cloud:** managed automatic backups (daily full + hourly
  incremental on Basic); restore via the Cloud console.
- **Self-hosted:** scheduled `cockroach dump`/`BACKUP` to S3; the nightly
  Lambda already archives audit logs to `s3://<bucket>/audit-archive/`.
- Restore drill: restore into a fresh cluster, run
  `python -m tejasri.cli migrate` (no-op if current), re-run
  `create-app-user`, point `DATABASE_URL` at the restored cluster, and run
  `pytest -m integration` as the smoke check.

## Failure runbooks

**Database node down (single-node dev/demo):** `docker start crdb`; the API
reports `degraded` readiness meanwhile and reconnects automatically (lazy
pool). Vector recall needs no warm-up after restart — this is the demo.

**Region/cluster loss (Cloud):** restore latest backup to a new cluster →
update `DATABASE_URL` secret → redeploy API. RPO = backup cadence; RTO ≈
restore time + one deploy.

**LLM provider outage:** nothing to do — the failover chain and the
deterministic template mode keep the platform answering; watch
`tejasri_agent_turns_total{degraded="true"}` in /metrics.

**Leaked JWT secret:** rotate `JWT_SECRET_KEY` and redeploy — all sessions
are invalidated at once (tokens are 30-minute, stateless). Follow with an
audit-log review for the exposure window.

**Corrupt safety dataset deploy:** the dataset is versioned and loaded at
startup; roll back to the previous artifact and redeploy. Every audit entry
records the `dataset_version` used for its verdict, so affected turns are
identifiable retroactively.
