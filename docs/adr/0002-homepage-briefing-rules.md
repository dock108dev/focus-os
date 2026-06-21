# ADR 0002: Homepage briefing rules

## Status

Superseded by ADR 0011.

## Context

The homepage is close, but topic fallbacks were exposing developer implementation details such as missing source setup. That weakens the chief-of-staff feel.

The product is not simply “What deserves attention today?” The stronger filter is whether the item is interesting or consequential without needing explanatory filler.

## Decision

Every homepage item should answer:

1. What happened?
2. Why should Mike care?
3. Is there an action?

Fallback topic briefings may appear inside topic status as quiet waiting states, but they must not be promoted into the primary briefing.

This ADR originally accepted a first-class Recommended Actions card. ADR 0011 and ADR 0012 supersede that choice: the homepage now avoids generic action framing and classifies items as Action Required, Potential Opportunity, or Worth Knowing.

## Consequences

The homepage should hide provider names, API setup, missing connectors, and other developer status unless Mike explicitly opens an internal source health view in the future.

Signals remain useful, but they should not all become review tasks.
