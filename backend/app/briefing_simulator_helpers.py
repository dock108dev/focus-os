from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SimulatedScenario:
    name: str
    notes: str
    financial: list[dict]
    topical: list[dict]


def signal(
    title: str,
    why_now: str,
    *,
    category: str,
    source: str,
    topic: str | None = None,
    priority: int = 5,
    importance: int | None = None,
    actionability: int | None = None,
    detail_id: str | None = None,
    story_type: str | None = None,
) -> dict:
    return {
        "title": title,
        "why_now": why_now,
        "action": "",
        "priority": priority,
        "source": source,
        "topic": topic,
        "detail_id": detail_id
        or f"sim:{source}:{title.lower().replace(' ', '-')[:60]}",
        "category": category,
        "importance_score": importance if importance is not None else priority * 10,
        "actionability_score": actionability if actionability is not None else 10,
        "expiration_hours": 72 if category in {"action", "opportunity"} else 168,
        "why_user_cares": why_now,
        "story_type": story_type,
    }


def finance_signal(
    title: str,
    why_now: str,
    *,
    category: str = "action",
    priority: int = 8,
    importance: int = 86,
) -> dict:
    return signal(
        title,
        why_now,
        category=category,
        source="portfolio",
        topic="portfolio",
        priority=priority,
        importance=importance,
        actionability=80 if category == "action" else 54,
        detail_id=f"finance:sim:{title.lower().replace(' ', '-')[:50]}",
        story_type="focusos",
    )

