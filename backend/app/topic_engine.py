from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

from openai import OpenAI, OpenAIError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .attention import enrich_attention_item
from .models import Topic, TopicBriefing
from .source_status import record_source_status
from .voice import clean_action_text, clean_editorial_text


logger = logging.getLogger(__name__)


class AIProviderConfigurationError(RuntimeError):
    """Raised when AI briefing generation is explicitly configured incorrectly."""


AI_PROVIDER_EXCEPTIONS = (
    AIProviderConfigurationError,
    OpenAIError,
    subprocess.SubprocessError,
    OSError,
    TimeoutError,
    ValueError,
    TypeError,
    json.JSONDecodeError,
)


@dataclass(frozen=True)
class TopicGenerationError:
    topic: str
    provider: str
    error_type: str
    message: str


DEFAULT_TOPICS = [
    {
        "name": "Yankees",
        "priority": 8,
        "source_type": "unstructured",
        "category": "Sports",
        "refresh_frequency": "daily",
        "prompt": "Summarize Yankees results from the previous day. Include next scheduled game and any significant injuries or storylines.",
    },
    {
        "name": "Bitcoin",
        "priority": 9,
        "source_type": "structured",
        "category": "Crypto",
        "refresh_frequency": "daily",
        "prompt": "Summarize Bitcoin movement over the previous 24 hours and identify any major catalysts.",
    },
    {
        "name": "Iran",
        "priority": 7,
        "source_type": "unstructured",
        "category": "Geopolitics",
        "refresh_frequency": "daily",
        "prompt": "Summarize meaningful developments involving Iran from the last 24 hours. Ignore low-impact stories. Focus on military, geopolitical, economic, or global implications.",
    },
    {
        "name": "Major World Sports",
        "priority": 6,
        "source_type": "unstructured",
        "category": "Sports",
        "refresh_frequency": "daily",
        "prompt": "Identify globally significant sporting events beginning within the next 7 days. Include championships, majors, international tournaments, and marquee matchups.",
    },
    {
        "name": "AI",
        "priority": 6,
        "source_type": "unstructured",
        "category": "Technology",
        "refresh_frequency": "daily",
        "prompt": "Summarize meaningful AI developments from the last 24 hours. Ignore routine product announcements unless they change what Mike should pay attention to.",
    },
    {
        "name": "Golf",
        "priority": 5,
        "source_type": "structured",
        "category": "Weather",
        "refresh_frequency": "daily",
        "prompt": "Identify the best golf day this week using weather and schedule constraints. Prefer clear, low-wind days.",
    },
]


def seed_topics_if_empty(db: Session) -> None:
    has_topic = db.scalar(select(Topic.id).limit(1))
    if has_topic:
        return
    db.add_all([Topic(**row) for row in DEFAULT_TOPICS])
    db.commit()


def fallback_payload(topic: Topic) -> dict:
    fallback_by_name = {
        "Yankees": {
            "title": "Waiting for sports source setup",
            "summary": "Yankees is configured, but no sports source has produced a briefing yet.",
            "bullets": [
                "Results, next game, injuries, and storylines will appear here once connected."
            ],
            "action": "",
        },
        "Bitcoin": {
            "title": "Waiting for market source setup",
            "summary": "Bitcoin is configured, but no market source has produced a briefing yet.",
            "bullets": [
                "24-hour movement and major catalysts will appear here once connected."
            ],
            "action": "",
        },
        "Iran": {
            "title": "Waiting for AI briefing setup",
            "summary": "Iran is configured, but no AI briefing has been generated yet.",
            "bullets": [
                "Military, geopolitical, economic, and global implications will appear here once connected."
            ],
            "action": "",
        },
        "Major World Sports": {
            "title": "Waiting for sports calendar setup",
            "summary": "Major World Sports is configured, but no sports calendar has produced a briefing yet.",
            "bullets": [
                "Championships, majors, international tournaments, and marquee matchups will appear here once connected."
            ],
            "action": "",
        },
        "AI": {
            "title": "Waiting for AI briefing setup",
            "summary": "AI is configured, but no industry briefing has been generated yet.",
            "bullets": [
                "Major model releases, infrastructure shifts, and company moves will appear here once connected."
            ],
            "action": "",
        },
        "Golf": {
            "title": "Waiting for weather source setup",
            "summary": "Golf is configured, but no weather source has produced a recommendation yet.",
            "bullets": [
                "Best day, wind, rain, and tee-time windows will appear here once connected."
            ],
            "action": "",
        },
    }
    default = fallback_by_name.get(
        topic.name,
        {
            "title": f"{topic.name} is configured",
            "summary": "This topic has a prompt but no live source has generated a briefing yet.",
            "bullets": [topic.prompt],
            "action": "",
        },
    )
    return {
        **default,
        "priority": topic.priority,
        "generated_by": "fallback",
    }


def parse_ai_payload(raw_text: str, topic: Topic) -> dict:
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {
            "title": f"{topic.name}: attention check",
            "summary": clean_editorial_text(raw_text.strip())[:1200],
            "bullets": [],
            "action": "",
            "priority": topic.priority,
            "generated_by": "openai-web-search",
        }

    try:
        parsed = json.loads(raw_text[start : end + 1])
    except json.JSONDecodeError:
        parsed = {}

    return {
        "title": clean_editorial_text(
            str(parsed.get("title") or f"{topic.name}: attention check")
        )[:240],
        "summary": clean_editorial_text(str(parsed.get("summary") or raw_text.strip()))[
            :2000
        ],
        "bullets": [
            clean_editorial_text(str(item))[:280] for item in parsed.get("bullets", [])
        ][:4],
        "action": clean_action_text(str(parsed.get("action") or ""))[:240],
        "priority": int(parsed.get("priority") or topic.priority),
        "generated_by": "openai-web-search",
    }


def briefing_prompt(topic: Topic) -> str:
    return (
        "You are generating Mike's FocusOS morning attention briefing. "
        "Use web search when available for current facts. "
        "Do not edit files. Do not run local commands unless needed to answer. "
        "Do not produce financial advice, trading decisions, order instructions, or autonomous actions. "
        "Return strict JSON with keys: title, summary, bullets, action, priority. "
        "Write like an editor, not an assistant. Never use phrases like 'Mike should care', 'why this matters', "
        "'review whether', 'consider whether', or 'decide whether'. "
        "The title must answer why the update is being shown before what happened. "
        "The summary should add concrete context only when useful. "
        "Some summaries can be one short sentence. Bullets must contain at most four short supporting facts. "
        "Set action to an empty string unless immediate action is genuinely warranted. "
        "Never expose source setup, API availability, or implementation details to Mike.\n\n"
        f"Today is {date.today().isoformat()}.\n"
        f"Topic: {topic.name}\n"
        f"Category: {topic.category}\n"
        f"Source type: {topic.source_type}\n"
        f"Priority baseline: {topic.priority}\n"
        f"Prompt: {topic.prompt}"
    )


def generate_openai_payload(topic: Topic) -> dict | None:
    if not os.getenv("OPENAI_API_KEY"):
        raise AIProviderConfigurationError(
            "OPENAI_API_KEY is required when AI_PROVIDER=openai."
        )

    timeout_seconds = float(os.getenv("OPENAI_REQUEST_TIMEOUT", "20"))
    client = OpenAI(timeout=timeout_seconds, max_retries=0)
    model = os.getenv("OPENAI_MODEL", "gpt-5.5")
    response = client.responses.create(
        model=model,
        tools=[{"type": "web_search", "search_context_size": "low"}],
        input=briefing_prompt(topic),
    )
    payload = parse_ai_payload(response.output_text, topic)
    return {**payload, "generated_by": "openai-web-search"}


def generate_codex_cli_payload(topic: Topic) -> dict | None:
    codex_path = os.getenv("CODEX_CLI_PATH", "codex")
    timeout_seconds = float(os.getenv("CODEX_CLI_TIMEOUT", "90"))
    workspace = os.getenv("CODEX_CLI_WORKDIR", str(Path(__file__).resolve().parents[2]))

    with tempfile.NamedTemporaryFile("w+", suffix=".txt", delete=True) as output:
        command = [
            codex_path,
            "--search",
            "exec",
            "--skip-git-repo-check",
            "--ephemeral",
            "--sandbox",
            "read-only",
            "-C",
            workspace,
            "-o",
            output.name,
            briefing_prompt(topic),
        ]
        subprocess.run(
            command,
            cwd=workspace,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=True,
        )
        output.seek(0)
        raw_text = output.read()

    payload = parse_ai_payload(raw_text, topic)
    return {**payload, "generated_by": "codex-cli"}


def generate_ai_payload(topic: Topic) -> dict | None:
    provider = os.getenv(
        "AI_PROVIDER", "openai" if os.getenv("OPENAI_API_KEY") else "fallback"
    ).lower()

    if provider == "codex_cli":
        return generate_codex_cli_payload(topic)
    if provider == "openai":
        return generate_openai_payload(topic)
    if provider == "fallback":
        return None
    raise AIProviderConfigurationError(f"Unsupported AI_PROVIDER {provider!r}.")


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
                    message=str(exc),
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
            .where(Topic.is_active == True, Topic.source_type != "structured")
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
            select(Topic).where(Topic.is_active == True).order_by(Topic.priority.desc())
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
    topics = list(db.scalars(select(Topic).where(Topic.is_active == True)).all())
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


def topic_attention_items(briefings: Iterable[TopicBriefing]) -> list[dict]:
    items = []
    for briefing in briefings:
        if briefing.generated_by == "fallback":
            continue
        metadata = topic_decision_metadata(briefing)
        items.append(
            enrich_attention_item(
                {
                    "title": clean_editorial_text(briefing.title),
                    "why_now": clean_editorial_text(briefing.summary),
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
