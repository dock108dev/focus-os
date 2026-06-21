# Task Status

This file tracks high-level work only. Keep it current when scope changes or a task moves.

## Done

- Created local React, TypeScript, Vite frontend.
- Created FastAPI backend with local SQLite fallback and PostgreSQL Docker config.
- Added manual finance CSV import.
- Added portfolio summary, allocation, cash, opportunities, and finance attention signals.
- Added topic and topic briefing models.
- Added morning briefing endpoint.
- Added scheduler service for local Docker.
- Replaced custom scheduler loop with APScheduler.
- Added Codex CLI AI provider for local topic generation.
- Added future-enhancements parking lot.
- Tested a Recommended Actions card, then removed visible action-card framing from the homepage.
- Updated fallback topic briefings so they do not appear as Today’s Attention.
- Standardized user-facing product casing as `FocusOS`.
- Moved morning briefing job out of the synchronous request path.
- Added Yahoo Finance market price refresh.
- Added CoinGecko Bitcoin price refresh.
- Added Open-Meteo golf weather recommendation.
- Added internal source health/status endpoint.
- Centralized Mike-specific finance personalization rules.
- Added clickable recommendation evidence with underlying data, sources, methodology, and items not shown.
- Implemented the visual MVP direction as a mobile-first morning briefing packet.
- Revised the visual direction to a modern private briefing memo with Dark Ink palette, softer dividers, evidence language, and tablet two-pane layout.
- Simplified the homepage into an edited briefing list with no visible priority, category, evidence, score, confidence, or generic action labels.
- Added briefing information classes: Action Required, Potential Opportunity, and Worth Knowing.
- Separated Portfolio State, Portfolio Intelligence, and the Morning Briefing attention feed.
- Added product-voice guardrails that remove patronizing generated phrasing and redesigned the appendix around sources, supporting facts, and collapsed details.
- Removed homepage right rail sections so the homepage renders only the Morning Briefing output.
- Cleared generic backend action text so `Review whether...` copy does not leak into future surfaces.
- Made `/api/briefing.attention` the homepage SSOT and removed frontend reconstruction from portfolio intelligence fields.
- Cleaned repo entry docs, split frontend API/types from `App.tsx`, moved seed-data setup out of `main.py`, and added Docker build-context ignores.

## In Progress

- Keep homepage focused on editorial conclusions instead of generated explanations or implementation details.
- Keep docs current as product decisions change.

## Next

- Run the 30-day habit test: did Mike voluntarily open FocusOS at least 25 days?
- Use the habit-test result to decide whether to add more source types or reassess the product.
- Promote Portfolio and Portfolio Intelligence into dedicated pages only if the homepage proves useful first.
- Add separate Portfolio and Topic surfaces only after the one-scroll Morning Brief proves useful.

## Later

- ESPN sports source for Yankees and Rutgers.
- Curated major world sports calendar.
- Google Calendar integration.
- YouTube subscription monitoring.
- Historical attention analytics.
- Native iOS app.
- Parallelized or queued Codex CLI topic generation if local AI remains the provider.
- Internal source health view, only if source health becomes hard to diagnose from the API.
- Full route-based detail pages if the inline detail panel becomes too cramped.
- Further visual QA on physical iPad/iPhone dimensions during the 30-day habit test.
