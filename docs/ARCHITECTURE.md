# TEJASRI Architecture

> Source of truth: [BLUEPRINT.md](BLUEPRINT.md). Decisions: [adr/](adr/). This document describes the implemented system.

## System overview

TEJASRI is a Healthcare Memory Platform. Version 1 ships one vertical slice: a longitudinal medication-adherence & care-continuity agent. The defining property of the system is that **agent memory is load-bearing**: care-plan state, workflow state, conversation history, and semantic clinical memory all live in CockroachDB under SERIALIZABLE guarantees. If the process dies mid-conversation, no partial state exists; when it restarts, nothing is lost.

```
Client (patient / coordinator UI)
        │ HTTPS
        ▼
FastAPI backend ──────────────────────────────┐
  api/            routers, schemas, wiring    │
  application/    use cases (agent turn,      │
                  care-plan ops, tasks)       │
  domain/         entities + interfaces       │
  infrastructure/ CockroachDB repos, LLM      │
                  adapters, safety engine,    │
                  AWS clients                 │
        │ SQL (SERIALIZABLE, RLS-scoped)      │ MCP (read-only, audited)
        ▼                                     ▼
CockroachDB — the memory layer (single system of record)
        ▲
AWS Lambda (nightly adherence/embedding job) · S3 (datasets, backups, audit archive)
```

## Layering (clean architecture)

| Layer | Path | Rules |
|---|---|---|
| Domain | `backend/src/tejasri/domain/` | Pure Python: entities, value objects, `Protocol` interfaces. No framework or infrastructure imports. |
| Application | `backend/src/tejasri/application/` | Use cases orchestrating domain objects through interfaces. Depends on `domain` only. |
| Infrastructure | `backend/src/tejasri/infrastructure/` | Implements domain interfaces: CockroachDB repositories, LLM providers, safety datasets, AWS. |
| API | `backend/src/tejasri/api/` | FastAPI routers + Pydantic schemas. Translates HTTP ⇄ use cases. No business logic. |
| Core | `backend/src/tejasri/core/` | Cross-cutting: typed settings, structured logging, error types. |

Dependency direction: `api → application → domain ← infrastructure`. Wiring happens at the composition root (`main.py` + `api/deps.py`).

## Memory model

| Kind | Table | Purpose |
|---|---|---|
| Short-term | `conversations` | Per-patient message history across sessions |
| Transactional | `care_plans` (versioned), `tasks` (state machine) | The state whose loss would make the agent unsafe |
| Long-term semantic | `clinical_notes` (`VECTOR(384)` + C-SPANN index, prefix-partitioned by `(tenant_id, patient_id)`) | Meaning-based recall of patient history |
| Accountability | `audit_log` | Every agent action + safety-check result |

Every tenant-scoped table has Row-Level Security enabled and forced; sessions set `app.tenant_id` before any query.

## Safety architecture

Deterministic first, LLM second:

1. Drug-name normalization via RxNorm (RxCUI). Low-confidence matches are flagged `needs_confirmation`.
2. Drug–drug interaction and allergy checks against deterministic datasets (DDInter 2.0, openFDA labels).
3. The LLM receives the deterministic verdict as context and produces an **explanation only**. Post-processing enforces that flagged interactions are disclosed and severity ratings are never altered.
4. State transitions that matter (e.g., care-plan changes) require human confirmation.

## LLM abstraction

`LLMProvider` interface (generate + embed) with three adapters: Gemini (default, free tier), Ollama (local fallback, automatic failover on 429/5xx), Bedrock (dormant, swap-in). Embeddings default to local sentence-transformers (384-dim) so semantic memory is deterministic and offline-capable.

## Extension points (v1 scope boundary)

Future modules (Hospital Memory, Clinical Timeline, Caregiver Portal, Doctor Workspace, FHIR adapter, Bedrock adapter, plugin architecture) attach through:
- new `application/` use cases over the same domain interfaces,
- new adapters implementing existing `domain` Protocols,
- new API routers — without touching the memory core.

They are documented in [ROADMAP.md](ROADMAP.md) and deliberately **not** implemented in v1.

## Cross-cutting concerns

- **Observability:** structured JSON logs with a trace-id per agent turn; request logging middleware; metrics endpoints (Phase 6).
- **Resilience:** SERIALIZABLE transactions + retry-on-conflict; LLM provider failover; failure-injection demo (Phase 6).
- **Cost guards:** AWS budget alert, CockroachDB resource limits, no VPC/NAT/EKS (see BLUEPRINT Part B).
