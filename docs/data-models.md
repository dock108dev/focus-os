# Data Models

The backend uses SQLAlchemy models in `backend/app/models.py`. Tables are created at startup with `Base.metadata.create_all()`.

## Portfolio

`holdings`

- Imported portfolio rows.
- Source, account, symbol, name, asset class, quantity, price, market value, cost basis, and import date.

`portfolio_snapshots`

- Daily portfolio totals used for daily and monthly change calculations.
- Stores `as_of`, `total_value`, and `cash_available`.

## Topics

`topics`

- Configured briefing topics.
- Stores name, priority, source type, category, refresh frequency, prompt, and active flag.

`topic_briefings`

- Generated or fallback briefing rows for topics.
- Stores title, summary, bullets, action, source type, priority, and provider label.

## Structured Sources

`market_prices`

- Latest stored Yahoo Finance market price facts by symbol and date.
- Unique by `symbol` and `as_of`.

`crypto_prices`

- Latest stored CoinGecko crypto facts by asset and date.
- Current implementation stores Bitcoin.

`weather_recommendations`

- Open-Meteo activity recommendation rows.
- Current implementation stores a golf recommendation with raw candidate forecast data.

## Operations

`source_statuses`

- Internal status records for source refreshes and AI topic generation.
- Stores status, last run timestamp, message, and details.

`job_runs`

- Morning briefing job status records.
- Stores queued/running/succeeded/failed state, timestamps, message, and details.

## Relationships

`Topic` has many `TopicBriefing` rows. Other tables are currently queried directly rather than through ORM relationships.
