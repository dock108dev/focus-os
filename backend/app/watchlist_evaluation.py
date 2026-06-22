from __future__ import annotations

from datetime import date
from typing import Iterable

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .attention import enrich_attention_item
from .models import WatchEvaluation, WatchItem
from .watch_provenance import source_watch_id
from .watchlist_parsing import infer_watch_kind, watch_domain
from .watchlist_rules import DEFAULT_WATCH_FOR, WATCH_KINDS
from .watchlist_store import latest_watch_evaluation

def archive_expired_watch_items(db: Session, today: date | None = None) -> int:
    today = today or date.today()
    rows = list(
        db.scalars(
            select(WatchItem).where(
                WatchItem.status == "active",
                WatchItem.expires_at.is_not(None),
                WatchItem.expires_at < today,
            )
        ).all()
    )
    for row in rows:
        row.status = "archived"
    if rows:
        db.commit()
    return len(rows)


def planning_dimensions(row: WatchItem) -> str:
    dimensions = row.watch_for or DEFAULT_WATCH_FOR
    if len(dimensions) == 1:
        return dimensions[0]
    return ", ".join(dimensions[:-1]) + f", and {dimensions[-1]}"


def quiet_summary_for_watch(row: WatchItem) -> str:
    title = row.title.lower()
    if "bitcoin" in title:
        return "No BTC accumulation trigger today. Price movement did not meet the review rule."
    if "trading systems" in title:
        return "No trading-system action. Liquidity still keeps this on hold."
    if "side project" in title or "focusos validation" in title:
        return "No project changed ship-or-stop posture today."
    if "big tech" in title or "ai, and major company" in title:
        return "No major tech release changed your workflow today."
    if "sports radar" in title:
        return "No major game, injury, playoff, or spoiler-safe recap item found."
    if "golf weather" in title:
        return "No better local golf window than the current watch-only item."
    if "shopping" in title:
        return "No saved shopping interest produced a high-confidence match."
    if "media" in title or "watchlist radar" in title:
        return "No saved media interest produced a high-confidence match."
    if "life notes" in title:
        return "No dated reminder entered its action window."
    if "personal finance" in title:
        return "No liquidity or portfolio threshold crossed today."
    if "investing ideas" in title or "market pullbacks" in title:
        return "No tracked market move changed the review posture today."
    if row.event_date:
        days_until = (row.event_date - date.today()).days
        if days_until >= 0:
            return f"{days_until} days away. No planning trigger has opened yet."
        return "Event has passed with no recap item needed."
    return "No material change reached the briefing threshold today."


def evaluate_watch_item(row: WatchItem, today: date | None = None) -> dict:
    today = today or date.today()
    domain = watch_domain(row.title, row.watch_for or [])
    inferred_kind = infer_watch_kind(row.title, row.watch_for or [])
    watch_kind = row.watch_kind if row.watch_kind in WATCH_KINDS else inferred_kind
    evidence = {
        "watch_kind": watch_kind,
        "priority": row.priority,
        "watch_for": row.watch_for or [],
        "personal_state": row.personal_state or {},
        "external_state": row.external_state or {},
        "personal_context": row.personal_context or {},
        "source_config": row.source_config or {},
        "evaluation_rules": row.evaluation_rules or {},
        "surface_when": row.surface_when or [],
        "event_date": row.event_date.isoformat() if row.event_date else None,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        "domain": domain,
    }

    if row.event_date is None:
        return {
            "title": row.title,
            "summary": "No dated trigger has made this watch item briefing-worthy yet.",
            "category": "awareness",
            "importance_score": 30,
            "actionability_score": 0,
            "should_surface": False,
            "trigger_reason": "Waiting for a material update or dated decision point.",
            "evidence": evidence,
        }

    days_until = (row.event_date - today).days
    evidence["days_until_event"] = days_until

    if days_until < 0:
        days_since = abs(days_until)
        if days_since <= 1 and "summary" in (row.watch_for or []):
            return {
                "title": f"{row.title} happened yesterday",
                "summary": "A recap would now save effort, so this watch item should turn into a summary request.",
                "category": "awareness",
                "importance_score": 72,
                "actionability_score": 20,
                "should_surface": True,
                "trigger_reason": "The watched event has passed and the item asked for a useful summary.",
                "evidence": evidence,
            }
        return {
            "title": row.title,
            "summary": "The watched event has passed and no further update is needed.",
            "category": "awareness",
            "importance_score": 20,
            "actionability_score": 0,
            "should_surface": False,
            "trigger_reason": "Event has passed without a summary trigger.",
            "evidence": evidence,
        }

    if days_until == 0:
        return {
            "title": f"{row.title} is today",
            "summary": f"Check {planning_dimensions(row)} now because the watched event is inside today's decision window.",
            "category": "action",
            "importance_score": 90,
            "actionability_score": 82,
            "should_surface": True,
            "trigger_reason": "The watched event is today.",
            "evidence": evidence,
        }

    if days_until == 1:
        return {
            "title": f"{row.title} is tomorrow",
            "summary": f"Planning details are close enough to matter. Check {planning_dimensions(row)} before the window closes.",
            "category": "action",
            "importance_score": 84,
            "actionability_score": 74,
            "should_surface": True,
            "trigger_reason": "The watched event is one day away.",
            "evidence": evidence,
        }

    if 2 <= days_until <= 5:
        return {
            "title": f"{row.title} planning is starting to matter",
            "summary": f"The decision window is opening. Monitor {planning_dimensions(row)} now so this does not become last-minute.",
            "category": "opportunity",
            "importance_score": 76,
            "actionability_score": 56,
            "should_surface": True,
            "trigger_reason": "The watched event entered its planning window.",
            "evidence": evidence,
        }

    if days_until <= 7 and domain == "Technology":
        return {
            "title": f"{row.title} is coming up",
            "summary": "This is close enough to watch for agenda, timing, and post-event summary value.",
            "category": "awareness",
            "importance_score": 64,
            "actionability_score": 16,
            "should_surface": True,
            "trigger_reason": "A watched technology event is within a week.",
            "evidence": evidence,
        }

    return {
        "title": row.title,
        "summary": "The watch item is active, but it is not close enough or changed enough to brief today.",
        "category": "awareness",
        "importance_score": 30,
        "actionability_score": 0,
        "should_surface": False,
        "trigger_reason": "No meaningful update today.",
        "evidence": evidence,
    }


def evaluate_active_watch_items(
    db: Session, today: date | None = None
) -> list[WatchEvaluation]:
    today = today or date.today()
    archive_expired_watch_items(db, today=today)
    rows = list(
        db.scalars(
            select(WatchItem)
            .where(WatchItem.status == "active", WatchItem.enabled.is_(True))
            .order_by(WatchItem.created_at, WatchItem.id)
        ).all()
    )
    evaluations: list[WatchEvaluation] = []
    for row in rows:
        if row.last_evaluated_on == today:
            latest = latest_watch_evaluation(db, row.id)
            if latest:
                evaluations.append(latest)
            continue
        result = evaluate_watch_item(row, today=today)
        db.execute(
            delete(WatchEvaluation).where(
                WatchEvaluation.watch_item_id == row.id,
                WatchEvaluation.as_of == today,
            )
        )
        evaluation = WatchEvaluation(watch_item_id=row.id, as_of=today, **result)
        row.last_evaluated_on = today
        db.add(evaluation)
        evaluations.append(evaluation)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return list(
            db.scalars(
                select(WatchEvaluation)
                .join(WatchItem)
                .where(
                    WatchEvaluation.as_of == today,
                    WatchItem.status == "active",
                    WatchItem.enabled.is_(True),
                )
                .order_by(WatchEvaluation.id)
            ).all()
        )
    for evaluation in evaluations:
        db.refresh(evaluation)
    return evaluations


def surfaced_watch_evaluations(
    db: Session, today: date | None = None
) -> list[WatchEvaluation]:
    today = today or date.today()
    return list(
        db.scalars(
            select(WatchEvaluation)
            .where(
                WatchEvaluation.as_of == today,
                WatchEvaluation.should_surface.is_(True),
            )
            .order_by(
                WatchEvaluation.importance_score.desc(),
                WatchEvaluation.actionability_score.desc(),
                WatchEvaluation.id,
            )
        ).all()
    )


def active_watch_status(db: Session) -> list[dict]:
    rows = list(
        db.scalars(
            select(WatchItem)
            .where(WatchItem.status == "active", WatchItem.enabled.is_(True))
            .order_by(
                WatchItem.expires_at.is_(None),
                WatchItem.expires_at,
                WatchItem.created_at,
            )
        ).all()
    )
    statuses: list[dict] = []
    for row in rows:
        latest = latest_watch_evaluation(db, row.id)
        if latest and latest.should_surface:
            summary = latest.trigger_reason
        else:
            summary = quiet_summary_for_watch(row)
        statuses.append(
            {
                "id": row.id,
                "title": row.title,
                "summary": summary,
                "status": row.status,
                "watch_kind": row.watch_kind,
                "priority": row.priority,
                "domain": watch_domain(row.title, row.watch_for or []),
                "should_surface": bool(latest and latest.should_surface),
                "source_watch_ids": [source_watch_id(row.title)],
                "suppression_rule": (
                    "No material update today."
                    if not (latest and latest.should_surface)
                    else None
                ),
                "event_date": row.event_date.isoformat() if row.event_date else None,
                "detail_id": f"watch:{row.id}",
            }
        )
    return statuses[:5]


def watch_attention_items(evaluations: Iterable[WatchEvaluation]) -> list[dict]:
    items = []
    for row in evaluations:
        watch = row.watch_item
        domain = (
            watch_domain(watch.title, watch.watch_for or []) if watch else "Watchlist"
        )
        items.append(
            enrich_attention_item(
                {
                    "title": row.title,
                    "why_now": row.summary,
                    "action": "",
                    "priority": max(1, round(row.importance_score / 10)),
                    "detail_id": f"watch:{row.watch_item_id}",
                    "source": "watchlist",
                    "topic": "watchlist",
                    "domain": domain,
                    "vertical": domain,
                    "story_type": "focusos",
                    "suggested_posture": "Watch",
                    "attention_section": (
                        "Today"
                        if row.category in {"action", "opportunity"}
                        else "Around You"
                    ),
                    "situation": row.title,
                    "why_it_matters": row.trigger_reason,
                    "what_changed": row.trigger_reason,
                    "source_watch_ids": [f"watch:{row.watch_item_id}"],
                    "triggered_surface_rule": row.trigger_reason,
                    "suppressed_by": None,
                    "why_today": row.summary,
                    "watch_kind": watch.watch_kind if watch else None,
                    "watch_priority": watch.priority if watch else None,
                },
                category=row.category,
                importance_score=row.importance_score,
                actionability_score=row.actionability_score,
                expiration_hours=24 if row.category == "action" else 72,
                why_user_cares=row.trigger_reason,
            )
        )
    return items
