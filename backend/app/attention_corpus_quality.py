from __future__ import annotations

from typing import Iterable

from .attention_corpus_models import DOMAIN_TARGETS, EVALUATIONS, EVENT_CLASSES
from .attention_corpus_watch_data import CONFIGURED_WATCHES, WATCH_PRESETS

def corpus_summary(events: Iterable[dict]) -> dict:
    rows = list(events)
    watch_reviews = watch_quality_reviews()
    preset_reviews = preset_quality_reviews()
    by_domain = {domain: 0 for domain in DOMAIN_TARGETS}
    by_class = {event_class: 0 for event_class in EVENT_CLASSES}
    by_evaluation = {evaluation: 0 for evaluation in EVALUATIONS}
    for row in rows:
        by_domain[row["domain"]] += 1
        by_class[row["event_class"]] += 1
        by_evaluation[row["evaluation"]] += 1
    return {
        "total_events": len(rows),
        "configured_watch_count": len(CONFIGURED_WATCHES),
        "valid_watch_count": sum(1 for review in watch_reviews if review["valid"]),
        "valid_preset_count": sum(1 for review in preset_reviews if review["valid"]),
        "domain_counts": by_domain,
        "class_counts": by_class,
        "evaluation_counts": by_evaluation,
        "unique_title_count": len({row["title"] for row in rows}),
    }


def configured_watches() -> list[dict]:
    return [
        {
            "id": watch_id(watch.name),
            "name": watch.name,
            "object": watch.object,
            "conditions": list(watch.conditions),
            "sources": list(watch.sources),
            "cadence": watch.cadence,
            "surface_rules": list(watch.surface_rules),
            "suppression_rules": list(watch.suppression_rules),
            "expiration": watch.expiration,
            "preferred_output": watch.preferred_output,
        }
        for watch in CONFIGURED_WATCHES
    ]


def watch_id(name: str) -> str:
    return (
        "watch:"
        + name.lower()
        .replace("&", "and")
        .replace("/", "-")
        .replace(" ", "-")
        .replace("_", "-")
    )


def watch_presets() -> list[dict]:
    return [
        {
            "name": preset.name,
            "creates_watch": preset.creates_watch,
            "created_watch_id": watch_id(preset.creates_watch),
            "default_sources": list(preset.default_sources),
            "default_cadence": preset.default_cadence,
            "editable_fields": list(preset.editable_fields),
        }
        for preset in WATCH_PRESETS
    ]


def realistic_source(source: str) -> bool:
    source_lower = source.lower()
    return any(
        token in source_lower
        for token in (
            "advisory",
            "billing",
            "calendar",
            "checklist",
            "changelog",
            "coingecko",
            "course",
            "developer",
            "domain",
            "docs",
            "email",
            "enterprise",
            "feed",
            "fed",
            "folder",
            "fred",
            "github",
            "import",
            "index",
            "jira",
            "market",
            "manufacturer",
            "messages",
            "notes",
            "pharmacy",
            "portal",
            "pricing",
            "project",
            "queue",
            "range",
            "recommendation",
            "rule",
            "schedule",
            "sector",
            "slack",
            "state",
            "team",
            "ticket",
            "tooling",
            "vet",
            "watch",
            "weather",
        )
    )


def watch_quality_review_for(watch: dict) -> dict:
    silent = (
        f"{watch['object']} remains silent when {watch['conditions'][0]} is unchanged "
        f"and no surface rule is met."
    )
    surface = (
        f"Surface when {watch['surface_rules'][0]}: output as {watch['preferred_output']}."
    )
    suppress = (
        f"Suppress when input is {watch['suppression_rules'][0]}."
    )
    criteria = {
        "object_specific_enough": bool(watch["object"])
        and watch["object"].lower() not in {"stuff", "things", "news", "updates"},
        "sources_realistic": len(watch["sources"]) >= 2
        and all(realistic_source(source) for source in watch["sources"]),
        "cadence_appropriate": any(
            token in watch["cadence"]
            for token in ("daily", "weekly", "monthly", "workday", "event")
        ),
        "surface_rules_concrete": len(watch["surface_rules"]) >= 2,
        "suppression_rules_aggressive": len(watch["suppression_rules"]) >= 2,
        "expiration_makes_sense": bool(watch["expiration"]),
        "helps_memory_not_noise": "generic" in " ".join(watch["suppression_rules"]).lower()
        or "only" in watch["preferred_output"].lower()
        or "small action" in watch["preferred_output"].lower()
        or "decision" in watch["preferred_output"].lower()
        or "posture" in watch["preferred_output"].lower(),
        "has_silent_monitoring_example": bool(silent),
        "has_useful_surface_example": bool(surface),
        "has_explicit_suppression_example": bool(suppress),
    }
    return {
        "watch_id": watch["id"],
        "name": watch["name"],
        "valid": all(criteria.values()),
        "criteria": criteria,
        "outcomes": {
            "silent_monitoring": silent,
            "useful_surface": surface,
            "explicit_suppression": suppress,
        },
    }


def watch_quality_reviews() -> list[dict]:
    return [watch_quality_review_for(watch) for watch in configured_watches()]


def preset_quality_reviews() -> list[dict]:
    watch_ids = {watch["id"] for watch in configured_watches()}
    reviews = []
    for preset in watch_presets():
        criteria = {
            "creates_editable_watch": preset["created_watch_id"] in watch_ids,
            "has_realistic_default_sources": len(preset["default_sources"]) >= 2,
            "has_default_cadence": bool(preset["default_cadence"]),
            "does_not_create_fixed_category": len(preset["editable_fields"]) >= 8,
        }
        reviews.append(
            {
                "preset": preset["name"],
                "created_watch_id": preset["created_watch_id"],
                "valid": all(criteria.values()),
                "criteria": criteria,
            }
        )
    return reviews


def source_watch_ids_for_event(domain: str, subject: str) -> list[str]:
    if domain == "Work":
        return [watch_id("Work migrations")]
    if domain == "Finance & Markets":
        if subject == "Bitcoin":
            return [watch_id("Bitcoin range")]
        if subject == "UNH":
            return [watch_id("UNH watch")]
        if subject == "mortgage rates":
            return [watch_id("Mortgage rates")]
        return [watch_id("Market backdrop")]
    if domain == "Technology & AI":
        return [watch_id("WWDC and coding tools")]
    if domain == "Personal & Family":
        return [watch_id("Family dates")]
    if domain == "Dog":
        return [watch_id("Bogey care")]
    if domain == "Sports & Golf":
        return [watch_id("Yankees and Rutgers")]
    if domain == "Golf Equipment":
        return [watch_id("Golf weather and equipment")]
    if domain == "Books & Entertainment":
        return [watch_id("Media queue")]
    if domain == "Health":
        return [watch_id("Health admin")]
    if domain == "Life Logistics":
        return [watch_id("Life logistics")]
    if domain == "Home Ownership":
        return [watch_id("Home maintenance")]
    if domain == "Travel":
        return [watch_id("Travel logistics")]
    if domain == "Side Projects":
        return [watch_id("Side projects")]
    raise ValueError(f"No configured watch lineage for domain {domain}")


def triggered_surface_rule_for_event(event_class: str, evaluation: str) -> str:
    if evaluation in {"Lead Story", "Surface"}:
        if event_class == "Deadline":
            return "deadline or expiration is inside the action window"
        if event_class == "Opportunity":
            return "configured decision window opened"
        if event_class == "Context Change":
            return "watched context changed enough to alter posture"
        if event_class == "Maintenance":
            return "configured upkeep window is due or deferred"
        if event_class == "Monitoring":
            return "watched condition changed enough to mention"
    if evaluation == "Mention":
        return "configured watch produced a current-day context note"
    return ""


def suppressed_by_for_event(evaluation: str, suppression_rules: list[str]) -> str | None:
    if evaluation == "Ignore":
        return suppression_rules[0] if suppression_rules else "did not meet surface rules"
    if evaluation == "Monitor":
        return "did not meet surface rules"
    return None


def briefing_output_for_event(event: dict) -> dict:
    return {
        "event_id": event["id"],
        "title": event["title"],
        "domain": event["domain"],
        "evaluation": event["evaluation"],
        "source_watch_ids": event["source_watch_ids"],
        "triggered_surface_rule": event["triggered_surface_rule"],
        "suppressed_by": None,
        "why_today": event["why_today"],
    }


def planning_layers() -> dict:
    return {
        "Configured Watches": "User-authored attention configuration: what matters, what to check, where to check, cadence, surface rules, suppression rules, expiration, and preferred output.",
        "Generated Events": "System observations produced from configured watches and other sources. These are candidates, not briefing items.",
        "Briefing Outputs": "Only the filtered conclusions that changed, need attention now, or would otherwise be forgotten.",
    }

