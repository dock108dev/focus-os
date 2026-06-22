# Testing

Run backend tests from the repository root:

```bash
python -m pytest -q
```

The backend suite covers:

- CSV import parsing and validation.
- Portfolio attention thresholds and morning feed assembly.
- Structured source attention item rules.
- Topic fallback and AI payload cleanup.
- API security headers, CORS origin checks, upload limits, and internal API key checks.
- Recommendation detail routing.
- Watch Admin create, update, status, delete, and provenance serialization.
- Briefing archive metadata, prior-date reads, and mock archive generation.
- Novelty tracking for repeated briefing stories.
- Scheduler next-run calculation.

Run the frontend production build from `frontend/`:

```bash
npm ci
npm run build
```

The build runs TypeScript and Vite production bundling.

Validate Docker configuration from the repository root:

```bash
docker compose config
```

Run a local Docker smoke check:

```bash
docker compose up --build
curl http://localhost:8000/api/health
curl http://localhost:8000/api/briefing
```

If `FOCUSOS_INTERNAL_API_KEY` is set, include `X-FocusOS-Key` for job and source-status routes.

## Current Test Gaps

There is no browser automation test for the React UI. Frontend validation is currently TypeScript plus Vite build.

External source refreshes are not hit by the unit tests. Tests mock source payloads or validate item-building logic.
