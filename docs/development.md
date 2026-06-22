# Development Guide

This guide covers the commands a local engineer needs most often. See [Environment And Config](env-and-config.md), [Architecture](architecture.md), and [Operations](operations.md) for deeper reference.

## Local Stack

Run the full local stack:

```bash
cp .env.example .env
docker compose up --build
```

Docker services:

- Web: `http://localhost:5173`
- API: `http://localhost:8000`
- PostgreSQL: `localhost:5432`
- Scheduler: triggers the morning briefing job daily by POSTing to the API.

The API creates tables on startup and seeds sample holdings, portfolio snapshots, topics, and fallback topic briefings when the database is empty.

## Backend Without Docker

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r backend/requirements.txt
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

Without `DATABASE_URL`, the backend uses local SQLite at `focusos-dev.db`. The API still creates tables and seeds default data on startup.

## Frontend Without Docker

```bash
cd frontend
npm ci
npm run dev
```

The Vite dev server proxies `/api` to `http://localhost:8000` unless `VITE_API_TARGET` is set.

## Validation

Backend tests:

```bash
python -m pytest -q
```

Frontend build:

```bash
cd frontend
npm run build
```

Full Docker smoke check:

```bash
docker compose up --build
curl http://localhost:8000/api/health
curl http://localhost:8000/api/briefing
```

## CSV Import

```bash
curl -F "file=@holdings.csv" "http://localhost:8000/api/import/holdings?source=Fidelity&replace=true"
```

Accepted column names include:

- `symbol`, `ticker`
- `name`, `description`
- `quantity`, `qty`, `shares`
- `price`, `last price`, `current price`
- `market value`, `current value`, `value`
- `cost basis`, `total cost`
- `account`, `account name`
- `asset class`, `type`, `category`

CSV uploads must use a `.csv` filename and stay under `FOCUSOS_MAX_IMPORT_BYTES`.

## Morning Briefing Job

Manual trigger:

```bash
curl -X POST http://localhost:8000/api/jobs/morning-briefing
```

Check status:

```bash
curl http://localhost:8000/api/jobs/morning-briefing/<job_id>
```

If `FOCUSOS_INTERNAL_API_KEY` is configured, include:

```bash
curl -H "X-FocusOS-Key: $FOCUSOS_INTERNAL_API_KEY" -X POST http://localhost:8000/api/jobs/morning-briefing
```

## Archive And Watch Admin

The briefing endpoint also serves archive snapshots:

```bash
curl "http://localhost:8000/api/briefing?date=2026-06-21"
```

Future dates return `400`. Past dates return `404` unless an archived or mock briefing exists for that day.

Watch Admin is the editable attention-configuration surface:

```bash
curl http://localhost:8000/api/watch-items
curl -H "Content-Type: application/json" -d '{"text":"Travel\nWatch flight timing, weather, and parking changes."}' http://localhost:8000/api/watch-items
curl -X POST http://localhost:8000/api/watch-items/<watch_item_id>/complete
curl -X POST http://localhost:8000/api/watch-items/<watch_item_id>/archive
curl -X DELETE http://localhost:8000/api/watch-items/<watch_item_id>
```

The frontend uses Watch Admin separately from the Morning Briefing. Watch rows are inputs and provenance; only surfaced watch evaluations can become briefing outputs.

## Source Health

```bash
curl http://localhost:8000/api/internal/source-status
```

This endpoint is internal-only. Source diagnostics should not appear on the homepage.

## More Detail

- Configuration reference: [env-and-config.md](env-and-config.md)
- Test matrix: [testing.md](testing.md)
- Scheduler and source operations: [operations.md](operations.md)
- Cleanup and large-file notes: [maintenance.md](maintenance.md)
