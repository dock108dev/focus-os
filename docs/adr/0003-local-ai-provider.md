# ADR 0003: Local AI provider

## Status

Accepted.

## Context

Direct OpenAI web-search calls worked for basic responses but were too slow or timeout-prone for local multi-topic generation. The local environment already has an authenticated Codex CLI, and the Docker backend image now installs the same CLI family so container behavior can match local behavior.

## Decision

Support `AI_PROVIDER=codex_cli` for local and Docker development.

The Codex provider runs:

```bash
codex --search exec --skip-git-repo-check --ephemeral --sandbox read-only ...
```

Direct OpenAI API support remains available with `AI_PROVIDER=openai`. The CLI provider should be able to perform the same web-search briefing role as the API provider when credentials are present.

## Consequences

Codex CLI is viable but slow for six topics. The morning briefing job stays outside the synchronous request path. Docker no longer treats the CLI provider as missing; missing credentials or runtime provider failures are real source-status errors, not an unsupported-image limitation.
