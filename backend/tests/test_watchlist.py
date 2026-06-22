from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.database import Base
from app.models import WatchItem
from app.seeding import seed_default_watches
from app.watch_provenance import DEFAULT_MIKE_WATCHES
from app.watch_provenance import source_watch_id
from app.watchlist import (
    archive_expired_watch_items,
    create_watch_item,
    evaluate_active_watch_items,
    parse_watch_item,
    serialize_watch_item,
    watch_attention_items,
)


def in_memory_sessionmaker():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def in_memory_session() -> Iterator[Session]:
    testing_session = in_memory_sessionmaker()
    db = testing_session()
    try:
        yield db
    finally:
        db.close()


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
    today = date(2026, 6, 21)
    with in_memory_session() as db:
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

    assert len(surfaced) == 1
    assert (
        surfaced[0].title == "Outdoor concert in 4 days planning is starting to matter"
    )
    assert surfaced[0].category == "opportunity"
    assert attention[0]["detail_id"] == "watch:1"
    assert attention[0]["story_type"] == "focusos"
    assert attention[0]["domain"] == "Life"
    assert attention[0]["source_watch_ids"] == ["watch:1"]
    assert attention[0]["triggered_surface_rule"]
    assert attention[0]["suppressed_by"] is None
    assert attention[0]["why_today"]


def test_expired_watch_items_are_archived_automatically():
    with in_memory_session() as db:
        row = create_watch_item(
            db,
            "Past concert 2026-06-19\nWatch parking.",
            today=date(2026, 6, 18),
        )
        archived = archive_expired_watch_items(db, today=date(2026, 6, 22))
        db.refresh(row)

    assert archived == 1
    assert row.status == "archived"


def test_mike_default_profile_seeds_active_configured_watches():
    with in_memory_session() as db:
        seeded = seed_default_watches(db)
        seeded_again = seed_default_watches(db)
        evaluations = evaluate_active_watch_items(db, today=date(2026, 6, 21))
        watches = [
            serialize_watch_item(row)
            for row in db.scalars(select(WatchItem)).all()
        ]

    assert seeded == len(DEFAULT_MIKE_WATCHES)
    assert seeded_again == 0
    assert len(evaluations) == len(DEFAULT_MIKE_WATCHES)
    assert len(watches) == len(DEFAULT_MIKE_WATCHES)
    titles = {watch["title"] for watch in watches}
    assert {
        "Portfolio & market positioning",
        "Yankees",
        "Rutgers",
        "Golf weather",
        "Golf equipment",
        "AI / developer tools",
        "Work / namespace migration",
        "Side projects",
        "Home maintenance",
        "Bogey",
        "Life logistics",
        "Travel",
    } <= titles
    portfolio_watch = next(
        watch for watch in watches if watch["title"] == "Portfolio & market positioning"
    )
    assert portfolio_watch["status"] == "active"
    assert portfolio_watch["source_watch_id"] == source_watch_id(
        "Portfolio & market positioning"
    )
    assert portfolio_watch["conditions"]
    assert portfolio_watch["source_inputs"]
    assert portfolio_watch["cadence"] == "daily"
    assert portfolio_watch["surface_rules"]
    assert portfolio_watch["suppression_rules"]
    assert portfolio_watch["expires_at"] is None


def test_watch_item_api_creates_and_feeds_briefing():
    TestingSessionLocal = in_memory_sessionmaker()

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
    watch_config = created.json()["watch_item"]
    assert watch_config["conditions"][:2] == ["weather", "parking"]
    assert "weather" in watch_config["source_inputs"]
    assert watch_config["cadence"] == "daily"
    assert watch_config["surface_rules"]
    assert "generic reminders" in watch_config["suppression_rules"]
    assert watch_config["preferred_output"] == "watch"
    assert watches.status_code == 200
    assert watches.json()["watch_items"][0]["latest_evaluation"]["should_surface"]
    assert briefing.status_code == 200
    assert any(
        item["detail_id"].startswith("watch:") for item in briefing.json()["attention"]
    )


def test_watch_item_api_supports_owner_lifecycle():
    TestingSessionLocal = in_memory_sessionmaker()

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
