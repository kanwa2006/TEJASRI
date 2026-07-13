# ADR 0001 — CockroachDB as the sole system of record (memory layer)

- **Status:** Accepted
- **Date:** 2026-07-13

## Context

TEJASRI's agent memory (care-plan state, task state machine, conversation history, semantic clinical-note embeddings) is load-bearing: losing any of it makes the agent unsafe. We need transactional state, vector search, and multi-tenant isolation. Alternatives considered: Postgres + pgvector, a dedicated vector DB (e.g., a managed vector store) beside Postgres, or CockroachDB alone.

## Decision

Use **CockroachDB as the single system of record** for all four memory kinds:

- SERIALIZABLE transactions for care-plan edits and task-state transitions.
- C-SPANN distributed vector index (`VECTOR(384)`, L2) on `clinical_notes`, prefix-partitioned by `(tenant_id, patient_id)`.
- Row-Level Security for tenant isolation enforced at the database.
- `audit_log` table for accountability.

## Rationale

- pgvector's HNSW index is single-node/in-memory; async replication can lose recent writes; no built-in per-tenant vector isolation.
- A separate vector DB splits the source of truth: a vector could exist for a note whose transaction rolled back, or vice versa. In CockroachDB a vector is searchable the instant its transaction commits.
- RLS + prefix-partitioned vector indexes give per-tenant isolation for both relational and semantic memory in one mechanism.
- One system to operate, back up, and reason about — consolidation is the point for memory that "can't go down."

## Consequences

- C-SPANN is public preview: **L2 distance only**; `IMPORT INTO` unsupported on vector-indexed tables (import first, index after); avoid large batch vector inserts; requires `SET CLUSTER SETTING feature.vector_index.enabled = true`.
- Verify vector indexing works on the target CockroachDB Cloud Basic tier; confirmed fallback is a self-hosted single-node Docker (v25.2+) for dev/CI.
- All repositories must implement retry-on-serializable-conflict.
