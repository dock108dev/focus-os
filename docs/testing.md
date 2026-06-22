# Testing

Run backend tests from the repository root:

```bash
python -m pip install -r backend/requirements-dev.txt
python -m pytest -q
```

The default backend test command enforces 90% line coverage over `backend/app`.

Run backend lint and security checks from the repository root:

```bash
python -m ruff check backend/app backend/tests
python -m bandit -q -r backend/app
python -m pip_audit -r backend/requirements-dev.txt
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
npm run lint
npm run security:audit
npm run build
```

The frontend gate runs ESLint, npm high-severity audit, TypeScript, and Vite production bundling.

Validate Docker configuration from the repository root:

```bash
docker compose config
docker compose config --no-interpolate
docker compose build api scheduler web
```

Run a local Docker smoke check:

```bash
docker compose up --build
curl http://localhost:8000/api/health
curl http://localhost:8000/api/briefing
```

If `FOCUSOS_INTERNAL_API_KEY` is set, include `X-FocusOS-Key` for job, source-status, archive-generation, and daily-review routes.

## CI

GitHub Actions runs backend linting, Bandit source scanning, pip-audit dependency scanning, backend tests with a 90% coverage gate, frontend ESLint, npm audit, the frontend production build, Docker Compose config validation, and Docker image builds for the API, scheduler, and web services. Pushes to `main` publish API and web images to GitHub Container Registry with `main` and commit-SHA tags.

## Current Test Gaps

There is no browser automation test for the React UI. Frontend validation is currently ESLint, npm audit, TypeScript, and Vite build.

External source refreshes are not hit by the unit tests. Tests mock source payloads or validate item-building logic.
