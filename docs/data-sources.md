# Data Source Plan

The product should not add 40 sources before proving that Mike opens the homepage every morning. Add sources in tiers and only promote a source when it improves the daily answer to:

> What should I know today?

## Tier 1: Immediate MVP Sources

### Finance

Purpose: portfolio, cash, allocation, market movement, and opportunities.

Initial approach:

- Manual CSV import for Fidelity, SoFi, and Tastytrade.
- Yahoo Finance for market prices.
- Alpha Vantage if Yahoo becomes unreliable.
- Polygon later if precision and paid reliability matter.

### Crypto

Purpose: Bitcoin movement and catalysts.

Initial approach:

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

- “Thursday is the best golf day this week.”

Weather should probably arrive before sports because it creates direct personal actions.

### Sports

Purpose: only Mike-relevant sports attention.

Initial approach:

- ESPN APIs.

Initial scope:

- Yankees.
- Rutgers.
- Major events.

SportsDataIO is a later paid option if ESPN is not enough.

## Implemented Source Status

Source health is stored internally and exposed at:

```text
/api/internal/source-status
```

This endpoint is intentionally not shown on the homepage. Mike should see useful cards, not connector diagnostics.

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
