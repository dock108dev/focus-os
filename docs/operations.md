# Operations

FocusOS is designed for local operation first. Docker Compose is the supported full-stack runtime for development.

## Start The Stack

```bash
cp .env.example .env
docker compose up --build
```

Useful endpoints:

- Web: `http://localhost:5173`
- API health: `http://localhost:8000/api/health`
- Briefing payload: `http://localhost:8000/api/briefing`

## Morning Briefing Job

Queue a refresh manually:

```bash
curl -X POST http://localhost:8000/api/jobs/morning-briefing
```

Read status:

```bash
curl http://localhost:8000/api/jobs/morning-briefing/<job_id>
```

When `FOCUSOS_INTERNAL_API_KEY` is configured:

```bash
curl -H "X-FocusOS-Key: $FOCUSOS_INTERNAL_API_KEY" -X POST http://localhost:8000/api/jobs/morning-briefing
```

The API returns immediately after queuing. Refresh work runs in-process on a daemon thread, so this is not a durable job queue.

## Source Health

Read internal source status:

```bash
curl http://localhost:8000/api/internal/source-status
```

With an internal key:

```bash
curl -H "X-FocusOS-Key: $FOCUSOS_INTERNAL_API_KEY" http://localhost:8000/api/internal/source-status
```

Source health is intentionally internal. It should not appear on the homepage.

## CSV Imports

Import holdings:

```bash
curl -F "file=@holdings.csv" "http://localhost:8000/api/import/holdings?source=Fidelity&replace=true"
```

The importer accepts common holdings CSV headers, derives market value from quantity and price when needed, and replaces rows for the selected source when `replace=true`.

## Data Storage

Docker uses PostgreSQL volume `focusos_postgres`. Local backend execution without `DATABASE_URL` creates `focusos-dev.db` in the current working directory.

There are no migrations yet. The backend uses `Base.metadata.create_all()` on startup.
