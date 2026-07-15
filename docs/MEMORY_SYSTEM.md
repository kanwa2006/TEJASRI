# The TEJASRI Memory System

> Why memory is load-bearing — the core design the platform is built around.

## Four kinds of memory, one system of record

| Kind | Table | What breaks if it's lost |
|---|---|---|
| **Transactional** | `care_plans` (versioned), `tasks` (state machine) | The agent gives unsafe or contradictory guidance — a lost plan edit means reasoning about the wrong medications |
| **Short-term** | `conversations` | Continuity: "as we discussed yesterday" stops working |
| **Long-term semantic** | `clinical_notes` — `VECTOR(384)` + C-SPANN index | The agent forgets the patient's history and answers generically |
| **Accountability** | `audit_log` | Trust: actions become unexplainable and unreviewable |

All four live in CockroachDB under SERIALIZABLE isolation. There is no cache,
no secondary store, no queue whose loss could desynchronize them.

## Write path of one agent turn

```
user message
  → INSERT conversations (committed BEFORE anything else — a crash here loses nothing)
  → embed(message) locally (384-dim, deterministic)
  → SELECT … ORDER BY embedding <-> $q LIMIT 5      (C-SPANN, tenant/patient prefix)
  → SELECT care_plan; SafetyEngine.check(...)        (deterministic, in-memory dataset)
  → LLM explains the verdict (Gemini → Ollama failover → deterministic template)
  → disclosure enforcement (every engine flag must appear in the answer)
  → INSERT conversations (agent answer)
  → INSERT audit_log (provider, evidence ids, flags, plan version)
```

A vector is searchable the instant its transaction commits — there is no
indexing lag between "the note exists" and "the agent can recall it."

## Concurrency model

Care-plan updates use **optimistic versioning inside SERIALIZABLE
transactions** (`infrastructure/repositories/workflows.py`):

- Concurrent writers either serialize cleanly (automatic retry on SQLSTATE
  40001 with backoff, `db/pool.py`) or fail loudly with a version conflict.
- `tests/integration/test_workflows.py::test_concurrent_updates_never_lose_state`
  races five writers and asserts exactly one wins and the version count is
  exact. `scripts/demo_resilience.py` shows the same live.

## Tenant isolation of memory

Row-Level Security is **forced** on every memory table, keyed on a session
variable set by the connection pool (`SET app.tenant_id`). The application
connects as a non-admin user because admin bypasses RLS (ADR 0006) — this
was discovered by test, not assumed. The vector index itself is prefixed by
`(tenant_id, patient_id)`, so semantic search physically scans only one
patient's vectors: isolation and performance from the same design choice.

## Why CockroachDB and not Postgres + pgvector

- pgvector's HNSW index is in-memory per node and needs rebuild/warm-up after
  restart; C-SPANN is ordinary distributed table data on disk — recall works
  immediately after a node restart (demonstrated in the resilience demo).
- Async replication can acknowledge a write that a failover then loses; for
  a care plan that is a patient-safety bug, not an inconvenience.
- One system holds state + vectors + isolation, so a committed transaction
  is the *only* definition of truth. A separate vector DB would reintroduce
  the split-brain problem the platform exists to eliminate.

C-SPANN preview constraints respected: L2 (`<->`) only; import data before
creating the index; small insert batches (see [DEPLOYMENT.md](DEPLOYMENT.md)).

## Degradation ladder

| Failure | Behavior |
|---|---|
| LLM primary down (429/5xx) | Failover to Ollama (`FailoverLLMProvider`) |
| All LLMs down | Deterministic template answer from the same evidence; `degraded: true` surfaced in API and UI |
| Serialization conflict | Automatic retry with exponential backoff |
| Stale care-plan version | 409 with current version — client refetches |
| Database down | `/health/ready` reports degraded; liveness stays up |

The safety engine and the memory layer have **no** degraded mode by design:
they either work or the request fails loudly.
