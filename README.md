# FocusOS

FocusOS is a local-first personal morning briefing app. The MVP answers one question in under 60 seconds:

> What deserves my attention today?

The current app has a FastAPI backend, a Vite React frontend, PostgreSQL in Docker, and an APScheduler service that triggers the morning briefing job. The homepage consumes `/api/briefing.attention` as the single supported Morning Briefing feed.

## Run Locally

```bash
cp .env.example .env
docker compose up --build
```

Then open:

- Web: http://localhost:5173
- API health: http://localhost:8000/api/health
- Briefing payload: http://localhost:8000/api/briefing

The API seeds sample holdings and default topics when the database is empty, so the app has a useful shape before the first import.

## Common Workflows

- Import holdings CSV: `POST /api/import/holdings?source=Fidelity&replace=true`
- Trigger morning briefing: `POST /api/jobs/morning-briefing`
- Check job status: `GET /api/jobs/morning-briefing/{job_id}`
- Read internal source health: `GET /api/internal/source-status`

Operational routes require `X-FocusOS-Key` when `FOCUSOS_INTERNAL_API_KEY` is set.

## Project Map

- `backend/app`: FastAPI routes, models, attention rules, source refreshers, topic generation, and seeding.
- `backend/tests`: backend behavior tests.
- `frontend/src`: React briefing UI.
- `docs/development.md`: setup, environment, testing, and operational commands.
- `docs/mvp-spec.md`: current product scope and homepage rules.
- `docs/data-sources.md`: implemented and planned source integrations.
- `docs/security-hardening.md`: security posture and deferred hardening decisions.
- `docs/adr`: architecture decision records.

## MVP Rule

Every attention item must answer:

1. What happened?
2. Is it interesting or consequential?
3. Is action genuinely required?

If a finance signal or topic briefing cannot satisfy those checks, it should not appear in Today's Attention.
