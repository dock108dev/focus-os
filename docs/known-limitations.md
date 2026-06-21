# Known Limitations

These are current implementation limits, not hidden roadmap commitments.

## Local-First Runtime

The app is built for a personal local stack. There is no production deployment manifest, managed secret flow, backup procedure, or multi-user account model.

## No Migrations

Database tables are created with SQLAlchemy `create_all()` on startup. Schema migrations are not implemented.

## Background Jobs Are Not Durable

The morning job runs in a daemon thread inside the API process. If the API process exits during a refresh, that job is not resumed.

## External Source Coverage Is Narrow

Implemented structured sources are Yahoo Finance for holdings-derived symbols, CoinGecko for Bitcoin, and Open-Meteo for golf weather. Sports APIs, YouTube, calendar, travel, and broader news connectors are not implemented.

## Fallback Briefings Are Not Homepage Attention

When AI or structured providers are unavailable, fallback topic briefings are stored for shape and detail, but they are intentionally suppressed from Today's Attention.

## Codex CLI Provider Is Local Only By Default

The stock backend Docker image does not install Codex CLI. `AI_PROVIDER=codex_cli` is intended for a local backend environment unless the image is extended.

## Frontend Test Coverage

The frontend currently has no browser or component test suite. Validation is TypeScript compilation and Vite build.

## Security Scope

The API includes origin checks for unsafe methods, optional internal API keys, upload limits, and security headers. It does not implement user authentication, authorization roles, rate limiting, audit logs, or encrypted local storage.
