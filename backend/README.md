# TEJASRI Backend

FastAPI service implementing the TEJASRI Healthcare Memory Platform. See the
[project README](../README.md) for mission and architecture, and
[docs/DEVELOPMENT.md](../docs/DEVELOPMENT.md) for setup.

Layout (clean architecture): `src/tejasri/{domain,application,infrastructure,api,core}`.

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check . && mypy src && pytest
uvicorn tejasri.main:app --reload
```
