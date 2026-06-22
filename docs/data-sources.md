# Data Source Plan

The product should not add 40 sources before proving that Mike opens the homepage every morning. Add sources in tiers and only promote a source when it improves the daily answer to:

> What should I know today?

## Tier 1: Immediate MVP Sources

### Finance

Purpose: portfolio, cash, allocation, market movement, and opportunities.

Implemented:

- Manual CSV import for Fidelity, SoFi, and Tastytrade.
- Yahoo Finance for holdings-derived market prices plus tracked symbols UNH, USO, SPY, QQQ, AAPL, and S&P 500 proxy.

Planned alternatives:

- Alpha Vantage if Yahoo becomes unreliable.
- Polygon later if precision and paid reliability matter.

### Crypto

Purpose: Bitcoin movement and catalysts.

Implemented:

- CoinGecko.

CoinGecko is free, reliable enough for MVP, and simple.

### Weather

Purpose: recommendations, not weather reporting.

Original candidates:

- OpenWeather.
- Pirate Weather as an alternative.

Implemented MVP source:

- Open-Meteo.

Open-Meteo was selected first because it requires no API key and allows the golf recommendation to work locally immediately.

Priority use case:

- “Basking Ridge has a standout playable golf window.”

Open-Meteo is evaluated against Basking Ridge defaults. Monday is suppressed because the course is closed, and Friday afternoon is downranked because it is likely crowded.

### Public GitHub

Purpose: repo health for Mike's public `dock108dev` repos.

Implemented:

- GitHub public REST API.
- Non-archived public repos only.
- Open PR detection.
- Automated PR detection from author metadata.
- About-two-week inactivity detection.
- Optional `GITHUB_TOKEN` for authenticated API calls; unauthenticated public calls are used when unset.

Missing:

- Private repos unless granted.
- Security alerts unless token scope allows them.
- Failing Actions beyond public metadata available to the current API path.

### Sports

Purpose: only Mike-relevant sports attention.

Planned:

- ESPN APIs.

Initial scope:

- Yankees.
- Rutgers.
- Major events.

SportsDataIO is a later paid option if ESPN is not enough.

## Current Structured Refresh Behavior

The morning job refreshes:

- Yahoo Finance market prices for non-cash, non-Bitcoin holdings and Mike's tracked market symbols.
- CoinGecko Bitcoin price and 24-hour movement.
- Open-Meteo seven-day Basking Ridge weather for the golf recommendation.
- GitHub public repo health for `dock108dev`.
- AI or fallback briefings for active unstructured topics.

The app records source health for refreshes and provider failures. Failed source refreshes do not stop every other source from refreshing, but database commit failures are allowed to fail the job.

## Implemented Source Status

Source health is stored internally and exposed at:

```text
/api/internal/source-status
```

This endpoint is intentionally not shown on the homepage. Mike should see useful cards, not connector diagnostics.

The source registry is also exposed at:

```text
/api/source-registry
/api/personal-accounts
```

The registry separates personal accounts/interests from provider integrations and marks missing or auth-required sources explicitly.

## Tier 2: AI Sources

These are where AI summarization and filtering should do the work.

### Geopolitics

Topics:

- Iran.
- China/Taiwan.
- Ukraine.

Use AI web search. Do not build a bespoke API integration.

### AI Industry

Topics:

- OpenAI.
- Anthropic.
- Google.
- Major model releases.
- Major infrastructure, policy, or talent shifts.

Use AI summarization. Suppress routine product announcements.

### Major World Sports

Do not scrape scores as the primary mechanism.

Build a curated calendar that changes slowly:

- Tennis majors.
- Golf majors.
- World Cup.
- Olympics.
- Formula 1.
- Indy 500.
- Daytona.
- Ryder Cup.

AI can summarize context around these events once the calendar identifies what matters.

## Tier 3: Personal Sources

These are future-state sources where the product can become more personal.

### YouTube

Monitor subscriptions and new uploads, then rank by relevance.

### Calendar

Google Calendar integration.

Use it to avoid recommending actions during conflicts and identify free windows.

### Travel

Track flights, passport reminders, planned trips, destination weather, and events that overlap with travel.
