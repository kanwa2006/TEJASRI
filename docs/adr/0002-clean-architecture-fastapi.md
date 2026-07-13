# ADR 0002 — Clean architecture on FastAPI (Python 3.12)

- **Status:** Accepted
- **Date:** 2026-07-13

## Context

TEJASRI must support future modules (hospital memory, caregiver portal, doctor workspace, FHIR adapter) without architectural redesign, stay testable, and keep business logic out of controllers. The backend stack must be productive at hackathon pace yet production-grade.

## Decision

- **FastAPI on Python 3.12**, packaged as `backend/src/tejasri/` with strict layering:
  `api → application → domain ← infrastructure`.
- Domain layer defines entities and `typing.Protocol` interfaces; infrastructure implements them; wiring occurs only at the composition root (`main.py` / `api/deps.py`) via constructor injection.
- Strict typing (`mypy --strict`), ruff for lint + format, pytest for tests.

## Rationale

- FastAPI gives typed request/response validation (Pydantic), async I/O for DB + LLM calls, and OpenAPI docs for free — useful for demos and API documentation.
- Protocol-based interfaces keep the domain free of framework imports and make the LLM provider, repositories, and safety engine swappable and unit-testable with fakes.
- A src-layout package prevents accidental imports of uninstalled code and keeps tooling honest.

## Consequences

- Slightly more ceremony (interfaces + wiring) than a flat app — accepted for testability and the module roadmap.
- New modules attach as new use cases/routers/adapters; the memory core remains untouched.
- Frontend (Phase 5) lives in `frontend/` as a separate workspace in the monorepo.
