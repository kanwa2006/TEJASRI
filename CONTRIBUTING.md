# Contributing to TEJASRI

Thank you for considering a contribution. TEJASRI aims to be a flagship open-source healthcare platform — contributions are held to production standards, and we'll help you get there.

## Ground rules

- **Synthetic data only.** Never commit or test with real patient data. All fixtures derive from Synthea.
- **Safety logic is deterministic.** Changes to the safety engine must keep the LLM in an explain-only role.
- **Every change ships with tests and docs.** A PR is complete when code, tests, types, lint, and documentation all pass/update together.

## Development setup

```bash
git clone https://github.com/kanwa2006/TEJASRI.git
cd TEJASRI/backend
python -m venv .venv && source .venv/bin/activate   # .venv\Scripts\activate on Windows
pip install -e ".[dev]"
pytest -m "not integration"
```

Integration tests need a local CockroachDB:

```bash
docker run -d --name crdb -p 26257:26257 -p 8080:8080 cockroachdb/cockroach:latest-v25.2 start-single-node --insecure
pytest
```

## Quality gates

All of these must pass before a PR is merged (CI enforces them):

```bash
ruff check . && ruff format --check .
mypy src
pytest
```

## Engineering conventions

Read [docs/ENGINEERING.md](docs/ENGINEERING.md) before contributing — it
covers the non-negotiable product rules, clean-architecture layering, coding
standards, and hard-won CockroachDB/asyncpg gotchas.

## Commit conventions

We use [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, `ci:`. Keep commits logically grouped; keep the default branch green.

## Pull requests

1. Fork / branch from `main`.
2. Make your change with tests and docs.
3. Update `CHANGELOG.md` under `[Unreleased]`.
4. Open a PR describing **what** changed and **why**. Link related issues.

## Architecture changes

Significant design changes require an ADR in `docs/adr/` (copy the format of existing records). Discuss in an issue first for anything that touches the memory model, safety engine, or tenant isolation.

## Code of conduct

Be kind, be professional, assume good intent. Harassment or disrespect is not tolerated.
