from __future__ import annotations

import re


DEFAULT_MIKE_WATCHES = [
    {
        "title": "Portfolio & market positioning",
        "original_text": "Portfolio & market positioning\nWatch cash, concentration, pullbacks, Bitcoin, mortgage rates, and material market moves.",
        "watch_for": [
            "cash",
            "concentration",
            "pullbacks",
            "Bitcoin",
            "mortgage rates",
            "market moves",
        ],
        "surface_when": [
            "cash crosses review threshold",
            "position concentration crosses threshold",
            "pullback or market move changes review posture",
        ],
    },
    {
        "title": "Yankees",
        "original_text": "Yankees\nWatch results, next game timing, injuries, standings, and posture-changing storylines.",
        "watch_for": ["results", "next game", "injuries", "standings"],
        "surface_when": [
            "result changes series or standings context",
            "schedule or injury news changes what is worth catching",
        ],
    },
    {
        "title": "Rutgers",
        "original_text": "Rutgers\nWatch game timing, results, injuries, rankings, and schedule changes.",
        "watch_for": ["results", "schedule changes", "injuries", "rankings"],
        "surface_when": [
            "game timing or result changes attention posture",
            "injury or ranking news materially changes context",
        ],
    },
    {
        "title": "Golf weather",
        "original_text": "Golf weather\nWatch rain, wind, temperature, tee-time windows, and playable weather changes.",
        "watch_for": ["weather", "wind", "rain", "tee time"],
        "surface_when": [
            "weather score creates a playable golf window",
            "rain or wind risk changes materially",
        ],
    },
    {
        "title": "Golf equipment",
        "original_text": "Golf equipment\nWatch club releases, fitting windows, price changes, and gear decisions.",
        "watch_for": ["equipment", "fitting", "price changes", "release windows"],
        "surface_when": [
            "fitting or purchase window opens",
            "price or availability changes materially",
        ],
    },
    {
        "title": "AI / developer tools",
        "original_text": "AI / developer tools\nWatch model releases, coding-agent workflow changes, APIs, pricing, Xcode, and developer tooling.",
        "watch_for": ["ai", "developer tooling", "api", "pricing", "xcode"],
        "surface_when": [
            "tooling change alters daily workflow",
            "pricing or API change affects project choices",
        ],
    },
    {
        "title": "Work / namespace migration",
        "original_text": "Work / namespace migration\nWatch blocked teams, adoption gaps, repo migration status, and decision deadlines.",
        "watch_for": ["blocked teams", "adoption gaps", "migration status", "deadline"],
        "surface_when": [
            "team silence blocks migration progress",
            "deadline or adoption gap changes execution risk",
        ],
    },
    {
        "title": "Side projects",
        "original_text": "Side projects\nWatch validation, cost, progress stalls, launch windows, and ship-or-stop signals.",
        "watch_for": ["validation", "cost", "progress stalls", "launch windows"],
        "surface_when": [
            "validation changes project direction",
            "cost or stalled progress creates a ship-or-stop decision",
        ],
    },
    {
        "title": "Home maintenance",
        "original_text": "Home maintenance\nWatch due dates, weather-sensitive tasks, contractor timing, and small issues becoming expensive.",
        "watch_for": ["due dates", "weather", "contractor timing", "maintenance risk"],
        "surface_when": [
            "weather or due date creates a narrow action window",
            "maintenance delay increases cost or risk",
        ],
    },
    {
        "title": "Bogey",
        "original_text": "Bogey\nWatch appointments, food, boarding, medication, coverage, and care logistics.",
        "watch_for": ["appointments", "food", "boarding", "medication", "coverage"],
        "surface_when": [
            "care coverage or appointment window needs action",
            "food, medication, or boarding detail changes materially",
        ],
    },
    {
        "title": "Life logistics",
        "original_text": "Life logistics\nWatch renewals, paperwork, deadlines, family dates, bills, and admin windows.",
        "watch_for": ["renewals", "paperwork", "deadlines", "family dates", "bills"],
        "surface_when": [
            "deadline enters current planning window",
            "paperwork or renewal detail blocks completion",
        ],
    },
    {
        "title": "Travel",
        "original_text": "Travel\nWatch flights, hotels, weather, airport timing, parking, documents, and itinerary changes.",
        "watch_for": ["flights", "hotels", "weather", "airport timing", "parking"],
        "surface_when": [
            "travel detail changes within the planning window",
            "weather, timing, or document issue changes the plan",
        ],
    },
]


def watch_key(value: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return key or "watch"


def source_watch_id(title: str) -> str:
    return f"watch:{watch_key(title)}"


def provenance_for_attention_item(item: dict) -> dict:
    source = str(item.get("source") or "").lower()
    topic = str(item.get("topic") or "").lower()
    detail_id = str(item.get("detail_id") or "")
    domain = str(item.get("domain") or item.get("vertical") or "").lower()
    title = str(item.get("title") or "").lower()
    why_today = str(item.get("why_today") or item.get("why_now") or "")

    if detail_id == "portfolio:review" or detail_id.startswith("finance:"):
        return {
            "source_watch_ids": [source_watch_id("Portfolio & market positioning")],
            "triggered_surface_rule": "portfolio review threshold crossed",
            "suppressed_by": None,
            "why_today": why_today,
        }
    if source == "market" or detail_id.startswith("market:"):
        return {
            "source_watch_ids": [source_watch_id("Portfolio & market positioning")],
            "triggered_surface_rule": "market move or pullback threshold crossed",
            "suppressed_by": None,
            "why_today": why_today,
        }
    if source == "crypto" or detail_id.startswith("crypto:") or topic == "bitcoin":
        return {
            "source_watch_ids": [source_watch_id("Portfolio & market positioning")],
            "triggered_surface_rule": "Bitcoin range or daily move threshold crossed",
            "suppressed_by": None,
            "why_today": why_today,
        }
    if source == "weather" or topic == "golf" or detail_id.startswith("weather:golf"):
        return {
            "source_watch_ids": [source_watch_id("Golf weather")],
            "triggered_surface_rule": "golf weather window crossed planning threshold",
            "suppressed_by": None,
            "why_today": why_today,
        }
    if topic == "yankees" or "yankees" in title:
        return {
            "source_watch_ids": [source_watch_id("Yankees")],
            "triggered_surface_rule": "watched team result or schedule update changed",
            "suppressed_by": None,
            "why_today": why_today,
        }
    if topic == "rutgers" or "rutgers" in title:
        return {
            "source_watch_ids": [source_watch_id("Rutgers")],
            "triggered_surface_rule": "watched team result or schedule update changed",
            "suppressed_by": None,
            "why_today": why_today,
        }
    if topic == "ai" or domain == "technology":
        return {
            "source_watch_ids": [source_watch_id("AI / developer tools")],
            "triggered_surface_rule": "developer-tool or AI update met attention threshold",
            "suppressed_by": None,
            "why_today": why_today,
        }
    if source == "watchlist":
        return {
            "source_watch_ids": list(item.get("source_watch_ids") or []),
            "triggered_surface_rule": str(item.get("triggered_surface_rule") or ""),
            "suppressed_by": item.get("suppressed_by"),
            "why_today": why_today,
        }
    return {
        "source_watch_ids": ["system:manual-or-topic-import"],
        "triggered_surface_rule": "system or manual source met briefing threshold",
        "suppressed_by": None,
        "why_today": why_today,
    }
