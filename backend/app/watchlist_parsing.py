from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Iterable

from .watchlist_rules import (
    DEFAULT_WATCH_FOR,
    PERSONAL_SOURCE_LABELS,
    EXTERNAL_SOURCE_LABELS,
    SOURCE_HINTS,
    WATCH_KEYWORDS,
    WEEKDAYS,
)

def clean_title(value: str) -> str:
    for line in value.splitlines():
        text = line.strip(" -\t")
        if text:
            first_sentence = re.split(r"[.!?]", text, maxsplit=1)[0].strip()
            return first_sentence[:120] or "Watch item"
    return "Watch item"


def extract_event_date(text: str, today: date | None = None) -> date | None:
    today = today or date.today()
    lower = text.lower()

    iso_match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
    if iso_match:
        return date.fromisoformat(iso_match.group(1))

    in_days = re.search(r"\bin\s+(\d{1,2})\s+days?\b", lower)
    if in_days:
        return today + timedelta(days=int(in_days.group(1)))

    if "tomorrow" in lower:
        return today + timedelta(days=1)
    if "today" in lower:
        return today

    for name, weekday in WEEKDAYS.items():
        if re.search(rf"\b{name}\b", lower):
            delta = (weekday - today.weekday()) % 7
            return today + timedelta(days=delta or 7)
    return None


def extract_watch_for(text: str) -> list[str]:
    lower_words = set(re.findall(r"[a-z0-9]+", text.lower()))
    found = [
        label
        for label, keywords in WATCH_KEYWORDS.items()
        if lower_words.intersection(keywords)
    ]
    if "weather" in found and "traffic" not in found and "parking" in found:
        found.append("traffic")
    return found or list(DEFAULT_WATCH_FOR)


def watch_domain(title: str, watch_for: Iterable[str]) -> str:
    lower = title.lower()
    dimensions = set(watch_for)
    if any(token in lower for token in ("portfolio", "market", "bitcoin", "mortgage")):
        return "Finance & Markets"
    if "yankees" in lower:
        return "Sports"
    if "rutgers" in lower:
        return "Rutgers"
    if "bogey" in lower:
        return "Dog"
    if "golf equipment" in lower:
        return "Golf Equipment"
    if "golf weather" in lower:
        return "Golf"
    if any(token in lower for token in ("wwdc", "apple", "xcode", "siri")):
        return "Technology"
    if any(token in lower for token in ("flight", "vacation", "airport", "hotel")):
        return "Travel"
    if any(token in lower for token in ("project", "deadline", "work", "migration")):
        return "Work"
    if "home" in lower:
        return "Home"
    if "life" in lower:
        return "Life"
    if dimensions.intersection({"weather", "parking", "traffic"}):
        return "Life"
    return "Watchlist"


def source_inputs_for(watch_for: Iterable[str]) -> list[str]:
    sources = [
        SOURCE_HINTS[dimension]
        for dimension in watch_for
        if dimension in SOURCE_HINTS
    ]
    return list(dict.fromkeys(sources or ["user-provided watch config"]))


def split_source_inputs(watch_for: Iterable[str]) -> tuple[list[str], list[str]]:
    personal: list[str] = []
    external: list[str] = []
    for source in source_inputs_for(watch_for):
        if source in PERSONAL_SOURCE_LABELS or source == "user-provided watch config":
            personal.append(source)
        if source in EXTERNAL_SOURCE_LABELS:
            external.append(source)
        if source not in PERSONAL_SOURCE_LABELS and source not in EXTERNAL_SOURCE_LABELS:
            external.append(source)
    return list(dict.fromkeys(personal)), list(dict.fromkeys(external))


def infer_watch_kind(title: str, watch_for: Iterable[str]) -> str:
    personal_sources, external_sources = split_source_inputs(watch_for)
    lower_title = title.lower()
    if "portfolio" in lower_title:
        return "hybrid"
    if personal_sources and external_sources:
        return "hybrid"
    if external_sources and not personal_sources:
        return "external_monitor"
    return "personal_tracker"
