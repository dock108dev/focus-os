from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from .attention import pct
from .models import Topic, TopicBriefing
from .personalization import MIKE_PROFILE
from .structured_crypto import latest_crypto_prices
from .structured_weather import latest_weather_recommendations


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
