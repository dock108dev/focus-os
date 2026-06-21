from __future__ import annotations

import hashlib
import json
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import DisplayedStory


def story_key(item: dict) -> str:
    domain = item.get("vertical") or item.get("source") or "unknown"
    detail_id = item.get("detail_id") or item.get("title") or "untitled"
    return f"{domain}:{detail_id}".lower()


def story_fingerprint(item: dict) -> str:
    payload = {
        "title": item.get("title"),
        "summary": item.get("why_now"),
        "category": item.get("category"),
        "signals": [
            {
                "title": signal.get("title"),
                "category": signal.get("category"),
                "importance_score": signal.get("importance_score"),
            }
            for signal in item.get("signals", [])
        ],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def apply_novelty(
    db: Session, items: list[dict], today: date | None = None
) -> list[dict]:
    current_day = today or date.today()
    enriched: list[dict] = []
    for item in items:
        key = story_key(item)
        fingerprint = story_fingerprint(item)
        previous = db.scalar(
            select(DisplayedStory).where(DisplayedStory.story_key == key)
        )
        next_item = dict(item)
        next_item["story_key"] = key
        next_item["novelty_fingerprint"] = fingerprint
        if not previous:
            next_item["novelty_status"] = "new"
            next_item["novelty_reason"] = "This story has not appeared before."
            next_item["what_changed"] = (
                next_item.get("what_changed") or next_item["novelty_reason"]
            )
        elif previous.fingerprint != fingerprint:
            next_item["novelty_status"] = "changed"
            next_item["novelty_reason"] = "The story changed since it was last shown."
            next_item["what_changed"] = next_item["novelty_reason"]
        elif previous.last_seen_on < current_day:
            next_item["novelty_status"] = "repeated"
            next_item["novelty_reason"] = (
                "This appears again because the condition is still active."
            )
            next_item["what_changed"] = next_item["novelty_reason"]
            if next_item.get("category") == "awareness":
                next_item["importance_score"] = max(
                    0, int(next_item.get("importance_score") or 0) - 20
                )
        else:
            next_item["novelty_status"] = "seen_today"
            next_item["novelty_reason"] = "This was already shown today."
            next_item["what_changed"] = (
                next_item.get("what_changed") or next_item["novelty_reason"]
            )
        enriched.append(next_item)
    return enriched


def record_displayed_stories(
    db: Session, items: list[dict], today: date | None = None
) -> None:
    current_day = today or date.today()
    for item in items:
        key = item.get("story_key") or story_key(item)
        fingerprint = item.get("novelty_fingerprint") or story_fingerprint(item)
        row = db.scalar(select(DisplayedStory).where(DisplayedStory.story_key == key))
        if row:
            row.domain = item.get("vertical") or item.get("source") or row.domain
            row.category = item.get("category") or row.category
            row.title = item.get("title") or row.title
            row.fingerprint = fingerprint
            row.last_seen_on = current_day
            row.seen_count += 1
        else:
            db.add(
                DisplayedStory(
                    story_key=key,
                    domain=item.get("vertical") or item.get("source") or "unknown",
                    category=item.get("category") or "awareness",
                    title=item.get("title") or "",
                    fingerprint=fingerprint,
                    first_seen_on=current_day,
                    last_seen_on=current_day,
                    seen_count=1,
                )
            )
    db.commit()
