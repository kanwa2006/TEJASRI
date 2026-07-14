# Environment Variables

All configuration is environment-driven (12-factor). Local development reads
`.env` (gitignored); see `.env.example` for a template. **Never commit
secrets.**

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `TEJASRI_ENV` | no | `development` | `development` / `test` / `production` (production disables /docs, enables HSTS) |
| `TEJASRI_LOG_LEVEL` | no | `INFO` | Structured-log level |
| `DATABASE_URL` | yes | local insecure node | CockroachDB DSN — **must** be the least-privilege `tejasri_app` user (ADR 0006) |
| `JWT_SECRET_KEY` | yes | — | 32+ random bytes; rotating it invalidates all sessions |
| `JWT_ACCESS_TOKEN_MINUTES` | no | `30` | Access-token lifetime |
| `LLM_PROVIDER` | no | `gemini` | `gemini` / `ollama` / `bedrock` (primary) |
| `LLM_FAILOVER` | no | `true` | Append Ollama to the failover chain |
| `GEMINI_API_KEY` | for gemini | empty | Free-tier key; absence triggers failover |
| `GEMINI_MODEL` | no | `gemini-2.0-flash` | Generation model |
| `GEMINI_EMBEDDING_MODEL` | no | `text-embedding-004` | Truncated to 384 dims |
| `OLLAMA_BASE_URL` | no | `http://localhost:11434` | Local LLM endpoint |
| `OLLAMA_MODEL` | no | `llama3.2` | Local model name |
| `BEDROCK_MODEL` | no | claude-3-haiku | Dormant adapter (`pip install -e ".[aws]"`) |
| `EMBEDDING_PROVIDER` | no | `hash` | `hash` (deterministic) / `local` (bge-small, needs `local-embeddings` extra) / `gemini` |
| `AWS_REGION` | no | `ap-south-1` | For S3/Bedrock clients |
| `S3_BUCKET` | no | empty | Audit-archive / dataset bucket |

AWS credentials come from the standard AWS chain (env/instance role) — never
from application settings.

Generate a secret: `python -c "import secrets; print(secrets.token_hex(32))"`
