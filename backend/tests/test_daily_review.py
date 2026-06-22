from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.briefing_archive import upsert_archived_briefing
from app.database import Base
from app.daily_review import build_daily_review, github_debug_payload, top_quiet_reason, top_surface_reason
from app.models import JobRun, SourceStatus
from app.source_status import record_source_status, serialize_source_status


def in_memory_sessionmaker():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def test_daily_review_summarizes_job_sources_and_briefing_counts():
    testing_session = in_memory_sessionmaker()
    today = date.today()
    with testing_session() as db:
        db.add(
            JobRun(
                name="morning-briefing",
                status="succeeded",
                message="Morning briefing generated.",
                created_at=datetime.now(timezone.utc),
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                details={
                    "structured": {
                        "market_prices": 9,
                        "crypto_prices": 1,
                        "weather_recommendations": 1,
                        "github_facts": 0,
                    },
                    "topic_briefings": 6,
                    "watch_evaluations": 12,
                },
            )
        )
        db.add(
            SourceStatus(
                name="GitHub API",
                status="ok",
                message="Checked 2 public non-archived repos.",
                last_run_at=datetime.now(timezone.utc),
                details={
                    "owner": "dock108dev",
                    "repos_scanned": 2,
                    "archived_repos_ignored": 1,
                    "open_prs_found": 0,
                    "failed_workflows_found": 0,
                    "security_alerts": "unavailable_without_authenticated_security_scope",
                    "active_repo_ages": [
                        {"repo": "focus-os", "days_since_push": 0},
                        {"repo": "static", "days_since_push": 4},
                    ],
                    "facts": [],
                    "errors": [],
                },
            )
        )
        db.add(
            SourceStatus(
                name="CoinGecko",
                status="ok",
                message="Fetched Bitcoin price.",
                last_run_at=datetime.now(timezone.utc),
                details={},
            )
        )
        db.commit()
        upsert_archived_briefing(
            db,
            today,
            {
                "attention": [
                    {
                        "title": "Review portfolio positioning",
                        "why_now": "Portfolio thresholds changed.",
                        "category": "action",
                        "suggested_posture": "Review",
                    },
                    {
                        "title": "Golf weather stayed ordinary",
                        "why_now": "No standout window.",
                        "category": "awareness",
                    },
                ],
                "assistant_briefing": {
                    "mode": "focused",
                    "primary_focus": {
                        "title": "Review portfolio positioning",
                        "summary": "Portfolio thresholds changed.",
                        "why_today": "Portfolio thresholds changed.",
                    },
                    "needs_attention": [{"title": "Review portfolio positioning"}],
                    "watch_only": [],
                    "quiet": [
                        {
                            "title": "Golf weather stayed ordinary",
                            "suppressed_by": "ordinary weather with no notable window",
                        }
                    ],
                },
            },
            source="live",
        )

    def override_db() -> Iterator[Session]:
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[main.get_db] = override_db
    client = TestClient(main.app)
    try:
        response = client.get("/api/internal/daily-review")
        source_status = client.get("/api/internal/source-status")
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["date"] == today.isoformat()
    assert payload["job_result"]["status"] == "succeeded"
    assert payload["source_counts"]["market_prices"] == 9
    assert payload["source_counts"]["github_facts"] == 0
    assert payload["source_counts"]["watch_evaluations"] == 12
    assert payload["briefing_counts"]["needs_attention"] == 1
    assert payload["briefing_counts"]["quiet"] == 1
    assert payload["top_item"] == "Review portfolio positioning"
    assert payload["github_debug"]["repos_scanned"] == 2
    assert payload["github_debug"]["active_repo_ages"][0]["repo"] == "focus-os"
    assert any(item["name"] == "Direct Fidelity" for item in payload["missing_sources"])
    assert payload["warnings"] == []

    assert source_status.status_code == 200
    assert any(
        item["name"] == "BTC cost basis"
        for item in source_status.json()["known_missing"]
    )


def test_daily_review_reports_missing_job_and_degraded_sources():
    testing_session = in_memory_sessionmaker()
    today = date.today()
    payload = {
        "attention": [
            {
                "title": "Quiet watch",
                "why_today": "It is informational only.",
                "category": "awareness",
            }
        ],
        "assistant_briefing": {
            "primary_focus": {"title": "No single focus today"},
            "quiet": [],
        },
    }

    with testing_session() as db:
        db.add(
            SourceStatus(
                name="GitHub API",
                status="partial",
                message="No token configured.",
                details="not a dict",
            )
        )
        db.add(
            SourceStatus(
                name="Yahoo Finance",
                status="error",
                message="Provider unreachable.",
                details={"symbols": ["MSFT"]},
            )
        )
        db.commit()

        review = build_daily_review(db, today, payload)

    assert review["job_result"]["status"] == "missing"
    assert review["source_counts"]["github_facts"] == 0
    assert review["top_item"] == "Quiet watch"
    assert review["top_reasons"]["surfaced"] == "It is informational only."
    assert review["top_reasons"]["stayed_quiet"] == "It is informational only."
    assert [row["name"] for row in review["sources_failed"]] == ["GitHub API", "Yahoo Finance"]
    assert "No morning briefing job run was recorded for this date." in review["warnings"]
    assert "GitHub adapter has not recorded any scanned public repos." in review["warnings"]
    assert review["github_debug"]["status"] == "partial"
    assert review["github_debug"]["repos_scanned"] == 0


def test_daily_review_fallback_reason_helpers_and_source_status_upsert():
    testing_session = in_memory_sessionmaker()

    assert top_surface_reason({"assistant_briefing": {"primary_focus": {}}}) == (
        "No item met the primary-focus threshold."
    )
    assert top_quiet_reason({"assistant_briefing": {"quiet": []}, "attention": []}) == (
        "No quiet items were available to explain."
    )
    assert github_debug_payload([{"name": "GitHub API", "status": "ok", "details": []}]) == {
        "status": "ok",
        "owner": None,
        "repos_scanned": 0,
        "archived_repos_ignored": 0,
        "open_prs_found": 0,
        "failed_workflows_found": 0,
        "security_alerts": "unavailable",
        "active_repo_ages": [],
        "facts": 0,
        "errors": [],
    }

    with testing_session() as db:
        record_source_status(db, "Custom Feed", "ok", "Fetched.", {"count": 1})
        record_source_status(db, "Custom Feed", "partial")
        row = db.query(SourceStatus).filter_by(name="Custom Feed").one()
        serialized = serialize_source_status(row)

    assert serialized["name"] == "Custom Feed"
    assert serialized["status"] == "partial"
    assert serialized["message"] == ""
    assert serialized["details"] == {}
    assert serialized["last_run_at"] is not None
