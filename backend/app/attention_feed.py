from __future__ import annotations

from typing import Iterable

from .attention_core import (
    MAX_HOMEPAGE_TOPICS,
    MIN_HOMEPAGE_TOPICS,
    apply_attention_engine_fields,
    attention_sort_key,
    enrich_attention_item,
    normalize_attention_category,
    portfolio_summary_lines,
    should_include_homepage_item,
    vertical_for_item,
)


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
