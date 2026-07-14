# Judge Walkthrough — Where the Evidence Lives

A 10-minute guided tour mapping each judging criterion to concrete,
inspectable artifacts.

## 1. Agentic Memory Design

- The model: [docs/MEMORY_SYSTEM.md](../MEMORY_SYSTEM.md) — four memory
  kinds, one system of record, the write path of a turn.
- The schema: [backend/src/tejasri/infrastructure/db/migrations/](../../backend/src/tejasri/infrastructure/db/migrations/)
  — `0002_memory_core.sql` is the blueprint DDL, including the C-SPANN
  vector index with tenant/patient prefix.
- Memory-first ordering in code:
  `backend/src/tejasri/application/agent_service.py` (`handle_turn`, step 1
  commits the user message before anything else).
- **Proof it's load-bearing:** run `python scripts/demo_resilience.py` —
  concurrent-writer race, hard DB restart, zero loss, instant recall.

## 2. Technical Implementation

- Vector recall: `infrastructure/repositories/memory.py` — parameterized L2
  query, distances returned to the UI.
- SERIALIZABLE retry discipline: `infrastructure/db/pool.py`
  (`run_serializable`, SQLSTATE 40001 backoff).
- Optimistic versioning: `infrastructure/repositories/workflows.py`.
- Provider-agnostic LLM with failover: `infrastructure/llm.py`; local
  deterministic embeddings: `infrastructure/embeddings.py`.
- Quality gates: `ruff` + `mypy --strict` + 60+ tests including integration
  against a real CockroachDB node — see `.github/workflows/ci.yml` and the
  green Actions history.

## 3. Real-World Impact

- Quantified problem with citations: README §"Why TEJASRI exists" (WHO 2003;
  Kleinsinger PMC6045499; NCT03748420).
- Human-in-the-loop safety posture: [docs/adr/0004](../adr/0004-deterministic-safety-engine.md),
  [docs/adr/0005](../adr/0005-synthetic-data-only.md) — assistive, not a
  medical device; synthetic data only.
- The safety gate in action: try adding warfarin + ibuprofen in the Care
  plan tab — the update is blocked with cited severities until a human
  acknowledges.

## 4. Production Readiness

- **RLS isolation, tested at real privilege:**
  `tests/integration/test_rls_isolation.py` + ADR 0006 (admin bypasses RLS —
  discovered by test, fixed with a least-privilege runtime user).
- Observability: structured JSON logs with per-request trace IDs
  (`core/logging.py`, `main.py`), Prometheus-format `/metrics`
  (`core/metrics.py`), agent-turn and safety-flag counters.
- Security: Argon2id + JWT, timing-equalized login, per-IP token buckets
  (strict on auth), security headers, parameterized SQL, secrets via env —
  [SECURITY.md](../../SECURITY.md).
- Ops: versioned SQL migrations + CLI, DR runbook
  ([docs/DISASTER_RECOVERY.md](../DISASTER_RECOVERY.md)), $0 cost guards
  (no VPC/NAT/EKS; AWS budget alert documented in DEPLOYMENT).

## 5. Creativity & Originality

- **The LLM never decides.** Deterministic, source-cited safety verdicts
  with code-enforced disclosure (`_enforce_disclosure`) — and a deterministic
  template fallback so total LLM outage reduces eloquence, never safety.
- **Honest confidence.** Retrieval confidence is derived from vector
  distance and labeled as such — no invented certainty.
- **The insight:** agentic healthcare apps need a durable state machine,
  not a stateless chatbot. TEJASRI is that state machine with a
  conversation on top.

## Fastest way to see everything (15 min)

```bash
docker run -d --name crdb -p 26257:26257 cockroachdb/cockroach:latest-v25.2 \
  start-single-node --insecure
cd backend && pip install -e ".[dev]"
export DATABASE_URL=postgresql://root@localhost:26257/defaultdb?sslmode=disable
python -m tejasri.cli migrate && python -m tejasri.cli create-app-user
export DATABASE_URL=postgresql://tejasri_app@localhost:26257/defaultdb?sslmode=disable
export JWT_SECRET_KEY=$(python -c "import secrets;print(secrets.token_hex(32))")
pytest                                   # full suite incl. RLS + memory proofs
uvicorn tejasri.main:app &               # API on :8000
python ../scripts/demo_resilience.py     # the money shot
cd ../frontend && npm install && npm run dev   # UI on :5173
```
