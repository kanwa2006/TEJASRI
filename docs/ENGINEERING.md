# Engineering Guide

Conventions and constraints for contributing to TEJASRI. Architecture
rationale lives in [ARCHITECTURE.md](ARCHITECTURE.md) and
[DESIGN_DECISIONS.md](DESIGN_DECISIONS.md); decisions are recorded as ADRs in
[adr/](adr/) — respect them, and supersede with a new ADR rather than
silently diverging.

## Non-negotiable product rules

1. **Synthetic data only.** Never introduce real PHI. All patient data comes from Synthea.
2. **Deterministic safety is authoritative.** Drug-interaction and allergy checks are deterministic (a versioned, source-cited dataset). The LLM only explains results; it never invents or overrides a severity rating.
3. **No autonomous clinical action.** The agent proposes; a human confirms state transitions that matter.
4. **Every recommendation is explainable** (evidence, retrieved memory, source, confidence, reasoning) and **every agent action is audited** (`audit_log`).
5. **Multi-tenant isolation via CockroachDB RLS** on every tenant-scoped table. Set `app.tenant_id` per session; never bypass.
6. Prominent "not a medical device" disclaimers stay in the UI, README, and demos.

## Architecture at a glance

- Monorepo: `backend/` (FastAPI, Python 3.12), `frontend/` (React + Vite), `docs/`, `scripts/`, `aws/`.
- Backend uses clean architecture inside `backend/src/tejasri/`:
  - `domain/` — entities, value objects, repository/service interfaces (Protocols). No framework imports.
  - `application/` — use cases / orchestration. Depends only on `domain`.
  - `infrastructure/` — CockroachDB repositories, LLM adapters (Gemini/Ollama/Bedrock), safety datasets, AWS. Implements domain interfaces.
  - `api/` — FastAPI routers, request/response schemas, dependency wiring. No business logic in routers.
  - `core/` — config (pydantic-settings), structured logging, errors, metrics, rate limiting.
- Dependency direction: `api → application → domain ← infrastructure`. Never import `infrastructure` from `domain` or `application`.
- LLM access only through the `LLMProvider` interface. Provider selected by `LLM_PROVIDER` env var.
- CockroachDB is the sole system of record. All state mutations are SERIALIZABLE transactions with retry-on-conflict.

## Coding standards

- Python 3.12, fully typed. `mypy` strict must pass. `ruff check` and `ruff format` must pass.
- Parameterized SQL only. No string-built queries.
- Business logic lives in `application/` services, not routers or repositories.
- Tests: pytest. Unit tests under `backend/tests/unit/`, integration under `backend/tests/integration/` (require a local CockroachDB via Docker; marked `@pytest.mark.integration`).
- Secrets via environment variables only (`.env` locally, gitignored). Never commit keys. Keep `.env.example` current.
- Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`, `refactor:`, `ci:`). Keep the default branch green.

## Workflow

1. Understand the task; inspect only the relevant files.
2. Implement incrementally; validate immediately (`ruff`, `mypy`, `pytest`).
3. Update docs and `CHANGELOG.md` when behavior changes.
4. Commit logically grouped work.
5. Definition of done: implementation + tests + docs + types + lint + build, no placeholder/TODO in core paths.

## Scope discipline

Do not implement roadmap/vision modules (FHIR, doctor workspace, hospital
integration, etc.) inside v1 — add extension points and document them in
[ROADMAP.md](ROADMAP.md) instead.

## Hard-won CockroachDB + asyncpg rules

- Inside `run_serializable` transactions use `conn.fetch(...)` (the portal
  runs to completion), **never** `fetchrow`/`fetchval`: CockroachDB rejects a
  new statement while a row-limited portal is suspended
  ("multiple active portals is in preview"), aborting the transaction.
- Never run two pytest processes against one node concurrently — they block
  each other's transactions and look like hangs.
- Admin/root bypasses RLS. All runtime and integration-test connections go
  through the `tejasri_app` user ([ADR 0006](adr/0006-least-privilege-app-user.md)).
- Vectors travel as text literals cast with `$n::VECTOR`; L2 (`<->`) only.

## Commands

```bash
# backend, from backend/
pip install -e ".[dev]"
ruff check . && ruff format --check .
mypy src
pytest -m "not integration"   # fast suite
pytest                        # full suite (needs Docker CockroachDB)
uvicorn tejasri.main:app --reload

# frontend, from frontend/
npm install
npm run lint
npm run build
npm run dev
```
