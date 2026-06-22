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

## File Size Policy

Maintained source files should stay below roughly 500 lines. Split by stable product
or technical responsibility before adding a size exception.

Current source splits:

- Attention: core scoring, finance summaries, feed assembly, and public facade.
- Attention corpus: models, watches, scenario catalogs, generation, quality review, simulation, and rendering.
- Briefing simulator: scenario catalog, helpers, and simulator runner.
- Structured sources: common helpers plus finance, crypto, weather, GitHub, topic, and facade modules.
- Topic engine: defaults, fallbacks, provider execution, and public orchestration.
- Watchlist: rules, parsing, config, storage, evaluation, and public facade.
- Watch provenance: stable id helpers plus generated/catalog watch data.
- Frontend: app orchestration, briefing, archive, watch admin, appendix, header, shared watch formatting, and CSS by UI area.

Allowed large generated artifacts:

- `docs/simulations/*.md`: generated review evidence. They are intentionally
  stored as readable markdown so product regressions can be inspected in diffs.
- `frontend/package-lock.json`: npm lockfile.

Generated simulation JSON is written compactly to avoid line-count noise.

## Cleanup Rules

- Keep the homepage contract centered on `GET /api/briefing` and its `attention` output.
- Keep operational diagnostics in internal routes and docs, not on the homepage.
- Prefer deleting stale docs over adding parallel explanations.
- Keep new tests focused on behavior that would otherwise be easy to regress.
