from __future__ import annotations

from collections.abc import Iterator
from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.database import Base
from app.watchlist import (
    archive_expired_watch_items,
    create_watch_item,
    evaluate_active_watch_items,
    parse_watch_item,
    watch_attention_items,
)


def test_plain_english_watch_extracts_event_and_monitoring_dimensions():
    parsed = parse_watch_item(
        "Outdoor concert Friday\nWatch weather, parking, timing, and plan changes.",
        today=date(2026, 6, 21),
    )

    assert parsed["title"] == "Outdoor concert Friday"
    assert parsed["event_date"] == date(2026, 6, 26)
    assert parsed["expires_at"] == date(2026, 6, 27)
    assert "weather" in parsed["watch_for"]
    assert "parking" in parsed["watch_for"]
    assert "timing" in parsed["watch_for"]
    assert "schedule changes" in parsed["watch_for"]


def test_watch_evaluation_surfaces_planning_window_but_suppresses_far_future():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    today = date(2026, 6, 21)
    try:
        create_watch_item(
            db,
            "Outdoor concert in 4 days\nWatch weather, parking, traffic, and door time.",
            today=today,
        )
        create_watch_item(
            db,
            "Conference in 18 days\nWatch agenda and schedule changes.",
            today=today,
        )

        evaluations = evaluate_active_watch_items(db, today=today)
        surfaced = [row for row in evaluations if row.should_surface]
        attention = watch_attention_items(surfaced)
    finally:
        db.close()

    assert len(surfaced) == 1
    assert (
        surfaced[0].title == "Outdoor concert in 4 days planning is starting to matter"
    )
    assert surfaced[0].category == "opportunity"
    assert attention[0]["detail_id"] == "watch:1"
    assert attention[0]["story_type"] == "focusos"
    assert attention[0]["domain"] == "Life"


def test_expired_watch_items_are_archived_automatically():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        row = create_watch_item(
            db,
            "Past concert 2026-06-19\nWatch parking.",
            today=date(2026, 6, 18),
        )
        archived = archive_expired_watch_items(db, today=date(2026, 6, 22))
        db.refresh(row)
    finally:
        db.close()

    assert archived == 1
    assert row.status == "archived"


def test_watch_item_api_creates_and_feeds_briefing(monkeypatch):
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
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[main.get_db] = override_db
    client = TestClient(main.app)
    try:
        created = client.post(
            "/api/watch-items",
            json={
                "text": "Outdoor concert in 4 days\nWatch weather, parking, and traffic."
            },
        )
        watches = client.get("/api/watch-items")
        briefing = client.get("/api/briefing")
    finally:
        main.app.dependency_overrides.clear()

    assert created.status_code == 200
    assert created.json()["watch_item"]["watch_for"][:2] == ["weather", "parking"]
    assert watches.status_code == 200
    assert watches.json()["watch_items"][0]["latest_evaluation"]["should_surface"]
    assert briefing.status_code == 200
    assert any(
        item["detail_id"].startswith("watch:") for item in briefing.json()["attention"]
    )


def test_watch_item_api_supports_owner_lifecycle(monkeypatch):
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
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[main.get_db] = override_db
    client = TestClient(main.app)
    try:
        created = client.post(
            "/api/watch-items",
            json={
                "text": "Outdoor concert in 4 days\nWatch weather, parking, and traffic."
            },
        )
        watch_id = created.json()["watch_item"]["id"]
        edited = client.patch(
            f"/api/watch-items/{watch_id}",
            json={
                "text": "Outdoor concert in 3 days\nWatch weather, parking, timing, and venue changes."
            },
        )
        completed = client.post(f"/api/watch-items/{watch_id}/complete")
        archived = client.post(f"/api/watch-items/{watch_id}/archive")
        watches_after_archive = client.get("/api/watch-items")
        removed = client.delete(f"/api/watch-items/{watch_id}")
        watches_after_remove = client.get("/api/watch-items")
    finally:
        main.app.dependency_overrides.clear()

    assert created.status_code == 200
    assert created.json()["active_count"] == 1
    assert edited.status_code == 200
    assert edited.json()["watch_item"]["title"] == "Outdoor concert in 3 days"
    assert "venue" not in edited.json()["watch_item"]["watch_for"]
    assert completed.status_code == 200
    assert completed.json()["active_count"] == 0
    assert completed.json()["watch_item"]["status"] == "completed"
    assert archived.status_code == 200
    assert archived.json()["watch_item"]["status"] == "archived"
    assert watches_after_archive.json()["counts"]["archived"] == 1
    assert removed.status_code == 200
    assert removed.json()["active_count"] == 0
    assert watches_after_remove.json()["watch_items"] == []
