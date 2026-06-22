# Security Hardening Notes

## Security Understanding

FocusOS is a local-first personal briefing app with a FastAPI backend, SQLite/PostgreSQL storage, a Vite React frontend, and an APScheduler service that triggers the morning briefing job.

Primary trust boundaries:

- Browser to API: public briefing/detail reads, CSV upload writes, and frontend-triggered local interactions.
- Scheduler to API: operational job trigger.
- API to database: personal holdings, topic briefings, job status, source status, and raw source payloads.
- API to third parties: OpenAI Responses API, Codex CLI local provider, CoinGecko, Yahoo Finance, and Open-Meteo.
- Local configuration: provider keys, CORS origins, upload limits, and optional internal API key.

## Fixed Findings

### Untrusted browser origins could trigger state-changing requests

- Category: API and browser security
- Affected area: `POST /api/import/holdings`, `POST /api/jobs/morning-briefing`
- Severity: medium
- Confidence: high
- Status: fixed

Before this change, CORS configured read visibility but did not reject state-changing requests from untrusted browser origins. A malicious page could submit a form-style POST to mutate local app state even if it could not read the response.

Implemented fix: unsafe methods now reject browser requests whose `Origin` is outside `FOCUSOS_CORS_ORIGINS`.

### CSV uploads were read without an application-level size limit

- Category: Input handling and abuse control
- Affected area: `POST /api/import/holdings`
- Severity: medium
- Confidence: high
- Status: fixed

Before this change, the API read the full uploaded holdings file before parsing. A large upload could consume unnecessary memory and request time.

Implemented fix: CSV uploads are capped by `FOCUSOS_MAX_IMPORT_BYTES`, defaulting to 1 MiB, and non-CSV uploads are rejected.

### Operational internal routes had no deployable shared-secret guard

- Category: Authentication and operational security
- Affected area: `POST /api/jobs/morning-briefing`, `GET /api/jobs/morning-briefing/{job_id}`, `GET /api/internal/source-status`
- Severity: low
- Confidence: high
- Status: fixed

FocusOS is local-first, so public briefing reads remain unauthenticated. Internal operational endpoints can now require `X-FocusOS-Key` when `FOCUSOS_INTERNAL_API_KEY` is set. The scheduler passes that key automatically. Shared-key comparison uses constant-time comparison.

### Browser hardening headers were missing

- Category: Web hardening
- Affected area: all API responses
- Severity: low
- Confidence: high
- Status: fixed

Implemented fix: API responses now include `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, and `Cache-Control`. HSTS is opt-in with `FOCUSOS_ENABLE_HSTS=true` for HTTPS deployments.

### Docker development ports were reachable beyond loopback

- Category: Deployment and network exposure
- Affected area: Docker Compose web, API, and PostgreSQL ports
- Severity: medium
- Confidence: high
- Status: fixed

Before this change, Compose published `5432`, `8000`, and `5173` on all host interfaces. That could expose unauthenticated local-first surfaces and the development database to other machines on the same network.

Implemented fix: Compose now binds those ports to `127.0.0.1` while preserving service-to-service access on the Docker network.

### Job failure details could expose provider error text

- Category: Data protection and logging
- Affected area: morning job status details
- Severity: low
- Confidence: medium
- Status: fixed

Implemented fix: failed morning jobs now store the exception type instead of raw exception text in job status details. Stack traces remain in server logs.

### Background jobs could continue without durable status tracking

- Category: Reliability and observability
- Affected area: morning job background worker
- Severity: medium
- Confidence: high
- Status: fixed

Before this change, a missing `job_runs` row caused the status helper to log and return. The background worker could continue refreshing sources without a durable job status record, making an operational failure hard to distinguish from normal execution.

Implemented fix: missing job status rows now raise `JobRunMissingError`, stop the refresh work, and emit `morning_briefing_job_status_missing` if the worker cannot persist the failed state.

### Structured API validation errors were hidden behind generic frontend copy

- Category: Observability and debugging
- Affected area: frontend API error rendering
- Severity: low
- Confidence: high
- Status: fixed

Implemented fix: frontend API error parsing now extracts concise messages from FastAPI validation arrays instead of showing only the generic fallback label.

## Deferred Findings

### Local `.env` contains a live-looking OpenAI API key

- Category: Secrets and environment handling
- Severity: high
- Confidence: high
- Status: needs decision

The local `.env` file is ignored by `.gitignore`, but the key was present in the workspace during this hardening pass. Rotate the key in the OpenAI dashboard and replace the local value afterward. This report intentionally does not copy the key.

### Public read endpoints expose personal portfolio-derived data

- Category: Data protection and privacy
- Severity: medium
- Confidence: high
- Status: deferred

The MVP is local-first and intentionally unauthenticated. If FocusOS is exposed beyond a trusted local network, add full authentication and authorization before deployment.

### Codex CLI provider depends on a configured executable path

- Category: Supply chain and local execution
- Severity: low
- Confidence: medium
- Status: accepted

`AI_PROVIDER=codex_cli` runs a configured `codex` executable with `shell=False`, read-only sandboxing, and a configured workspace. The backend Docker image installs the CLI, so this provider is supported for local and Docker development when credentials are present.

## Manual Verification Items

- Rotate the OpenAI key that was present in `.env`.
- Confirm production reverse proxy TLS before enabling `FOCUSOS_ENABLE_HSTS=true`.
- Decide whether a non-local deployment should require authentication on all endpoints, including `/api/briefing` and recommendation details.
