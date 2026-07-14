# Testing Guide

## Philosophy

Every safety-relevant property is tested at the level where it can actually
fail: the safety engine as pure logic, RLS at the database with the app's
real (least-privilege) credentials, concurrency against a real CockroachDB.
Fakes implement the domain Protocols, so unit tests run in milliseconds
without mocks of framework internals.

## Layout

```
backend/tests/
  unit/          no I/O — services with fakes, safety engine, embeddings,
                 tokens/passwords, rate limiter, metrics
  integration/   @pytest.mark.integration — real CockroachDB required:
                 migrations, RLS isolation proofs, vector recall, API flows,
                 care-plan concurrency race, agent turn end-to-end
```

## Running

```bash
cd backend
pytest -m "not integration" -q     # fast suite (~2s)
docker run -d --name crdb -p 26257:26257 \
  cockroachdb/cockroach:latest-v25.2 start-single-node --insecure
pytest -q                          # everything
```

Integration fixtures (tests/integration/conftest.py) apply migrations and
provision the `tejasri_app` least-privilege user automatically; override the
target with `DATABASE_URL`.

## The tests that carry the judging claims

| Claim | Test |
|---|---|
| Tenant B cannot see tenant A | `test_rls_isolation.py::test_tenants_cannot_see_each_others_patients` |
| No tenant context ⇒ no rows | `test_rls_isolation.py::test_connection_without_tenant_context_sees_no_rows` |
| Pooled connections don't leak tenant context | `test_rls_isolation.py::test_tenant_context_is_cleared_on_connection_release` |
| Semantic recall works & is isolated | `test_memory.py` |
| Concurrent writers never lose state | `test_workflows.py::test_concurrent_updates_never_lose_state` |
| Safety flags always disclosed | `test_agent_service.py::test_disclosure_is_enforced_when_llm_omits_a_flag` |
| Total LLM outage ⇒ degraded, not down | `test_workflows.py::test_agent_turn_end_to_end_with_llm_down` |
| Illegal task transitions rejected | `test_task_service.py` |

## Load & resilience

- `scripts/load_test.py` — concurrency + p50/p95/p99 latency stats.
- `scripts/demo_resilience.py` — concurrent-writer race + hard DB restart +
  zero-loss verification (the demo video's core).

## CI

`.github/workflows/ci.yml`: ruff (lint + format) → mypy strict → unit tests,
plus a second job running the integration suite against a Dockerized
single-node CockroachDB. Both must be green on main.
