from __future__ import annotations

import logging
import os
import urllib.parse
from datetime import date
from typing import Iterable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .attention import enrich_attention_item
from .models import WeatherRecommendation
from .source_status import record_source_status
from .structured_common import SOURCE_REFRESH_EXCEPTIONS, load_json


logger = logging.getLogger(__name__)


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


def score_golf_day(
    max_temp: float, precipitation_probability: float, wind_speed: float
) -> int:
    temp_score = max(0, 40 - abs(max_temp - 72))
    rain_score = max(0, 35 - precipitation_probability)
    wind_score = max(0, 25 - wind_speed)
    return round(temp_score + rain_score + wind_score)


def refresh_weather_recommendations(db: Session) -> list[WeatherRecommendation]:
    latitude = float(os.getenv("GOLF_LATITUDE", "40.7062"))
    longitude = float(os.getenv("GOLF_LONGITUDE", "-74.5493"))
    location = os.getenv("GOLF_LOCATION", "Basking Ridge, NJ")
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

        for candidate in candidates:
            weekday = candidate["date"].weekday()
            if weekday == 0:
                candidate["score"] = 0
                candidate["suppression"] = "Monday because course is closed."
            elif weekday == 4:
                candidate["score"] = max(0, candidate["score"] - 12)
                candidate["suppression"] = "Friday afternoon downranked because it is likely packed."
            else:
                candidate["suppression"] = None

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
