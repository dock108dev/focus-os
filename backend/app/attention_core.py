from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from .watch_provenance import provenance_for_attention_item


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

