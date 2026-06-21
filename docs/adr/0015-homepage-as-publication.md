# ADR 0015: Homepage as publication

## Status

Accepted.

## Context

The homepage still rendered the system inputs beside the briefing output:

- Portfolio
- Portfolio Intelligence
- Topics

This duplicated the same information that appeared in the Morning Briefing and made the product feel like a dashboard pretending to be a briefing.

## Decision

The homepage should show only the Morning Briefing.

Rules:

- No right rail on the homepage.
- No Topics section on the homepage.
- No Portfolio section on the homepage.
- No Portfolio Intelligence section on the homepage.
- The homepage renders outputs, not inputs.
- Tapping a story opens the appendix with sources, evidence, calculations, and details.
- Portfolio and Topics can become separate surfaces later, but they do not belong on the first screen.

Visual direction:

- One scroll.
- One featured item.
- Secondary stories below.
- Minimal dividers instead of repeated cards.

## Consequences

The homepage should feel more like a publication and less like database records arranged into cards.

The app can still use portfolio and topic data internally, but the user sees the curated result first.
