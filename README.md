# FocusOS

FocusOS is a local-first personal morning briefing app. It combines portfolio imports, structured source refreshes, and topic briefings into one edited feed that answers one question in under 60 seconds:

> What deserves my attention today?

The current app has a FastAPI backend, a Vite React frontend, PostgreSQL in Docker, and an APScheduler service that triggers the morning briefing job. The homepage consumes `attention` from `GET /api/briefing` as the single supported Morning Briefing feed.

## Run Locally

```bash
cp .env.example .env
docker compose up --build
```

Then open:

- Web: http://localhost:5173
- API health: http://localhost:8000/api/health
- Briefing payload: http://localhost:8000/api/briefing

The API creates tables on startup and seeds default topics, configured watches, and fallback topic briefings when the database is empty. Portfolio holdings are not seeded; import real holdings CSVs before expecting portfolio-specific attention.

## Common Workflows

- Import holdings CSV: `POST /api/import/holdings?source=Fidelity&replace=true`
- Trigger morning briefing: `POST /api/jobs/morning-briefing`
- Check job status: `GET /api/jobs/morning-briefing/{job_id}`
- Manage watches: `GET`, `POST`, `PATCH`, and `DELETE` under `/api/watch-items`
- Read archived briefings: `GET /api/briefing?date=YYYY-MM-DD`
- Read internal source health: `GET /api/internal/source-status`

Operational routes require `X-FocusOS-Key` when `FOCUSOS_INTERNAL_API_KEY` is set.

## Test And Build

```bash
python -m ruff check backend/app backend/tests
python -m pytest -q
cd frontend
npm ci
npm run lint
npm run build
```

See [Testing](docs/testing.md) for security scans, dependency audits, Docker validation, and CI coverage gates.

## Documentation

- [Development Guide](docs/development.md): local setup, run commands, and common API workflows.
- [Architecture](docs/architecture.md): services, request flow, source refresh flow, and route map.
- [Environment And Config](docs/env-and-config.md): supported environment variables and defaults.
- [Testing](docs/testing.md): validation commands and what each one covers.
- [Operations](docs/operations.md): scheduler behavior, job status, source health, and Docker smoke checks.
- [Data Models](docs/data-models.md): current SQLAlchemy tables and relationships.
- [Data Sources](docs/data-sources.md): implemented source integrations and planned source tiers.
- [Maintenance Notes](docs/maintenance.md): validation commands, cleanup rules, and large-file rationale.
- [Known Limitations](docs/known-limitations.md): intentionally unsupported or unverified behavior.
- [MVP Specification](docs/mvp-spec.md): product scope and homepage rules.

## Project Map

- `backend/app`: FastAPI routes, models, attention rules, source refreshers, topic generation, and seeding.
- `backend/tests`: backend behavior tests.
- `frontend/src`: React briefing UI.
- `docs/adr`: architecture decision records and product decisions.

## MVP Rule

Every attention item must answer:

1. What happened?
2. Is it interesting or consequential?
3. Is action genuinely required?

If a finance signal or topic briefing cannot satisfy those checks, it should not appear in Today's Attention.
