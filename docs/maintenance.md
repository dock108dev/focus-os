# Maintenance Notes

Use this page when deciding whether cleanup should split files, remove generated assets, or add new validation.

## Regular Validation

Run these checks from the repository root before handing off source changes:

```bash
python -m ruff check backend/app backend/tests
python -m bandit -q -r backend/app
python -m pip_audit -r backend/requirements-dev.txt
python -m pytest -q
cd frontend
npm run lint
npm run security:audit
npm run build
```

Run this after changing Docker, environment, or service wiring:

```bash
docker compose config
docker compose config --no-interpolate
docker compose build api scheduler web
```

## Large Files Retained

These files are intentionally above roughly 500 lines today:

- `backend/app/attention_corpus.py`: owns the Mike v1 attention corpus generator and watch model used to produce simulation artifacts. Keep it together until the corpus review is finished.
- `backend/app/attention.py`: owns core attention scoring, grouping, novelty-facing metadata, and assistant briefing assembly. Split only when there is a stable boundary that reduces coupling.
- `backend/app/briefing_simulator.py`: keeps product simulation scenarios in one catalog so regressions are easy to inspect.
- `backend/app/watchlist.py`: contains watch parsing, source inference, evaluation, and serialization. It can split after watch behavior settles.
- `backend/app/watch_provenance.py`: owns the configured-watch catalog and stable source-watch id mapping. Keep it together while watch identity is still part of the product contract.
- `backend/app/topic_engine.py`: keeps topic defaults, provider execution, fallback generation, and topic serialization together. Provider code is the likely first extraction point.
- `backend/app/main.py`: is the FastAPI route map and startup wiring. Request schemas live in `backend/app/api_schemas.py`; extract route modules if the API grows beyond the current local-first app shape.
- `backend/app/structured_sources.py`: groups the current Yahoo Finance, CoinGecko, and Open-Meteo refreshers. Split by provider when source behavior needs independent tests or configuration.
- `backend/tests/test_runtime_coverage.py`: exercises hard-to-hit runtime branches for the 90% backend coverage gate. Split when those branch tests cluster around stable modules.
- `frontend/src/App.tsx`: still represents one compact product surface with briefing, archive, watch admin, and appendix views. Extract view components when UI flows stabilize.
- `frontend/src/styles.css`: global styles for the single Vite app. Move to component styles only after component boundaries are clearer.
- `docs/simulations/*.json` and `docs/simulations/*.md`: generated product simulation artifacts and reviewable evidence, not hand-maintained app code.
- `frontend/package-lock.json`: npm lockfile.

## Cleanup Rules

- Keep the homepage contract centered on `GET /api/briefing` and its `attention` output.
- Keep operational diagnostics in internal routes and docs, not on the homepage.
- Prefer deleting stale docs over adding parallel explanations.
- Keep new tests focused on behavior that would otherwise be easy to regress.
