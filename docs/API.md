# API Reference

Interactive documentation: run the backend and open `http://127.0.0.1:8000/docs`
(OpenAPI, disabled in production). All endpoints are under `/api/v1`;
authenticated routes take `Authorization: Bearer <JWT>`.

## Conventions

- Errors: `{"error": "<Type>", "detail": "<message>"}` with 401/403/404/409/422/429/502.
- Every response carries `x-request-id` (propagated if supplied) — the same
  trace ID appears in structured logs.
- Rate limits: 10 req burst on `/auth/*`, 120 elsewhere, per client IP.

## Auth

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/register` | Create a tenant (clinic) + first admin; returns JWT |
| POST | `/auth/login` | Returns JWT with `tenant_id`, `user_id`, `role` claims |

## Patients

| Method | Path | Purpose |
|---|---|---|
| POST | `/patients` | Create (display_name, dob?, conditions[], allergies[]) |
| GET | `/patients` | List (tenant-scoped by RLS) |
| GET | `/patients/{id}` | Fetch one; 404 across tenants |

## Memory (clinical notes)

| Method | Path | Purpose |
|---|---|---|
| POST | `/patients/{id}/notes` | Store note; embedded + vector-indexed on commit |
| GET | `/patients/{id}/notes` | Recent notes |
| GET | `/patients/{id}/notes/recall?q=&limit=` | Semantic recall (C-SPANN, L2); returns notes + distances |

## Care plan

| Method | Path | Purpose |
|---|---|---|
| GET | `/patients/{id}/care-plan` | Plan + live deterministic safety verdict |
| PUT | `/patients/{id}/care-plan/medications` | Versioned update. Body: `medications[]`, `expected_version`, `acknowledge_warnings`. Flagged updates return `applied: false` until acknowledged; stale versions → 409 |

## Agent

| Method | Path | Purpose |
|---|---|---|
| POST | `/patients/{id}/agent/turn` | One conversation turn. Returns `answer`, `safety` (flags + severities + sources), `evidence` (recalled notes + distances), `provider`, `degraded`, `retrieval_confidence`, `disclosure_enforced`, `care_plan_version` |
| GET | `/patients/{id}/conversation` | Durable message history |

## Workflow tasks

| Method | Path | Purpose |
|---|---|---|
| POST | `/patients/{id}/tasks` | Create (`kind`: refill, pharmacist_review, followup, adherence_check) |
| GET | `/patients/{id}/tasks` | List |
| POST | `/tasks/{task_id}/transition` | `to_state`: open, in_progress, blocked, done. Illegal transitions → 409 |

## Timeline & audit

| Method | Path | Purpose |
|---|---|---|
| GET | `/patients/{id}/timeline` | Merged chronological events (conversations, notes, tasks, audit) |
| GET | `/audit?patient_id=&limit=` | Audit history (tenant-scoped) |

## Operations

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness (no dependencies) |
| GET | `/health/ready` | Readiness incl. database ping |
| GET | `/metrics` *(root, not /api/v1)* | Prometheus text format |
