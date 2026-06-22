from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import date
from typing import Iterable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .attention import enrich_attention_item
from .models import Topic, TopicBriefing
from .source_status import record_source_status
from .topic_defaults import DEFAULT_TOPICS
from .topic_fallbacks import fallback_payload
from .topic_providers import (
    AI_PROVIDER_EXCEPTIONS,
    AIProviderConfigurationError as AIProviderConfigurationError,
    generate_ai_payload as generate_ai_payload,
    parse_ai_payload as parse_ai_payload,
    provider_error_message,
)
from .voice import clean_action_text, clean_editorial_text


logger = logging.getLogger(__name__)
SPORTS_CATCH_UP_TOPICS = {
    "cowboys",
    "f1",
    "major world sports",
    "pga",
    "rutgers",
    "yankees",
}



@dataclass(frozen=True)
class TopicGenerationError:
    topic: str
    provider: str
    error_type: str
    message: str



def seed_topics_if_empty(db: Session) -> None:
    has_topic = db.scalar(select(Topic.id).limit(1))
    if has_topic:
        return
    db.add_all([Topic(**row) for row in DEFAULT_TOPICS])
    db.commit()



def generate_topic_briefing(
    topic: Topic, errors: list[TopicGenerationError] | None = None
) -> TopicBriefing:
    provider = os.getenv(
        "AI_PROVIDER", "openai" if os.getenv("OPENAI_API_KEY") else "fallback"
    ).lower()
    try:
        payload = generate_ai_payload(topic) or fallback_payload(topic)
    except AI_PROVIDER_EXCEPTIONS as exc:
        logger.warning(
            "topic_briefing_provider_failed",
            exc_info=True,
            extra={"topic": topic.name, "provider": provider},
        )
        if errors is not None:
            errors.append(
                TopicGenerationError(
                    topic=topic.name,
                    provider=provider,
                    error_type=type(exc).__name__,
                    message=provider_error_message(exc),
                )
            )
        payload = fallback_payload(topic)
    return TopicBriefing(
        topic_id=topic.id,
        as_of=date.today(),
        title=payload["title"],
        summary=payload["summary"],
        bullets=payload["bullets"],
        action=payload["action"],
        source_type=topic.source_type,
        priority=payload["priority"],
        generated_by=payload["generated_by"],
    )


def run_morning_briefing(db: Session) -> list[TopicBriefing]:
    seed_topics_if_empty(db)
    from .structured_sources import structured_topic_briefings

    provider = os.getenv(
        "AI_PROVIDER", "openai" if os.getenv("OPENAI_API_KEY") else "fallback"
    ).lower()
    topics = list(
        db.scalars(
            select(Topic)
            .where(Topic.is_active.is_(True), Topic.source_type != "structured")
            .order_by(Topic.priority.desc())
        ).all()
    )
    today = date.today()
    db.execute(delete(TopicBriefing).where(TopicBriefing.as_of == today))
    ai_errors: list[TopicGenerationError] = []
    briefings = structured_topic_briefings(db) + [
        generate_topic_briefing(topic, ai_errors) for topic in topics
    ]
    db.add_all(briefings)
    db.commit()

    if provider == "fallback":
        record_source_status(
            db,
            "AI Topic Briefings",
            "skipped",
            "AI provider is not configured; deterministic fallback briefings were generated.",
            {"provider": provider, "topics": [topic.name for topic in topics]},
        )
    elif ai_errors:
        record_source_status(
            db,
            "AI Topic Briefings",
            "error" if len(ai_errors) == len(topics) else "partial",
            f"AI topic generation failed for {len(ai_errors)} of {len(topics)} topics.",
            {"provider": provider, "errors": [error.__dict__ for error in ai_errors]},
        )
    else:
        record_source_status(
            db,
            "AI Topic Briefings",
            "ok",
            f"Generated {len(topics)} AI topic briefings.",
            {"provider": provider, "topics": [topic.name for topic in topics]},
        )
    return briefings


def seed_topic_briefings_if_empty(db: Session) -> None:
    has_briefing = db.scalar(select(TopicBriefing.id).limit(1))
    if has_briefing:
        return

    seed_topics_if_empty(db)
    topics = list(
        db.scalars(
            select(Topic).where(Topic.is_active.is_(True)).order_by(Topic.priority.desc())
        ).all()
    )
    db.add_all(
        [
            TopicBriefing(
                topic_id=topic.id,
                as_of=date.today(),
                title=payload["title"],
                summary=payload["summary"],
                bullets=payload["bullets"],
                action=payload["action"],
                source_type=topic.source_type,
                priority=payload["priority"],
                generated_by=payload["generated_by"],
            )
            for topic in topics
            for payload in [fallback_payload(topic)]
        ]
    )
    db.commit()


def latest_topic_briefings(db: Session) -> list[TopicBriefing]:
    topics = list(db.scalars(select(Topic).where(Topic.is_active.is_(True))).all())
    rows: list[TopicBriefing] = []
    for topic in topics:
        briefing = db.scalar(
            select(TopicBriefing)
            .where(TopicBriefing.topic_id == topic.id)
            .order_by(TopicBriefing.as_of.desc(), TopicBriefing.created_at.desc())
            .limit(1)
        )
        if briefing:
            rows.append(briefing)
    return sorted(rows, key=lambda row: row.priority, reverse=True)


def topic_decision_metadata(briefing: TopicBriefing) -> dict:
    topic_name = (briefing.topic.name if briefing.topic else "").lower()
    text = f"{briefing.title} {briefing.summary} {' '.join(briefing.bullets or [])}".lower()
    has_action = bool(clean_action_text(briefing.action))

    if has_action or any(
        token in text
        for token in (
            "deadline",
            "blocked",
            "renewal",
            "threshold crossed",
            "requires action",
        )
    ):
        return {
            "category": "action",
            "importance_score": max(82, briefing.priority * 10),
            "actionability_score": 82,
            "expiration_hours": 72,
            "why_user_cares": "This update could get worse if it is ignored for the next 72 hours.",
        }
    if topic_name == "golf" or any(
        token in text
        for token in (
            "best golf",
            "opportunity",
            "buy range",
            "cheap airfare",
            "ticket release",
        )
    ):
        return {
            "category": "opportunity",
            "importance_score": max(74, briefing.priority * 10),
            "actionability_score": 52,
            "expiration_hours": 72,
            "why_user_cares": "This is a time-sensitive upside window.",
        }
    return {
        "category": "awareness",
        "importance_score": max(42, min(72, briefing.priority * 8)),
        "actionability_score": 8,
        "expiration_hours": 168,
        "why_user_cares": "This is relevant context, but it does not currently require a decision.",
    }


def is_sports_catch_up_briefing(briefing: TopicBriefing) -> bool:
    topic_name = (briefing.topic.name if briefing.topic else "").lower()
    if topic_name not in SPORTS_CATCH_UP_TOPICS:
        return False
    text = f"{briefing.title} {briefing.summary} {' '.join(briefing.bullets or [])}".lower()
    if topic_name == "yankees":
        return True
    return any(
        token in text
        for token in (
            "completed",
            "game recap",
            "highlights",
            "last night",
            "postgame",
            "qualifying recap",
            "race recap",
            "recap available",
        )
    )


def spoiler_safe_catch_up_title(briefing: TopicBriefing) -> str:
    topic_name = briefing.topic.name if briefing.topic else "Sports"
    normalized = topic_name.lower()
    if normalized == "yankees":
        return "Yankees recap available from last night"
    if normalized == "rutgers":
        return "Rutgers highlights are available"
    if normalized == "cowboys":
        return "Cowboys postgame highlights are available"
    if normalized == "f1":
        return "F1 race recap is available"
    if normalized == "pga":
        return "PGA recap is available"
    return "Major sports recap available"


def catch_up_metadata(metadata: dict) -> dict:
    return {
        **metadata,
        "category": "awareness",
        "importance_score": min(70, int(metadata.get("importance_score") or 60)),
        "actionability_score": min(20, int(metadata.get("actionability_score") or 8)),
        "suggested_posture": "Catch Up",
        "attention_section": "Catch Up",
        "why_user_cares": (
            "A completed event has a recap available if you want to catch up."
        ),
    }


def catch_up_summary(briefing: TopicBriefing) -> str:
    topic_name = briefing.topic.name if briefing.topic else "Sports"
    if topic_name.lower() == "yankees":
        return "Spoiler-safe highlights are available if you want to catch up."
    return "A completed event has a recap available if you want to catch up."


def topic_attention_items(briefings: Iterable[TopicBriefing]) -> list[dict]:
    items = []
    for briefing in briefings:
        if briefing.generated_by == "fallback":
            continue
        metadata = topic_decision_metadata(briefing)
        catch_up = is_sports_catch_up_briefing(briefing)
        if catch_up:
            metadata = catch_up_metadata(metadata)
        items.append(
            enrich_attention_item(
                {
                    "title": (
                        spoiler_safe_catch_up_title(briefing)
                        if catch_up
                        else clean_editorial_text(briefing.title)
                    ),
                    "why_now": (
                        catch_up_summary(briefing)
                        if catch_up
                        else clean_editorial_text(briefing.summary)
                    ),
                    "action": clean_action_text(briefing.action),
                    "priority": briefing.priority,
                    "source": "topic",
                    "topic": briefing.topic.name if briefing.topic else None,
                    "detail_id": f"topic:{briefing.id}",
                },
                **metadata,
            )
        )
    return items


def serialize_topic(topic: Topic) -> dict:
    return {
        "id": topic.id,
        "name": topic.name,
        "priority": topic.priority,
        "source_type": topic.source_type,
        "category": topic.category,
        "refresh_frequency": topic.refresh_frequency,
        "prompt": topic.prompt,
        "is_active": topic.is_active,
    }


def serialize_briefing(briefing: TopicBriefing) -> dict:
    return {
        "id": briefing.id,
        "topic": briefing.topic.name if briefing.topic else "",
        "category": briefing.topic.category if briefing.topic else "",
        "source_type": briefing.source_type,
        "priority": briefing.priority,
        "as_of": briefing.as_of.isoformat(),
        "title": clean_editorial_text(briefing.title),
        "summary": clean_editorial_text(briefing.summary),
        "bullets": [clean_editorial_text(item) for item in (briefing.bullets or [])],
        "action": clean_action_text(briefing.action),
        "generated_by": briefing.generated_by,
    }
