from __future__ import annotations

import json
import logging
import os
import re
import urllib.parse
import urllib.request
import urllib.error
from datetime import date, datetime, timedelta, timezone
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
    WatchItem,
)
from .personalization import MIKE_PROFILE
from .source_status import record_source_status
from .watch_provenance import source_watch_id


HTTP_TIMEOUT = 15
logger = logging.getLogger(__name__)
DEFAULT_TRACKED_MARKET_SYMBOLS = ["UNH", "USO", "SPY", "QQQ", "AAPL", "^GSPC"]
NON_MARKET_SYMBOLS = {"CASH", "SPAXX", "FDRXX", "CORE", "USD", "BTC"}
SYMBOL_ALIASES = {
    "BITCOIN": "BTC",
    "S&P 500": "^GSPC",
    "S&P 500 PROXY": "^GSPC",
    "SP500": "^GSPC",
}
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
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Source URL must use http or https")
    request = urllib.request.Request(
        url, headers=headers or {"User-Agent": "FocusOS/0.1"}
    )
    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:  # nosec B310
        return json.load(response)


def latest_market_prices(db: Session) -> list[MarketPrice]:
    rows: list[MarketPrice] = []
    symbols = tracked_market_symbols(db)
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


def normalize_symbol(value: str) -> str:
    text = value.strip().upper().replace("$", "")
    text = SYMBOL_ALIASES.get(text, text)
    if text.endswith(" PROXY"):
        text = text.removesuffix(" PROXY").strip()
        text = SYMBOL_ALIASES.get(text, text)
    return text


def is_symbol_like(value: str) -> bool:
    symbol = normalize_symbol(value)
    return bool(symbol) and bool(re.fullmatch(r"\^?[A-Z0-9.]{1,8}", symbol))


def infer_symbol_posture(note: str) -> str:
    lower = note.lower()
    if "short" in lower:
        return "short"
    if any(token in lower for token in ("accumulate", "buy", "add", "entry")):
        return "accumulate"
    if any(token in lower for token in ("trim", "sell", "exit")):
        return "trim"
    return "watch"


def symbol_note_text(value: object) -> str:
    if isinstance(value, dict):
        return str(value.get("note") or value.get("thesis") or "").strip()
    return str(value or "").strip()


def finance_symbol_preferences(db: Session) -> dict[str, dict]:
    preferences: dict[str, dict] = {}
    rows = db.scalars(
        select(WatchItem).where(WatchItem.status == "active", WatchItem.enabled.is_(True))
    ).all()
    for row in rows:
        context = row.personal_context or {}
        manual_facts = context.get("manual_facts") if isinstance(context, dict) else {}
        if not isinstance(manual_facts, dict):
            manual_facts = {}

        source_id = source_watch_id(row.title)
        tracked = manual_facts.get("tracked_symbols") or []
        if isinstance(tracked, str):
            tracked = [tracked]
        for raw_symbol in list(tracked) + list(context.get("interests") or []):
            symbol = normalize_symbol(str(raw_symbol))
            if not is_symbol_like(symbol):
                continue
            preferences.setdefault(
                symbol,
                {
                    "symbol": symbol,
                    "note": "",
                    "position": "watch",
                    "source_watch_id": source_id,
                    "watch_title": row.title,
                },
            )

        notes = manual_facts.get("symbol_notes") or {}
        if isinstance(notes, dict):
            for raw_symbol, raw_note in notes.items():
                symbol = normalize_symbol(str(raw_symbol))
                if not is_symbol_like(symbol):
                    continue
                note = symbol_note_text(raw_note)
                position = (
                    str(raw_note.get("position")).strip().lower()
                    if isinstance(raw_note, dict) and raw_note.get("position")
                    else infer_symbol_posture(note)
                )
                preferences[symbol] = {
                    "symbol": symbol,
                    "note": note,
                    "position": position,
                    "source_watch_id": source_id,
                    "watch_title": row.title,
                }
    return preferences


def tracked_market_symbols(db: Session) -> list[str]:
    symbols = {
        row.symbol.upper()
        for row in db.scalars(select(Holding)).all()
        if row.symbol
        and row.symbol.upper() not in NON_MARKET_SYMBOLS
    }
    symbols.update(
        symbol
        for symbol in finance_symbol_preferences(db)
        if symbol not in NON_MARKET_SYMBOLS
    )
    symbols.update(DEFAULT_TRACKED_MARKET_SYMBOLS)
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


def github_api(path: str) -> dict | list:
    token = os.getenv("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "FocusOS/0.1",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return load_json(f"https://api.github.com{path}", headers=headers)


def refresh_github_repo_health(db: Session) -> dict:
    owner = os.getenv("FOCUSOS_GITHUB_OWNER", "dock108dev")
    now = datetime.now(timezone.utc)
    errors: list[str] = []
    facts: list[dict] = []
    missing_requirements: list[str] = []
    active_repo_ages: list[dict] = []
    failed_workflows: list[dict] = []
    open_prs_found = 0
    archived_repos_ignored = 0
    try:
        repos_payload = github_api(
            f"/users/{urllib.parse.quote(owner)}/repos?type=owner&sort=updated&per_page=100"
        )
        all_repos = [repo for repo in repos_payload if isinstance(repo, dict)]
        archived_repos_ignored = sum(1 for repo in all_repos if repo.get("archived"))
        repos = [
            repo
            for repo in all_repos
            if not repo.get("archived")
        ][:20]
        for repo in repos:
            name = repo.get("name", "")
            pushed_at = repo.get("pushed_at")
            stale = False
            days_since_push = None
            if pushed_at:
                pushed = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
                days_since_push = (now - pushed).days
                stale = now - pushed > timedelta(days=14)
            active_repo_ages.append(
                {
                    "repo": name,
                    "pushed_at": pushed_at,
                    "days_since_push": days_since_push,
                    "url": repo.get("html_url"),
                }
            )
            if stale:
                facts.append(
                    {
                        "kind": "stale_repo",
                        "repo": name,
                        "summary": "Active public repo has no commits for about 2 weeks.",
                        "pushed_at": pushed_at,
                        "url": repo.get("html_url"),
                    }
                )
            try:
                pulls = github_api(
                    f"/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(name)}/pulls?state=open&per_page=10"
                )
                for pull in pulls:
                    open_prs_found += 1
                    author = ((pull.get("user") or {}).get("login") or "").lower()
                    automated = any(
                        token in author
                        for token in ("dependabot", "renovate", "copilot", "github-actions")
                    )
                    facts.append(
                        {
                            "kind": "automated_pr" if automated else "open_pr",
                            "repo": name,
                            "summary": "Open automated PR." if automated else "Open PR needs review.",
                            "title": pull.get("title"),
                            "url": pull.get("html_url"),
                            "author": author,
                        }
                    )
            except SOURCE_REFRESH_EXCEPTIONS as exc:
                errors.append(f"{name} pulls: {type(exc).__name__}: {exc}")
            try:
                workflow_runs_payload = github_api(
                    f"/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(name)}/actions/runs?status=failure&per_page=5"
                )
                workflow_runs = workflow_runs_payload.get("workflow_runs", [])
                for run in workflow_runs:
                    if not isinstance(run, dict):
                        continue
                    failed = {
                        "repo": name,
                        "workflow": run.get("name"),
                        "title": run.get("display_title"),
                        "conclusion": run.get("conclusion"),
                        "status": run.get("status"),
                        "updated_at": run.get("updated_at"),
                        "url": run.get("html_url"),
                    }
                    failed_workflows.append(failed)
                    facts.append(
                        {
                            "kind": "failed_workflow",
                            "repo": name,
                            "summary": "Recent GitHub Actions workflow failure.",
                            "title": run.get("display_title") or run.get("name"),
                            "url": run.get("html_url"),
                            "updated_at": run.get("updated_at"),
                        }
                    )
            except SOURCE_REFRESH_EXCEPTIONS as exc:
                errors.append(f"{name} workflows: {type(exc).__name__}: {exc}")
        missing_requirements.append(
            "Security alerts require authenticated API scope and are not checked in the public MVP."
        )
    except SOURCE_REFRESH_EXCEPTIONS as exc:
        logger.warning("github_repo_health_refresh_failed", exc_info=True)
        record_source_status(
            db,
            "GitHub API",
            "error",
            "GitHub repo health refresh failed.",
            {"error": str(exc)},
        )
        return {
            "status": "error",
            "facts": [],
            "errors": [str(exc)],
            "missing_requirements": missing_requirements,
        }

    status = "ok" if not errors else "partial"
    result = {
        "source_id": "GitHub API",
        "status": status,
        "checked_at": now.isoformat(),
        "facts": facts,
        "errors": errors[:10],
        "missing_requirements": missing_requirements,
        "owner": owner,
        "repos_scanned": len(repos),
        "archived_repos_ignored": archived_repos_ignored,
        "open_prs_found": open_prs_found,
        "failed_workflows_found": len(failed_workflows),
        "failed_workflows": failed_workflows[:10],
        "security_alerts": "unavailable_without_authenticated_security_scope",
        "active_repo_ages": active_repo_ages,
    }
    record_source_status(
        db,
        "GitHub API",
        status,
        f"Checked {len(repos)} public non-archived repos.",
        result,
    )
    return result


def refresh_structured_sources(db: Session) -> dict:
    github = refresh_github_repo_health(db)
    return {
        "market_prices": len(refresh_market_prices(db)),
        "crypto_prices": len(refresh_crypto_prices(db)),
        "weather_recommendations": len(refresh_weather_recommendations(db)),
        "github_facts": len(github.get("facts", [])),
    }


def symbol_source_watch_ids(preference: dict | None) -> list[str]:
    if not preference:
        return []
    source_id = str(preference.get("source_watch_id") or "")
    return [source_id] if source_id else []


def market_pullback_copy(symbol: str, pullback: Decimal, preference: dict | None) -> dict:
    note = str((preference or {}).get("note") or "").strip()
    position = str((preference or {}).get("position") or "").lower()
    if position == "short":
        return {
            "title": f"{symbol} is moving in favor of your short thesis",
            "why_now": (
                f"{symbol} is down {pct(pullback)} from its five-day high."
                + (f" Note: {note}" if note else " You marked this as a short-position watch.")
            ),
            "category": "opportunity",
            "importance_score": 80,
            "actionability_score": 45,
            "why_user_cares": note or "You marked this symbol as a short-position watch.",
            "triggered_surface_rule": "tracked short-position symbol moved lower",
        }
    return {
        "title": f"{symbol} is down {pct(pullback)} from its five-day high",
        "why_now": (
            f"{note} The symbol is down {pct(pullback)} from its five-day high."
            if note
            else "Historically, similar large-cap pullbacks have been worth a closer look."
        ),
        "category": "opportunity",
        "importance_score": 80,
        "actionability_score": 55,
        "why_user_cares": note or "The position crossed the pullback review range.",
        "triggered_surface_rule": "tracked symbol crossed pullback review range",
    }


def market_move_copy(row: MarketPrice, preference: dict | None) -> dict:
    change = Decimal(row.five_day_change_pct or 0)
    direction = "up" if change > 0 else "down"
    note = str((preference or {}).get("note") or "").strip()
    position = str((preference or {}).get("position") or "").lower()
    title = f"{row.symbol} is {direction} {pct(abs(change))} over five trading days"
    why_now = "The move is outside the normal watch range for this position."
    why_user_cares = "The move is notable context but does not require intervention."
    if position == "short" and change > 0:
        title = f"{row.symbol} moved against your short thesis"
        why_now = (
            f"{row.symbol} is up {pct(abs(change))} over five trading days."
            + (f" Note: {note}" if note else " You marked this as a short-position watch.")
        )
        why_user_cares = note or "You marked this symbol as a short-position watch."
    elif note:
        why_now = f"{note} The symbol moved {direction} {pct(abs(change))} over five trading days."
        why_user_cares = note
    return {
        "title": title,
        "why_now": why_now,
        "why_user_cares": why_user_cares,
        "triggered_surface_rule": "tracked symbol moved outside review range",
    }


def market_attention_items(
    rows: Iterable[MarketPrice], symbol_preferences: dict[str, dict] | None = None
) -> list[dict]:
    items = []
    preferences = symbol_preferences or {}
    for row in rows:
        preference = preferences.get(row.symbol.upper())
        if row.five_day_high and row.price:
            pullback = (
                (Decimal(row.five_day_high) - Decimal(row.price))
                / Decimal(row.five_day_high)
                * 100
            )
            if pullback >= Decimal(str(MIKE_PROFILE["pullback_review_pct"])):
                copy = market_pullback_copy(row.symbol, pullback, preference)
                items.append(
                    enrich_attention_item(
                        {
                            "title": copy["title"],
                            "why_now": copy["why_now"],
                            "action": "",
                            "priority": 7,
                            "source": "market",
                            "detail_id": f"market:{row.symbol}:pullback",
                            "source_watch_ids": symbol_source_watch_ids(preference),
                            "triggered_surface_rule": copy["triggered_surface_rule"],
                        },
                        category=copy["category"],
                        importance_score=copy["importance_score"],
                        actionability_score=copy["actionability_score"],
                        expiration_hours=72,
                        why_user_cares=copy["why_user_cares"],
                    )
                )
        if abs(Decimal(row.five_day_change_pct or 0)) >= Decimal(
            str(MIKE_PROFILE["market_move_review_pct"])
        ):
            copy = market_move_copy(row, preference)
            items.append(
                enrich_attention_item(
                    {
                        "title": copy["title"],
                        "why_now": copy["why_now"],
                        "action": "",
                        "priority": 6,
                        "source": "market",
                        "detail_id": f"market:{row.symbol}:move",
                        "source_watch_ids": symbol_source_watch_ids(preference),
                        "triggered_surface_rule": copy["triggered_surface_rule"],
                    },
                    category="awareness",
                    importance_score=60,
                    actionability_score=10,
                    expiration_hours=168,
                    why_user_cares=copy["why_user_cares"],
                )
            )
    return items


def crypto_attention_items(
    rows: Iterable[CryptoPrice], symbol_preferences: dict[str, dict] | None = None
) -> list[dict]:
    items = []
    preferences = symbol_preferences or {}
    for row in rows:
        change = Decimal(row.change_24h_pct or 0)
        if abs(change) >= Decimal(str(MIKE_PROFILE["market_move_review_pct"])):
            direction = "up" if change > 0 else "down"
            symbol = getattr(row, "symbol", "BTC") or "BTC"
            preference = preferences.get(symbol.upper()) or preferences.get("BTC")
            note = str((preference or {}).get("note") or "").strip()
            position = str((preference or {}).get("position") or "").lower()
            why_now = "Bitcoin moved outside its normal daily range."
            why_user_cares = (
                "The move may create a time-sensitive review window."
                if change < 0
                else "The move is notable context but does not require a crypto action."
            )
            category = "opportunity" if change < 0 else "awareness"
            importance_score = 84 if change < 0 else 68
            actionability_score = 58 if change < 0 else 12
            if note:
                why_now = f"{note} Bitcoin is {direction} {pct(abs(change))} over 24 hours."
                why_user_cares = note
            if position == "short" and change < 0:
                why_now = (
                    f"Bitcoin is down {pct(abs(change))} over 24 hours."
                    + (f" Note: {note}" if note else " You marked this as a short-position watch.")
                )
            items.append(
                enrich_attention_item(
                    {
                        "title": f"Bitcoin is {direction} {pct(abs(change))} over 24 hours",
                        "why_now": why_now,
                        "action": "",
                        "priority": 9,
                        "source": "crypto",
                        "detail_id": "crypto:BTC:24h",
                        "source_watch_ids": symbol_source_watch_ids(preference),
                        "triggered_surface_rule": "tracked BTC move crossed review range",
                    },
                    category=category,
                    importance_score=importance_score,
                    actionability_score=actionability_score,
                    expiration_hours=72 if change < 0 else 168,
                    why_user_cares=why_user_cares,
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


def github_attention_items(db: Session) -> list[dict]:
    from .models import SourceStatus

    status = db.scalar(select(SourceStatus).where(SourceStatus.name == "GitHub API"))
    details = status.details if status else {}
    facts = details.get("facts") if isinstance(details, dict) else []
    if not isinstance(facts, list):
        facts = []
    items = []
    for fact in facts[:5]:
        kind = fact.get("kind")
        if kind not in {"automated_pr", "open_pr", "stale_repo", "failed_workflow"}:
            continue
        category = "action" if kind in {"automated_pr", "open_pr", "failed_workflow"} else "awareness"
        title = (
            f"{fact.get('repo')} has an automated PR"
            if kind == "automated_pr"
            else f"{fact.get('repo')} has an open PR"
            if kind == "open_pr"
            else f"{fact.get('repo')} has a failing workflow"
            if kind == "failed_workflow"
            else f"{fact.get('repo')} has been quiet for about 2 weeks"
        )
        items.append(
            enrich_attention_item(
                {
                    "title": title,
                    "why_now": fact.get("summary", "GitHub repo health changed."),
                    "action": "",
                    "priority": 8 if category == "action" else 5,
                    "source": "github",
                    "topic": "github",
                    "detail_id": f"github:{fact.get('repo')}:{kind}",
                    "source_watch_ids": ["watch:personal-github-repo-health"],
                    "triggered_surface_rule": fact.get("summary", "GitHub repo health rule triggered."),
                    "why_today": fact.get("summary", "GitHub repo health changed."),
                },
                category=category,
                importance_score=82 if category == "action" else 58,
                actionability_score=72 if category == "action" else 12,
                expiration_hours=72,
                why_user_cares="Public repo health can create a quick action queue.",
            )
        )
    return items


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
