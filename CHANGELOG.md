# Changelog

All notable changes to TEJASRI are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
