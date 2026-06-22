from __future__ import annotations

import logging
import re
import urllib.parse
from datetime import date
from decimal import Decimal
from typing import Iterable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .attention import enrich_attention_item, pct
from .models import Holding, MarketPrice, WatchItem
from .personalization import MIKE_PROFILE
from .source_status import record_source_status
from .structured_common import SOURCE_REFRESH_EXCEPTIONS, load_json
from .watch_provenance import source_watch_id


logger = logging.getLogger(__name__)
DEFAULT_TRACKED_MARKET_SYMBOLS = ["UNH", "USO", "SPY", "QQQ", "AAPL", "^GSPC"]
NON_MARKET_SYMBOLS = {"CASH", "SPAXX", "FDRXX", "CORE", "USD", "BTC"}
SYMBOL_ALIASES = {
    "BITCOIN": "BTC",
    "S&P 500": "^GSPC",
    "S&P 500 PROXY": "^GSPC",
    "SP500": "^GSPC",
}


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
