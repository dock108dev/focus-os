# ADR 0011: Homepage editorial confidence

## Status

Accepted.

## Context

The homepage still exposed too many layers of hierarchy:

- product label
- page title
- section labels
- category labels
- item headlines
- priority scores
- evidence links
- action copy

This made the briefing feel generated from data rather than edited by a trusted chief of staff. Generic calls to action such as "review whether," "decide whether," and "consider whether" pushed the thinking back onto Mike.

## Decision

The homepage should read as one edited memo:

- Morning Briefing
- item
- item
- item

Homepage rules:

- Render the product name as `FocusOS`.
- Do not uppercase the product name in CSS.
- Do not show priorities, categories, confidence, scores, source labels, or evidence links in the primary briefing.
- Do not show generic action text in the primary briefing.
- Treat each homepage item as clickable; the card existing is the call to attention.
- Use editorial interpretation for item copy, for example "Bitcoin remains within expected volatility ranges" instead of raw movement language when the move is not meaningful.
- Keep portfolio and topic context out of the homepage unless it becomes a story. ADR 0015 removes the right rail entirely.
- Show evidence, scores, calculations, sources, methodology, raw payloads, and hidden items only in the briefing appendix modal.

## Consequences

The homepage now optimizes for confidence instead of visible machinery. It should feel like somebody already did the work and only surfaced what matters.

The appendix keeps auditability without making the morning read feel like an admin interface.
