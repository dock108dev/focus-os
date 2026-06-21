from datetime import date

from app.models import Topic, TopicBriefing
from app.topic_engine import (
    AIProviderConfigurationError,
    generate_topic_briefing,
    fallback_payload,
    parse_ai_payload,
    topic_attention_items,
)


def test_fallback_topic_payload_stays_out_of_task_language():
    topic = Topic(
        name="Iran",
        priority=7,
        source_type="unstructured",
        category="Geopolitics",
        refresh_frequency="daily",
        prompt="Summarize meaningful developments involving Iran.",
    )

    payload = fallback_payload(topic)

    assert payload["title"] == "Waiting for AI briefing setup"
    assert payload["action"] == ""
    assert payload["generated_by"] == "fallback"


def test_ai_payload_removes_patronizing_care_language():
    topic = Topic(
        name="Yankees",
        priority=8,
        source_type="unstructured",
        category="Sports",
        refresh_frequency="daily",
        prompt="Summarize Yankees results.",
    )
    raw = """
    {
      "title": "Yankees shut out Cincinnati 5-0",
      "summary": "Mike should care because the Yankees got a clean win behind 13 strikeouts.",
      "bullets": ["Why Mike should care: Chisholm returned from injury."],
      "action": "Review whether to watch highlights.",
      "priority": 8
    }
    """

    payload = parse_ai_payload(raw, topic)

    assert payload["summary"] == "The Yankees got a clean win behind 13 strikeouts."
    assert payload["bullets"] == ["Chisholm returned from injury."]
    assert payload["action"] == ""


def test_high_priority_topic_briefing_can_join_today_attention():
    topic = Topic(
        id=1,
        name="Bitcoin",
        priority=9,
        source_type="structured",
        category="Crypto",
        refresh_frequency="daily",
        prompt="Summarize Bitcoin movement.",
    )
    briefing = TopicBriefing(
        id=42,
        topic=topic,
        topic_id=1,
        as_of=date.today(),
        title="Bitcoin moved enough to review",
        summary="Bitcoin crossed the configured daily movement threshold.",
        bullets=["24-hour move crossed threshold"],
        action="Review whether this changes today's cash plan.",
        priority=9,
        generated_by="openai-web-search",
    )

    items = topic_attention_items([briefing])

    assert items == [
        {
            "title": "Bitcoin moved enough to review",
            "why_now": "Bitcoin crossed the configured daily movement threshold.",
            "action": "",
            "priority": 9,
            "source": "topic",
            "topic": "Bitcoin",
            "detail_id": "topic:42",
            "classification": "awareness",
        }
    ]


def test_fallback_topic_briefing_stays_out_of_today_attention():
    topic = Topic(
        id=1,
        name="Bitcoin",
        priority=9,
        source_type="structured",
        category="Crypto",
        refresh_frequency="daily",
        prompt="Summarize Bitcoin movement.",
    )
    briefing = TopicBriefing(
        topic=topic,
        topic_id=1,
        as_of=date.today(),
        title="Waiting for market source setup",
        summary="Bitcoin is configured, but no market source has produced a briefing yet.",
        bullets=[],
        action="",
        priority=9,
        generated_by="fallback",
    )

    assert topic_attention_items([briefing]) == []


def test_generate_topic_briefing_records_provider_failure(monkeypatch):
    topic = Topic(
        id=1,
        name="Iran",
        priority=7,
        source_type="unstructured",
        category="Geopolitics",
        refresh_frequency="daily",
        prompt="Summarize meaningful developments involving Iran.",
    )

    def fail_provider(_topic):
        raise AIProviderConfigurationError("missing provider key")

    monkeypatch.setattr("app.topic_engine.generate_ai_payload", fail_provider)
    errors = []

    briefing = generate_topic_briefing(topic, errors)

    assert briefing.generated_by == "fallback"
    assert errors[0].topic == "Iran"
    assert errors[0].error_type == "AIProviderConfigurationError"
