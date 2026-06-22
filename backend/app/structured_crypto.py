from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Iterable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .attention import enrich_attention_item, pct
from .models import CryptoPrice
from .personalization import MIKE_PROFILE
from .source_status import record_source_status
from .structured_common import SOURCE_REFRESH_EXCEPTIONS, load_json
from .structured_finance import symbol_source_watch_ids


logger = logging.getLogger(__name__)


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
