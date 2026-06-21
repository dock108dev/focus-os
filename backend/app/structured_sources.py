from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request
import urllib.error
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Iterable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .attention import enrich_attention_item, pct
from .models import (
    CryptoPrice,
    Holding,
    MarketPrice,
    Topic,
    TopicBriefing,
    WeatherRecommendation,
)
from .personalization import MIKE_PROFILE
from .source_status import record_source_status


HTTP_TIMEOUT = 15
logger = logging.getLogger(__name__)
SOURCE_REFRESH_EXCEPTIONS = (
    urllib.error.URLError,
    TimeoutError,
    json.JSONDecodeError,
    KeyError,
    IndexError,
    ValueError,
    TypeError,
    InvalidOperation,
)


def load_json(url: str, headers: dict[str, str] | None = None) -> dict:
    request = urllib.request.Request(
        url, headers=headers or {"User-Agent": "FocusOS/0.1"}
    )
    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
        return json.load(response)


def latest_market_prices(db: Session) -> list[MarketPrice]:
    rows: list[MarketPrice] = []
    symbols = db.scalars(select(MarketPrice.symbol).distinct()).all()
    for symbol in symbols:
        row = db.scalar(
            select(MarketPrice)
            .where(MarketPrice.symbol == symbol)
            .order_by(MarketPrice.as_of.desc(), MarketPrice.created_at.desc())
            .limit(1)
        )
        if row:
            rows.append(row)
    return rows


def latest_crypto_prices(db: Session) -> list[CryptoPrice]:
    rows: list[CryptoPrice] = []
    asset_ids = db.scalars(select(CryptoPrice.asset_id).distinct()).all()
    for asset_id in asset_ids:
        row = db.scalar(
            select(CryptoPrice)
            .where(CryptoPrice.asset_id == asset_id)
            .order_by(CryptoPrice.as_of.desc(), CryptoPrice.created_at.desc())
            .limit(1)
        )
        if row:
            rows.append(row)
    return rows


def latest_weather_recommendations(db: Session) -> list[WeatherRecommendation]:
    rows: list[WeatherRecommendation] = []
    activities = db.scalars(select(WeatherRecommendation.activity).distinct()).all()
    for activity in activities:
        row = db.scalar(
            select(WeatherRecommendation)
            .where(WeatherRecommendation.activity == activity)
            .order_by(
                WeatherRecommendation.as_of.desc(),
                WeatherRecommendation.created_at.desc(),
            )
            .limit(1)
        )
        if row:
            rows.append(row)
    return rows


def tracked_market_symbols(db: Session) -> list[str]:
    symbols = {
        row.symbol.upper()
        for row in db.scalars(select(Holding)).all()
        if row.symbol
        and row.symbol.upper() not in {"CASH", "SPAXX", "FDRXX", "CORE", "USD", "BTC"}
    }
    return sorted(symbols)


def fetch_yahoo_symbol(symbol: str) -> MarketPrice:
    encoded = urllib.parse.quote(symbol)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?range=5d&interval=1d"
    payload = load_json(url)
    result = payload["chart"]["result"][0]
    meta = result["meta"]
    closes = [
        Decimal(str(value))
        for value in result["indicators"]["quote"][0].get("close", [])
        if value is not None
    ]
    price = Decimal(str(meta.get("regularMarketPrice") or closes[-1]))
    previous_close = Decimal(
        str(meta.get("previousClose") or (closes[-2] if len(closes) > 1 else price))
    )
    five_day_high = max(closes) if closes else price
    first_close = closes[0] if closes else price
    five_day_change_pct = (
        ((price - first_close) / first_close * 100) if first_close else Decimal("0")
    )

    return MarketPrice(
        symbol=symbol.upper(),
        price=price,
        previous_close=previous_close,
        five_day_high=five_day_high,
        five_day_change_pct=five_day_change_pct,
        as_of=date.today(),
    )


def refresh_market_prices(db: Session) -> list[MarketPrice]:
    symbols = tracked_market_symbols(db)
    if not symbols:
        record_source_status(
            db, "Yahoo Finance", "skipped", "No tracked market symbols."
        )
        return []

    rows = []
    errors: list[str] = []
    for symbol in symbols:
        try:
            rows.append(fetch_yahoo_symbol(symbol))
        except SOURCE_REFRESH_EXCEPTIONS as exc:
            logger.warning(
                "market_symbol_refresh_failed", exc_info=True, extra={"symbol": symbol}
            )
            errors.append(f"{symbol}: {type(exc).__name__}: {exc}")

    today = date.today()
    for row in rows:
        db.execute(
            delete(MarketPrice).where(
                MarketPrice.symbol == row.symbol, MarketPrice.as_of == today
            )
        )
    db.add_all(rows)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    status = "ok" if rows and not errors else "partial" if rows else "error"
    message = f"Fetched {len(rows)} of {len(symbols)} market symbols."
    record_source_status(
        db, "Yahoo Finance", status, message, {"errors": errors[:5], "symbols": symbols}
    )
    return rows


def refresh_crypto_prices(db: Session) -> list[CryptoPrice]:
    url = (
        "https://api.coingecko.com/api/v3/simple/price"
        "?ids=bitcoin&vs_currencies=usd&include_24hr_change=true&include_last_updated_at=true"
    )
    try:
        payload = load_json(url)
        bitcoin = payload["bitcoin"]
        row = CryptoPrice(
            asset_id="bitcoin",
            symbol="BTC",
            price=Decimal(str(bitcoin["usd"])),
            change_24h_pct=Decimal(str(bitcoin.get("usd_24h_change") or 0)),
            as_of=date.today(),
        )
    except SOURCE_REFRESH_EXCEPTIONS as exc:
        logger.warning("crypto_price_refresh_failed", exc_info=True)
        record_source_status(
            db,
            "CoinGecko",
            "error",
            "Bitcoin price refresh failed.",
            {"error": str(exc)},
        )
        return []

    db.execute(
        delete(CryptoPrice).where(
            CryptoPrice.asset_id == "bitcoin", CryptoPrice.as_of == date.today()
        )
    )
    db.add(row)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    record_source_status(
        db,
        "CoinGecko",
        "ok",
        "Fetched Bitcoin price.",
        {"last_updated_at": bitcoin.get("last_updated_at")},
    )
    return [row]


def score_golf_day(
    max_temp: float, precipitation_probability: float, wind_speed: float
) -> int:
    temp_score = max(0, 40 - abs(max_temp - 72))
    rain_score = max(0, 35 - precipitation_probability)
    wind_score = max(0, 25 - wind_speed)
    return round(temp_score + rain_score + wind_score)


def refresh_weather_recommendations(db: Session) -> list[WeatherRecommendation]:
    latitude = float(os.getenv("GOLF_LATITUDE", "40.0583"))
    longitude = float(os.getenv("GOLF_LONGITUDE", "-74.4057"))
    location = os.getenv("GOLF_LOCATION", "Central New Jersey")
    timezone_name = os.getenv("WEATHER_TIMEZONE", "America/New_York")
    params = urllib.parse.urlencode(
        {
            "latitude": latitude,
            "longitude": longitude,
            "daily": "temperature_2m_max,precipitation_probability_max,wind_speed_10m_max",
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "timezone": timezone_name,
            "forecast_days": 7,
        }
    )
    url = f"https://api.open-meteo.com/v1/forecast?{params}"

    try:
        payload = load_json(url)
        daily = payload["daily"]
        candidates = []
        for idx, day_text in enumerate(daily["time"]):
            max_temp = float(daily["temperature_2m_max"][idx])
            precipitation = float(daily["precipitation_probability_max"][idx] or 0)
            wind = float(daily["wind_speed_10m_max"][idx] or 0)
            candidates.append(
                {
                    "date": date.fromisoformat(day_text),
                    "max_temp": max_temp,
                    "precipitation_probability": precipitation,
                    "wind_speed": wind,
                    "score": score_golf_day(max_temp, precipitation, wind),
                }
            )

        best = max(candidates, key=lambda item: item["score"])
        title = f"{best['date'].strftime('%A')} is likely your best golf opportunity this week"
        reason = (
            f"Forecast is {round(best['max_temp'])}F with {round(best['precipitation_probability'])}% rain risk "
            f"and {round(best['wind_speed'])} mph wind."
        )
        row = WeatherRecommendation(
            activity="Golf",
            location=location,
            recommended_date=best["date"],
            title=title,
            reason=reason,
            action="",
            score=int(best["score"]),
            as_of=date.today(),
            raw={
                "candidates": [
                    {
                        **candidate,
                        "date": candidate["date"].isoformat(),
                    }
                    for candidate in candidates
                ]
            },
        )
    except SOURCE_REFRESH_EXCEPTIONS as exc:
        logger.warning("weather_recommendation_refresh_failed", exc_info=True)
        record_source_status(
            db,
            "Open-Meteo",
            "error",
            "Golf weather refresh failed.",
            {"error": str(exc)},
        )
        return []

    db.execute(
        delete(WeatherRecommendation).where(
            WeatherRecommendation.activity == "Golf",
            WeatherRecommendation.as_of == date.today(),
        )
    )
    db.add(row)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    record_source_status(
        db,
        "Open-Meteo",
        "ok",
        "Fetched golf weather recommendation.",
        {"location": location},
    )
    return [row]


def refresh_structured_sources(db: Session) -> dict:
    return {
        "market_prices": len(refresh_market_prices(db)),
        "crypto_prices": len(refresh_crypto_prices(db)),
        "weather_recommendations": len(refresh_weather_recommendations(db)),
    }


def market_attention_items(rows: Iterable[MarketPrice]) -> list[dict]:
    items = []
    for row in rows:
        if row.five_day_high and row.price:
            pullback = (
                (Decimal(row.five_day_high) - Decimal(row.price))
                / Decimal(row.five_day_high)
                * 100
            )
            if pullback >= Decimal(str(MIKE_PROFILE["pullback_review_pct"])):
                items.append(
                    enrich_attention_item(
                        {
                            "title": f"{row.symbol} is down {pct(pullback)} from its five-day high",
                            "why_now": (
                                "Historically, similar large-cap pullbacks have been worth a closer look."
                            ),
                            "action": "",
                            "priority": 7,
                            "source": "market",
                            "detail_id": f"market:{row.symbol}:pullback",
                        },
                        category="opportunity",
                        importance_score=80,
                        actionability_score=55,
                        expiration_hours=72,
                        why_user_cares="The position crossed the pullback review range.",
                    )
                )
        if abs(Decimal(row.five_day_change_pct or 0)) >= Decimal(
            str(MIKE_PROFILE["market_move_review_pct"])
        ):
            direction = "up" if row.five_day_change_pct > 0 else "down"
            items.append(
                enrich_attention_item(
                    {
                        "title": f"{row.symbol} is {direction} {pct(abs(Decimal(row.five_day_change_pct)))} over five trading days",
                        "why_now": "The move is outside the normal watch range for this position.",
                        "action": "",
                        "priority": 6,
                        "source": "market",
                        "detail_id": f"market:{row.symbol}:move",
                    },
                    category="awareness",
                    importance_score=60,
                    actionability_score=10,
                    expiration_hours=168,
                    why_user_cares="The move is notable context but does not require intervention.",
                )
            )
    return items


def crypto_attention_items(rows: Iterable[CryptoPrice]) -> list[dict]:
    items = []
    for row in rows:
        change = Decimal(row.change_24h_pct or 0)
        if abs(change) >= Decimal(str(MIKE_PROFILE["market_move_review_pct"])):
            direction = "up" if change > 0 else "down"
            items.append(
                enrich_attention_item(
                    {
                        "title": f"Bitcoin is {direction} {pct(abs(change))} over 24 hours",
                        "why_now": "Bitcoin moved outside its normal daily range.",
                        "action": "",
                        "priority": 9,
                        "source": "crypto",
                        "detail_id": "crypto:BTC:24h",
                    },
                    category="opportunity" if change < 0 else "awareness",
                    importance_score=84 if change < 0 else 68,
                    actionability_score=58 if change < 0 else 12,
                    expiration_hours=72 if change < 0 else 168,
                    why_user_cares=(
                        "The move may create a time-sensitive review window."
                        if change < 0
                        else "The move is notable context but does not require a crypto action."
                    ),
                )
            )
    return items


def weather_attention_items(rows: Iterable[WeatherRecommendation]) -> list[dict]:
    return [
        enrich_attention_item(
            {
                "title": row.title.replace(
                    "is the best golf day this week",
                    "is likely your best golf window this week",
                ),
                "why_now": row.reason,
                "action": row.action,
                "priority": 8,
                "source": "weather",
                "detail_id": f"weather:{row.activity.lower()}",
            },
            category="opportunity",
            importance_score=78,
            actionability_score=52,
            expiration_hours=72,
            why_user_cares="A good weather window disappears if it is not planned around.",
        )
        for row in rows
        if row.score >= 65
    ]


def structured_topic_briefings(db: Session) -> list[TopicBriefing]:
    briefings: list[TopicBriefing] = []

    bitcoin = db.scalar(select(Topic).where(Topic.name == "Bitcoin"))
    crypto = latest_crypto_prices(db)
    if bitcoin and crypto:
        row = crypto[0]
        change = Decimal(row.change_24h_pct or 0)
        threshold = Decimal(str(MIKE_PROFILE["market_move_review_pct"]))
        direction = "up" if change > 0 else "down"
        title = (
            f"Bitcoin is {direction} {pct(abs(change))} over 24 hours"
            if abs(change) >= threshold
            else "No crypto actions required today"
        )
        summary = (
            f"Bitcoin is at ${Decimal(row.price):,.0f}. The 24-hour move crossed the "
            f"{MIKE_PROFILE['market_move_review_pct']}% watch threshold."
            if abs(change) >= threshold
            else f"Bitcoin is at ${Decimal(row.price):,.0f}. The 24-hour move remains within normal volatility."
        )
        briefings.append(
            TopicBriefing(
                topic_id=bitcoin.id,
                as_of=date.today(),
                title=title,
                summary=summary,
                bullets=[
                    f"Price: ${Decimal(row.price):,.0f}",
                    f"24-hour move: {pct(change)}",
                ],
                action="",
                source_type="structured",
                priority=bitcoin.priority,
                generated_by="CoinGecko",
            )
        )

    golf = db.scalar(select(Topic).where(Topic.name == "Golf"))
    weather = latest_weather_recommendations(db)
    if golf and weather:
        row = weather[0]
        briefings.append(
            TopicBriefing(
                topic_id=golf.id,
                as_of=date.today(),
                title=row.title,
                summary=row.reason,
                bullets=[f"Location: {row.location}", f"Score: {row.score}/100"],
                action=row.action,
                source_type="structured",
                priority=max(golf.priority, 8),
                generated_by="Open-Meteo",
            )
        )

    return briefings
