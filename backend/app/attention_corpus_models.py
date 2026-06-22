from __future__ import annotations

from dataclasses import dataclass
from datetime import date

DOMAIN_TARGETS = {
    "Work": 250,
    "Finance & Markets": 230,
    "Technology & AI": 165,
    "Personal & Family": 90,
    "Dog": 75,
    "Sports & Golf": 110,
    "Golf Equipment": 60,
    "Books & Entertainment": 60,
    "Health": 75,
    "Life Logistics": 120,
    "Home Ownership": 85,
    "Travel": 85,
    "Side Projects": 95,
}

EVENT_CLASSES = [
    "Deadline",
    "Opportunity",
    "Context Change",
    "Monitoring",
    "Maintenance",
    "Noise",
]
EVALUATIONS = ["Ignore", "Monitor", "Mention", "Surface", "Lead Story"]
LEAD_STORY_TARGET = 26
SIMULATION_START = date(2026, 5, 3)
SIMULATION_DAYS = 50


@dataclass(frozen=True)
class AttentionScenario:
    domain: str
    event_class: str
    object: str
    subject: str
    title_templates: tuple[str, ...]
    description_templates: tuple[str, ...]
    mike_relevance: str
    value_if_caught: str
    loss_if_ignored: str
    sources: tuple[str, ...]
    lead_eligible: bool = False
    watch_conditions: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConfiguredWatch:
    name: str
    object: str
    conditions: tuple[str, ...]
    sources: tuple[str, ...]
    cadence: str
    surface_rules: tuple[str, ...]
    suppression_rules: tuple[str, ...]
    expiration: str
    preferred_output: str


@dataclass(frozen=True)
class WatchPreset:
    name: str
    creates_watch: str
    default_sources: tuple[str, ...]
    default_cadence: str
    editable_fields: tuple[str, ...]
