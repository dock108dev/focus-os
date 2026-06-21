from decimal import Decimal

import pytest

from app.structured_sources import (
    crypto_attention_items,
    market_attention_items,
    refresh_crypto_prices,
    score_golf_day,
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


def test_crypto_attention_flags_large_bitcoin_move():
    rows = [Row(change_24h_pct=Decimal("-8.2"))]

    items = crypto_attention_items(rows)

    assert items[0]["title"] == "Bitcoin is down 8.2% over 24 hours"
    assert items[0]["source"] == "crypto"
    assert items[0]["detail_id"] == "crypto:BTC:24h"
    assert items[0]["category"] == "opportunity"
    assert items[0]["importance_score"] == 84
    assert items[0]["expiration_hours"] == 72


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
