from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from .attention import holding_value, is_technology, pct, summarize
from .attention import build_attention, build_portfolio_review_item
from .models import Holding, TopicBriefing
from .personalization import MIKE_PROFILE
from .structured_sources import (
    crypto_attention_items,
    latest_crypto_prices,
    latest_market_prices,
    latest_weather_recommendations,
    market_attention_items,
)
from .voice import clean_action_text, clean_editorial_text
from .watchlist import latest_watch_evaluation, watch_domain
from .watch_provenance import provenance_for_attention_item


def not_found(detail_id: str) -> dict:
    return {
        "id": detail_id,
        "title": "Recommendation not found",
        "summary": "The recommendation is no longer available in the current briefing.",
        "action": "Refresh the briefing.",
        "why_generated": [],
        "raw_data": {},
        "source_data": {},
        "ai_processing": None,
        "suppressed_signals": [],
    }


def base_detail(detail_id: str, title: str, summary: str, action: str) -> dict:
    return {
        "id": detail_id,
        "title": title,
        "summary": summary,
        "action": action,
        "why_generated": [],
        "raw_data": {},
        "source_data": {},
        "ai_processing": None,
        "suppressed_signals": [],
    }


def finance_detail(db: Session, detail_id: str) -> dict:
    holdings = list(db.scalars(select(Holding)).all())
    summary = summarize(holdings)

    if detail_id == "finance:cash":
        detail = base_detail(
            detail_id,
            f"${summary['cash_available']:,.0f} cash is available",
            "This appeared because cash crossed Mike's portfolio review threshold.",
            "",
        )
        detail["why_generated"] = [
            "Why it appeared: cash is high enough to need a purpose.",
            f"Cash is above ${MIKE_PROFILE['cash_attention_min']:,.0f}.",
            f"Cash is above Mike's {MIKE_PROFILE['cash_attention_pct']}% review threshold.",
        ]
        detail["raw_data"] = {
            "cash_available": summary["cash_available"],
            "cash_percent": summary["cash_percent"],
            "current_value": summary["current_value"],
        }
        detail["source_data"] = {
            "provider": "Manual portfolio imports",
            "accounts": sorted({row.source for row in holdings}),
        }
        return detail

    if detail_id == "finance:technology":
        tech_value = sum(
            (holding_value(row) for row in holdings if is_technology(row)), Decimal("0")
        )
        total = Decimal(str(summary["current_value"]))
        tech_percent = float(tech_value / total * 100) if total else 0
        detail = base_detail(
            detail_id,
            f"Technology allocation is {tech_percent:.1f}%",
            "This appeared because technology concentration is high enough to affect new capital decisions.",
            "",
        )
        detail["why_generated"] = [
            "Why it appeared: a concentration threshold was crossed.",
            f"Threshold crossed: technology is above Mike's {MIKE_PROFILE['technology_concentration_pct']}% limit.",
            f"Evidence: technology is {tech_percent:.1f}% of the portfolio.",
        ]
        detail["raw_data"] = {
            "technology_value": float(tech_value),
            "technology_percent": tech_percent,
            "threshold": MIKE_PROFILE["technology_concentration_pct"],
            "positions": [
                {
                    "symbol": row.symbol,
                    "value": float(holding_value(row)),
                    "source": row.source,
                }
                for row in holdings
                if is_technology(row)
            ],
        }
        detail["source_data"] = {
            "provider": "Manual portfolio imports",
            "accounts": sorted({row.source for row in holdings}),
        }
        return detail

    parts = detail_id.split(":")
    if len(parts) == 4 and parts[0] == "finance" and parts[1] == "position":
        symbol = parts[2]
        kind = parts[3]
        row = next(
            (
                holding
                for holding in holdings
                if holding.symbol.upper() == symbol.upper()
            ),
            None,
        )
        if not row:
            return not_found(detail_id)
        value = holding_value(row)
        total = Decimal(str(summary["current_value"]))
        concentration = float(value / total * 100) if total else 0
        drawdown = (
            float((Decimal(row.cost_basis) - value) / Decimal(row.cost_basis) * 100)
            if row.cost_basis
            else 0
        )
        title = (
            f"{symbol} is {concentration:.1f}% of the portfolio"
            if kind == "concentration"
            else f"{symbol} is down {drawdown:.1f}% from cost basis"
        )
        detail = base_detail(
            detail_id,
            title,
            "This appeared because the holding crossed one of Mike's position review thresholds.",
            "",
        )
        detail["why_generated"] = [
            "Why it appeared: this position reached a portfolio review condition.",
            f"Threshold crossed: {MIKE_PROFILE['single_position_concentration_pct']}% concentration or {MIKE_PROFILE['pullback_review_pct']}% pullback.",
            f"Evidence: portfolio weight is {concentration:.1f}%.",
            f"Evidence: cost-basis drawdown is {drawdown:.1f}%.",
        ]
        detail["raw_data"] = {
            "symbol": row.symbol,
            "name": row.name,
            "source": row.source,
            "account": row.account,
            "quantity": float(row.quantity),
            "price": float(row.price),
            "market_value": float(value),
            "cost_basis": float(row.cost_basis or 0),
            "portfolio_weight": concentration,
            "cost_basis_drawdown": drawdown,
        }
        detail["source_data"] = {
            "provider": "Manual portfolio imports",
            "as_of": row.as_of.isoformat(),
        }
        return detail

    return not_found(detail_id)


def portfolio_review_detail(db: Session, detail_id: str) -> dict:
    holdings = list(db.scalars(select(Holding)).all())
    summary = summarize(holdings)
    signals = (
        build_attention(holdings, summary)
        + market_attention_items(latest_market_prices(db))
        + crypto_attention_items(latest_crypto_prices(db))
    )
    if not signals:
        return base_detail(
            detail_id,
            "No major portfolio actions currently identified",
            "Portfolio thresholds were checked and none require attention.",
            "",
        )

    grouped = build_portfolio_review_item(signals)
    detail = base_detail(
        detail_id,
        grouped["title"],
        "This appeared because multiple portfolio signals belong to one portfolio state, not separate homepage stories.",
        "",
    )
    detail["why_generated"] = [
        "Why it appeared: portfolio thresholds are active and grouped into one review item.",
        f"Thresholds checked: cash above {MIKE_PROFILE['cash_attention_pct']}%, technology above {MIKE_PROFILE['technology_concentration_pct']}%, single positions above {MIKE_PROFILE['single_position_concentration_pct']}%, pullbacks above {MIKE_PROFILE['pullback_review_pct']}%.",
        f"Evidence: {len(signals)} portfolio signals are currently active.",
        "Novelty rule: persistent portfolio facts are collapsed here so they do not consume the whole briefing every day.",
        *[f"Signal: {item['title']} - {item['why_now']}" for item in signals],
    ]
    detail["raw_data"] = {"signals": signals}
    detail["raw_data"]["provenance"] = provenance_for_attention_item(grouped)
    detail["source_data"] = {
        "provider": "Manual portfolio imports",
        "accounts": sorted({row.source for row in holdings}),
        "latest_as_of": summary["latest_as_of"],
    }
    detail["suppressed_signals"] = [
        {
            "reason": "Collapsed into Portfolio to preserve homepage diversity.",
            "items": signals,
        }
    ]
    return detail


def market_detail(db: Session, detail_id: str) -> dict:
    try:
        _, symbol, kind = detail_id.split(":", 2)
    except ValueError:
        return not_found(detail_id)
    if kind not in {"pullback", "move"}:
        return not_found(detail_id)
    row = next(
        (
            item
            for item in latest_market_prices(db)
            if item.symbol.upper() == symbol.upper()
        ),
        None,
    )
    if not row:
        return not_found(detail_id)

    pullback = (
        float(
            (Decimal(row.five_day_high) - Decimal(row.price))
            / Decimal(row.five_day_high)
            * 100
        )
        if row.five_day_high
        else 0
    )
    title = (
        f"{row.symbol} is down {pullback:.1f}% from its five-day high"
        if kind == "pullback"
        else f"{row.symbol} moved {pct(row.five_day_change_pct)} over five trading days"
    )
    detail = base_detail(
        detail_id,
        title,
        "This appeared because the current market source found a move large enough to review.",
        "",
    )
    detail["why_generated"] = [
        "Why it appeared: the position moved outside the configured watch range.",
        f"Threshold checked: {MIKE_PROFILE['market_move_review_pct']}% move.",
        f"Evidence: five-day change is {pct(row.five_day_change_pct)}.",
    ]
    detail["raw_data"] = {
        "symbol": row.symbol,
        "price": float(row.price),
        "previous_close": float(row.previous_close),
        "five_day_high": float(row.five_day_high),
        "five_day_change_pct": float(row.five_day_change_pct),
        "pullback_from_five_day_high": pullback,
    }
    detail["source_data"] = {
        "provider": row.source,
        "fetch_date": row.as_of.isoformat(),
    }
    return detail


def crypto_detail(db: Session, detail_id: str) -> dict:
    row = next(
        (item for item in latest_crypto_prices(db) if item.symbol.upper() == "BTC"),
        None,
    )
    if not row:
        return not_found(detail_id)
    detail = base_detail(
        detail_id,
        f"Bitcoin moved {pct(row.change_24h_pct)} over 24 hours",
        "This appeared because Bitcoin crossed the daily movement review threshold.",
        "",
    )
    detail["why_generated"] = [
        "Why it appeared: Bitcoin moved outside the configured daily watch range.",
        f"Threshold crossed: {MIKE_PROFILE['market_move_review_pct']}% over 24 hours.",
        f"Evidence: 24-hour move is {pct(row.change_24h_pct)}.",
    ]
    detail["raw_data"] = {
        "price": float(row.price),
        "change_24h_pct": float(row.change_24h_pct),
    }
    detail["source_data"] = {
        "provider": row.source,
        "fetch_date": row.as_of.isoformat(),
    }
    return detail


def weather_detail(db: Session, detail_id: str) -> dict:
    row = next(
        (
            item
            for item in latest_weather_recommendations(db)
            if item.activity.lower() == "golf"
        ),
        None,
    )
    if not row:
        return not_found(detail_id)
    detail = base_detail(
        detail_id,
        row.title,
        "This appeared because the seven-day forecast produced a usable golf window.",
        row.action,
    )
    detail["why_generated"] = [
        "Why it appeared: a time-sensitive weather window ranked highest this week.",
        "Threshold checked: golf-day score of at least 65/100.",
        f"Evidence: winning score is {row.score}/100.",
        f"Evidence: {row.reason}",
    ]
    detail["raw_data"] = row.raw or {}
    detail["source_data"] = {
        "provider": row.source,
        "location": row.location,
        "fetch_date": row.as_of.isoformat(),
        "recommended_date": row.recommended_date.isoformat(),
    }
    detail["suppressed_signals"] = [
        {
            "reason": "Lower golf score than the recommended day.",
            "items": (row.raw or {}).get("candidates", [])[1:],
        }
    ]
    return detail


def topic_detail(db: Session, detail_id: str) -> dict:
    try:
        briefing_id = int(detail_id.split(":", 1)[1])
    except (IndexError, ValueError):
        return not_found(detail_id)
    row = db.get(TopicBriefing, briefing_id)
    if not row:
        return not_found(detail_id)
    detail = base_detail(
        detail_id,
        clean_editorial_text(row.title),
        "This appeared because the topic briefing was classified as relevant to today's attention.",
        clean_action_text(row.action),
    )
    detail["why_generated"] = [
        f"Why it appeared: {clean_editorial_text(row.summary)}",
        f"Threshold checked: topic priority {row.priority}/10 with source {row.generated_by}.",
        *[f"Evidence: {clean_editorial_text(item)}" for item in (row.bullets or [])],
    ]
    detail["raw_data"] = {
        "bullets": [clean_editorial_text(item) for item in (row.bullets or [])]
    }
    detail["source_data"] = {
        "provider": row.generated_by,
        "source_type": row.source_type,
        "as_of": row.as_of.isoformat(),
    }
    detail["ai_processing"] = (
        {
            "prompt": row.topic.prompt if row.topic else None,
            "parsed_title": row.title,
            "parsed_summary": row.summary,
            "parsed_action": row.action,
        }
        if row.generated_by not in {"fallback", "CoinGecko", "Open-Meteo"}
        else None
    )
    detail["suppressed_signals"] = [
        {"reason": "Below topic priority or actionability threshold.", "items": []}
    ]
    return detail


def watch_detail(db: Session, detail_id: str) -> dict:
    try:
        watch_item_id = int(detail_id.split(":", 1)[1])
    except (IndexError, ValueError):
        return not_found(detail_id)
    row = latest_watch_evaluation(db, watch_item_id)
    if not row or not row.watch_item:
        return not_found(detail_id)
    watch = row.watch_item
    detail = base_detail(
        detail_id,
        row.title,
        "This appeared because a user-created watch item reached a meaningful update or decision point.",
        "",
    )
    detail["why_generated"] = [
        f"Why it appeared: {row.trigger_reason}",
        f"Threshold checked: {', '.join(watch.surface_when or [])}.",
        f"Monitoring: {', '.join(watch.watch_for or [])}.",
    ]
    detail["raw_data"] = {
        "watch_item": {
            "id": watch.id,
            "title": watch.title,
            "original_text": watch.original_text,
            "event_date": watch.event_date.isoformat() if watch.event_date else None,
            "expires_at": watch.expires_at.isoformat() if watch.expires_at else None,
            "watch_for": watch.watch_for or [],
            "surface_when": watch.surface_when or [],
            "status": watch.status,
        },
        "provenance": {
            "source_watch_ids": [f"watch:{watch.id}"],
            "triggered_surface_rule": row.trigger_reason,
            "suppressed_by": None,
            "why_today": row.summary,
        },
        "evaluation": {
            "as_of": row.as_of.isoformat(),
            "category": row.category,
            "importance_score": row.importance_score,
            "actionability_score": row.actionability_score,
            "should_surface": row.should_surface,
            "summary": row.summary,
        },
    }
    detail["source_data"] = {
        "provider": "User-created watchlist",
        "domain": watch_domain(watch.title, watch.watch_for or []),
        "as_of": row.as_of.isoformat(),
    }
    detail["ai_processing"] = {
        "parsed_title": watch.title,
        "parsed_event_date": watch.event_date.isoformat() if watch.event_date else None,
        "parsed_expiration": watch.expires_at.isoformat() if watch.expires_at else None,
        "parsed_watch_for": watch.watch_for or [],
        "parsed_surface_when": watch.surface_when or [],
    }
    return detail


def recommendation_detail(db: Session, detail_id: str) -> dict:
    if detail_id == "portfolio:review":
        return portfolio_review_detail(db, detail_id)
    if detail_id.startswith("finance:"):
        return finance_detail(db, detail_id)
    if detail_id.startswith("market:"):
        return market_detail(db, detail_id)
    if detail_id.startswith("crypto:"):
        return crypto_detail(db, detail_id)
    if detail_id.startswith("weather:"):
        return weather_detail(db, detail_id)
    if detail_id.startswith("topic:"):
        return topic_detail(db, detail_id)
    if detail_id.startswith("watch:"):
        return watch_detail(db, detail_id)
    return not_found(detail_id)
