# ADR 0006: Personalized finance thresholds

## Status

Accepted.

## Context

Generic market facts are not enough. The product should surface portfolio context only when it is interesting or consequential.

Finance cards should reflect Mike’s behavior, especially the idea that large-cap pullbacks are review moments before adding capital.

## Decision

Centralize Mike-specific thresholds in `backend/app/personalization.py`.

Current rules include:

- cash review threshold
- technology concentration threshold
- single-position concentration threshold
- pullback review threshold
- market move review threshold
- large-cap pullback review language

## Consequences

Finance signals can become more personal without hard-coding copy throughout the codebase.

These rules are review prompts only. They must not become trading decisions or financial advice.
