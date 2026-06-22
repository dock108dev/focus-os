from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.database import Base
from app.models import (
    CryptoPrice,
    Holding,
    JobRun,
    MarketPrice,
    SourceStatus,
    Topic,
    TopicBriefing,
    WatchEvaluation,
    WatchItem,
    WeatherRecommendation,
)
from app.recommendations import recommendation_detail
from app.structured_sources import (
    fetch_yahoo_symbol,
    github_api,
    github_attention_items,
    refresh_crypto_prices,
    refresh_github_repo_health,
    refresh_market_prices,
    refresh_weather_recommendations,
    structured_topic_briefings,
)
from app.topic_engine import generate_ai_payload, parse_ai_payload, provider_error_message
from app.seeding import (
    purge_legacy_sample_portfolio,
    seed_if_empty,
    seed_snapshots_if_empty,
)
from app.topic_engine import run_morning_briefing
from app.watchlist import (
    evaluate_watch_item,
    normalize_watch_kind,
    normalize_watch_priority,
    quiet_summary_for_watch,
    update_watch_item,
    validation_warnings_for,
    watch_domain,
)


def in_memory_sessionmaker():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(
        autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
    )


def override_app_db(testing_session) -> Iterator[Session]:
    db = testing_session()
    try:
        yield db
    finally:
        db.close()


def add_recommendation_fixture(db: Session) -> dict[str, int]:
    today = date.today()
    db.add_all(
        [
            Holding(
                source="Fidelity",
                account="Brokerage",
                symbol="CASH",
                name="Cash",
                asset_class="Cash",
                quantity=8000,
                price=1,
                market_value=8000,
                cost_basis=8000,
                as_of=today,
            ),
            Holding(
                source="Fidelity",
                account="Brokerage",
                symbol="MSFT",
                name="Microsoft",
                asset_class="Technology",
                quantity=10,
                price=700,
                market_value=7000,
                cost_basis=8000,
                as_of=today,
            ),
        ]
    )
    db.add(
        MarketPrice(
            symbol="MSFT",
            price=Decimal("95"),
            previous_close=Decimal("100"),
            five_day_high=Decimal("105"),
            five_day_change_pct=Decimal("-6"),
            as_of=today,
        )
    )
    db.add(
        CryptoPrice(
            asset_id="bitcoin",
            symbol="BTC",
            price=Decimal("62000"),
            change_24h_pct=Decimal("-8.2"),
            as_of=today,
        )
    )
    db.add(
        WeatherRecommendation(
            activity="Golf",
            location="Basking Ridge, NJ",
            recommended_date=today + timedelta(days=2),
            title="Wednesday is likely your best golf opportunity this week",
            reason="Forecast is 72F with 5% rain risk and 8 mph wind.",
            action="",
            score=88,
            as_of=today,
            raw={"candidates": [{"date": today.isoformat(), "score": 88}, {"score": 55}]},
        )
    )
    topic = Topic(
        name="AI",
        priority=8,
        source_type="unstructured",
        category="Technology",
        refresh_frequency="daily",
        prompt="Summarize AI tooling.",
    )
    db.add(topic)
    db.flush()
    briefing = TopicBriefing(
        topic_id=topic.id,
        topic=topic,
        as_of=today,
        title="Tooling update crossed the workflow threshold",
        summary="A developer tool release changed the practical workflow.",
        bullets=["The release removes a repeated manual step."],
        action="Review whether to switch workflows.",
        source_type="unstructured",
        priority=8,
        generated_by="openai-web-search",
    )
    db.add(briefing)
    watch = WatchItem(
        title="Outdoor concert",
        original_text="Outdoor concert tomorrow\nWatch weather and parking.",
        event_date=today + timedelta(days=1),
        watch_for=["weather", "parking"],
        surface_when=["event is near"],
        personal_context={"accounts": [], "interests": ["weather"]},
        source_config={"connected_sources": ["weather"], "manual_inputs": []},
        evaluation_rules={"surface_when": ["event is near"], "suppress_when": []},
        prompt_config={},
    )
    db.add(watch)
    db.flush()
    db.add(
        WatchEvaluation(
            watch_item_id=watch.id,
            as_of=today,
            title="Outdoor concert is tomorrow",
            summary="Planning details are close enough to matter.",
            category="action",
            importance_score=84,
            actionability_score=74,
            should_surface=True,
            trigger_reason="The watched event is one day away.",
        )
    )
    db.commit()
    return {"topic_id": briefing.id, "watch_id": watch.id}


def test_recommendation_detail_routes_cover_all_detail_types():
    testing_session = in_memory_sessionmaker()
    with testing_session() as db:
        ids = add_recommendation_fixture(db)

        cash = recommendation_detail(db, "finance:cash")
        technology = recommendation_detail(db, "finance:technology")
        position = recommendation_detail(db, "finance:position:MSFT:concentration")
        missing_position = recommendation_detail(db, "finance:position:ZZZ:concentration")
        market_pullback = recommendation_detail(db, "market:MSFT:pullback")
        market_move = recommendation_detail(db, "market:MSFT:move")
        crypto = recommendation_detail(db, "crypto:BTC:24h")
        weather = recommendation_detail(db, "weather:golf")
        topic = recommendation_detail(db, f"topic:{ids['topic_id']}")
        watch = recommendation_detail(db, f"watch:{ids['watch_id']}")
        missing_topic = recommendation_detail(db, "topic:not-an-id")
        unknown = recommendation_detail(db, "unknown:thing")

    assert cash["title"].startswith("$")
    assert technology["raw_data"]["technology_percent"] > 0
    assert position["raw_data"]["symbol"] == "MSFT"
    assert missing_position["title"] == "Recommendation not found"
    assert market_pullback["raw_data"]["pullback_from_five_day_high"] > 0
    assert "five trading days" in market_move["title"]
    assert crypto["raw_data"]["change_24h_pct"] == -8.2
    assert weather["suppressed_signals"][0]["items"]
    assert topic["ai_processing"]["parsed_title"]
    assert watch["raw_data"]["watch_item"]["title"] == "Outdoor concert"
    assert missing_topic["title"] == "Recommendation not found"
    assert unknown["title"] == "Recommendation not found"


def test_yahoo_fetch_and_market_refresh_status_paths(monkeypatch):
    testing_session = in_memory_sessionmaker()

    yahoo_payload = {
        "chart": {
            "result": [
                {
                    "meta": {"regularMarketPrice": 95, "previousClose": 100},
                    "indicators": {"quote": [{"close": [105, 100, 95]}]},
                }
            ]
        }
    }
    monkeypatch.setattr("app.structured_sources.load_json", lambda _url, headers=None: yahoo_payload)
    row = fetch_yahoo_symbol("msft")
    assert row.symbol == "MSFT"
    assert row.five_day_high == Decimal("105")

    def fake_fetch(symbol: str):
        if symbol == "BAD":
            raise ValueError("bad symbol")
        return row

    with testing_session() as db:
        monkeypatch.setattr("app.structured_sources.tracked_market_symbols", lambda _db: ["MSFT", "BAD"])
        monkeypatch.setattr("app.structured_sources.fetch_yahoo_symbol", fake_fetch)
        rows = refresh_market_prices(db)
        status = db.scalar(select(SourceStatus).where(SourceStatus.name == "Yahoo Finance"))

    assert len(rows) == 1
    assert status.status == "partial"
    assert "BAD" in status.details["errors"][0]

    with testing_session() as db:
        monkeypatch.setattr("app.structured_sources.tracked_market_symbols", lambda _db: [])
        assert refresh_market_prices(db) == []
        skipped = db.scalar(select(SourceStatus).where(SourceStatus.name == "Yahoo Finance"))
    assert skipped.status == "skipped"


def test_crypto_and_weather_refresh_success_and_error_paths(monkeypatch):
    testing_session = in_memory_sessionmaker()
    with testing_session() as db:
        monkeypatch.setattr(
            "app.structured_sources.load_json",
            lambda _url, headers=None: {
                "bitcoin": {"usd": 62000, "usd_24h_change": -8.2, "last_updated_at": 1}
            },
        )
        crypto = refresh_crypto_prices(db)
        status = db.scalar(select(SourceStatus).where(SourceStatus.name == "CoinGecko"))
    assert crypto[0].symbol == "BTC"
    assert status.status == "ok"

    with testing_session() as db:
        monkeypatch.setattr("app.structured_sources.load_json", lambda _url, headers=None: {})
        assert refresh_crypto_prices(db) == []
        status = db.scalar(select(SourceStatus).where(SourceStatus.name == "CoinGecko"))
    assert status.status == "error"

    weather_payload = {
        "daily": {
            "time": [
                "2026-06-22",
                "2026-06-23",
                "2026-06-26",
            ],
            "temperature_2m_max": [72, 74, 80],
            "precipitation_probability_max": [10, 5, 0],
            "wind_speed_10m_max": [8, 6, 5],
        }
    }
    with testing_session() as db:
        monkeypatch.setattr("app.structured_sources.load_json", lambda _url, headers=None: weather_payload)
        weather = refresh_weather_recommendations(db)
        status = db.scalar(select(SourceStatus).where(SourceStatus.name == "Open-Meteo"))
    assert weather[0].score > 0
    assert status.status == "ok"

    with testing_session() as db:
        monkeypatch.setattr("app.structured_sources.load_json", lambda _url, headers=None: {})
        assert refresh_weather_recommendations(db) == []
        status = db.scalar(select(SourceStatus).where(SourceStatus.name == "Open-Meteo"))
    assert status.status == "error"


def test_github_refresh_attention_and_api_auth(monkeypatch):
    testing_session = in_memory_sessionmaker()
    seen_headers = {}

    def fake_load_json(url, headers=None):
        seen_headers.update(headers or {})
        return {"ok": url}

    monkeypatch.setenv("GITHUB_TOKEN", "secret-token")
    monkeypatch.setattr("app.structured_sources.load_json", fake_load_json)
    assert github_api("/rate_limit")["ok"].endswith("/rate_limit")
    assert seen_headers["Authorization"] == "Bearer secret-token"

    now = datetime.now(timezone.utc)

    def fake_github(path: str):
        if path.startswith("/users/"):
            return [
                {
                    "name": "focus-os",
                    "archived": False,
                    "pushed_at": (now - timedelta(days=20)).isoformat().replace("+00:00", "Z"),
                    "html_url": "https://github.example/focus-os",
                },
                {"name": "old", "archived": True},
            ]
        if path.endswith("/pulls?state=open&per_page=10"):
            return [
                {
                    "title": "Bump dependency",
                    "html_url": "https://github.example/pr",
                    "user": {"login": "dependabot[bot]"},
                }
            ]
        if path.endswith("/actions/runs?status=failure&per_page=5"):
            return {
                "workflow_runs": [
                    {
                        "name": "CI",
                        "display_title": "CI failed",
                        "conclusion": "failure",
                        "status": "completed",
                        "updated_at": now.isoformat(),
                        "html_url": "https://github.example/run",
                    }
                ]
            }
        raise AssertionError(path)

    with testing_session() as db:
        monkeypatch.setattr("app.structured_sources.github_api", fake_github)
        result = refresh_github_repo_health(db)
        attention = github_attention_items(db)

    assert result["status"] == "ok"
    assert result["archived_repos_ignored"] == 1
    assert {item["title"] for item in attention} >= {
        "focus-os has an automated PR",
        "focus-os has a failing workflow",
        "focus-os has been quiet for about 2 weeks",
    }

    with testing_session() as db:
        monkeypatch.setattr("app.structured_sources.github_api", lambda _path: (_ for _ in ()).throw(ValueError("down")))
        error = refresh_github_repo_health(db)
    assert error["status"] == "error"


def test_structured_topic_briefings_for_crypto_and_weather():
    testing_session = in_memory_sessionmaker()
    today = date.today()
    with testing_session() as db:
        db.add_all(
            [
                Topic(name="Bitcoin", priority=9, source_type="structured", category="Crypto", refresh_frequency="daily", prompt="BTC"),
                Topic(name="Golf", priority=8, source_type="structured", category="Weather", refresh_frequency="daily", prompt="Golf"),
            ]
        )
        db.add(CryptoPrice(asset_id="bitcoin", symbol="BTC", price=Decimal("62000"), change_24h_pct=Decimal("-8.2"), as_of=today))
        db.add(
            WeatherRecommendation(
                activity="Golf",
                location="Basking Ridge, NJ",
                recommended_date=today,
                title="Today is likely your best golf opportunity this week",
                reason="Good golf weather.",
                score=80,
                as_of=today,
                raw={},
            )
        )
        db.commit()
        briefings = structured_topic_briefings(db)

    assert {briefing.generated_by for briefing in briefings} == {"CoinGecko", "Open-Meteo"}


def test_main_endpoint_error_and_internal_routes(monkeypatch):
    testing_session = in_memory_sessionmaker()

    def override_db() -> Iterator[Session]:
        yield from override_app_db(testing_session)

    class NoopThread:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            pass

    main.app.dependency_overrides[main.get_db] = override_db
    monkeypatch.setattr(main, "Thread", NoopThread)
    client = TestClient(main.app)
    try:
        future = client.get(f"/api/briefing?date={date.today() + timedelta(days=1)}")
        past = client.get(f"/api/briefing?date={date.today() - timedelta(days=3)}")
        mock_archive = client.post("/api/internal/briefing-archive/mock", json={"days": 2, "replace": True})
        watches_bad = client.post("/api/watch-items", json={})
        missing_patch = client.patch("/api/watch-items/999", json={"status": "active"})
        missing_complete = client.post("/api/watch-items/999/complete")
        missing_archive = client.post("/api/watch-items/999/archive")
        missing_delete = client.delete("/api/watch-items/999")
        topics = client.get("/api/topics")
        source_registry = client.get("/api/source-registry")
        accounts = client.get("/api/personal-accounts")
        recommendation = client.get("/api/recommendations/unknown:item")
        queued = client.post("/api/jobs/morning-briefing")
        missing_job = client.get("/api/jobs/morning-briefing/999")
        status = client.get("/api/internal/source-status")
        review_future = client.get(f"/api/internal/daily-review?date={date.today() + timedelta(days=1)}")
        review_past = client.get(f"/api/internal/daily-review?date={date.today() - timedelta(days=5)}")
        bad_import = client.post(
            "/api/import/holdings?source=Manual&replace=true",
            files={"file": ("holdings.csv", b"symbol,quantity\nMSFT,not-a-number\n", "text/csv")},
        )
    finally:
        main.app.dependency_overrides.clear()

    assert future.status_code == 400
    assert past.status_code == 404
    assert mock_archive.status_code == 200
    assert watches_bad.status_code == 400
    assert missing_patch.status_code == 404
    assert missing_complete.status_code == 404
    assert missing_archive.status_code == 404
    assert missing_delete.status_code == 404
    assert topics.status_code == 200
    assert source_registry.json()["global_guardrails"]
    assert accounts.json()["personal_accounts"]
    assert recommendation.json()["title"] == "Recommendation not found"
    assert queued.status_code == 200
    assert missing_job.json()["status"] == "missing"
    assert "registry" in status.json()
    assert review_future.status_code == 400
    assert review_past.status_code == 404
    assert bad_import.status_code == 400


def test_job_helpers_snapshot_changes_and_background_paths(monkeypatch, caplog):
    testing_session = in_memory_sessionmaker()
    with testing_session() as db:
        job = main.create_job_run(db, "morning-briefing")
        main.update_job_run(db, job.id, "running", "Running")
        with pytest.raises(main.JobRunMissingError):
            main.update_job_run(db, 999, "missing", "Missing")
        db.add_all(
            [
                main.PortfolioSnapshot(as_of=date.today() - timedelta(days=35), total_value=90, cash_available=10),
                main.PortfolioSnapshot(as_of=date.today() - timedelta(days=1), total_value=100, cash_available=12),
            ]
        )
        db.commit()
        summary = main.apply_snapshot_changes(db, {"current_value": 120, "cash_available": 20})

    assert summary["daily_change"] == 20
    assert summary["monthly_change"] == 30

    class SessionFactory:
        def __call__(self):
            return testing_session()

    monkeypatch.setattr(main, "SessionLocal", SessionFactory())
    monkeypatch.setattr(main, "refresh_structured_sources", lambda _db: {"market_prices": 1})
    monkeypatch.setattr(main, "run_morning_briefing", lambda _db: [object(), object()])
    monkeypatch.setattr(main, "evaluate_active_watch_items", lambda _db: [object()])
    with testing_session() as db:
        job = main.create_job_run(db, "morning-briefing")
    main.run_morning_job_background(job.id)
    with testing_session() as db:
        assert db.get(JobRun, job.id).status == "succeeded"

    monkeypatch.setattr(main, "refresh_structured_sources", lambda _db: (_ for _ in ()).throw(RuntimeError("boom")))
    with testing_session() as db:
        job = main.create_job_run(db, "morning-briefing")
    main.run_morning_job_background(job.id)
    with testing_session() as db:
        assert db.get(JobRun, job.id).status == "failed"

    main.run_morning_job_background(999)
    assert "morning_briefing_job_status_missing" in caplog.text


def test_topic_engine_provider_and_parse_branches(monkeypatch):
    topic = Topic(name="AI", priority=6, source_type="unstructured", category="Tech", refresh_frequency="daily", prompt="AI")

    plain = parse_ai_payload("plain text without json", topic)
    invalid = parse_ai_payload("{not json}", topic)
    assert plain["title"] == "AI: attention check"
    assert invalid["title"] == "AI: attention check"

    monkeypatch.setenv("AI_PROVIDER", "fallback")
    assert generate_ai_payload(topic) is None
    monkeypatch.setenv("AI_PROVIDER", "nonsense")
    with pytest.raises(Exception, match="Unsupported AI_PROVIDER"):
        generate_ai_payload(topic)

    assert "timed out" in provider_error_message(__import__("subprocess").TimeoutExpired("cmd", 3))
    assert "not found" in provider_error_message(FileNotFoundError("missing", "codex"))


def test_schema_migration_adds_missing_watch_columns(monkeypatch):
    legacy_engine = create_engine("sqlite:///:memory:")
    with legacy_engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE watch_items (id INTEGER PRIMARY KEY, title VARCHAR(240))"
        )

    monkeypatch.setattr(main, "engine", legacy_engine)

    main.ensure_watch_item_schema()

    with legacy_engine.connect() as connection:
        columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(watch_items)")}

    assert {
        "watch_kind",
        "priority",
        "enabled",
        "personal_state",
        "external_state",
        "personal_context",
        "source_config",
        "evaluation_rules",
        "prompt_config",
    } <= columns


def test_seeding_updates_existing_watches_and_creates_snapshots():
    testing_session = in_memory_sessionmaker()
    today = date.today()
    with testing_session() as db:
        assert purge_legacy_sample_portfolio(db) == 0
        db.add(
            Holding(
                source="Manual",
                account="Brokerage",
                symbol="MSFT",
                name="Microsoft",
                asset_class="Technology",
                quantity=1,
                price=100,
                market_value=100,
                cost_basis=100,
                as_of=today,
            )
        )
        db.add(
            WatchItem(
                title="Yankees",
                original_text="legacy",
                status="active",
                enabled=True,
                watch_for=[],
            )
        )
        db.add(
            WatchItem(
                title="Bitcoin accumulation posture",
                original_text="stale",
                watch_kind="personal_tracker",
                priority="quiet_by_default",
                check_frequency="weekly",
                watch_for=["old"],
                surface_when=["old"],
                personal_context={},
                source_config={},
                evaluation_rules={},
                prompt_config={"daily_prompt_override": "surface meaningful BTC move and suppress noise"},
            )
        )
        db.add(
            WatchItem(
                title="Custom weather watch",
                original_text="Custom weather watch\nWatch weather.",
                watch_kind="personal_tracker",
                watch_for=["weather"],
                surface_when=["weather changes"],
                personal_state={},
                external_state={},
            )
        )
        db.commit()

        seed_snapshots_if_empty(db, Decimal("100"), Decimal("10"))
        seed_if_empty(db)
        legacy = db.scalar(select(WatchItem).where(WatchItem.title == "Yankees"))
        bitcoin = db.scalar(select(WatchItem).where(WatchItem.title == "Bitcoin accumulation posture"))
        custom = db.scalar(select(WatchItem).where(WatchItem.title == "Custom weather watch"))
        snapshots = list(db.scalars(select(main.PortfolioSnapshot)).all())

    assert legacy.status == "archived"
    assert legacy.enabled is False
    assert bitcoin.watch_kind == "hybrid"
    assert bitcoin.check_frequency == "daily"
    assert bitcoin.personal_context["manual_facts"]["btc_cost_basis"] == 75000
    assert custom.watch_kind == "external_monitor"
    assert custom.external_state["freshness_window"] == "same-day"
    assert len(snapshots) == 3


def test_run_morning_briefing_records_fallback_error_and_ok_statuses(monkeypatch):
    def add_topic(db: Session):
        db.add(
            Topic(
                name="AI",
                priority=8,
                source_type="unstructured",
                category="Technology",
                refresh_frequency="daily",
                prompt="Summarize AI.",
            )
        )
        db.commit()

    monkeypatch.setattr("app.structured_sources.structured_topic_briefings", lambda _db: [])

    with in_memory_sessionmaker()() as db:
        add_topic(db)
        monkeypatch.setenv("AI_PROVIDER", "fallback")
        run_morning_briefing(db)
        status = db.scalar(select(SourceStatus).where(SourceStatus.name == "AI Topic Briefings"))
        assert status.status == "skipped"

    with in_memory_sessionmaker()() as db:
        add_topic(db)
        monkeypatch.setenv("AI_PROVIDER", "codex_cli")

        def failing_payload(_topic):
            raise FileNotFoundError("missing", "codex")

        monkeypatch.setattr("app.topic_engine.generate_ai_payload", failing_payload)
        run_morning_briefing(db)
        status = db.scalar(select(SourceStatus).where(SourceStatus.name == "AI Topic Briefings"))
        assert status.status == "error"

    with in_memory_sessionmaker()() as db:
        add_topic(db)
        monkeypatch.setenv("AI_PROVIDER", "codex_cli")
        monkeypatch.setattr(
            "app.topic_engine.generate_ai_payload",
            lambda topic: {
                "title": "AI release changed workflow",
                "summary": "A tool release changed practical development workflow.",
                "bullets": ["Workflow impact"],
                "action": "",
                "priority": topic.priority,
                "generated_by": "codex-cli",
            },
        )
        run_morning_briefing(db)
        status = db.scalar(select(SourceStatus).where(SourceStatus.name == "AI Topic Briefings"))
        assert status.status == "ok"


def test_watchlist_branch_helpers_and_update_paths():
    today = date(2026, 6, 21)
    with pytest.raises(ValueError, match="Watch kind"):
        normalize_watch_kind("mystery")
    with pytest.raises(ValueError, match="Watch priority"):
        normalize_watch_priority("urgent")

    assert watch_domain("Rutgers kickoff", ["results"]) == "Rutgers"
    assert watch_domain("Bogey medication", ["medication"]) == "Dog"
    assert watch_domain("Golf equipment sale", ["equipment"]) == "Golf Equipment"
    assert quiet_summary_for_watch(
        WatchItem(title="Future thing", original_text="", event_date=today + timedelta(days=3))
    ).endswith("No planning trigger has opened yet.")
    assert quiet_summary_for_watch(
        WatchItem(title="Past thing", original_text="", event_date=today - timedelta(days=1))
    ) == "Event has passed with no recap item needed."

    row = WatchItem(
        title="Conference",
        original_text="Conference",
        event_date=today + timedelta(days=10),
        watch_for=["timing"],
        surface_when=["timing changes"],
        source_config={"manual_inputs": ["agenda"], "missing_sources": ["calendar"]},
        evaluation_rules={"suppress_when": []},
        prompt_config={"daily_prompt_override": "surface only"},
    )
    warnings = validation_warnings_for(row)
    assert "No suppression rules configured" in warnings
    assert "Prompt override lacks a suppress rule" in warnings

    testing_session = in_memory_sessionmaker()
    with testing_session() as db:
        db.add(row)
        db.commit()
        updated = update_watch_item(
            db,
            row,
            title="Conference tomorrow",
            original_text="Conference tomorrow\nWatch weather and timing.",
            event_date=today + timedelta(days=1),
            check_frequency="weekly",
            watch_kind="external",
            priority="primary",
            enabled=False,
            watch_for=["weather", "timing"],
            evaluation_rules={"surface_when": ["event is near"], "suppress_when": ["routine updates"]},
            prompt_config={"daily_prompt_override": "surface event changes and suppress routine updates"},
            status="completed",
            today=today,
        )
        assert updated.watch_kind == "external_monitor"
        assert updated.priority == "primary_allowed"
        assert updated.status == "completed"
        assert updated.personal_state["next_relevant_date"]
        with pytest.raises(ValueError, match="Watch status"):
            update_watch_item(db, row, status="lost")


def test_evaluate_watch_item_event_timing_branches():
    today = date(2026, 6, 21)
    yesterday_summary = evaluate_watch_item(
        WatchItem(
            title="Yankees game",
            original_text="Yankees game",
            event_date=today - timedelta(days=1),
            watch_for=["summary"],
        ),
        today=today,
    )
    past_no_summary = evaluate_watch_item(
        WatchItem(
            title="Old event",
            original_text="Old event",
            event_date=today - timedelta(days=3),
            watch_for=["timing"],
        ),
        today=today,
    )
    today_item = evaluate_watch_item(
        WatchItem(title="Concert", original_text="Concert", event_date=today, watch_for=["parking"]),
        today=today,
    )
    tomorrow_item = evaluate_watch_item(
        WatchItem(title="Flight", original_text="Flight", event_date=today + timedelta(days=1), watch_for=["airport timing"]),
        today=today,
    )
    tech_week = evaluate_watch_item(
        WatchItem(title="WWDC", original_text="WWDC", event_date=today + timedelta(days=7), watch_for=["developer tooling"]),
        today=today,
    )

    assert yesterday_summary["should_surface"] is True
    assert past_no_summary["should_surface"] is False
    assert today_item["category"] == "action"
    assert tomorrow_item["trigger_reason"] == "The watched event is one day away."
    assert tech_week["category"] == "awareness"
