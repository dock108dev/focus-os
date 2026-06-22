from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Iterable

from .models import Holding
from .personalization import MIKE_PROFILE, large_cap_pullback_reason
from .watch_provenance import provenance_for_attention_item


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
ATTENTION_BUCKETS = {
    "action": "Today",
    "opportunity": "Today",
    "awareness": "Around You",
}
POSTURE_BY_CATEGORY = {
    "action": "Review",
    "opportunity": "Consider",
    "awareness": "Watch",
}
MAX_HOMEPAGE_TOPICS = 7
MIN_HOMEPAGE_TOPICS = 3
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
    suggested_posture: str | None = None,
    attention_section: str | None = None,
    situation: str | None = None,
    why_it_matters: str | None = None,
    what_changed: str | None = None,
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
    next_item["attention_bucket"] = ATTENTION_BUCKETS[resolved_category]
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
    next_item["suggested_posture"] = (
        suggested_posture
        or next_item.get("suggested_posture")
        or POSTURE_BY_CATEGORY[resolved_category]
    )
    next_item["attention_section"] = (
        attention_section
        or next_item.get("attention_section")
        or ATTENTION_BUCKETS[resolved_category]
    )
    next_item["situation"] = (
        situation or next_item.get("situation") or next_item.get("title", "")
    )
    next_item["why_it_matters"] = (
        why_it_matters or next_item.get("why_it_matters") or next_item["why_user_cares"]
    )
    next_item["what_changed"] = (
        what_changed
        or next_item.get("what_changed")
        or "This is appearing because it affects today's attention."
    )
    provenance = provenance_for_attention_item(next_item)
    next_item["source_watch_ids"] = list(
        next_item.get("source_watch_ids") or provenance["source_watch_ids"]
    )
    next_item["triggered_surface_rule"] = (
        next_item.get("triggered_surface_rule")
        or provenance["triggered_surface_rule"]
    )
    next_item["suppressed_by"] = (
        next_item.get("suppressed_by")
        if "suppressed_by" in next_item
        else provenance["suppressed_by"]
    )
    next_item["why_today"] = (
        next_item.get("why_today") or provenance["why_today"] or next_item.get("why_now", "")
    )
    next_item["generation_metadata"] = attention_generation_metadata(next_item)
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


def attention_generation_metadata(item: dict) -> dict:
    expiration_hours = int(item.get("expiration_hours") or 168)
    expiration_days = max(1, int((expiration_hours + 23) / 24))
    existing = item.get("generation_metadata")
    existing_metadata = existing if isinstance(existing, dict) else {}
    return {
        "why_generated": existing_metadata.get("why_generated")
        or item.get("why_now")
        or item.get("title", ""),
        "what_changed": item.get("what_changed")
        or "This is appearing because it affects today's attention.",
        "why_user_should_care": item.get("why_user_cares")
        or item.get("why_it_matters")
        or item.get("why_now")
        or item.get("title", ""),
        "expiration_date": (
            date.today() + timedelta(days=expiration_days)
        ).isoformat(),
    }


def vertical_for_item(item: dict) -> str:
    source = (item.get("source") or "").lower()
    topic = (item.get("topic") or "").lower()
    title = (item.get("title") or "").lower()
    if source == "portfolio" or item.get("detail_id", "").startswith("finance:"):
        return "Portfolio"
    if source == "weather" or topic == "golf":
        return "Life"
    if source == "work" or topic == "work" or "project" in title:
        return "Work"
    if source == "github" or topic == "github":
        return "GitHub"
    if (
        source == "travel"
        or topic == "travel"
        or "flight" in title
        or "vacation" in title
    ):
        return "Travel"
    if topic == "rutgers" or "rutgers" in title:
        return "Rutgers"
    if (
        topic in {"yankees", "major world sports"}
        or "yankees" in title
        or "world cup" in title
    ):
        return "Sports"
    if topic == "iran" or "iran" in title:
        return "World"
    if topic == "ai":
        return "Technology"
    if source in {"crypto", "market"} or topic == "bitcoin":
        return "Markets"
    return "Awareness"


def portfolio_signal_label(item: dict) -> str:
    title = item.get("title", "")
    if "technology allocation" in title.lower():
        return "Technology allocation above target"
    if "cash is available" in title.lower():
        return "Cash available for deployment"
    if "from cost basis" in title.lower():
        return title.replace(" is down ", " drawdown ").replace(" from cost basis", "")
    if "of the portfolio" in title.lower():
        symbol = title.split()[0]
        return f"{symbol} above concentration threshold"
    return title


def portfolio_summary_lines(financial_items: list[dict]) -> list[str]:
    concentration_symbols = [
        item["title"].split()[0]
        for item in financial_items
        if "of the portfolio" in item.get("title", "").lower()
    ]
    pullbacks = [
        item
        for item in financial_items
        if "pullback" in item.get("why_user_cares", "").lower()
        or "from cost basis" in item.get("title", "").lower()
        or "five-day high" in item.get("title", "").lower()
    ]
    lines: list[str] = []
    if any(
        "technology allocation" in item.get("title", "").lower()
        for item in financial_items
    ):
        lines.append("Technology concentration is above target.")
    if concentration_symbols:
        symbols = " and ".join(concentration_symbols[:2])
        overflow = len(concentration_symbols) - 2
        suffix = f" plus {overflow} more" if overflow > 0 else ""
        lines.append(f"{symbols}{suffix} exceed position limits.")
    if any(
        "cash is available" in item.get("title", "").lower() for item in financial_items
    ):
        lines.append("Cash is available for deployment or reserve.")
    if pullbacks:
        label = "opportunity" if len(pullbacks) == 1 else "opportunities"
        lines.append(f"{len(pullbacks)} pullback {label} detected.")
    return lines


def should_include_homepage_item(item: dict) -> bool:
    vertical = item.get("vertical") or vertical_for_item(item)
    category = normalize_attention_category(
        item.get("category") or item.get("classification")
    )
    if vertical == "Markets" and category == "awareness":
        return False
    return True


def apply_attention_engine_fields(item: dict) -> dict:
    next_item = dict(item)
    domain = (
        next_item.get("domain")
        or next_item.get("vertical")
        or vertical_for_item(next_item)
    )
    category = normalize_attention_category(
        next_item.get("category") or next_item.get("classification")
    )
    title = next_item.get("title", "")
    topic = (next_item.get("topic") or "").lower()
    source = (next_item.get("source") or "").lower()

    posture = next_item.get("suggested_posture") or POSTURE_BY_CATEGORY[category]
    if (
        category == "awareness"
        and (topic == "yankees" or "yankees" in title.lower())
        and not any(
            token in title.lower() for token in ("playoff", "clinch", "division")
        )
    ):
        posture = "Ignore"
        next_item["why_now"] = (
            "Good result, but no meaningful change to your posture today."
        )
    elif category == "awareness" and (topic == "yankees" or "yankees" in title.lower()):
        posture = "Watch"
    elif category == "awareness" and domain in {"World", "Technology"}:
        posture = "Watch"
    if domain == "Life":
        next_item["title"] = next_item.get("title", "").replace(
            "is the best golf day this week",
            "is likely your best golf window this week",
        )

    story_type = next_item.get("story_type")
    if not story_type:
        story_type = "focusos" if domain in {"Portfolio", "Life"} else "external"

    section = next_item.get("attention_section")
    if not section:
        if category in {"action", "opportunity"}:
            section = "Today"
        elif posture == "Ignore" or domain == "World":
            section = "Background"
        else:
            section = "Around You"
    elif category == "awareness" and domain == "World":
        section = "Background"

    why_it_matters = (
        next_item.get("why_it_matters")
        or next_item.get("why_user_cares")
        or next_item.get("why_now", "")
    )
    what_changed = next_item.get("what_changed")
    if not what_changed:
        if domain == "Life":
            what_changed = "The forecast created a better planning window than the rest of the week."
        elif next_item.get("novelty_reason"):
            what_changed = next_item["novelty_reason"]
        elif source == "weather":
            what_changed = "The forecast created a better planning window than the rest of the week."
        elif posture == "Ignore":
            what_changed = (
                "This is relevant context, but it does not change your posture today."
            )
        else:
            what_changed = (
                "This is appearing because it may shape what stays on your radar today."
            )

    next_item.update(
        {
            "domain": domain,
            "vertical": domain,
            "suggested_posture": posture,
            "story_type": story_type,
            "attention_section": section,
            "attention_bucket": section,
            "situation": next_item.get("situation") or title,
            "why_it_matters": why_it_matters,
            "what_changed": what_changed,
        }
    )
    next_item["generation_metadata"] = attention_generation_metadata(next_item)
    return next_item


def build_portfolio_review_item(financial_attention: Iterable[dict]) -> dict:
    financial_items = sorted(
        [enrich_attention_item(item) for item in financial_attention],
        key=attention_sort_key,
    )
    if not financial_items:
        return enrich_attention_item(build_portfolio_status_item([]))

    action_count = sum(1 for item in financial_items if item["category"] == "action")
    opportunity_count = sum(
        1 for item in financial_items if item["category"] == "opportunity"
    )
    category = "action" if action_count else "opportunity"
    title = (
        "Review portfolio positioning"
        if action_count
        else "Portfolio opportunity window is open"
    )
    lines = portfolio_summary_lines(financial_items)
    why_now = f"{len(financial_items)} portfolio signals crossed review thresholds."
    if lines:
        why_now = f"{why_now} {' '.join(lines[:3])}"
    if opportunity_count and action_count:
        why_now += (
            f" {opportunity_count} are opportunities, not separate homepage stories."
        )

    return enrich_attention_item(
        {
            "title": title,
            "why_now": why_now,
            "action": "",
            "priority": max(int(item.get("priority") or 0) for item in financial_items),
            "detail_id": "portfolio:review",
            "source": "portfolio",
            "vertical": "Portfolio",
            "domain": "Portfolio",
            "signal_count": len(financial_items),
            "signals": financial_items,
            "change_summary": lines,
            "situation": "Portfolio positioning needs attention.",
            "why_it_matters": "Your portfolio has concentration, cash, and pullback signals that can affect near-term allocation decisions.",
            "what_changed": "Multiple review thresholds are active at the same time, so the portfolio belongs on your radar as one situation.",
            "suggested_posture": "Review",
            "attention_section": "Today",
        },
        category=category,
        importance_score=max(
            int(item.get("importance_score") or 0) for item in financial_items
        ),
        actionability_score=max(
            int(item.get("actionability_score") or 0) for item in financial_items
        ),
        expiration_hours=min(
            int(item.get("expiration_hours") or 168) for item in financial_items
        ),
        why_user_cares="Portfolio thresholds are grouped so persistent state does not crowd out the rest of the briefing.",
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
    grouped_items = [
        enrich_attention_item(item) for group in attention_groups for item in group
    ]
    portfolio_related = [
        item
        for item in grouped_items
        if (item.get("source") or "").lower() in {"market", "crypto"}
        and normalize_attention_category(
            item.get("category") or item.get("classification")
        )
        in {"action", "opportunity"}
    ]
    non_portfolio_items = [
        item for item in grouped_items if item not in portfolio_related
    ] if financial_items else grouped_items
    portfolio_item = (
        build_portfolio_review_item(financial_items + portfolio_related)
        if financial_items
        else None
    )
    candidates = sorted(
        [
            apply_attention_engine_fields(
                {**enrich_attention_item(item), "vertical": vertical_for_item(item)}
            )
            for item in non_portfolio_items
            if should_include_homepage_item(
                {**enrich_attention_item(item), "vertical": vertical_for_item(item)}
            )
        ]
        + ([apply_attention_engine_fields(portfolio_item)] if portfolio_item else []),
        key=attention_sort_key,
    )

    attention_feed = []
    seen_titles: set[str] = set()
    seen_verticals: set[str] = set()
    for item in candidates:
        vertical = item.get("vertical") or vertical_for_item(item)
        if item["title"] in seen_titles or vertical in seen_verticals:
            continue
        seen_titles.add(item["title"])
        seen_verticals.add(vertical)
        item["vertical"] = vertical
        item["domain"] = vertical
        item = apply_attention_engine_fields(item)
        attention_feed.append(item)
        if len(attention_feed) >= MAX_HOMEPAGE_TOPICS:
            break

    return attention_feed


def homepage_scan_violations(items: list[dict]) -> list[str]:
    violations: list[str] = []
    if len(items) < MIN_HOMEPAGE_TOPICS or len(items) > MAX_HOMEPAGE_TOPICS:
        violations.append(
            f"Homepage story count must be {MIN_HOMEPAGE_TOPICS}-{MAX_HOMEPAGE_TOPICS}; got {len(items)}."
        )
    domains = [
        item.get("domain") or item.get("vertical") or vertical_for_item(item)
        for item in items
    ]
    duplicate_domains = sorted(
        {domain for domain in domains if domains.count(domain) > 1}
    )
    if duplicate_domains:
        violations.append(
            f"Homepage has more than one story for: {', '.join(duplicate_domains)}."
        )
    unclear = [
        item.get("title", "Untitled")
        for item in items
        if not item.get("why_now") or len(str(item.get("why_now"))) < 24
    ]
    if unclear:
        violations.append(
            f"Homepage stories need self-contained recommendations: {', '.join(unclear)}."
        )
    return violations


def assistant_item(item: dict) -> dict:
    return {
        "title": item.get("title", ""),
        "summary": item.get("why_now", ""),
        "detail_id": item.get("detail_id", ""),
        "domain": item.get("domain") or item.get("vertical") or vertical_for_item(item),
        "category": normalize_attention_category(
            item.get("category") or item.get("classification")
        ),
        "importance_score": int(item.get("importance_score") or 0),
        "story_type": item.get("story_type", "external"),
        "source_watch_ids": list(item.get("source_watch_ids") or []),
        "triggered_surface_rule": item.get("triggered_surface_rule") or "",
        "suppressed_by": item.get("suppressed_by"),
        "why_today": item.get("why_today") or item.get("why_now", ""),
        "watch_kind": item.get("watch_kind"),
        "watch_priority": item.get("watch_priority"),
    }


def assistant_item_key(item: dict) -> str:
    detail_id = str(item.get("detail_id") or "")
    if detail_id:
        return detail_id
    title = str(item.get("title") or "")
    domain = str(item.get("domain") or item.get("vertical") or "")
    return f"{domain}:{title}"


def is_catch_up_item(item: dict) -> bool:
    if item.get("attention_section") == "Catch Up":
        return True
    if item.get("attention_bucket") == "Catch Up":
        return True
    return item.get("suggested_posture") == "Catch Up"


def is_quiet_attention_item(item: dict) -> bool:
    title = item.get("title", "").lower()
    if title.startswith("no major portfolio"):
        return True
    if item.get("suggested_posture") == "Ignore":
        return True
    return int(item.get("importance_score") or 0) < 72


def build_assistant_briefing(
    attention: Iterable[dict], watch_status: Iterable[dict] | None = None
) -> dict:
    items = list(attention)
    catch_up_items = [item for item in items if is_catch_up_item(item)]
    needs_attention_items = [
        item
        for item in items
        if not is_catch_up_item(item)
        and (
            normalize_attention_category(
                item.get("category") or item.get("classification")
            )
            == "action"
            or item.get("suggested_posture") in {"Act", "Review"}
        )
    ]
    catch_up_keys = {assistant_item_key(item) for item in catch_up_items}
    needs_attention_keys = {assistant_item_key(item) for item in needs_attention_items}
    watch_only_items = [
        item
        for item in items
        if assistant_item_key(item) not in needs_attention_keys
        and assistant_item_key(item) not in catch_up_keys
        and not is_quiet_attention_item(item)
    ]
    quiet_attention_items = [
        item
        for item in items
        if assistant_item_key(item) not in catch_up_keys
        and is_quiet_attention_item(item)
    ]
    quiet_watch_items = [
        {
            "title": row.get("title", "Watch"),
            "summary": row.get(
                "summary", "No material change reached the briefing threshold today."
            ),
            "detail_id": row.get("detail_id", ""),
            "domain": row.get("domain", "Watchlist"),
            "category": "awareness",
            "importance_score": 0,
            "story_type": "focusos",
            "source_watch_ids": row.get("source_watch_ids", []),
            "triggered_surface_rule": "",
            "suppressed_by": row.get(
                "suppression_rule",
                "No material change reached the briefing threshold today.",
            ),
            "why_today": row.get(
                "summary", "No material change reached the briefing threshold today."
            ),
            "watch_kind": row.get("watch_kind"),
            "watch_priority": row.get("priority"),
        }
        for row in list(watch_status or [])
        if not row.get("should_surface")
    ][:8]
    meaningful = [
        item
        for item in items
        if normalize_attention_category(
            item.get("category") or item.get("classification")
        )
        == "action"
        or (not is_catch_up_item(item) and not is_quiet_attention_item(item))
    ]
    primary_source = meaningful[0] if meaningful else None
    primary_score = (
        int(primary_source.get("importance_score") or 0) if primary_source else 0
    )
    has_primary = primary_source is not None and (
        primary_score >= 80
        or normalize_attention_category(
            primary_source.get("category") or primary_source.get("classification")
        )
        == "action"
    )

    if has_primary:
        primary_focus = assistant_item(primary_source)
        primary_key = assistant_item_key(primary_source)
        mode = "focused"
        secondary_candidates = [
            item for item in items if assistant_item_key(item) != primary_key
        ]
        needs_attention_items = [
            item
            for item in needs_attention_items
            if assistant_item_key(item) != primary_key
        ]
        watch_only_items = [
            item
            for item in watch_only_items
            if assistant_item_key(item) != primary_key
        ]
        catch_up_items = [
            item for item in catch_up_items if assistant_item_key(item) != primary_key
        ]
        quiet_attention_items = [
            item
            for item in quiet_attention_items
            if assistant_item_key(item) != primary_key
        ]
    else:
        primary_focus = {
            "title": "No single focus today",
            "summary": "Nothing is strong enough to dominate the morning. Skim the notes and keep moving.",
            "detail_id": "",
            "domain": "FocusOS",
            "category": "awareness",
            "importance_score": 0,
            "story_type": "focusos",
            "source_watch_ids": [],
            "triggered_surface_rule": "",
            "suppressed_by": None,
            "why_today": "No item met the primary-focus threshold.",
        }
        mode = "quiet"
        primary_key = ""
        secondary_candidates = items

    secondary_notes = [
        assistant_item(item)
        for item in secondary_candidates
        if not (
            item.get("title", "").lower().startswith("no major portfolio")
            and len(secondary_candidates) > 3
        )
    ][:3]

    return {
        "greeting": "Good Morning Mike",
        "mode": mode,
        "primary_focus": primary_focus,
        "secondary_notes": secondary_notes,
        "needs_attention": [assistant_item(item) for item in needs_attention_items],
        "watch_only": [assistant_item(item) for item in watch_only_items],
        "catch_up": [assistant_item(item) for item in catch_up_items],
        "quiet": [assistant_item(item) for item in quiet_attention_items][:4]
        + quiet_watch_items,
        "watch_status": list(watch_status or []),
    }
