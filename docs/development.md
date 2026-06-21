# Development Guide

This guide reflects the current FocusOS implementation.

## Local Stack

Run the full local stack:

```bash
cp .env.example .env
docker compose up --build
```

Services:

- Web: `http://localhost:5173`
- API: `http://localhost:8000`
- PostgreSQL: `localhost:5432`
- Scheduler: triggers the morning briefing job daily.

The API creates tables on startup and seeds sample holdings, portfolio snapshots, topics, and fallback topic briefings when the database is empty.

## Backend Without Docker

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r backend/requirements.txt
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

Without `DATABASE_URL`, the backend uses local SQLite at `focusos-dev.db`.

## Frontend Without Docker

```bash
cd frontend
npm ci
npm run dev
```

The Vite dev server proxies `/api` to `http://localhost:8000`.

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

## Environment

Copy `.env.example` to `.env` for local overrides.

Core variables:

- `DATABASE_URL`: optional SQLAlchemy database URL. Defaults to local SQLite.
- `OPENAI_API_KEY`: enables OpenAI topic generation when `AI_PROVIDER=openai`.
- `OPENAI_MODEL`: model for OpenAI topic generation.
- `OPENAI_REQUEST_TIMEOUT`: per-topic provider timeout in seconds.
- `AI_PROVIDER`: `fallback`, `openai`, or `codex_cli`.
- `FOCUSOS_CORS_ORIGINS`: comma-separated browser origins allowed to make state-changing requests.
- `FOCUSOS_INTERNAL_API_KEY`: optional shared secret for internal operational routes.
- `FOCUSOS_MAX_IMPORT_BYTES`: CSV upload limit, default `1048576`.
- `FOCUSOS_ENABLE_HSTS`: enable only behind HTTPS.
- `MORNING_JOB_TIME`: scheduler trigger time, default `06:00`.
- `GOLF_LATITUDE`, `GOLF_LONGITUDE`, `GOLF_LOCATION`, `WEATHER_TIMEZONE`: Open-Meteo golf recommendation inputs.

Codex CLI local provider:

- `CODEX_CLI_PATH`: executable path, default `codex`.
- `CODEX_CLI_TIMEOUT`: per-topic timeout, default `90`.
- `CODEX_CLI_WORKDIR`: workspace passed to Codex CLI. Defaults to the repository root.

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

## Source Health

```bash
curl http://localhost:8000/api/internal/source-status
```

This endpoint is internal-only. Source diagnostics should not appear on the homepage.
