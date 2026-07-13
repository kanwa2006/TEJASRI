# Development Guide

## Prerequisites

- Python 3.12+
- Docker (local CockroachDB node for integration tests)
- Git

## Setup

```bash
git clone https://github.com/kanwa2006/TEJASRI.git
cd TEJASRI/backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Unix:
source .venv/bin/activate
pip install -e ".[dev]"
```

Copy the environment template and fill values as needed:

```bash
cp ../.env.example ../.env
```

## Running the API

```bash
cd backend
uvicorn tejasri.main:app --reload
# http://127.0.0.1:8000/docs — OpenAPI UI
# http://127.0.0.1:8000/api/v1/health — health check
```

## Local CockroachDB

```bash
docker run -d --name crdb -p 26257:26257 -p 8081:8080 \
  cockroachdb/cockroach:latest-v25.2 start-single-node --insecure
```

Apply the schema and create the least-privilege runtime user (ADR 0006 —
admin users bypass Row-Level Security, so the app never runs as `root`):

```bash
# admin DSN for provisioning
export DATABASE_URL="postgresql://root@localhost:26257/defaultdb?sslmode=disable"
python -m tejasri.cli migrate          # enables vector indexing + applies migrations
python -m tejasri.cli create-app-user  # creates tejasri_app with table-only grants
```

Then point the application at the app user in `.env`:

```
DATABASE_URL=postgresql://tejasri_app@localhost:26257/defaultdb?sslmode=disable
```

## Quality gates

Run before every commit — CI enforces the same set:

```bash
ruff check . && ruff format --check .
mypy src
pytest -m "not integration"   # fast suite, no external services
pytest                        # full suite (needs Docker CockroachDB)
```

## Test layout

- `backend/tests/unit/` — pure unit tests; no I/O, no network, no DB.
- `backend/tests/integration/` — marked `integration`; require CockroachDB.

## Conventions

See [CLAUDE.md](../CLAUDE.md) for engineering rules, layering constraints, and commit conventions. Architecture rationale lives in [ARCHITECTURE.md](ARCHITECTURE.md) and [adr/](adr/).
