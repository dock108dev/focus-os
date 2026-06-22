from datetime import date
import subprocess

from app.models import Topic, TopicBriefing
from app.topic_engine import (
    AIProviderConfigurationError,
    fallback_payload,
    generate_topic_briefing,
    parse_ai_payload,
    provider_error_message,
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

    assert items[0]["title"] == "Bitcoin moved enough to review"
    assert (
        items[0]["why_now"]
        == "Bitcoin crossed the configured daily movement threshold."
    )
    assert items[0]["action"] == ""
    assert items[0]["source"] == "topic"
    assert items[0]["topic"] == "Bitcoin"
    assert items[0]["detail_id"] == "topic:42"
    assert items[0]["category"] == "awareness"
    assert items[0]["importance_score"] == 72
    assert (
        items[0]["why_user_cares"]
        == "This is relevant context, but it does not currently require a decision."
    )


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


def test_sports_topic_recaps_are_spoiler_safe_catch_up_items():
    topic = Topic(
        id=1,
        name="Yankees",
        priority=8,
        source_type="unstructured",
        category="Sports",
        refresh_frequency="daily",
        prompt="Summarize Yankees results.",
    )
    briefing = TopicBriefing(
        id=77,
        topic=topic,
        topic_id=1,
        as_of=date.today(),
        title="Yankees beat Boston 6-2",
        summary="Yankees won 6-2 and moved within one game of first place.",
        bullets=["Final score: Yankees 6, Boston 2"],
        action="",
        priority=8,
        generated_by="codex-cli",
    )

    item = topic_attention_items([briefing])[0]

    assert item["title"] == "Yankees recap available from last night"
    assert "6-2" not in item["title"]
    assert item["why_now"] == (
        "Spoiler-safe highlights are available if you want to catch up."
    )
    assert "6-2" not in item["why_now"]
    assert item["attention_section"] == "Catch Up"
    assert item["suggested_posture"] == "Catch Up"
    assert item["category"] == "awareness"


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


def test_provider_error_message_does_not_echo_full_command_prompt():
    exc = subprocess.CalledProcessError(
        1,
        ["codex", "exec", "prompt containing private briefing text"],
        stderr="authentication failed",
    )

    message = provider_error_message(exc)

    assert "status 1" in message
    assert "authentication failed" in message
    assert "private briefing text" not in message
