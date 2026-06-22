from decimal import Decimal
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import MarketPrice, WatchItem
from app.structured_sources import (
    crypto_attention_items,
    finance_symbol_preferences,
    latest_market_prices,
    market_attention_items,
    refresh_crypto_prices,
    score_golf_day,
    tracked_market_symbols,
    weather_attention_items,
)


class Row:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def test_market_attention_flags_pullback_from_recent_high():
    rows = [
        Row(
            symbol="MSFT",
            price=Decimal("95"),
            five_day_high=Decimal("105"),
            five_day_change_pct=Decimal("-6"),
        )
    ]

    items = market_attention_items(rows)

    assert items[0]["title"] == "MSFT is down 9.5% from its five-day high"
    assert items[0]["source"] == "market"
    assert items[0]["classification"] == "opportunity"


def test_market_attention_uses_short_symbol_note_for_pullback():
    rows = [
        Row(
            symbol="USO",
            price=Decimal("88"),
            five_day_high=Decimal("100"),
            five_day_change_pct=Decimal("-7"),
        )
    ]
    preferences = {
        "USO": {
            "position": "short",
            "note": "Short position from the trading account.",
            "source_watch_id": "watch:investing-ideas-and-market-pullbacks",
        }
    }

    items = market_attention_items(rows, preferences)

    assert items[0]["title"] == "USO is moving in favor of your short thesis"
    assert "buy" not in items[0]["why_now"].lower()
    assert "Short position" in items[0]["why_now"]
    assert items[0]["source_watch_ids"] == [
        "watch:investing-ideas-and-market-pullbacks"
    ]


def test_watchlist_symbol_notes_feed_market_tracking():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    with TestingSessionLocal() as db:
        db.add(
            WatchItem(
                title="Custom stock watch",
                original_text="Custom stock watch",
                watch_kind="hybrid",
                priority="watch_only",
                watch_for=["SMCI"],
                personal_context={
                    "why_i_care": "Track saved stock ideas.",
                    "accounts": ["Fidelity"],
                    "interests": ["SMCI"],
                    "owned_assets": [],
                    "ignored_accounts": [],
                    "manual_facts": {
                        "tracked_symbols": ["SMCI"],
                        "symbol_notes": {"SMCI": "Buy only after a meaningful pullback."},
                    },
                },
                source_config={},
                evaluation_rules={},
            )
        )
        db.commit()

        preferences = finance_symbol_preferences(db)
        symbols = tracked_market_symbols(db)

    assert preferences["SMCI"]["position"] == "accumulate"
    assert "SMCI" in symbols


def test_latest_market_prices_ignores_untracked_stale_symbols():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    with TestingSessionLocal() as db:
        db.add_all(
            [
                MarketPrice(
                    symbol="MSFT",
                    price=Decimal("95"),
                    previous_close=Decimal("100"),
                    five_day_high=Decimal("105"),
                    five_day_change_pct=Decimal("-6"),
                    as_of=date.today(),
                ),
                MarketPrice(
                    symbol="UNH",
                    price=Decimal("300"),
                    previous_close=Decimal("310"),
                    five_day_high=Decimal("315"),
                    five_day_change_pct=Decimal("-4"),
                    as_of=date.today(),
                ),
            ]
        )
        db.commit()

        symbols = {row.symbol for row in latest_market_prices(db)}

    assert "UNH" in symbols
    assert "MSFT" not in symbols


def test_crypto_attention_flags_large_bitcoin_move():
    rows = [Row(change_24h_pct=Decimal("-8.2"))]

    items = crypto_attention_items(rows)

    assert items[0]["title"] == "Bitcoin is down 8.2% over 24 hours"
    assert items[0]["source"] == "crypto"
    assert items[0]["detail_id"] == "crypto:BTC:24h"
    assert items[0]["category"] == "opportunity"
    assert items[0]["importance_score"] == 84
    assert items[0]["expiration_hours"] == 72


def test_crypto_attention_uses_bitcoin_symbol_note():
    rows = [Row(symbol="BTC", change_24h_pct=Decimal("-8.2"))]

    items = crypto_attention_items(
        rows,
        {
            "BTC": {
                "position": "accumulate",
                "note": "Accumulate only when the pullback improves cost basis.",
                "source_watch_id": "watch:bitcoin-accumulation-posture",
            }
        },
    )

    assert items[0]["title"] == "Bitcoin is down 8.2% over 24 hours"
    assert items[0]["why_now"].startswith("Accumulate only")
    assert items[0]["source_watch_ids"] == ["watch:bitcoin-accumulation-posture"]


def test_weather_attention_promotes_good_golf_day():
    rows = [
        Row(
            title="Thursday is the best golf day this week",
            reason="Forecast is 72F with 5% rain risk and 8 mph wind.",
            action="",
            score=88,
            activity="Golf",
        )
    ]

    assert weather_attention_items(rows)[0]["source"] == "weather"
    assert weather_attention_items(rows)[0]["classification"] == "opportunity"
    assert score_golf_day(72, 5, 8) > score_golf_day(95, 60, 22)


def test_crypto_refresh_propagates_database_commit_failures(monkeypatch):
    class FailingCommitSession:
        rolled_back = False

        def execute(self, _statement):
            return None

        def add(self, _row):
            return None

        def commit(self):
            raise RuntimeError("database unavailable")

        def rollback(self):
            self.rolled_back = True

    db = FailingCommitSession()
    monkeypatch.setattr(
        "app.structured_sources.load_json",
        lambda _url: {
            "bitcoin": {"usd": 62000, "usd_24h_change": 1.5, "last_updated_at": 1}
        },
    )

    with pytest.raises(RuntimeError, match="database unavailable"):
        refresh_crypto_prices(db)

    assert db.rolled_back
