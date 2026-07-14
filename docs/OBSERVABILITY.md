# Observability

## Structured logs

All logs are single-line JSON on stdout (12-factor). Every HTTP request gets
a `trace_id` (from `x-request-id` or generated) bound via contextvars, so a
full agent turn — request, recall, safety check, LLM call/failover,
persistence — shares one correlatable ID. The same ID is returned in the
response header.

Key events: `request` (method, path, status, duration_ms), `llm_failover`,
`agent_degraded_mode`, `serializable_retry`, `migration_applied`,
`db_pool_created`.

## Metrics (`GET /metrics`, Prometheus text format)

| Metric | Meaning |
|---|---|
| `tejasri_requests_total{method,path,status}` | Traffic and error rate (path = route template, bounded cardinality) |
| `tejasri_request_duration_seconds` (histogram) | Latency distribution |
| `tejasri_agent_turns_total{provider,degraded}` | Which LLM answered; how often the deterministic fallback ran |
| `tejasri_safety_flags_total` | Safety-engine flags raised |

Dependency-free by design (free-tier deployment); the format is standard, so
pointing a real Prometheus + Grafana at `/metrics` needs zero code changes.

### Signals worth alerting on

- `degraded="true"` turns rising → LLM providers failing (platform still up).
- 5xx rate in `tejasri_requests_total` → check `application_error` logs by trace_id.
- `serializable_retry` warnings clustering → hot-row contention.

## Health

- `/api/v1/health` — liveness, dependency-free.
- `/api/v1/health/ready` — includes a database ping; returns `degraded`
  rather than crashing when the memory layer is unreachable.

## Audit trail (the domain-level observability)

`audit_log` records every state change and agent turn with actor, action,
and detail (provider used, evidence note IDs, safety flags, dataset version,
plan version). Browsable per patient via `GET /api/v1/audit` and the
Timeline tab; archived nightly to S3 by the Lambda job.
