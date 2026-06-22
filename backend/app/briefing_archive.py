from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .attention import (
    build_assistant_briefing,
    build_morning_attention_feed,
    homepage_scan_violations,
)
from .briefing_simulator import build_simulated_days, layout_recommendation
from .models import ArchivedBriefing


BRIEFING_PAYLOAD_DUPLICATE_KEYS = (
    "structured_attention",
    "financial_attention",
    "portfolio_intelligence",
)


def archive_metadata(payload: dict, briefing_date: date, source: str) -> dict:
    next_payload = dict(payload)
    for duplicate_key in BRIEFING_PAYLOAD_DUPLICATE_KEYS:
        next_payload.pop(duplicate_key, None)
    today = date.today()
    if "assistant_briefing" not in next_payload:
        next_payload["assistant_briefing"] = build_assistant_briefing(
            next_payload.get("attention", []),
            watch_status=next_payload.get("watch_status", []),
        )
    next_payload["briefing_date"] = briefing_date.isoformat()
    next_payload["is_archived"] = briefing_date < today
    next_payload["read_only"] = briefing_date < today
    next_payload["archive_source"] = source
    return next_payload


def upsert_archived_briefing(
    db: Session, briefing_date: date, payload: dict, source: str = "live"
) -> ArchivedBriefing:
    archived = db.scalar(
        select(ArchivedBriefing).where(ArchivedBriefing.briefing_date == briefing_date)
    )
    payload = archive_metadata(payload, briefing_date, source)
    if archived is None:
        archived = ArchivedBriefing(
            briefing_date=briefing_date,
            payload=payload,
            source=source,
        )
        db.add(archived)
    else:
        archived.payload = payload
        archived.source = source
    db.commit()
    db.refresh(archived)
    return archived


def get_archived_payload(db: Session, briefing_date: date) -> dict | None:
    archived = db.scalar(
        select(ArchivedBriefing).where(ArchivedBriefing.briefing_date == briefing_date)
    )
    if archived is None:
        return None
    return archive_metadata(archived.payload or {}, briefing_date, archived.source)


def mock_generated_at(briefing_date: date) -> str:
    return datetime.combine(
        briefing_date,
        time(hour=6, minute=30),
        tzinfo=timezone.utc,
    ).isoformat()


def mock_summary(briefing_date: date) -> dict:
    return {
        "current_value": 0,
        "daily_change": 0,
        "daily_change_pct": 0,
        "monthly_change": 0,
        "monthly_change_pct": 0,
        "cash_available": 0,
        "cash_percent": 0,
        "allocation": [],
        "latest_as_of": briefing_date.isoformat(),
    }


def mock_watch_status(scenario_name: str, briefing_date: date) -> list[dict]:
    base = [
        {
            "id": 1,
            "title": "Outdoor concert Friday",
            "summary": "Watching weather, parking, and timing.",
            "status": "active",
            "event_date": (briefing_date + timedelta(days=4)).isoformat(),
            "detail_id": "",
        },
        {
            "id": 2,
            "title": "Rutgers ticket renewal Friday",
            "summary": "Watching renewal window and deadline.",
            "status": "active",
            "event_date": (briefing_date + timedelta(days=5)).isoformat(),
            "detail_id": "",
        },
    ]
    if scenario_name in {"vacation week", "major event day"}:
        base.insert(
            0,
            {
                "id": 3,
                "title": "Vacation departure",
                "summary": "Watching weather, airport timing, and advisories.",
                "status": "active",
                "event_date": (briefing_date + timedelta(days=2)).isoformat(),
                "detail_id": "",
            },
        )
    if scenario_name == "ai breakthrough day":
        base.insert(
            0,
            {
                "id": 4,
                "title": "WWDC keynote",
                "summary": "Watching Apple, AI, Siri, Xcode, and developer tooling.",
                "status": "active",
                "event_date": (briefing_date + timedelta(days=5)).isoformat(),
                "detail_id": "",
            },
        )
    return base[:3]


def mock_briefing_payload(briefing_date: date, scenario) -> dict:
    attention = build_morning_attention_feed([scenario.topical], scenario.financial)
    layout = layout_recommendation(attention)
    watch_status = mock_watch_status(scenario.name, briefing_date)
    return archive_metadata(
        {
            "generated_at": mock_generated_at(briefing_date),
            "summary": mock_summary(briefing_date),
            "attention": attention,
            "assistant_briefing": build_assistant_briefing(
                attention, watch_status=watch_status
            ),
            "watch_status": watch_status,
            "opportunities": [],
            "recommended_actions": [],
            "topic_briefings": [],
            "holdings_count": 0,
            "sources": ["mock-archive"],
            "archive_review": {
                "scenario": scenario.name,
                "notes": scenario.notes,
                "recommended_layout": layout["mode"],
                "layout_reason": layout["reason"],
                "scan_violations": homepage_scan_violations(attention),
            },
        },
        briefing_date,
        "mock",
    )


def generate_mock_archive_payloads(
    total_days: int = 50, end_date: date | None = None
) -> list[tuple[date, dict]]:
    end_date = end_date or date.today()
    start_date = end_date - timedelta(days=total_days - 1)
    scenarios = build_simulated_days(total_days)
    return [
        (
            start_date + timedelta(days=index),
            mock_briefing_payload(start_date + timedelta(days=index), scenario),
        )
        for index, scenario in enumerate(scenarios)
    ]


def seed_mock_archive(
    db: Session,
    total_days: int = 50,
    end_date: date | None = None,
    replace: bool = False,
) -> int:
    written = 0
    for briefing_date, payload in generate_mock_archive_payloads(total_days, end_date):
        existing = db.scalar(
            select(ArchivedBriefing).where(
                ArchivedBriefing.briefing_date == briefing_date
            )
        )
        if existing is not None and not replace:
            continue
        upsert_archived_briefing(db, briefing_date, payload, source="mock")
        written += 1
    return written


def seed_mock_archive_if_empty(db: Session, total_days: int = 50) -> int:
    existing = db.scalar(select(ArchivedBriefing.id).limit(1))
    if existing is not None:
        return 0
    return seed_mock_archive(db, total_days=total_days, replace=False)
