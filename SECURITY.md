# Security Policy

TEJASRI treats security as a first-class feature. Although the platform runs exclusively on synthetic data, it is engineered as if it handled real PHI.

## Reporting a vulnerability

Please **do not** open a public issue for security vulnerabilities. Instead, use
[GitHub private vulnerability reporting](https://github.com/kanwa2006/TEJASRI/security/advisories/new)
on this repository. You will receive an acknowledgement within 72 hours.

Include: affected component, reproduction steps, impact assessment, and any suggested fix.

## Scope

- Backend API (authentication, authorization, injection, rate limiting)
- Multi-tenant isolation (Row-Level Security bypasses are highest severity)
- Secrets handling and configuration
- Dependency vulnerabilities

## Security design summary

- **Tenant isolation:** CockroachDB Row-Level Security enforced at the database, independent of application code.
- **Authentication:** JWT access tokens; passwords hashed with Argon2id.
- **Input validation:** all API input validated with Pydantic schemas; parameterized SQL only.
- **Secrets:** environment variables only; nothing sensitive is committed. `.env` is gitignored.
- **Auditability:** every agent action and safety-check result is persisted to an append-style audit log.
- **Least privilege:** read-only MCP access for agent introspection; scoped service accounts for CI.

## Supported versions

Security fixes target the `main` branch and the latest release.
