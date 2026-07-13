# ADR 0006 — Application connects as a least-privilege SQL user

- **Status:** Accepted
- **Date:** 2026-07-13

## Context

Integration testing (Phase 2) proved empirically that CockroachDB `admin`
members — including `root` — bypass Row-Level Security policies entirely,
mirroring PostgreSQL superuser behavior. An application connecting as an
admin would silently defeat the tenant-isolation guarantees of ADR 0001,
even with `FORCE ROW LEVEL SECURITY` applied.

## Decision

- The application runtime connects as a dedicated non-admin user
  (`tejasri_app`) with exactly `SELECT, INSERT, UPDATE, DELETE` on the
  application tables — no DDL, no admin, no BYPASSRLS.
- Migrations and provisioning run separately as an admin identity
  (`python -m tejasri.cli migrate`, then `create-app-user`).
- Integration tests connect the app gateway through `tejasri_app` so the
  RLS isolation tests exercise the same privilege level as production.

## Rationale

Least privilege was already a blueprint requirement; this makes it
structural. RLS only means something when the connecting role cannot
bypass it, so the privilege boundary is now part of the tested contract,
not a deployment nicety.

## Consequences

- Local/dev setup gains one step (`create-app-user`); documented in
  docs/DEVELOPMENT.md.
- On CockroachDB Cloud the app user is created via console/ccloud with a
  password; the DSN in `DATABASE_URL` must reference it.
- Future migrations that add tables must re-grant to `tejasri_app`
  (re-running `create-app-user` covers this).
