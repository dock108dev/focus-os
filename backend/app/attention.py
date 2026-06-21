from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable

from .models import Holding
from .personalization import MIKE_PROFILE, large_cap_pullback_reason


TECH_SYMBOLS = {
    "AAPL",
    "MSFT",
    "NVDA",
    "GOOGL",
    "GOOG",
    "AMZN",
    "META",
    "TSLA",
    "AMD",
    "AVGO",
}
CASH_SYMBOLS = {"CASH", "SPAXX", "FDRXX", "CORE", "USD"}
ATTENTION_CATEGORY_ORDER = {"action": 0, "opportunity": 1, "awareness": 2}
CLASSIFICATION_TO_CATEGORY = {
    "action": "action",
    "action_required": "action",
    "opportunity": "opportunity",
    "awareness": "awareness",
}
CATEGORY_TO_CLASSIFICATION = {
    "action": "action_required",
    "opportunity": "opportunity",
    "awareness": "awareness",
}


@dataclass(frozen=True)
class AttentionItem:
    title: str
    why_now: str
    action: str
    priority: int
    detail_id: str
    category: str = "awareness"
    importance_score: int = 0
    actionability_score: int = 0
    expiration_hours: int = 168
    why_user_cares: str = ""
    classification: str = "awareness"
    source: str = "portfolio"


@dataclass(frozen=True)
class Opportunity:
    title: str
    action: str
    priority: int
    detail_id: str


def money(value: Decimal | float | int) -> str:
    amount = Decimal(value)
    return f"${amount:,.0f}"


def pct(value: Decimal | float | int) -> str:
    return f"{Decimal(value):.1f}%"


def clamp_score(value: int | float | None, default: int) -> int:
    if value is None:
        return default
    return max(0, min(100, int(round(value))))


def normalize_attention_category(value: str | None) -> str:
    return CLASSIFICATION_TO_CATEGORY.get((value or "").lower(), "awareness")


def category_defaults(category: str, priority: int) -> tuple[int, int, int]:
    importance = clamp_score(priority * 10, 50)
    if category == "action":
        return max(importance, 80), 85, 72
    if category == "opportunity":
        return max(importance, 70), 55, 72
    return max(importance, 40), 10, 168


def enrich_attention_item(
    item: dict,
    *,
    category: str | None = None,
    importance_score: int | None = None,
    actionability_score: int | None = None,
    expiration_hours: int | None = None,
    why_user_cares: str | None = None,
) -> dict:
    next_item = dict(item)
    resolved_category = normalize_attention_category(
        category or next_item.get("category") or next_item.get("classification")
    )
    priority = int(next_item.get("priority") or 0)
    default_importance, default_actionability, default_expiration = category_defaults(
        resolved_category, priority
    )

    next_item["category"] = resolved_category
    next_item["classification"] = CATEGORY_TO_CLASSIFICATION[resolved_category]
    next_item["importance_score"] = clamp_score(
        next_item.get("importance_score"), default_importance
    )
    if importance_score is not None:
        next_item["importance_score"] = clamp_score(
            importance_score, default_importance
        )
    next_item["actionability_score"] = clamp_score(
        next_item.get("actionability_score"), default_actionability
    )
    if actionability_score is not None:
        next_item["actionability_score"] = clamp_score(
            actionability_score, default_actionability
        )
    next_item["expiration_hours"] = int(
        next_item.get("expiration_hours") or default_expiration
    )
    if expiration_hours is not None:
        next_item["expiration_hours"] = int(expiration_hours)
    next_item["why_user_cares"] = (
        why_user_cares
        or next_item.get("why_user_cares")
        or next_item.get("why_now")
        or next_item.get("title", "")
    )
    return next_item


def attention_sort_key(item: dict) -> tuple[int, int, int, int, int]:
    category = normalize_attention_category(
        item.get("category") or item.get("classification")
    )
    return (
        ATTENTION_CATEGORY_ORDER[category],
        -int(item.get("importance_score") or 0),
        -int(item.get("actionability_score") or 0),
        int(item.get("expiration_hours") or 9999),
        -int(item.get("priority") or 0),
    )


def is_cash(holding: Holding) -> bool:
    symbol = holding.symbol.upper()
    name = holding.name.lower()
    asset_class = holding.asset_class.lower()
    return symbol in CASH_SYMBOLS or "cash" in name or asset_class == "cash"


def is_technology(holding: Holding) -> bool:
    return (
        holding.symbol.upper() in TECH_SYMBOLS or "tech" in holding.asset_class.lower()
    )


def holding_value(holding: Holding) -> Decimal:
    if holding.market_value:
        return Decimal(holding.market_value)
    return Decimal(holding.quantity or 0) * Decimal(holding.price or 0)


def summarize(holdings: Iterable[Holding]) -> dict:
    rows = list(holdings)
    current_value = sum((holding_value(row) for row in rows), Decimal("0"))
    cash_available = sum(
        (holding_value(row) for row in rows if is_cash(row)), Decimal("0")
    )

    allocation: dict[str, Decimal] = defaultdict(Decimal)
    for row in rows:
        bucket = "Cash" if is_cash(row) else row.asset_class or "Unknown"
        allocation[bucket] += holding_value(row)

    allocation_rows = [
        {
            "label": label,
            "value": float(value),
            "percent": float(value / current_value * 100) if current_value else 0,
        }
        for label, value in sorted(
            allocation.items(), key=lambda item: item[1], reverse=True
        )
    ]

    latest_as_of = max((row.as_of for row in rows), default=date.today())

    return {
        "current_value": float(current_value),
        "daily_change": 0,
        "daily_change_pct": 0,
        "monthly_change": 0,
        "monthly_change_pct": 0,
        "cash_available": float(cash_available),
        "cash_percent": (
            float(cash_available / current_value * 100) if current_value else 0
        ),
        "allocation": allocation_rows,
        "latest_as_of": latest_as_of.isoformat(),
    }


def build_attention(holdings: Iterable[Holding], summary: dict) -> list[dict]:
    rows = list(holdings)
    total = Decimal(str(summary["current_value"]))
    items: list[AttentionItem] = []

    cash = Decimal(str(summary["cash_available"]))
    cash_percent = Decimal(str(summary["cash_percent"]))
    if (
        total
        and cash >= Decimal(str(MIKE_PROFILE["cash_attention_min"]))
        and cash_percent >= Decimal(str(MIKE_PROFILE["cash_attention_pct"]))
    ):
        items.append(
            AttentionItem(
                title=f"{money(cash)} cash is available",
                why_now=(
                    f"Cash is {pct(cash_percent)} of the portfolio, above Mike's "
                    f"{MIKE_PROFILE['cash_attention_pct']}% review threshold."
                ),
                action="",
                priority=10,
                detail_id="finance:cash",
                category=(
                    "action"
                    if cash_percent
                    >= Decimal(str(MIKE_PROFILE["cash_attention_pct"])) * Decimal("1.4")
                    else "awareness"
                ),
                importance_score=88,
                actionability_score=82,
                expiration_hours=72,
                why_user_cares="Cash crossed Mike's review threshold and needs a purpose.",
            )
        )

    tech_value = sum(
        (holding_value(row) for row in rows if is_technology(row)), Decimal("0")
    )
    tech_percent = (tech_value / total * 100) if total else Decimal("0")
    if tech_percent >= Decimal(str(MIKE_PROFILE["technology_concentration_pct"])):
        items.append(
            AttentionItem(
                title=f"Technology allocation is {pct(tech_percent)}",
                why_now=(
                    f"Technology is above Mike's {MIKE_PROFILE['technology_concentration_pct']}% concentration threshold, "
                    "so new buying could make the portfolio more concentrated."
                ),
                action="",
                priority=9,
                detail_id="finance:technology",
                category="action",
                importance_score=91,
                actionability_score=86,
                expiration_hours=72,
                why_user_cares="Adding more technology would worsen an existing concentration breach.",
            )
        )

    for row in rows:
        value = holding_value(row)
        if not total or value <= 0 or is_cash(row):
            continue

        concentration = value / total * 100
        if concentration >= Decimal(
            str(MIKE_PROFILE["single_position_concentration_pct"])
        ):
            items.append(
                AttentionItem(
                    title=f"{row.symbol.upper()} is {pct(concentration)} of the portfolio",
                    why_now=(
                        f"Single-position concentration is above Mike's {MIKE_PROFILE['single_position_concentration_pct']}% "
                        "threshold, so this position can drive the whole portfolio."
                    ),
                    action="",
                    priority=8,
                    detail_id=f"finance:position:{row.symbol.upper()}:concentration",
                    category="action",
                    importance_score=90,
                    actionability_score=84,
                    expiration_hours=72,
                    why_user_cares="This position is large enough to drive portfolio risk by itself.",
                )
            )

        if row.cost_basis and Decimal(row.cost_basis) > 0:
            drawdown = (Decimal(row.cost_basis) - value) / Decimal(row.cost_basis) * 100
            if drawdown >= Decimal(str(MIKE_PROFILE["pullback_review_pct"])):
                items.append(
                    AttentionItem(
                        title=f"{row.symbol.upper()} is down {pct(drawdown)} from cost basis",
                        why_now=large_cap_pullback_reason(),
                        action="",
                        priority=7,
                        detail_id=f"finance:position:{row.symbol.upper()}:pullback",
                        category="opportunity",
                        importance_score=82,
                        actionability_score=58,
                        expiration_hours=72,
                        why_user_cares="The price crossed Mike's pullback review threshold.",
                    )
                )

    deduped = {(item.title, item.action): item for item in items}
    ranked = sorted(
        (enrich_attention_item(item.__dict__) for item in deduped.values()),
        key=attention_sort_key,
    )
    return ranked[:10]


def build_opportunities(
    holdings: Iterable[Holding], summary: dict, attention: list[dict]
) -> list[dict]:
    rows = list(holdings)
    opportunities: list[Opportunity] = []

    if (
        summary["cash_available"] >= MIKE_PROFILE["cash_attention_min"]
        and summary["cash_percent"] >= MIKE_PROFILE["cash_attention_pct"]
    ):
        opportunities.append(
            Opportunity(
                title="High cash position",
                action="Deploy, reserve, or move to higher-yield cash.",
                priority=10,
                detail_id="finance:cash",
            )
        )

    underwater = [
        row
        for row in rows
        if row.cost_basis
        and Decimal(row.cost_basis) > holding_value(row)
        and not is_cash(row)
    ]
    for row in sorted(
        underwater,
        key=lambda item: Decimal(item.cost_basis or 0) - holding_value(item),
        reverse=True,
    )[:3]:
        opportunities.append(
            Opportunity(
                title=f"{row.symbol.upper()} review candidate",
                action="Lower price may improve the risk/reward.",
                priority=8,
                detail_id=f"finance:position:{row.symbol.upper()}:pullback",
            )
        )

    if any("Technology allocation" in item["title"] for item in attention):
        opportunities.append(
            Opportunity(
                title="Rebalance candidate",
                action="New buying outside technology would reduce concentration.",
                priority=7,
                detail_id="finance:technology",
            )
        )

    return [
        item.__dict__
        for item in sorted(opportunities, key=lambda item: item.priority, reverse=True)[
            :5
        ]
    ]


def build_recommended_actions(
    attention: list[dict],
    opportunities: list[dict],
    topic_briefings: Iterable[object],
) -> list[dict]:
    actions: list[dict] = []
    seen: set[str] = set()

    def add(title: str, reason: str, priority: int, detail_id: str) -> None:
        if title in seen:
            return
        seen.add(title)
        actions.append(
            {
                "title": title,
                "reason": reason,
                "priority": priority,
                "detail_id": detail_id,
            }
        )

    for item in opportunities:
        if item["title"] == "High cash position":
            add(
                "Deployable cash is elevated.",
                item["action"],
                item["priority"],
                "finance:cash",
            )
        elif "review candidate" in item["title"].lower():
            symbol = item["title"].split()[0]
            add(
                f"{symbol} is in a pullback range.",
                item["action"],
                item["priority"],
                f"finance:position:{symbol}:pullback",
            )
        elif item["title"] == "Rebalance candidate":
            add(
                "Check allocation drift.",
                item["action"],
                item["priority"],
                "finance:technology",
            )

    for item in attention:
        if "Technology allocation" in item["title"]:
            add(
                "Avoid adding more technology by default.",
                item["action"],
                item["priority"],
                item.get("detail_id", "finance:technology"),
            )
        elif "cash is available" in item["title"]:
            add(
                "Cash purpose is unresolved.",
                item["action"],
                item["priority"],
                item.get("detail_id", "finance:cash"),
            )

    for briefing in topic_briefings:
        if getattr(briefing, "generated_by", "") == "fallback":
            continue
        topic = getattr(getattr(briefing, "topic", None), "name", "")
        action = getattr(briefing, "action", "")
        priority = getattr(briefing, "priority", 0)
        detail_id = f"topic:{getattr(briefing, 'id', '')}"
        if topic == "Golf":
            add("Check the best golf window.", action, priority, detail_id)
        elif topic == "Yankees":
            add(
                "Yankees highlights may be worth catching.", action, priority, detail_id
            )
        elif topic:
            add(f"{topic} has a notable update.", action, priority, detail_id)

    return sorted(actions, key=lambda item: item["priority"], reverse=True)[:5]


def build_portfolio_status_item(financial_attention: Iterable[dict]) -> dict:
    pullback_item = next(
        (
            item
            for item in financial_attention
            if "from cost basis" in item["title"].lower()
        ),
        None,
    )
    if pullback_item:
        title = pullback_item["title"]
        return {
            "title": title if title.endswith(".") else f"{title}.",
            "why_now": "Historically, similar pullbacks have been review moments for large-cap positions.",
            "action": "",
            "priority": 0,
            "detail_id": pullback_item.get("detail_id", ""),
            "category": "opportunity",
            "importance_score": 75,
            "actionability_score": 50,
            "expiration_hours": 72,
            "why_user_cares": "A portfolio holding crossed a pullback review threshold.",
            "classification": "opportunity",
            "source": "portfolio",
        }

    return {
        "title": "No major portfolio actions currently identified.",
        "why_now": "No portfolio event is leading the morning brief.",
        "action": "",
        "priority": 0,
        "detail_id": "",
        "category": "awareness",
        "importance_score": 35,
        "actionability_score": 0,
        "expiration_hours": 168,
        "why_user_cares": "Portfolio thresholds were checked and none require attention.",
        "classification": "awareness",
        "source": "portfolio",
    }


def build_morning_attention_feed(
    attention_groups: Iterable[Iterable[dict]], financial_attention: Iterable[dict]
) -> list[dict]:
    financial_items = [enrich_attention_item(item) for item in financial_attention]
    candidates = sorted(
        [enrich_attention_item(item) for group in attention_groups for item in group]
        + financial_items,
        key=attention_sort_key,
    )

    attention_feed = []
    seen_titles: set[str] = set()
    for item in candidates:
        if item["title"] in seen_titles:
            continue
        seen_titles.add(item["title"])
        attention_feed.append(item)
        if len(attention_feed) >= 10:
            break

    if financial_items:
        return attention_feed

    portfolio_status = enrich_attention_item(
        build_portfolio_status_item(financial_items)
    )
    if portfolio_status["title"] not in seen_titles:
        attention_feed.append(portfolio_status)

    return attention_feed
