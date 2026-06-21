# ADR 0005: Background morning job

## Status

Accepted.

## Context

Codex CLI topic generation works locally but can take minutes for a six-topic batch. The morning briefing trigger should not block the HTTP request while structured sources and AI topics refresh.

## Decision

`POST /api/jobs/morning-briefing` creates a `JobRun`, starts work in a daemon thread, and returns immediately with a `job_id`.

Progress is read from:

```text
/api/jobs/morning-briefing/{job_id}
```

The background job refreshes structured sources first, then stores structured and AI topic briefings.

## Consequences

The homepage can remain responsive while the morning job runs.

This is good enough for the local MVP. A production version should replace the daemon thread with a real worker or queue.
