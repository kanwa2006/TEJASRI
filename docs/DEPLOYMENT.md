# Deployment Guide

Target: a $0-cost, hackathon-compliant production deployment.
Components: CockroachDB Cloud Basic (memory layer) · app host for the API +
frontend (Fly.io/Render free tier) · AWS Lambda + S3.

## 1. CockroachDB Cloud (Basic)

1. Create a Basic cluster at cockroachlabs.cloud ($400 trial credits, no card
   for Basic).
2. **Day-1 gate (blueprint):** verify vector indexing before anything else:
   ```sql
   SET CLUSTER SETTING feature.vector_index.enabled = true;
   CREATE TABLE _v (id UUID PRIMARY KEY, t UUID, e VECTOR(384), VECTOR INDEX (t, e));
   DROP TABLE _v;
   ```
   If either statement fails on Basic, fall back to a self-hosted single-node
   Docker deployment (fully supported, verified on v25.2).
3. Create the app SQL user and apply the schema (as the admin user):
   ```bash
   export DATABASE_URL="postgresql://<admin>:<pass>@<host>:26257/tejasri?sslmode=verify-full"
   python -m tejasri.cli migrate
   python -m tejasri.cli create-app-user     # then set a password for tejasri_app in the console
   ```
4. Point the app at the least-privilege user (never the admin — ADR 0006).
5. Set a resource/spend limit on the cluster in the Cloud console.

## 2. Backend API

Any container host works; the app is stateless. Example (Fly.io):

```bash
cd backend
fly launch --no-deploy           # generates fly.toml; internal port 8000
fly secrets set DATABASE_URL=... JWT_SECRET_KEY=$(python -c "import secrets;print(secrets.token_hex(32))") \
  GEMINI_API_KEY=... TEJASRI_ENV=production LLM_PROVIDER=gemini
fly deploy
```

Run command: `uvicorn tejasri.main:app --host 0.0.0.0 --port 8000`.
Required env: `DATABASE_URL`, `JWT_SECRET_KEY` (32+ bytes). Optional:
`GEMINI_API_KEY`, `EMBEDDING_PROVIDER=local` (install the
`local-embeddings` extra for real semantic vectors), `OLLAMA_BASE_URL`.

## 3. Frontend

```bash
cd frontend && npm run build     # static bundle in dist/
```
Serve `dist/` from any static host; proxy `/api` to the backend origin (in
dev, Vite's proxy handles this; in production configure the host's rewrite,
or serve both behind one reverse proxy).

## 4. AWS (Lambda + S3)

- Create an S3 bucket (default encryption on, public access blocked).
- Deploy the nightly Lambda per [aws/lambda/nightly_job/README.md](../aws/lambda/nightly_job/README.md)
  — zip deploy, EventBridge cron, least-privilege IAM, **no VPC**.

### Cost guards (non-negotiable, from the blueprint)

- AWS Budgets: create a **$1/month cost budget** with email alerts at 80%
  and 100% (Billing → Budgets).
- Never enable EKS or a NAT Gateway; the Lambda stays out of any VPC.
- CockroachDB resource limit set in the Cloud console.
- Any billing alert → tear down the component and fall back to local Docker.

## 5. Post-deploy verification

```bash
curl https://<api>/api/v1/health/ready        # {"status":"ok","database":"ok"}
curl https://<api>/metrics | head             # counters flowing
python scripts/demo_resilience.py --api https://<api> --skip-restart
```

## Rollback

The API is stateless: redeploy the previous image/revision. Schema
migrations are additive; the migration runner records state in
`schema_migrations`. Database restore: see [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md).
