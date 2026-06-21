# ADR 0008: APScheduler service

## Status

Accepted.

## Context

The MVP engineering prompt names APScheduler as the background job scheduler. The repo initially used a simple custom sleep loop in `backend/app/scheduler.py`.

## Decision

Use APScheduler's `BlockingScheduler` in the scheduler container. The schedule remains controlled by:

- `MORNING_JOB_TIME`
- `TZ`
- `FOCUSOS_API_URL`

## Consequences

The scheduler now matches the documented stack while keeping the deployment shape simple.

The scheduler triggers the API job endpoint, which queues the actual work in the API process.
