from __future__ import annotations

import re

from .watch_provenance_catalog import (
    DEFAULT_MIKE_WATCHES as DEFAULT_MIKE_WATCHES,
    LEGACY_DEFAULT_WATCH_TITLES as LEGACY_DEFAULT_WATCH_TITLES,
)


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
            "source_watch_ids": [source_watch_id("Personal finance and liquidity runway")],
            "triggered_surface_rule": "portfolio review threshold crossed",
            "suppressed_by": None,
            "why_today": why_today,
        }
    if source == "market" or detail_id.startswith("market:"):
        return {
            "source_watch_ids": [source_watch_id("Investing ideas and market pullbacks")],
            "triggered_surface_rule": "market move or pullback threshold crossed",
            "suppressed_by": None,
            "why_today": why_today,
        }
    if source == "crypto" or detail_id.startswith("crypto:") or topic == "bitcoin":
        return {
            "source_watch_ids": [source_watch_id("Bitcoin accumulation posture")],
            "triggered_surface_rule": "Bitcoin range or daily move threshold crossed",
            "suppressed_by": None,
            "why_today": why_today,
        }
    if source == "weather" or topic == "golf" or detail_id.startswith("weather:golf"):
        return {
            "source_watch_ids": [source_watch_id("Golf weather for Basking Ridge")],
            "triggered_surface_rule": "golf weather window crossed planning threshold",
            "suppressed_by": None,
            "why_today": why_today,
        }
    if topic == "yankees" or "yankees" in title:
        return {
            "source_watch_ids": [source_watch_id("Sports radar with spoiler-safe recap")],
            "triggered_surface_rule": "watched team result or schedule update changed",
            "suppressed_by": None,
            "why_today": why_today,
        }
    if topic == "rutgers" or "rutgers" in title:
        return {
            "source_watch_ids": [source_watch_id("Sports radar with spoiler-safe recap")],
            "triggered_surface_rule": "watched team result or schedule update changed",
            "suppressed_by": None,
            "why_today": why_today,
        }
    if topic == "ai" or domain == "technology":
        return {
            "source_watch_ids": [source_watch_id("Big tech, AI, and major company releases")],
            "triggered_surface_rule": "developer-tool or AI update met attention threshold",
            "suppressed_by": None,
            "why_today": why_today,
        }
    if source == "github" or topic == "github":
        return {
            "source_watch_ids": [source_watch_id("Personal GitHub repo health")],
            "triggered_surface_rule": "public repo health rule triggered",
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
