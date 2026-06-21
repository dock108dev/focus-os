# ADR 0001: Use docs as product memory

## Status

Accepted.

## Context

FocusOS is changing quickly. Product direction, implementation choices, future ideas, and task status need to remain visible without overloading the homepage or code comments.

## Decision

Use the `docs/` folder as the project memory:

- `docs/mvp-spec.md` owns current MVP scope.
- `docs/tasks.md` owns high-level done, in-progress, next, and later status.
- `docs/future-enhancements.md` owns parking-lot ideas that are not current scope.
- `docs/data-sources.md` owns source prioritization.
- `docs/adr/` records decisions that should not be rediscovered later.

## Consequences

Every meaningful product or architecture shift should update docs in the same change.

Future ideas should be preserved without being mistaken for MVP commitments.
