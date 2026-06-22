from __future__ import annotations

from datetime import timedelta
from typing import Iterable

from .attention_corpus_generation import generate_event_corpus
from .attention_corpus_models import EVALUATIONS, SIMULATION_DAYS, SIMULATION_START
from .attention_corpus_quality import briefing_output_for_event
from .attention_corpus_templates import SIMULATION_PATTERNS

def select_events(
    events: list[dict], domain: str, evaluation: str | None, count: int, offset: int
) -> list[dict]:
    candidates = [
        event
        for event in events
        if event["domain"] == domain
        and (evaluation is None or event["evaluation"] == evaluation)
    ]
    if not candidates:
        return []
    return [candidates[(offset + index) % len(candidates)] for index in range(count)]


def select_best_domain_events(
    events: list[dict],
    domain: str,
    count: int,
    offset: int,
    subject: str | None = None,
) -> list[dict]:
    scoped_events = [
        event
        for event in events
        if event["domain"] == domain and (subject is None or event["subject"] == subject)
    ]
    if not scoped_events and subject is not None:
        scoped_events = [event for event in events if event["domain"] == domain]
    selected: list[dict] = []
    selected.extend(select_events(scoped_events, domain, "Lead Story", 1, offset))
    for evaluation in ("Surface", "Mention"):
        selected.extend(
            select_events(scoped_events, domain, evaluation, count, offset + len(selected))
        )
        if len(selected) >= count:
            return selected[:count]
    return selected[:count]


def unique_events(events: Iterable[dict]) -> list[dict]:
    seen: set[str] = set()
    unique: list[dict] = []
    for event in events:
        if event["id"] in seen:
            continue
        seen.add(event["id"])
        unique.append(event)
    return unique


def simulation_pattern(day_index: int) -> dict:
    return SIMULATION_PATTERNS[day_index % len(SIMULATION_PATTERNS)]


def build_simulation_day(events: list[dict], day_index: int) -> dict:
    current_date = SIMULATION_START + timedelta(days=day_index)
    pattern = simulation_pattern(day_index)
    candidate_events: list[dict] = []
    candidate_events.extend(select_events(events, "Finance & Markets", "Monitor", 2, day_index))
    candidate_events.extend(select_events(events, "Sports & Golf", "Ignore", 1, day_index))
    candidate_events.extend(select_events(events, "Books & Entertainment", "Ignore", 1, day_index))
    candidate_events.extend(select_events(events, "Technology & AI", "Mention", 1, day_index))
    candidate_events.extend(select_events(events, "Life Logistics", "Mention", 1, day_index))
    if pattern["dominant"]:
        candidate_events.extend(
            select_best_domain_events(
                events,
                pattern["dominant"],
                3,
                day_index,
                subject=pattern.get("subject"),
            )
        )
    if pattern["primary"] == "competing":
        candidate_events.extend(select_best_domain_events(events, "Personal & Family", 2, day_index))
        candidate_events.extend(select_best_domain_events(events, "Work", 2, day_index + 3))
    candidate_events = unique_events(candidate_events)

    if pattern["primary"] is None:
        selected = [
            event for event in candidate_events if event["evaluation"] == "Mention"
        ][:4]
        primary_focus_id = None
    else:
        selected = [
            event for event in candidate_events if event["evaluation"] in {"Surface", "Lead Story"}
        ][:4]
        selected.extend(
            [event for event in candidate_events if event["evaluation"] == "Mention"][:2]
        )
        selected = unique_events(selected)
        lead_candidates = [
            event for event in selected if event["evaluation"] == "Lead Story"
        ]
        primary_focus_id = (
            max(lead_candidates, key=lambda event: event["attention_score"])["id"]
            if lead_candidates
            else None
        )

    suppressed = [event for event in candidate_events if event["evaluation"] == "Ignore"]
    outcome_counts = {evaluation: 0 for evaluation in EVALUATIONS}
    for event in candidate_events:
        outcome_counts[event["evaluation"]] += 1
    return {
        "date": current_date.isoformat(),
        "scenario": pattern["name"],
        "dominant_domain": pattern["dominant"],
        "primary_focus_id": primary_focus_id,
        "primary_focus_title": next(
            (event["title"] for event in selected if event["id"] == primary_focus_id),
            None,
        ),
        "allows_no_spotlight": primary_focus_id is None,
        "multiple_competing_focuses": pattern["primary"] == "competing"
        and sum(
            1
            for event in selected
            if event["evaluation"] in {"Surface", "Lead Story"}
        )
        > 1,
        "candidate_event_ids": [event["id"] for event in candidate_events],
        "selected_event_ids": [event["id"] for event in selected],
        "briefing_outputs": [briefing_output_for_event(event) for event in selected],
        "suppressed_event_ids": [event["id"] for event in suppressed],
        "outcome_counts": outcome_counts,
        "review_note": review_note(pattern["primary"]),
    }


def review_note(primary: str | None) -> str:
    if primary is None:
        return "Nothing deserves the spotlight today; verify the system does not manufacture a hero."
    if primary == "competing":
        return "Multiple high-value contexts compete; review whether one truly dominates."
    return "A dominant context exists; review whether it earns primary focus."


def build_may_june_simulation(events: list[dict] | None = None) -> list[dict]:
    rows = events or generate_event_corpus()
    return [build_simulation_day(rows, index) for index in range(SIMULATION_DAYS)]


def classification_rules() -> dict:
    return {
        "Deadline": "Time-bound event with meaningful loss if ignored.",
        "Opportunity": "Decision window where value can be captured or lost.",
        "Context Change": "New information changes future decisions or assumptions.",
        "Monitoring": "Object stays active but silent until conditions change.",
        "Maintenance": "Recurring or rare upkeep with date or risk pressure.",
        "Noise": "Generic update that should usually be suppressed.",
    }


def watch_model() -> dict:
    return {
        "definition": "A watch is user-authored attention infrastructure, not a passive briefing artifact.",
        "required_fields": [
            "object",
            "conditions",
            "sources",
            "cadence",
            "surface_rules",
            "suppression_rules",
            "expiration",
            "preferred_output",
        ],
        "default_behavior": "Evaluate on cadence, suppress unchanged or generic inputs, and emit briefing candidates only when surface rules are met.",
        "examples": {
            "Outdoor Concert": {
                "object": "outdoor concert",
                "conditions": ["weather", "parking", "timing", "venue changes"],
                "sources": ["calendar", "weather", "venue email", "parking feed"],
                "cadence": "daily until 72 hours out, then morning and afternoon",
                "surface_rules": [
                    "rain risk > 35%",
                    "parking changes materially",
                    "event is within 48 hours",
                    "venue sends an update",
                ],
                "suppression_rules": [
                    "generic reminders",
                    "unchanged weather",
                    "concert is coming up filler",
                ],
                "expiration": "day after event",
                "preferred_output": "brief only what changed or what needs a decision",
            },
            "WWDC": {
                "object": "WWDC",
                "conditions": ["keynote date", "major announcements", "developer impact"],
                "sources": ["Apple developer news", "calendar", "project notes"],
                "cadence": "daily during event week",
                "surface_rules": [
                    "project assumption changes",
                    "developer tooling impact is practical",
                ],
                "suppression_rules": ["generic launch coverage", "unchanged rumor recap"],
                "expiration": "7 days after keynote",
                "preferred_output": "project posture change",
            },
            "Vacation": {
                "object": "Trip",
                "conditions": ["flight", "weather", "travel advisories"],
                "sources": ["calendar", "airline email", "weather"],
                "cadence": "daily inside 7 days",
                "surface_rules": ["departure is near", "weather changes packing or timing"],
                "suppression_rules": ["generic countdowns", "unchanged itinerary"],
                "expiration": "return date",
                "preferred_output": "open travel loop",
            },
            "Mortgage Rate": {
                "object": "Mortgage-rate watch",
                "conditions": ["rate threshold", "Fed signal", "housing inventory"],
                "sources": ["FRED", "mortgage rate feed", "housing watch"],
                "cadence": "weekly, plus after Fed/CPI events",
                "surface_rules": ["rate threshold crossed", "housing math changes materially"],
                "suppression_rules": ["unchanged rates", "generic housing news"],
                "expiration": "configured review window",
                "preferred_output": "decision-window note",
            },
        },
    }

