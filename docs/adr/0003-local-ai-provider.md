# ADR 0003: Local AI provider

## Status

Accepted.

## Context

Direct OpenAI web-search calls worked for basic responses but were too slow or timeout-prone for local multi-topic generation. The local environment already has an authenticated Codex CLI.

## Decision

Support `AI_PROVIDER=codex_cli` for local development.

The Codex provider runs:

```bash
codex --search exec --skip-git-repo-check --ephemeral --sandbox read-only ...
```

Direct OpenAI API support remains available with `AI_PROVIDER=openai`.

## Consequences

Codex CLI is viable locally but slow for six topics. The morning briefing job should move out of the synchronous request path.

Docker remains configured for direct API use because the Codex CLI provider depends on local desktop auth and is not intended for the container.
