from __future__ import annotations

from datetime import date
from typing import Iterable

from .models import WatchItem
from .registries import GLOBAL_GUARDRAILS
from .watchlist_parsing import split_source_inputs
from .watchlist_rules import (
    DEFAULT_SUPPRESS_WHEN,
    PORTFOLIO_THRESHOLDS,
    WATCH_PRIORITIES,
)

def personal_state_for(
    title: str,
    original_text: str,
    watch_for: Iterable[str],
    surface_when: Iterable[str],
    event_date: date | None,
) -> dict:
    personal_sources, _ = split_source_inputs(watch_for)
    lower_title = title.lower()
    thresholds = PORTFOLIO_THRESHOLDS if "portfolio" in lower_title else {}
    known_facts = [line.strip(" -\t") for line in original_text.splitlines()[1:] if line.strip()]
    ignore = [
        "generic advice",
        "repeated reminders with no new state change",
        "inputs that do not meet configured surface rules",
    ]
    return {
        "inputs": personal_sources,
        "known_facts": known_facts[:4],
        "last_user_update": None,
        "thresholds": thresholds,
        "next_relevant_date": event_date.isoformat() if event_date else None,
        "actionable_when": list(surface_when),
        "ignore": ignore,
    }


def external_state_for(
    title: str,
    watch_for: Iterable[str],
    surface_when: Iterable[str],
) -> dict:
    _, external_sources = split_source_inputs(watch_for)
    lower_title = title.lower()
    watch_terms = list(watch_for)
    query_terms = [title, *watch_terms[:4]]
    freshness = "daily"
    if any(
        token in lower_title or token in watch_terms
        for token in ("weather", "travel", "yankees", "rutgers")
    ):
        freshness = "same-day"
    return {
        "sources": external_sources,
        "query_strategy": query_terms,
        "freshness_window": freshness,
        "signal_threshold": "material change from the previous checked state",
        "materiality_test": list(surface_when),
        "briefing_rule": "surface only when the change alters attention, timing, or posture",
    }


def normalize_watch_kind(value: str | None) -> str:
    kind = (value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if kind in {"personal", "personal_state", "personal_tracker"}:
        return "personal_tracker"
    if kind in {"external", "external_signal", "external_monitor"}:
        return "external_monitor"
    if kind == "hybrid":
        return "hybrid"
    raise ValueError("Watch kind must be personal_tracker, external_monitor, or hybrid.")


def normalize_watch_priority(value: str | None) -> str:
    priority = (value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if priority in WATCH_PRIORITIES:
        return priority
    if priority in {"primary", "can_be_primary"}:
        return "primary_allowed"
    if priority in {"quiet", "low"}:
        return "quiet_by_default"
    if not priority:
        return "watch_only"
    raise ValueError("Watch priority must be primary_allowed, watch_only, or quiet_by_default.")


def personal_context_for(
    title: str,
    original_text: str,
    watch_for: Iterable[str],
    *,
    why_i_care: str | None = None,
    accounts: list[str] | None = None,
    interests: list[str] | None = None,
    owned_assets: list[str] | None = None,
    ignored_accounts: list[str] | None = None,
) -> dict:
    text_lines = [line.strip() for line in original_text.splitlines() if line.strip()]
    return {
        "why_i_care": why_i_care or (text_lines[1] if len(text_lines) > 1 else f"Mike asked FocusOS to monitor {title}."),
        "accounts": accounts or [],
        "interests": interests or list(watch_for),
        "owned_assets": owned_assets or [],
        "ignored_accounts": ignored_accounts or [],
    }


def source_config_for(
    watch_for: Iterable[str],
    *,
    connected_sources: list[str] | None = None,
    available_sources: list[str] | None = None,
    missing_sources: list[str] | None = None,
    manual_inputs: list[str] | None = None,
) -> dict:
    personal_sources, external_sources = split_source_inputs(watch_for)
    return {
        "connected_sources": connected_sources or external_sources,
        "available_sources": available_sources or [],
        "missing_sources": missing_sources or [],
        "manual_inputs": manual_inputs or personal_sources,
    }


def evaluation_rules_for(
    surface_when: Iterable[str],
    suppress_when: Iterable[str] | None = None,
    *,
    primary_focus_allowed: bool | None = None,
) -> dict:
    return {
        "surface_when": list(surface_when),
        "suppress_when": list(suppress_when or DEFAULT_SUPPRESS_WHEN),
        "primary_focus_allowed": bool(primary_focus_allowed),
    }


def generated_daily_prompt(
    *,
    title: str,
    watch_kind: str,
    priority: str,
    personal_context: dict,
    source_config: dict,
    evaluation_rules: dict,
    daily_prompt_override: str | None = None,
) -> str:
    accounts_interests = list(personal_context.get("accounts") or []) + list(
        personal_context.get("interests") or []
    )
    lines = [
        "Evaluate this watch for today's FocusOS briefing.",
        "",
        f"Watch:\n{title}",
        "",
        f"Watch kind:\n{watch_kind}",
        "",
        f"Priority:\n{priority}",
        "",
        f"Why Mike cares:\n{personal_context.get('why_i_care', '')}",
        "",
        f"Personal accounts / interests:\n{', '.join(accounts_interests) or 'None'}",
        "",
        f"Connected data sources:\n{', '.join(source_config.get('connected_sources') or []) or 'None'}",
        "",
        f"Missing sources:\n{', '.join(source_config.get('missing_sources') or []) or 'None'}",
        "",
        f"Manual inputs:\n{', '.join(source_config.get('manual_inputs') or []) or 'None'}",
        "",
        f"Surface only when:\n{'; '.join(evaluation_rules.get('surface_when') or []) or 'No surface rules configured'}",
        "",
        f"Stay quiet when:\n{'; '.join(evaluation_rules.get('suppress_when') or []) or 'No suppression rules configured'}",
        "",
        "Global rules:",
        *[f"- {rule}" for rule in GLOBAL_GUARDRAILS],
    ]
    if daily_prompt_override:
        lines.extend(["", "User override instruction:", daily_prompt_override])
    lines.extend(
        [
            "",
            "Return:",
            "- status: needs_attention | watch_only | quiet",
            "- title",
            "- summary",
            "- source evidence",
            "- personal facts used",
            "- external facts checked",
            "- missing data",
            "- triggered rule",
            "- suppression result",
            "- recommended action if any",
        ]
    )
    return "\n".join(lines)


def prompt_config_for(
    *,
    title: str,
    watch_kind: str,
    priority: str,
    personal_context: dict,
    source_config: dict,
    evaluation_rules: dict,
    daily_prompt_override: str | None = None,
) -> dict:
    return {
        "generated_prompt": generated_daily_prompt(
            title=title,
            watch_kind=watch_kind,
            priority=priority,
            personal_context=personal_context,
            source_config=source_config,
            evaluation_rules=evaluation_rules,
            daily_prompt_override=daily_prompt_override,
        ),
        "daily_prompt_override": daily_prompt_override,
        "guardrails_enabled": True,
        "global_guardrails": list(GLOBAL_GUARDRAILS),
    }


def validation_warnings_for(row: WatchItem) -> list[str]:
    source_config = row.source_config or {}
    evaluation_rules = row.evaluation_rules or {}
    prompt_config = row.prompt_config or {}
    warnings: list[str] = []
    if not source_config.get("connected_sources") and not source_config.get("manual_inputs"):
        warnings.append("No data source enabled")
    if source_config.get("manual_inputs") and not row.original_text.strip():
        warnings.append("Manual input required")
    if not evaluation_rules.get("suppress_when"):
        warnings.append("No suppression rules configured")
    if len(row.watch_for or []) > 8:
        warnings.append("This watch may be too broad")
    if source_config.get("missing_sources") and not source_config.get("connected_sources"):
        warnings.append("This watch cannot currently produce real data")
    override = prompt_config.get("daily_prompt_override")
    if override:
        lower = str(override).lower()
        if "surface" not in lower:
            warnings.append("Prompt override lacks a surface rule")
        if "suppress" not in lower and "quiet" not in lower:
            warnings.append("Prompt override lacks a suppress rule")
    return warnings


def suppression_rules_for(row: WatchItem) -> list[str]:
    configured = (row.evaluation_rules or {}).get("suppress_when")
    rules = list(configured or DEFAULT_SUPPRESS_WHEN)
    surface_rules = row.surface_when or []
    if surface_rules:
        rules.append("inputs that do not meet configured surface rules")
    return rules

