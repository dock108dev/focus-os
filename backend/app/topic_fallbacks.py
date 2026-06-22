from __future__ import annotations

from .models import Topic


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

