from __future__ import annotations

from sqlalchemy.orm import Session

from .structured_common import SOURCE_REFRESH_EXCEPTIONS, load_json
from .structured_crypto import (
    crypto_attention_items,
    latest_crypto_prices,
    refresh_crypto_prices,
)
from .structured_finance import (
    fetch_yahoo_symbol,
    finance_symbol_preferences,
    latest_market_prices,
    market_attention_items,
    normalize_symbol,
    refresh_market_prices,
    tracked_market_symbols,
)
from .structured_github import github_attention_items, github_api, refresh_github_repo_health
from .structured_topics import structured_topic_briefings
from .structured_weather import (
    latest_weather_recommendations,
    refresh_weather_recommendations,
    score_golf_day,
    weather_attention_items,
)


__all__ = [
    "SOURCE_REFRESH_EXCEPTIONS",
    "crypto_attention_items",
    "finance_symbol_preferences",
    "fetch_yahoo_symbol",
    "github_api",
    "github_attention_items",
    "latest_crypto_prices",
    "latest_market_prices",
    "latest_weather_recommendations",
    "load_json",
    "market_attention_items",
    "normalize_symbol",
    "refresh_crypto_prices",
    "refresh_github_repo_health",
    "refresh_market_prices",
    "refresh_structured_sources",
    "refresh_weather_recommendations",
    "score_golf_day",
    "structured_topic_briefings",
    "tracked_market_symbols",
    "weather_attention_items",
]


def refresh_structured_sources(db: Session) -> dict:
    github = refresh_github_repo_health(db)
    return {
        "market_prices": len(refresh_market_prices(db)),
        "crypto_prices": len(refresh_crypto_prices(db)),
        "weather_recommendations": len(refresh_weather_recommendations(db)),
        "github_facts": len(github.get("facts", [])),
    }
