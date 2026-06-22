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
    active_watch_status,
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
        "Personal finance and liquidity runway",
        "Investing ideas and market pullbacks",
        "Bitcoin accumulation posture",
        "Trading systems and liquidity constraints",
        "Personal GitHub repo health",
        "Side project and FocusOS validation",
        "Big tech, AI, and major company releases",
        "Sports radar with spoiler-safe recap",
        "Golf weather for Basking Ridge",
        "Shopping and product interest radar",
        "Media and watchlist radar",
        "Life notes, reminders, and personal admin",
    } <= titles
    portfolio_watch = next(
        watch for watch in watches if watch["title"] == "Personal finance and liquidity runway"
    )
    assert portfolio_watch["status"] == "active"
    assert portfolio_watch["source_watch_id"] == source_watch_id(
        "Personal finance and liquidity runway"
    )
    assert portfolio_watch["watch_kind"] == "hybrid"
    assert portfolio_watch["priority"] == "primary_allowed"
    assert portfolio_watch["personal_accounts"] == ["Fidelity", "SoFi", "Tastytrade"]
    assert portfolio_watch["personal_context"]["manual_facts"] == {
        "liquid_cash_target": 10000,
        "liquid_cash_minimum": 5000,
    }
    assert "manual_portfolio_csv" in portfolio_watch["connected_data_sources"]
    assert "liquid cash balance" in portfolio_watch["manual_inputs"]
    assert portfolio_watch["evaluation_rules"]["primary_focus_allowed"] is True
    assert portfolio_watch["prompt_config"]["guardrails_enabled"] is True
    assert portfolio_watch["conditions"]
    assert portfolio_watch["cadence"] == "daily"
    assert portfolio_watch["surface_rules"]
    assert portfolio_watch["suppression_rules"]
    assert portfolio_watch["expires_at"] is None
    life_watch = next(
        watch for watch in watches if watch["title"] == "Life notes, reminders, and personal admin"
    )
    assert life_watch["watch_kind"] == "personal_tracker"
    assert "Bogey" in life_watch["personal_interests"]
    ai_watch = next(
        watch for watch in watches if watch["title"] == "Big tech, AI, and major company releases"
    )
    assert ai_watch["watch_kind"] == "external_monitor"
    assert ai_watch["priority"] == "watch_only"
    assert "official changelog/RSS adapter" in ai_watch["connected_data_sources"]
    investing_watch = next(
        watch for watch in watches if watch["title"] == "Investing ideas and market pullbacks"
    )
    assert (
        investing_watch["personal_context"]["manual_facts"]["symbol_notes"]["USO"][
            "position"
        ]
        == "short"
    )
    bitcoin_watch = next(
        watch for watch in watches if watch["title"] == "Bitcoin accumulation posture"
    )
    assert bitcoin_watch["personal_context"]["manual_facts"]["btc_cost_basis"] == 75000
    golf_watch = next(
        watch for watch in watches if watch["title"] == "Golf weather for Basking Ridge"
    )
    assert golf_watch["personal_context"]["manual_facts"]["location"] == (
        "Basking Ridge, NJ"
    )


def test_active_watch_status_explains_why_quiet_without_debug_copy():
    with in_memory_session() as db:
        seed_default_watches(db)
        evaluate_active_watch_items(db, today=date(2026, 6, 21))
        statuses = active_watch_status(db)

    bitcoin = next(
        item for item in statuses if item["title"] == "Bitcoin accumulation posture"
    )
    assert bitcoin["summary"] == (
        "No BTC accumulation trigger today. Price movement did not meet the review rule."
    )
    rendered = " ".join(item["summary"] for item in statuses).lower()
    assert "watching" not in rendered
    assert "configured" not in rendered
    assert "source inputs" not in rendered
    assert "suppression rule" not in rendered
    assert "evaluation" not in rendered


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
    assert watch_config["watch_kind"] == "external_monitor"
    assert watch_config["conditions"][:2] == ["weather", "parking"]
    assert "weather" in watch_config["source_inputs"]
    assert "weather" in watch_config["external_sources"]
    assert watch_config["external_state"]["freshness_window"] == "same-day"
    assert watch_config["personal_state"]["actionable_when"]
    assert watch_config["prompt_config"]["guardrails_enabled"]
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


def test_watch_item_api_supports_guided_setup_contract():
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
                "title": "Console release radar",
                "watch_kind": "hybrid",
                "priority": "quiet_by_default",
                "check_frequency": "weekly",
                "watch_for": ["console releases", "gaming PC"],
                "personal_context": {
                    "why_i_care": "Useful only when it changes purchase timing.",
                    "accounts": ["Amazon if integration becomes feasible"],
                    "interests": ["console releases", "gaming PC"],
                    "owned_assets": [],
                    "ignored_accounts": [],
                },
                "source_config": {
                    "connected_sources": ["manual_shopping_interests"],
                    "available_sources": ["Steam API"],
                    "missing_sources": ["direct Amazon purchase/preference integration unless available"],
                    "manual_inputs": ["saved products"],
                },
                "evaluation_rules": {
                    "surface_when": ["major console news changes purchase timing"],
                    "suppress_when": ["generic deals"],
                    "primary_focus_allowed": False,
                },
                "prompt_config": {
                    "daily_prompt_override": "Only surface if the news changes a saved purchase."
                },
            },
        )
    finally:
        main.app.dependency_overrides.clear()

    assert created.status_code == 200
    watch = created.json()["watch_item"]
    assert watch["watch_kind"] == "hybrid"
    assert watch["priority"] == "quiet_by_default"
    assert watch["personal_accounts"] == ["Amazon if integration becomes feasible"]
    assert watch["connected_data_sources"] == ["manual_shopping_interests"]
    assert watch["missing_sources"]
    assert "Prefer silence over filler" in watch["prompt_config"]["generated_prompt"]


def test_registry_endpoints_separate_sources_from_accounts():
    client = TestClient(main.app)
    sources = client.get("/api/source-registry")
    accounts = client.get("/api/personal-accounts")

    assert sources.status_code == 200
    assert accounts.status_code == 200
    source_ids = {item["source_id"] for item in sources.json()["sources"]}
    assert {"manual_portfolio_csv", "CoinGecko", "GitHub API", "Open-Meteo"} <= source_ids
    finance_accounts = accounts.json()["personal_accounts"]["finance_accounts"]
    assert {item["name"] for item in finance_accounts} == {
        "Fidelity",
        "SoFi",
        "Tastytrade",
    }
