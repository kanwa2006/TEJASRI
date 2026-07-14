# Changelog

All notable changes to TEJASRI are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-07-14 (Version 1)

### Added
- Semantic memory: clinical notes embedded (384-dim) and stored under a C-SPANN vector index prefixed by tenant/patient; recall API returns notes with L2 distances; conversation history repository.
- Embedding providers behind one interface: deterministic hash (default), sentence-transformers bge-small (optional extra), Gemini (truncated to 384).
- LLM adapters with failover: Gemini → Ollama → deterministic template degradation; dormant Bedrock adapter.
- Deterministic safety engine: versioned, source-cited interaction dataset (DDInter/openFDA-derived subset, drop-in replaceable), allergy cross-sensitivity, needs-confirmation flags for unknown drugs.
- Agent orchestrator: memory-first turns, evidence recall, code-enforced safety disclosure, honest retrieval confidence, full audit of every turn.
- Care plans with optimistic versioning inside SERIALIZABLE transactions, safety-gated on human acknowledgement; task state machine with validated transitions; unified patient timeline; audit history endpoint.
- AWS integration: S3 archiver and a deployable Lambda nightly job (adherence-check creation + audit archival).
- Frontend: React + Vite + Tailwind — login/register, patient roster, agent chat with explainability panel, care-plan editor with safety gate, semantic recall explorer, tasks, timeline, dark/light themes.
- Hardening: Prometheus-format /metrics, per-IP token-bucket rate limiting (strict on auth), security headers, resilience demo and load-test scripts.
- Documentation: memory system, API, deployment, testing, observability, disaster recovery, troubleshooting, environment variables, interview guide, and the hackathon kit (demo script, Devpost draft, judge walkthrough).

### Fixed
- CockroachDB rejects new statements while a row-limited portal is suspended inside explicit transactions; serializable transaction callers now use portal-completing fetches, and connection release is exception-proof (previously caused multi-minute hangs and pool leaks).

## [0.1.0] — 2026-07-13

### Added
- Project source of truth: complete TEJASRI blueprint at `docs/BLUEPRINT.md`.
- Repository foundation: license, contribution guide, security policy, engineering conventions (`CLAUDE.md`).
- Architecture documentation and initial Architecture Decision Records.
- Backend scaffold: FastAPI application with clean architecture layout (domain / application / infrastructure / api), typed configuration, structured JSON logging, and health endpoints.
- Quality tooling: ruff (lint + format), mypy (strict), pytest, GitHub Actions CI.
- Memory-core database schema as versioned SQL migrations: tenants, users, patients, care plans, conversations, clinical notes (`VECTOR(384)` + C-SPANN vector index), tasks, and audit log — with Row-Level Security forced on every PHI-shaped table.
- Database gateway with tenant-scoped connections (RLS session variable set/cleared automatically) and SERIALIZABLE transaction retry.
- Authentication: tenant registration and login with Argon2id password hashing and JWT access tokens carrying user/tenant/role claims.
- Patient roster API (create/get/list), fully tenant-isolated and audited.
- Operations CLI: `migrate` and `create-app-user` (least-privilege runtime user — admin bypasses RLS, ADR 0006).
- Integration test suite against a real CockroachDB node, including RLS isolation proofs and an end-to-end API flow; CI integration job.
- Readiness endpoint (`/health/ready`) verifying database reachability.
