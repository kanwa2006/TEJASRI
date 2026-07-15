# Design Decisions

The reasoning behind TEJASRI's major engineering choices, and the tradeoffs
each one accepts. Formal records live in [adr/](adr/); this document is the
narrative companion.

## Why memory is the product, not a chatbot

Losing a care-plan edit means the agent reasons about the wrong medications —
a safety failure, not an inconvenience. So TEJASRI keeps one system of
record for four kinds of memory (transactional care plans and tasks,
short-term conversation, long-term semantic notes, and the audit trail) and
treats that store as load-bearing. The conversation is a thin layer over a
durable state machine, not the other way around. See
[MEMORY_SYSTEM.md](MEMORY_SYSTEM.md).

## Why CockroachDB over Postgres + pgvector

1. pgvector's HNSW index is per-node and in-memory; a restart means warm-up
   and possibly a rebuild. C-SPANN is disk-based distributed table data, so
   recall works immediately after a node restart (shown by the resilience
   demo).
2. Async replication can acknowledge a write that a failover then loses. For
   care-plan state that is a patient-safety bug, not a performance footnote.
3. One system holds state, vectors, and tenant isolation together, so a
   committed transaction is the only definition of truth. A separate vector
   database would reintroduce the split-brain problem the platform exists to
   eliminate (a vector for a note whose transaction rolled back, or vice
   versa).
4. SERIALIZABLE isolation by default, with an explicit retry-on-conflict
   discipline in the connection pool.

**Tradeoff accepted:** C-SPANN is public preview — L2 distance only, no
`IMPORT INTO` on indexed tables. Designed around by importing data first,
indexing after, and inserting in small batches.

## Why Row-Level Security instead of application-level filtering

Defense in depth: a `WHERE`-clause bug in application code cannot leak
another tenant's rows because the database itself refuses. It is also
simpler than schema-per-tenant and enforced even when application code is
wrong. Integration testing surfaced that admin roles bypass RLS, so the
application connects as a dedicated least-privilege user and the isolation
tests run at exactly that privilege level ([ADR 0006](adr/0006-least-privilege-app-user.md)).

## Why the LLM only explains, never decides

Hallucinated or softened drug-interaction severities are unacceptable. A
deterministic engine over a versioned, source-cited dataset produces the
verdict; the LLM renders it in plain language. Enforcement is code, not a
prompt: post-processing verifies every flag the engine raised appears in the
answer and appends a standardized disclosure if not. A total LLM outage
degrades to a deterministic template answer built from the same evidence —
the platform never goes silent and never becomes less safe. See
[ADR 0004](adr/0004-deterministic-safety-engine.md).

## Why provider-agnostic LLM and local embeddings

The embeddings *are* the long-term memory, so making them depend on a
third-party API would couple memory durability to vendor uptime and (on free
tiers) to a vendor's data-retention policy. Local 384-dimensional embeddings
are deterministic, offline, and free. Text generation goes through a
ports-and-adapters interface (Gemini → Ollama failover, with a dormant
Bedrock adapter) so the orchestrator depends on no vendor SDK. See
[ADR 0003](adr/0003-provider-agnostic-llm.md).

## Why clean architecture

Future modules (hospital memory, caregiver portal, doctor workspace, a FHIR
adapter) must attach without redesign. Domain `Protocol` interfaces plus
constructor injection keep the domain free of framework imports, make every
adapter swappable, and let the agent orchestrator be unit-tested with fakes
in milliseconds. The cost is a little more ceremony (interfaces and a
composition root); the benefit is testability and a real extension path. See
[ADR 0002](adr/0002-clean-architecture-fastapi.md).

## Failure handling

| Failure | Behavior |
|---|---|
| Crash mid-turn | The user message is committed first; a SERIALIZABLE transaction is all-or-nothing, so no partial state exists. |
| Concurrent agents on one plan | Optimistic version inside a SERIALIZABLE transaction: one writer wins, the other gets a clean version conflict. Proven by a racing test and the live demo. |
| LLM 429 / outage | Provider failover, then deterministic template; the `degraded` flag surfaces honestly in the API, UI, and metrics. |
| Database restart | Recall works instantly (disk-based index); the readiness endpoint gates traffic while the pool reconnects. |
| Stale care-plan version | 409 with the current version so the client can refetch. |

## Scalability

The API is stateless, so it scales horizontally behind a load balancer; the
only shared state is CockroachDB, which scales horizontally by design. Vector
search cost is bounded per patient by the index prefix columns. The one
per-process component is the in-memory rate limiter, whose interface is
Redis-ready.

## Security posture

JWT (HS256, 30-minute expiry) with Argon2id password hashing; timing-
equalized login; a strict per-IP token bucket on auth routes; parameterized
SQL only; secrets via environment; security headers; and an append-only
audit of every state change and agent turn. All data is synthetic (Synthea),
so a public demo carries zero PHI risk ([ADR 0005](adr/0005-synthetic-data-only.md)).

## Known limitations (stated plainly)

- The bundled interaction dataset is a curated demonstration subset; the
  loader accepts a full DDInter 2.0 export without code changes.
- The default embedder is a deterministic hash embedder chosen for zero
  dependencies and reproducibility; a real semantic model
  (sentence-transformers bge-small) is implemented behind the same interface
  and enabled with one setting.
- Real patient data would only ever enter through the roadmap FHIR adapter
  under proper compliance — never before.
