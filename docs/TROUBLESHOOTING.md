# Troubleshooting

## API won't start / readiness degraded

- `{"status":"degraded","database":"unreachable"}` → CockroachDB is down or
  `DATABASE_URL` is wrong. Local: `docker start crdb`. The pool reconnects
  lazily; no restart needed.
- `ValueError: JWT secret key must be configured` → set `JWT_SECRET_KEY`
  (32+ random bytes).

## RLS surprises

- **Queries return zero rows as expected data** → the session has no tenant
  context. Application code must go through `Database.tenant_connection`;
  only the auth directory uses `system_connection`.
- **Rows from other tenants are visible** → you are connected as an admin
  user. Admin bypasses RLS (ADR 0006). Use the `tejasri_app` user:
  `python -m tejasri.cli create-app-user`.

## Vector index

- `CREATE VECTOR INDEX` fails → run
  `SET CLUSTER SETTING feature.vector_index.enabled = true` as admin
  (the `migrate` CLI attempts this automatically).
- Recall returns nothing → confirm notes exist for that patient (the index
  is prefixed by tenant + patient) and the tenant context is set.
- Slow bulk ingest → insert notes in small batches; never `IMPORT INTO` a
  vector-indexed table (preview limitation) — import first, index after.

## Tests

- Integration tests hang or fail with pool-close warnings → almost always
  **multiple pytest processes running concurrently against one node**,
  blocking each other's transactions. Kill strays
  (`taskkill /f /im python.exe` as needed / check `tasklist`), restart the
  node, run one suite at a time.
- `409 version conflict` in your own API client → you sent a stale
  `expected_version`; refetch the plan.

## LLM / agent

- Answers arrive with provider `deterministic-template` → all LLM providers
  are unreachable (missing `GEMINI_API_KEY`, Ollama not running). The
  platform is working as designed; configure a provider to restore prose.
- Gemini 429s → free-tier rate limits; the failover chain handles it. For
  demos, pre-pull an Ollama model: `ollama pull llama3.2`.

## Frontend

- API calls fail in dev → the Vite proxy targets `127.0.0.1:8000`; make
  sure the backend is on that port, or adjust `frontend/vite.config.ts`.
- Blank page after login → token expired (30 min); sign in again. 401s
  clear the stored session automatically.
