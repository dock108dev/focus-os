from __future__ import annotations

from datetime import datetime, timezone
import logging

from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import JobRun
from .structured_sources import refresh_structured_sources
from .topic_engine import run_morning_briefing
from .watchlist import evaluate_active_watch_items


logger = logging.getLogger(__name__)


class JobRunMissingError(RuntimeError):
    """Raised when a background job can no longer persist status."""


def create_job_run(db: Session, name: str) -> JobRun:
    job = JobRun(name=name, status="queued", message="Queued.")
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def update_job_run(
    db: Session,
    job_id: int,
    status: str,
    message: str,
    details: dict | None = None,
    completed: bool = False,
) -> None:
    job = db.get(JobRun, job_id)
    if not job:
        raise JobRunMissingError(f"Job run {job_id} is missing.")
    job.status = status
    job.message = message
    if details is not None:
        job.details = details
    if status == "running" and job.started_at is None:
        job.started_at = datetime.now(timezone.utc)
    if completed:
        job.completed_at = datetime.now(timezone.utc)
    db.commit()


def run_morning_job_background(job_id: int) -> None:
    with SessionLocal() as db:
        try:
            update_job_run(
                db,
                job_id,
                "running",
                "Refreshing structured sources and topic briefings.",
            )
            structured = refresh_structured_sources(db)
            briefings = run_morning_briefing(db)
            watch_evaluations = evaluate_active_watch_items(db)
            update_job_run(
                db,
                job_id,
                "succeeded",
                "Morning briefing generated.",
                {
                    "structured": structured,
                    "topic_briefings": len(briefings),
                    "watch_evaluations": len(watch_evaluations),
                },
                completed=True,
            )
        except Exception as exc:
            logger.exception("morning_briefing_job_failed", extra={"job_id": job_id})
            try:
                update_job_run(
                    db,
                    job_id,
                    "failed",
                    "Morning briefing failed.",
                    {"error_type": type(exc).__name__},
                    completed=True,
                )
            except JobRunMissingError:
                logger.error(
                    "morning_briefing_job_status_missing",
                    extra={"job_id": job_id, "original_error_type": type(exc).__name__},
                )
            except Exception:
                logger.exception(
                    "morning_briefing_job_failure_status_update_failed",
                    extra={"job_id": job_id, "original_error_type": type(exc).__name__},
                )
