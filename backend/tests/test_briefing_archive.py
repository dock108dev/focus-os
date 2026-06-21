from __future__ import annotations

from collections.abc import Iterator
from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.briefing_archive import generate_mock_archive_payloads, seed_mock_archive
from app.database import Base
from app.models import ArchivedBriefing


def test_mock_archive_generates_50_days_ending_today():
    today = date(2026, 6, 21)
    rows = generate_mock_archive_payloads(total_days=50, end_date=today)

    assert len(rows) == 50
    assert rows[0][0] == today - timedelta(days=49)
    assert rows[-1][0] == today
    assert all(row_date <= today for row_date, _ in rows)
    assert all("assistant_briefing" in payload for _, payload in rows)
    assert {payload["archive_review"]["scenario"] for _, payload in rows} >= {
        "boring market day",
        "crypto crash day",
        "golf weather week",
        "ai breakthrough day",
        "busy work week",
    }


def test_archive_api_serves_past_snapshot_and_rejects_future_dates():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    today = date.today()
    db = TestingSessionLocal()
    try:
        written = seed_mock_archive(db, total_days=50, end_date=today, replace=True)
        archived_count = db.scalar(select(func.count()).select_from(ArchivedBriefing))
    finally:
        db.close()

    def override_db() -> Iterator[Session]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[main.get_db] = override_db
    client = TestClient(main.app)
    past_date = today - timedelta(days=10)
    try:
        past = client.get(f"/api/briefing?date={past_date.isoformat()}")
        future = client.get(
            f"/api/briefing?date={(today + timedelta(days=1)).isoformat()}"
        )
    finally:
        main.app.dependency_overrides.clear()

    assert written == 50
    assert archived_count == 50
    assert past.status_code == 200
    assert past.json()["briefing_date"] == past_date.isoformat()
    assert past.json()["read_only"] is True
    assert past.json()["archive_source"] == "mock"
    assert len(past.json()["attention"]) >= 1
    assert past.json()["assistant_briefing"]["primary_focus"]
    assert len(past.json()["assistant_briefing"]["secondary_notes"]) <= 3
    assert future.status_code == 400


def test_today_briefing_is_regenerable_and_archived_as_live():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_db() -> Iterator[Session]:
        db = TestingSessionLocal()
        try:
            main.seed_if_empty(db)
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[main.get_db] = override_db
    client = TestClient(main.app)
    try:
        response = client.get("/api/briefing")
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["briefing_date"] == date.today().isoformat()
    assert payload["read_only"] is False
    assert payload["archive_source"] == "live"
    assert payload["assistant_briefing"]["greeting"] == "Good Morning Mike"
