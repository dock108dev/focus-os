# Architecture

FocusOS is a local-first morning briefing app with four runtime pieces:

- React/Vite web app in `frontend/src`.
- FastAPI backend in `backend/app`.
- SQL database through SQLAlchemy models in `backend/app/models.py`.
- APScheduler process in `backend/app/scheduler.py`.

The Docker stack runs PostgreSQL, API, scheduler, and web services. The backend can also run without Docker and will use local SQLite when `DATABASE_URL` is not set.

## Request Flow

The homepage requests:

```text
GET /api/briefing
```

The frontend uses only the response `attention` array for the primary Morning Briefing. Supporting payload fields exist for detail views and audit use, but the frontend should not rebuild the homepage from portfolio summaries, topic briefings, or source status.

Clickable briefing items call:

```text
GET /api/recommendations/{detail_id}
```

The backend returns an appendix payload with summary text, source metadata, supporting facts, raw data, optional AI methodology, and suppressed signals.

## Backend Route Map

- `GET /api/health`: liveness check.
- `GET /api/briefing`: assembled briefing payload.
- `GET /api/topics`: configured topics.
- `GET /api/recommendations/{detail_id}`: appendix detail for a briefing item.
- `POST /api/import/holdings`: CSV holdings import.
- `POST /api/jobs/morning-briefing`: queue the background morning refresh job.
- `GET /api/jobs/morning-briefing/{job_id}`: read job status.
- `GET /api/internal/source-status`: read source health.

Internal operational routes require `X-FocusOS-Key` only when `FOCUSOS_INTERNAL_API_KEY` is set.

## Morning Job Flow

The scheduler service reads `MORNING_JOB_TIME`, `TZ`, and `FOCUSOS_API_URL`. At the configured time, it sends `POST /api/jobs/morning-briefing`.

The API immediately creates a `JobRun`, returns a `job_id`, and runs refresh work in a daemon thread:

1. Refresh Yahoo Finance prices for tracked holdings.
2. Refresh CoinGecko Bitcoin price.
3. Refresh Open-Meteo golf weather recommendation.
4. Generate structured and unstructured topic briefings.
5. Record job success or failure in `job_runs`.

## Source Refresh Flow

Structured sources live in `backend/app/structured_sources.py`:

- Yahoo Finance chart endpoint for market prices.
- CoinGecko simple price endpoint for Bitcoin.
- Open-Meteo forecast endpoint for golf weather.

Topic generation lives in `backend/app/topic_engine.py`:

- `AI_PROVIDER=fallback`: deterministic fallback text.
- `AI_PROVIDER=openai`: OpenAI Responses API with web search.
- `AI_PROVIDER=codex_cli`: local Codex CLI web-search execution.

## Startup Seeding

`backend/app/main.py` creates tables during FastAPI lifespan startup. `backend/app/seeding.py` then seeds the empty database with sample holdings, portfolio snapshots, default topics, default configured watches, and fallback topic briefings.

## Current SSOTs

- Homepage briefing feed: `backend/app/main.py` serves `GET /api/briefing`, and `backend/app/attention.py` assembles the authoritative `attention` array.
- Watch configuration: persisted `WatchItem` rows in `backend/app/models.py` are evaluated by `backend/app/watchlist.py`.
- Watch provenance ids: `backend/app/watch_provenance.py` defines the stable `source_watch_id` format. The API serializes this id with each watch item; the frontend displays it but does not reconstruct it.
- Structured sources: `backend/app/structured_sources.py` owns market, crypto, and weather refresh/read behavior.
- Topic generation: `backend/app/topic_engine.py` owns AI provider selection and topic briefing serialization.

## Security Boundaries

Browser-origin checks apply to unsafe HTTP methods. CSV uploads are size-limited and must use CSV filenames/content types. Security headers are added to API responses. See [security-hardening.md](security-hardening.md) for the current security notes.
