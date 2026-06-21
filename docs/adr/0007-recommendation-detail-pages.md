# ADR 0007: Recommendation detail pages

## Status

Accepted.

## Context

The homepage should stay concise, but Mike needs enough transparency to trust a recommendation. The engineering prompt requires every recommendation to be clickable and details to show raw data, source metadata, AI processing, and suppressed signals.

## Decision

Add stable `detail_id` values to homepage recommendations and expose:

```text
/api/recommendations/{detail_id}
```

The React homepage opens an inline detail panel for clicked attention items and recommended actions.

Detail payloads include:

- recommendation text
- why it was generated
- raw data
- source data
- AI processing when applicable
- suppressed signals

## Consequences

This keeps the homepage readable while making recommendation logic inspectable.

The current implementation is an inline panel rather than full route-based pages. Full pages can be added later if the detail surface becomes too cramped.
