# ADR 0013: Portfolio layers vs attention feed

## Status

Accepted.

## Context

Portfolio facts were dominating the Morning Briefing:

- cash available
- technology allocation
- position concentration
- allocation percentages

Those facts are useful, but they are not automatically attention. When the brief becomes a list of portfolio rows, the product feels like a reporting dashboard instead of an editorial morning briefing.

## Decision

Separate portfolio information into three layers:

- Portfolio State: always-visible context such as value, cash, allocation, holdings, and performance.
- Portfolio Intelligence: analysis such as concentration, threshold crossings, allocation drift, and potential opportunities.
- Attention Feed: only conclusions or events that genuinely deserve morning attention.

The homepage Morning Briefing should not include routine portfolio state or ordinary portfolio intelligence. ADR 0015 removes the right rail; those layers can become dedicated Portfolio and Portfolio Intelligence pages later.

The Morning Briefing may include a portfolio conclusion such as "No major portfolio actions currently identified" when no portfolio event is important enough to lead the brief.

## Consequences

The brief remains editorial and event-driven.

Portfolio state remains accessible without pretending every portfolio fact is news.

Portfolio intelligence remains inspectable without making Mike feel like every signal is a task.
