from __future__ import annotations

from datetime import date, datetime
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .attention import normalize_attention_category
from .models import (
    CryptoPrice,
    JobRun,
    MarketPrice,
    SourceStatus,
    TopicBriefing,
    WatchEvaluation,
    WeatherRecommendation,
)
from .registries import KNOWN_MISSING_SOURCE_STATUSES
from .source_status import serialize_source_status


def _matches_date(value: datetime | None, selected_date: date) -> bool:
    return bool(value and value.date() == selected_date)


def serialize_job_run(row: JobRun | None) -> dict:
    if row is None:
        return {
            "status": "missing",
            "message": "No morning briefing job run recorded for this date.",
            "details": {},
        }
    return {
        "job_id": row.id,
        "name": row.name,
        "status": row.status,
        "message": row.message,
        "details": row.details or {},
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


def latest_job_for_date(db: Session, selected_date: date) -> JobRun | None:
    rows = list(
        db.scalars(
            select(JobRun)
            .where(JobRun.name == "morning-briefing")
            .order_by(JobRun.created_at.desc(), JobRun.id.desc())
        ).all()
    )
    for row in rows:
        if (
            _matches_date(row.completed_at, selected_date)
            or _matches_date(row.started_at, selected_date)
            or _matches_date(row.created_at, selected_date)
        ):
            return row
    return None


def _count_rows_for_date(
    db: Session, model, selected_date: date, column_name: str = "as_of"
) -> int:
    column = getattr(model, column_name)
    return int(
        db.scalar(select(func.count()).select_from(model).where(column == selected_date))
        or 0
    )


def source_counts_for_date(db: Session, selected_date: date, job: JobRun | None) -> dict:
    structured = {}
    if job and isinstance(job.details, dict):
        structured = job.details.get("structured") or {}

    return {
        "market_prices": structured.get("market_prices")
        if "market_prices" in structured
        else _count_rows_for_date(db, MarketPrice, selected_date),
        "crypto_prices": structured.get("crypto_prices")
        if "crypto_prices" in structured
        else _count_rows_for_date(db, CryptoPrice, selected_date),
        "weather_recommendations": structured.get("weather_recommendations")
        if "weather_recommendations" in structured
        else _count_rows_for_date(db, WeatherRecommendation, selected_date),
        "github_facts": structured.get("github_facts")
        if "github_facts" in structured
        else github_fact_count(db),
        "topic_briefings": (job.details or {}).get("topic_briefings")
        if job and isinstance(job.details, dict) and "topic_briefings" in job.details
        else _count_rows_for_date(db, TopicBriefing, selected_date),
        "watch_evaluations": (job.details or {}).get("watch_evaluations")
        if job and isinstance(job.details, dict) and "watch_evaluations" in job.details
        else _count_rows_for_date(db, WatchEvaluation, selected_date),
    }


def github_fact_count(db: Session) -> int:
    status = db.scalar(select(SourceStatus).where(SourceStatus.name == "GitHub API"))
    details = status.details if status and isinstance(status.details, dict) else {}
    facts = details.get("facts") if isinstance(details, dict) else []
    return len(facts) if isinstance(facts, list) else 0


def briefing_counts(payload: dict) -> dict:
    assistant = payload.get("assistant_briefing") or {}
    attention = payload.get("attention") or []
    quiet = assistant.get("quiet") or []
    suppressed = [
        item
        for item in [*attention, *quiet]
        if isinstance(item, dict) and item.get("suppressed_by")
    ]
    return {
        "needs_attention": len(assistant.get("needs_attention") or []),
        "watch_only": len(assistant.get("watch_only") or []),
        "catch_up": len(assistant.get("catch_up") or []),
        "quiet": len(quiet),
        "suppressed": len(suppressed),
        "attention_total": len(attention),
    }


def top_item(payload: dict) -> str | None:
    assistant = payload.get("assistant_briefing") or {}
    primary = assistant.get("primary_focus") or {}
    title = primary.get("title")
    if title and title != "No single focus today":
        return title
    attention = payload.get("attention") or []
    first = attention[0] if attention else None
    return first.get("title") if isinstance(first, dict) else None


def top_surface_reason(payload: dict) -> str:
    assistant = payload.get("assistant_briefing") or {}
    primary = assistant.get("primary_focus") or {}
    for key in ("why_today", "summary", "why_now"):
        value = primary.get(key)
        if value:
            return value
    attention = payload.get("attention") or []
    for item in attention:
        if isinstance(item, dict) and item.get("why_today"):
            return item["why_today"]
    return "No item met the primary-focus threshold."


def top_quiet_reason(payload: dict) -> str:
    assistant = payload.get("assistant_briefing") or {}
    quiet = assistant.get("quiet") or []
    for item in quiet:
        if isinstance(item, dict) and item.get("suppressed_by"):
            return item["suppressed_by"]
    attention = payload.get("attention") or []
    quiet_attention = [
        item
        for item in attention
        if isinstance(item, dict)
        and normalize_attention_category(
            item.get("category") or item.get("classification")
        )
        == "awareness"
    ]
    if quiet_attention:
        return (
            quiet_attention[0].get("why_today")
            or quiet_attention[0].get("why_now")
            or "Awareness-only item stayed quiet."
        )
    return "No quiet items were available to explain."


def current_source_statuses(db: Session) -> list[dict]:
    return [
        serialize_source_status(row)
        for row in db.scalars(select(SourceStatus).order_by(SourceStatus.name)).all()
    ]


def failed_sources(statuses: Iterable[dict]) -> list[dict]:
    return [
        row
        for row in statuses
        if row.get("status")
        in {
            "error",
            "partial",
            "missing",
            "manual_needed",
            "requires_configuration",
        }
    ]


def github_debug_payload(statuses: Iterable[dict]) -> dict:
    github = next((row for row in statuses if row.get("name") == "GitHub API"), None)
    details = github.get("details") if github else {}
    if not isinstance(details, dict):
        details = {}
    return {
        "status": github.get("status") if github else "missing",
        "owner": details.get("owner"),
        "repos_scanned": details.get("repos_scanned", 0),
        "archived_repos_ignored": details.get("archived_repos_ignored", 0),
        "open_prs_found": details.get("open_prs_found", 0),
        "failed_workflows_found": details.get("failed_workflows_found", 0),
        "security_alerts": details.get("security_alerts", "unavailable"),
        "active_repo_ages": details.get("active_repo_ages", []),
        "facts": len(details.get("facts") or []),
        "errors": details.get("errors", []),
    }


def build_daily_review(db: Session, selected_date: date, payload: dict) -> dict:
    job = latest_job_for_date(db, selected_date)
    statuses = current_source_statuses(db)
    source_failures = failed_sources(statuses)
    missing_sources = [*KNOWN_MISSING_SOURCE_STATUSES]
    warnings = []
    if job is None:
        warnings.append("No morning briefing job run was recorded for this date.")
    if github_debug_payload(statuses)["repos_scanned"] == 0:
        warnings.append("GitHub adapter has not recorded any scanned public repos.")

    return {
        "date": selected_date.isoformat(),
        "job_result": serialize_job_run(job),
        "source_counts": source_counts_for_date(db, selected_date, job),
        "briefing_counts": briefing_counts(payload),
        "top_item": top_item(payload),
        "sources_checked": statuses,
        "sources_failed": source_failures,
        "missing_sources": missing_sources,
        "top_reasons": {
            "surfaced": top_surface_reason(payload),
            "stayed_quiet": top_quiet_reason(payload),
        },
        "github_debug": github_debug_payload(statuses),
        "warnings": warnings,
    }
