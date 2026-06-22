from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Iterable

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .attention import enrich_attention_item
from .models import WatchEvaluation, WatchItem


DEFAULT_SURFACE_WHEN = [
    "risk changed materially",
    "decision deadline is near",
    "summary would save user effort",
]
DEFAULT_SUPPRESS_WHEN = [
    "generic reminders",
    "unchanged source data",
    "filler that only says the watched object is coming up",
]
DEFAULT_WATCH_FOR = ["timing", "schedule changes"]
SOURCE_HINTS = {
    "weather": "weather",
    "parking": "parking feed",
    "traffic": "maps or transit",
    "timing": "calendar",
    "schedule changes": "calendar or venue/source update",
    "summary": "post-event sources",
    "developer tooling": "developer docs",
    "ai": "vendor changelog",
}
WATCH_KEYWORDS = {
    "weather": {"weather", "rain", "temperature", "forecast"},
    "parking": {"parking", "drive"},
    "traffic": {"traffic", "transit", "train", "airport", "flight"},
    "timing": {"time", "timing", "door", "doors", "starts", "keynote", "kickoff"},
    "schedule changes": {"schedule", "changes", "delay", "postponed", "policy"},
    "summary": {"summarize", "summary", "announcements", "takeaways", "recap"},
    "developer tooling": {"xcode", "developer", "tooling", "api", "sdk"},
    "ai": {"ai", "siri", "model"},
}
WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def clean_title(value: str) -> str:
    for line in value.splitlines():
        text = line.strip(" -\t")
        if text:
            first_sentence = re.split(r"[.!?]", text, maxsplit=1)[0].strip()
            return first_sentence[:120] or "Watch item"
    return "Watch item"


def extract_event_date(text: str, today: date | None = None) -> date | None:
    today = today or date.today()
    lower = text.lower()

    iso_match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
    if iso_match:
        return date.fromisoformat(iso_match.group(1))

    in_days = re.search(r"\bin\s+(\d{1,2})\s+days?\b", lower)
    if in_days:
        return today + timedelta(days=int(in_days.group(1)))

    if "tomorrow" in lower:
        return today + timedelta(days=1)
    if "today" in lower:
        return today

    for name, weekday in WEEKDAYS.items():
        if re.search(rf"\b{name}\b", lower):
            delta = (weekday - today.weekday()) % 7
            return today + timedelta(days=delta or 7)
    return None


def extract_watch_for(text: str) -> list[str]:
    lower_words = set(re.findall(r"[a-z0-9]+", text.lower()))
    found = [
        label
        for label, keywords in WATCH_KEYWORDS.items()
        if lower_words.intersection(keywords)
    ]
    if "weather" in found and "traffic" not in found and "parking" in found:
        found.append("traffic")
    return found or list(DEFAULT_WATCH_FOR)


def watch_domain(title: str, watch_for: Iterable[str]) -> str:
    lower = title.lower()
    dimensions = set(watch_for)
    if "rutgers" in lower:
        return "Rutgers"
    if any(token in lower for token in ("wwdc", "apple", "xcode", "siri")):
        return "Technology"
    if any(token in lower for token in ("flight", "vacation", "airport", "hotel")):
        return "Travel"
    if any(token in lower for token in ("project", "deadline", "work")):
        return "Work"
    if dimensions.intersection({"weather", "parking", "traffic"}):
        return "Life"
    return "Watchlist"


def source_inputs_for(watch_for: Iterable[str]) -> list[str]:
    sources = [
        SOURCE_HINTS[dimension]
        for dimension in watch_for
        if dimension in SOURCE_HINTS
    ]
    return list(dict.fromkeys(sources or ["user-provided watch config"]))


def suppression_rules_for(row: WatchItem) -> list[str]:
    rules = list(DEFAULT_SUPPRESS_WHEN)
    surface_rules = row.surface_when or []
    if surface_rules:
        rules.append("inputs that do not meet configured surface rules")
    return rules


def parse_watch_item(text: str, today: date | None = None) -> dict:
    today = today or date.today()
    title = clean_title(text)
    event_date = extract_event_date(text, today)
    expires_at = (
        event_date + timedelta(days=1) if event_date else today + timedelta(days=30)
    )
    watch_for = extract_watch_for(text)
    return {
        "title": title,
        "original_text": text.strip(),
        "event_date": event_date,
        "expires_at": expires_at,
        "check_frequency": "daily",
        "watch_for": watch_for,
        "surface_when": list(DEFAULT_SURFACE_WHEN),
        "briefing_posture": "watch",
        "status": "active",
    }


def create_watch_item(db: Session, text: str, today: date | None = None) -> WatchItem:
    if not text.strip():
        raise ValueError("Watch text is required.")
    row = WatchItem(**parse_watch_item(text, today=today))
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_watch_item(
    db: Session,
    row: WatchItem,
    *,
    text: str | None = None,
    title: str | None = None,
    original_text: str | None = None,
    event_date: date | None = None,
    expires_at: date | None = None,
    check_frequency: str | None = None,
    watch_for: list[str] | None = None,
    surface_when: list[str] | None = None,
    status: str | None = None,
    today: date | None = None,
) -> WatchItem:
    if text is not None:
        if not text.strip():
            raise ValueError("Watch text is required.")
        parsed = parse_watch_item(text, today=today)
        for key, value in parsed.items():
            setattr(row, key, value)

    if title is not None:
        cleaned = clean_title(title)
        if not cleaned:
            raise ValueError("Watch title is required.")
        row.title = cleaned
    if original_text is not None:
        row.original_text = original_text.strip()
    if event_date is not None:
        row.event_date = event_date
    if expires_at is not None:
        row.expires_at = expires_at
    if check_frequency is not None:
        row.check_frequency = check_frequency.strip() or "daily"
    if watch_for is not None:
        row.watch_for = [item.strip() for item in watch_for if item.strip()]
    if surface_when is not None:
        row.surface_when = [item.strip() for item in surface_when if item.strip()]
    if status is not None:
        if status not in {"active", "completed", "archived"}:
            raise ValueError("Watch status must be active, completed, or archived.")
        row.status = status

    row.last_evaluated_on = None
    db.commit()
    db.refresh(row)
    return row


def set_watch_item_status(db: Session, row: WatchItem, status: str) -> WatchItem:
    return update_watch_item(db, row, status=status)


def remove_watch_item(db: Session, row: WatchItem) -> None:
    db.execute(delete(WatchEvaluation).where(WatchEvaluation.watch_item_id == row.id))
    db.delete(row)
    db.commit()


def watch_counts(db: Session) -> dict:
    rows = db.execute(
        select(WatchItem.status, func.count(WatchItem.id)).group_by(WatchItem.status)
    ).all()
    counts = {"active": 0, "completed": 0, "archived": 0, "total": 0}
    for status, count in rows:
        key = status if status in counts else "archived"
        counts[key] += count
        counts["total"] += count
    return counts


def serialize_watch_item(row: WatchItem, latest: WatchEvaluation | None = None) -> dict:
    watch_for = row.watch_for or []
    surface_when = row.surface_when or []
    return {
        "id": row.id,
        "title": row.title,
        "original_text": row.original_text,
        "event_date": row.event_date.isoformat() if row.event_date else None,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        "check_frequency": row.check_frequency,
        "watch_for": watch_for,
        "conditions": watch_for,
        "source_inputs": source_inputs_for(watch_for),
        "cadence": row.check_frequency,
        "surface_when": surface_when,
        "surface_rules": surface_when,
        "suppression_rules": suppression_rules_for(row),
        "briefing_posture": row.briefing_posture,
        "preferred_output": row.briefing_posture,
        "status": row.status,
        "last_evaluated_on": (
            row.last_evaluated_on.isoformat() if row.last_evaluated_on else None
        ),
        "latest_evaluation": serialize_watch_evaluation(latest) if latest else None,
        "why_today": latest.trigger_reason if latest else None,
    }


def serialize_watch_evaluation(row: WatchEvaluation) -> dict:
    return {
        "id": row.id,
        "watch_item_id": row.watch_item_id,
        "as_of": row.as_of.isoformat(),
        "title": row.title,
        "summary": row.summary,
        "category": row.category,
        "importance_score": row.importance_score,
        "actionability_score": row.actionability_score,
        "should_surface": row.should_surface,
        "trigger_reason": row.trigger_reason,
        "evidence": row.evidence or {},
        "generation_metadata": {
            "why_generated": row.trigger_reason,
            "what_changed": row.summary,
            "why_user_should_care": row.trigger_reason,
            "expiration_date": (
                row.as_of + timedelta(days=1 if row.category == "action" else 3)
            ).isoformat(),
        },
    }


def latest_watch_evaluation(db: Session, item_id: int) -> WatchEvaluation | None:
    return db.scalar(
        select(WatchEvaluation)
        .where(WatchEvaluation.watch_item_id == item_id)
        .order_by(WatchEvaluation.as_of.desc(), WatchEvaluation.created_at.desc())
        .limit(1)
    )


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


def evaluate_watch_item(row: WatchItem, today: date | None = None) -> dict:
    today = today or date.today()
    domain = watch_domain(row.title, row.watch_for or [])
    evidence = {
        "watch_for": row.watch_for or [],
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
            .where(WatchItem.status == "active")
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
    db.commit()
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
            .where(WatchItem.status == "active")
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
        elif row.event_date:
            days_until = (row.event_date - date.today()).days
            summary = (
                f"{days_until} days away. Watching {planning_dimensions(row)}."
                if days_until >= 0
                else "Event has passed; waiting for archive cleanup."
            )
        else:
            summary = f"Watching {planning_dimensions(row)}."
        statuses.append(
            {
                "id": row.id,
                "title": row.title,
                "summary": summary,
                "status": row.status,
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
                },
                category=row.category,
                importance_score=row.importance_score,
                actionability_score=row.actionability_score,
                expiration_hours=24 if row.category == "action" else 72,
                why_user_cares=row.trigger_reason,
            )
        )
    return items
