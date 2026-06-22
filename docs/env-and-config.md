# Environment And Config

Copy `.env.example` to `.env` for Docker Compose local defaults:

```bash
cp .env.example .env
```

## Backend

- `DATABASE_URL`: SQLAlchemy database URL. Defaults to `sqlite:///./focusos-dev.db` when unset.
- `OPENAI_API_KEY`: required only when `AI_PROVIDER=openai`.
- `OPENAI_MODEL`: OpenAI model name. Defaults in code to `gpt-5.5`.
- `OPENAI_REQUEST_TIMEOUT`: OpenAI client timeout in seconds. Defaults to `20`.
- `AI_PROVIDER`: `fallback`, `openai`, or `codex_cli`. If unset, code uses `openai` when `OPENAI_API_KEY` exists and `fallback` otherwise.
- `FOCUSOS_CORS_ORIGINS`: comma-separated browser origins allowed to make unsafe requests.
- `FOCUSOS_INTERNAL_API_KEY`: optional shared key for operational routes.
- `FOCUSOS_MAX_IMPORT_BYTES`: maximum CSV upload size. Invalid values fall back to 1 MiB.
- `FOCUSOS_ENABLE_HSTS`: enables HSTS response headers when set to `1`, `true`, or `yes`.
- `LOG_LEVEL`: scheduler/API logging level used where logging is configured.

## Scheduler

- `FOCUSOS_API_URL`: base URL the scheduler POSTs to. Docker sets this to `http://api:8000`.
- `MORNING_JOB_TIME`: daily trigger time in `HH:MM` format. Defaults to `06:00`.
- `TZ`: scheduler timezone. Docker defaults to `America/New_York`.

## Codex CLI Provider

These are read only when `AI_PROVIDER=codex_cli`:

- `CODEX_CLI_PATH`: executable path. Defaults to `codex`.
- `CODEX_CLI_TIMEOUT`: per-topic timeout in seconds. Defaults to `90`.
- `CODEX_CLI_WORKDIR`: workspace passed to the Codex CLI. Defaults to the repository root.

The backend Docker image installs the same `@openai/codex` CLI family used locally, so `AI_PROVIDER=codex_cli` is supported in Docker. The container still needs credentials through the same environment path used by the CLI, typically `OPENAI_API_KEY`.

## Weather Inputs

- `GOLF_LATITUDE`: Open-Meteo latitude. Defaults to Basking Ridge, NJ.
- `GOLF_LONGITUDE`: Open-Meteo longitude. Defaults to Basking Ridge, NJ.
- `GOLF_LOCATION`: display label stored with the golf recommendation.
- `WEATHER_TIMEZONE`: Open-Meteo forecast timezone. Defaults to `America/New_York`.

## GitHub Inputs

- `GITHUB_TOKEN`: optional GitHub API token. When unset, FocusOS uses public unauthenticated GitHub API calls.
- `FOCUSOS_GITHUB_OWNER`: GitHub user or organization to scan. Defaults to `dock108dev`.

## Frontend

- `VITE_API_TARGET`: Vite development proxy target for `/api`. Defaults to `http://localhost:8000` in `frontend/vite.config.ts`; Docker sets it to `http://api:8000`.

## Docker Defaults

Docker Compose sets `DATABASE_URL` to PostgreSQL, defaults `AI_PROVIDER` to `fallback`, forwards structured-source and Codex CLI settings into the API container, binds exposed ports to `127.0.0.1`, and mounts source directories into the API and web containers for local development. If `.env` sets `AI_PROVIDER=codex_cli`, the API uses the installed Codex CLI inside its container. The API and scheduler receive `FOCUSOS_INTERNAL_API_KEY`; if the key is configured, the scheduler sends it as `X-FocusOS-Key`.
