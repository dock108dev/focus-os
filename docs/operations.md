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
curl -H "X-FocusOS-Key: $FOCUSOS_INTERNAL_API_KEY" http://localhost:8000/api/jobs/morning-briefing/<job_id>
```

The API returns immediately after queuing. Refresh work runs in-process on a daemon thread, so this is not a durable job queue.

### Failure Handling

Morning jobs distinguish provider degradation from system failure:

- External source failures for Yahoo Finance, CoinGecko, Open-Meteo, GitHub, OpenAI, and Codex CLI are expected non-fatal failures. The job continues when possible and writes explicit rows to `/api/internal/source-status` with `ok`, `partial`, `error`, or `skipped` status.
- AI provider failures generate fallback topic rows, but the `AI Topic Briefings` source status records whether the provider was skipped, partially failed, or fully failed.
- Database write failures, missing job status rows, and unexpected application exceptions are system failures. The job is marked `failed` when the status row can be written, and stack traces are logged by the API process.
- If the background worker cannot find the queued job row, it stops the job work and logs `morning_briefing_job_status_missing`. That means the refresh did not have durable status tracking and should be investigated as a data integrity issue.

## Briefing Archive

Today's briefing is assembled live from current database state and then stored in `archived_briefings`. Prior days are read through the same endpoint:

```bash
curl "http://localhost:8000/api/briefing?date=2026-06-21"
```

Generate local mock archive snapshots for review:

```bash
curl -H "Content-Type: application/json" -d '{"days":50,"replace":false}' http://localhost:8000/api/internal/briefing-archive/mock
```

This mock-generation route is internal and requires `X-FocusOS-Key` when `FOCUSOS_INTERNAL_API_KEY` is configured.

## Watch Admin

Watch Admin stores editable attention configuration. The briefing can surface watch evaluations, but the watch list itself is not homepage content.

```bash
curl http://localhost:8000/api/watch-items
curl -H "Content-Type: application/json" -d '{"text":"Home maintenance\nWatch weather risk, due dates, and contractor timing."}' http://localhost:8000/api/watch-items
curl -X POST http://localhost:8000/api/watch-items/<watch_item_id>/complete
curl -X POST http://localhost:8000/api/watch-items/<watch_item_id>/archive
curl -X DELETE http://localhost:8000/api/watch-items/<watch_item_id>
```

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

## Daily Review

Use the daily review endpoint after a scheduled or manual morning job to inspect what happened without judging only the UI:

```bash
curl http://localhost:8000/api/internal/daily-review
curl "http://localhost:8000/api/internal/daily-review?date=2026-06-23"
```

With an internal key:

```bash
curl -H "X-FocusOS-Key: $FOCUSOS_INTERNAL_API_KEY" http://localhost:8000/api/internal/daily-review
```

The response includes the job result, source counts, briefing bucket counts, checked and failed sources, explicit missing integrations, GitHub scan debug information, and the top surfaced/quiet reasons.

## CSV Imports

Import holdings:

```bash
curl -F "file=@holdings.csv" "http://localhost:8000/api/import/holdings?source=Fidelity&replace=true"
```

The importer accepts common holdings CSV headers, derives market value from quantity and price when needed, and replaces rows for the selected source when `replace=true`.

## Data Storage

Docker uses PostgreSQL volume `focusos_postgres`. Local backend execution without `DATABASE_URL` creates `focusos-dev.db` in the current working directory.

Docker Compose publishes the web, API, and PostgreSQL ports on `127.0.0.1` only. The services can still reach each other on the Compose network, but they are not exposed to the local network by default.

There are no migrations yet. The backend uses `Base.metadata.create_all()` on startup.
