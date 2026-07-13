# TEJASRI

**Healthcare should never forget.**

TEJASRI (**T**echnology-**E**nabled **J**oint **A**gentic **S**ystem for **R**esilient care & **I**ntelligence) is an open-source **Healthcare Memory Platform**. Its first module is a longitudinal medication-adherence and care-continuity agent whose memory — care plans, conversations, clinical context, and workflow state — lives in a durable, transactional, vector-indexed database that survives failures with zero loss.

> ## ⚠️ Disclaimer
> TEJASRI is an **assistive tool, not a medical device**. It does not diagnose, prescribe, or replace clinical judgment. All recommendations are explanatory, evidence-linked, and require human confirmation. The platform runs exclusively on **synthetic patient data** ([Synthea](https://synthetichealth.github.io/synthea/)) — never real PHI.

---

## Why TEJASRI exists

Medication non-adherence is one of healthcare's largest invisible failures:

- Adherence among chronic-disease patients **averages only ~50%**, lower in developing countries (WHO, *Adherence to Long-Term Therapies*, 2003).
- Non-adherence causes an estimated **125,000 avoidable deaths and $100B+ in preventable costs annually** in the US alone (Kleinsinger, *Perm J*, PMC6045499).

A core reason: **healthcare systems forget.** Context is lost between visits, providers, and conversations. TEJASRI's answer is an agent that *remembers* — reliably, transactionally, and transparently — while humans stay in control.

## Product principles

1. Memory before intelligence.
2. Safety before automation.
3. Doctors before AI.
4. Humans always remain in control.
5. Every recommendation must be explainable.
6. Every action must be auditable.
7. Privacy is mandatory.
8. Transparency over confidence.
9. Production quality over feature count.
10. Simplicity over complexity.

## Architecture

```
                 ┌────────────────────────────────────────┐
   React/Next UI │  Web frontend                            │
   (patient/     │   └─> FastAPI backend                    │
    coordinator) │        ├─ Auth (JWT + Argon2id)          │
                 │        ├─ Agent Orchestrator             │
                 │        │    ├─ LLM Adapter (Gemini/       │
                 │        │    │   Ollama/Bedrock swap)      │
                 │        │    ├─ Memory Store/Recall        │
                 │        │    └─ Deterministic Safety Engine│
                 │        │        (DDInter/openFDA/RxNorm)  │
                 │        └─ MCP client ──► CockroachDB MCP  │
                 └───────────────┬────────────────────────┬─┘
                                 │ SQL (SERIALIZABLE)      │ MCP (read-only, audited)
                                 ▼                         ▼
                    ┌──────────────────────────────────────────┐
                    │  CockroachDB — THE MEMORY LAYER            │
                    │  patients | care_plans | conversations |   │
                    │  clinical_notes(VECTOR+C-SPANN) | tasks |  │
                    │  audit_log   (all RLS multi-tenant)        │
                    └──────────────────────────────────────────┘
        AWS: Lambda (nightly adherence/embedding job) + S3 (datasets, backups, audit archive)
```

**The memory model is load-bearing by design:**

| Memory type | Storage | Guarantee |
|---|---|---|
| Short-term (conversations) | `conversations` table | SERIALIZABLE transactions |
| Transactional (care plans, tasks) | `care_plans`, `tasks` state machine | Versioned, atomic transitions |
| Long-term semantic (clinical notes) | `clinical_notes` with `VECTOR(384)` + C-SPANN index | Searchable the instant its transaction commits |
| Accountability | `audit_log` | Every agent action recorded |

All tables are isolated per tenant with CockroachDB **Row-Level Security** — one clinic can never read another's rows, even through a shared connection.

**Safety design:** drug-interaction and allergy checks are **deterministic** (DDInter / openFDA / RxNorm datasets). The LLM only *explains* the deterministic result — it can never invent or override a severity rating.

## Source of truth

The complete product specification lives in [docs/BLUEPRINT.md](docs/BLUEPRINT.md). Architecture decisions are recorded in [docs/adr/](docs/adr/).

## Repository layout

```
backend/    FastAPI application (clean architecture: domain / application / infrastructure / api)
docs/       Blueprint, architecture, ADRs, guides
scripts/    Development and operations scripts
```

## Developer setup

Prerequisites: Python 3.12+, Docker (for a local CockroachDB node).

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate         # Windows — use .venv/bin/activate on Unix
pip install -e ".[dev]"
copy ..\.env.example ..\.env   # then fill in values
pytest                         # run the test suite
uvicorn tejasri.main:app --reload
```

Quality gates (run before every commit):

```bash
ruff check . && ruff format --check .
mypy src
pytest
```

## Roadmap

**v1 (current):** medication-adherence & care-continuity agent — durable memory core, deterministic safety engine, explainable recommendations, multi-tenant isolation, resilience demo.

**Vision (extension modules, out of v1 scope):** Hospital Memory · Care Continuity · Clinical Timeline · Caregiver Portal · Emergency Summary · Doctor Workspace · FHIR interoperability · Longitudinal Patient Intelligence.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Security reports: see [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE)
