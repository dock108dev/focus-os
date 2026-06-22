from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Iterable

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .attention import enrich_attention_item
from .models import WatchEvaluation, WatchItem
from .registries import GLOBAL_GUARDRAILS
from .watch_provenance import source_watch_id


DEFAULT_SURFACE_WHEN = [
    "risk changed materially",
    "decision deadline is near",
    "summary would save user effort",
]
DEFAULT_SUPPRESS_WHEN = [
    "generic reminders",
    "unchanged source data",
    "filler that only says the watched object is coming up",
]
DEFAULT_WATCH_FOR = ["timing", "schedule changes"]
WATCH_KINDS = {"personal_tracker", "external_monitor", "hybrid"}
WATCH_PRIORITIES = {"primary_allowed", "watch_only", "quiet_by_default"}
PERSONAL_SOURCE_LABELS = {
    "manual portfolio imports",
    "calendar",
    "work project status",
    "work project metrics",
    "repo migration tracker",
    "project notes",
    "project spend tracker",
    "project activity log",
    "project roadmap",
    "contractor messages",
    "home maintenance log",
    "vet or pharmacy source",
    "pet supply source",
    "boarding reservation source",
    "care calendar",
    "calendar and admin inbox",
    "admin inbox",
    "bill calendar",
    "hotel reservation source",
}
EXTERNAL_SOURCE_LABELS = {
    "weather",
    "parking feed",
    "maps or transit",
    "calendar or venue/source update",
    "post-event sources",
    "developer docs",
    "vendor pricing pages",
    "vendor changelog",
    "crypto price feed",
    "rate feed",
    "market price feed",
    "sports results feed",
    "sports schedule feed",
    "sports injury reports",
    "sports standings feed",
    "sports rankings feed",
    "golf retailer and manufacturer feeds",
    "golf fitting calendar",
    "retailer price feed",
    "manufacturer release calendar",
    "airline source",
    "airline and maps",
}
PORTFOLIO_THRESHOLDS = {
    "cash_above": 0.08,
    "technology_above": 0.45,
    "single_position_above": 0.25,
    "pullback_above": 0.05,
}
SOURCE_HINTS = {
    "weather": "weather",
    "wind": "weather",
    "rain": "weather",
    "tee time": "calendar",
    "parking": "parking feed",
    "traffic": "maps or transit",
    "timing": "calendar",
    "schedule changes": "calendar or venue/source update",
    "summary": "post-event sources",
    "developer tooling": "developer docs",
    "api": "developer docs",
    "pricing": "vendor pricing pages",
    "xcode": "developer docs",
    "ai": "vendor changelog",
    "cash": "manual portfolio imports",
    "concentration": "manual portfolio imports",
    "pullbacks": "manual portfolio imports",
    "Bitcoin": "crypto price feed",
    "mortgage rates": "rate feed",
    "market moves": "market price feed",
    "results": "sports results feed",
    "next game": "sports schedule feed",
    "injuries": "sports injury reports",
    "standings": "sports standings feed",
    "rankings": "sports rankings feed",
    "equipment": "golf retailer and manufacturer feeds",
    "fitting": "golf fitting calendar",
    "price changes": "retailer price feed",
    "release windows": "manufacturer release calendar",
    "blocked teams": "work project status",
    "adoption gaps": "work project metrics",
    "migration status": "repo migration tracker",
    "deadline": "calendar",
    "validation": "project notes",
    "cost": "project spend tracker",
    "progress stalls": "project activity log",
    "launch windows": "project roadmap",
    "due dates": "calendar",
    "contractor timing": "contractor messages",
    "maintenance risk": "home maintenance log",
    "appointments": "calendar",
    "food": "pet supply source",
    "boarding": "boarding reservation source",
    "medication": "vet or pharmacy source",
    "coverage": "care calendar",
    "renewals": "calendar and admin inbox",
    "paperwork": "admin inbox",
    "deadlines": "calendar",
    "family dates": "calendar",
    "bills": "bill calendar",
    "flights": "airline source",
    "hotels": "hotel reservation source",
    "airport timing": "airline and maps",
}
WATCH_KEYWORDS = {
    "weather": {"weather", "rain", "temperature", "forecast"},
    "parking": {"parking", "drive"},
    "traffic": {"traffic", "transit", "train", "airport", "flight"},
    "timing": {"time", "timing", "door", "doors", "starts", "keynote", "kickoff"},
    "schedule changes": {"schedule", "changes", "delay", "postponed", "policy"},
    "summary": {"summarize", "summary", "announcements", "takeaways", "recap"},
    "developer tooling": {"xcode", "developer", "tooling", "api", "sdk"},
    "ai": {"ai", "siri", "model"},
    "cash": {"cash"},
    "concentration": {"concentration", "allocation"},
    "pullbacks": {"pullback", "pullbacks", "drawdown"},
    "Bitcoin": {"bitcoin", "btc"},
    "mortgage rates": {"mortgage", "rates"},
    "market moves": {"market", "markets"},
    "results": {"results", "result", "won", "lost"},
    "next game": {"next", "game", "kickoff"},
    "injuries": {"injury", "injuries"},
    "standings": {"standings", "division"},
    "rankings": {"rankings", "ranking"},
    "equipment": {"equipment", "gear", "club", "clubs"},
    "fitting": {"fitting", "fit"},
    "price changes": {"price", "prices"},
    "release windows": {"release", "releases"},
    "blocked teams": {"blocked", "team", "teams"},
    "adoption gaps": {"adoption", "gaps"},
    "migration status": {"migration", "repo", "namespace"},
    "deadline": {"deadline", "deadlines"},
    "validation": {"validation", "validate"},
    "cost": {"cost", "costs"},
    "progress stalls": {"stalls", "stalled", "progress"},
    "launch windows": {"launch"},
    "due dates": {"due"},
    "contractor timing": {"contractor"},
    "maintenance risk": {"maintenance"},
    "appointments": {"appointment", "appointments"},
    "food": {"food"},
    "boarding": {"boarding"},
    "medication": {"medication", "medicine"},
    "coverage": {"coverage"},
    "renewals": {"renewal", "renewals"},
    "paperwork": {"paperwork"},
    "family dates": {"family"},
    "bills": {"bill", "bills"},
    "flights": {"flight", "flights"},
    "hotels": {"hotel", "hotels"},
    "airport timing": {"airport"},
}
WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


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


def parse_watch_item(text: str, today: date | None = None) -> dict:
    today = today or date.today()
    title = clean_title(text)
    event_date = extract_event_date(text, today)
    expires_at = (
        event_date + timedelta(days=1) if event_date else today + timedelta(days=30)
    )
    watch_for = extract_watch_for(text)
    surface_when = list(DEFAULT_SURFACE_WHEN)
    watch_kind = infer_watch_kind(title, watch_for)
    priority = "watch_only"
    personal_context = personal_context_for(title, text.strip(), watch_for)
    source_config = source_config_for(watch_for)
    evaluation_rules = evaluation_rules_for(surface_when, DEFAULT_SUPPRESS_WHEN)
    return {
        "title": title,
        "original_text": text.strip(),
        "event_date": event_date,
        "expires_at": expires_at,
        "check_frequency": "daily",
        "watch_kind": watch_kind,
        "priority": priority,
        "enabled": True,
        "watch_for": watch_for,
        "personal_state": personal_state_for(
            title, text.strip(), watch_for, surface_when, event_date
        ),
        "external_state": external_state_for(title, watch_for, surface_when),
        "personal_context": personal_context,
        "source_config": source_config,
        "evaluation_rules": evaluation_rules,
        "prompt_config": prompt_config_for(
            title=title,
            watch_kind=watch_kind,
            priority=priority,
            personal_context=personal_context,
            source_config=source_config,
            evaluation_rules=evaluation_rules,
        ),
        "surface_when": surface_when,
        "briefing_posture": "watch",
        "status": "active",
    }


def create_watch_item(db: Session, text: str, today: date | None = None) -> WatchItem:
    if not text.strip():
        raise ValueError("Watch text is required.")
    row = WatchItem(**parse_watch_item(text, today=today))
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def create_configured_watch_item(
    db: Session,
    *,
    title: str,
    original_text: str | None = None,
    watch_kind: str | None = None,
    priority: str | None = None,
    enabled: bool = True,
    check_frequency: str = "daily",
    watch_for: list[str] | None = None,
    personal_context: dict | None = None,
    source_config: dict | None = None,
    evaluation_rules: dict | None = None,
    prompt_config: dict | None = None,
    today: date | None = None,
) -> WatchItem:
    today = today or date.today()
    cleaned_title = clean_title(title)
    if not cleaned_title:
        raise ValueError("Watch title is required.")
    text = (original_text or cleaned_title).strip()
    dimensions = [item.strip() for item in (watch_for or extract_watch_for(text)) if item.strip()]
    surface_when = list((evaluation_rules or {}).get("surface_when") or DEFAULT_SURFACE_WHEN)
    suppress_when = list((evaluation_rules or {}).get("suppress_when") or DEFAULT_SUPPRESS_WHEN)
    resolved_kind = normalize_watch_kind(watch_kind or infer_watch_kind(cleaned_title, dimensions))
    resolved_priority = normalize_watch_priority(priority)
    context = personal_context or personal_context_for(cleaned_title, text, dimensions)
    sources = source_config or source_config_for(dimensions)
    rules = evaluation_rules_for(
        surface_when,
        suppress_when,
        primary_focus_allowed=(evaluation_rules or {}).get(
            "primary_focus_allowed", resolved_priority == "primary_allowed"
        ),
    )
    override = (prompt_config or {}).get("daily_prompt_override")
    prompts = prompt_config_for(
        title=cleaned_title,
        watch_kind=resolved_kind,
        priority=resolved_priority,
        personal_context=context,
        source_config=sources,
        evaluation_rules=rules,
        daily_prompt_override=override,
    )
    row = WatchItem(
        title=cleaned_title,
        original_text=text,
        event_date=extract_event_date(text, today),
        expires_at=None,
        check_frequency=check_frequency.strip() or "daily",
        watch_kind=resolved_kind,
        priority=resolved_priority,
        enabled=enabled,
        watch_for=dimensions,
        personal_state=personal_state_for(
            cleaned_title, text, dimensions, surface_when, None
        ),
        external_state=external_state_for(cleaned_title, dimensions, surface_when),
        personal_context=context,
        source_config=sources,
        evaluation_rules=rules,
        prompt_config=prompts,
        surface_when=surface_when,
        briefing_posture="briefing output" if resolved_priority == "primary_allowed" else "watch",
        status="active",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_watch_item(
    db: Session,
    row: WatchItem,
    *,
    text: str | None = None,
    title: str | None = None,
    original_text: str | None = None,
    event_date: date | None = None,
    expires_at: date | None = None,
    check_frequency: str | None = None,
    watch_kind: str | None = None,
    priority: str | None = None,
    enabled: bool | None = None,
    watch_for: list[str] | None = None,
    personal_state: dict | None = None,
    external_state: dict | None = None,
    personal_context: dict | None = None,
    source_config: dict | None = None,
    evaluation_rules: dict | None = None,
    prompt_config: dict | None = None,
    surface_when: list[str] | None = None,
    status: str | None = None,
    today: date | None = None,
) -> WatchItem:
    if text is not None:
        if not text.strip():
            raise ValueError("Watch text is required.")
        parsed = parse_watch_item(text, today=today)
        for key, value in parsed.items():
            setattr(row, key, value)

    if title is not None:
        cleaned = clean_title(title)
        if not cleaned:
            raise ValueError("Watch title is required.")
        row.title = cleaned
    if original_text is not None:
        row.original_text = original_text.strip()
    if event_date is not None:
        row.event_date = event_date
    if expires_at is not None:
        row.expires_at = expires_at
    if check_frequency is not None:
        row.check_frequency = check_frequency.strip() or "daily"
    if watch_kind is not None:
        row.watch_kind = normalize_watch_kind(watch_kind)
    if priority is not None:
        row.priority = normalize_watch_priority(priority)
    if enabled is not None:
        row.enabled = bool(enabled)
    if watch_for is not None:
        row.watch_for = [item.strip() for item in watch_for if item.strip()]
    if personal_state is not None:
        row.personal_state = personal_state
    if external_state is not None:
        row.external_state = external_state
    if personal_context is not None:
        row.personal_context = personal_context
    if source_config is not None:
        row.source_config = source_config
    if evaluation_rules is not None:
        row.evaluation_rules = evaluation_rules
        row.surface_when = [
            item.strip()
            for item in evaluation_rules.get("surface_when", row.surface_when or [])
            if str(item).strip()
        ]
    if prompt_config is not None:
        row.prompt_config = prompt_config
    if surface_when is not None:
        row.surface_when = [item.strip() for item in surface_when if item.strip()]
    if status is not None:
        if status not in {"active", "completed", "archived"}:
            raise ValueError("Watch status must be active, completed, or archived.")
        row.status = status

    if any(
        value is not None
        for value in (
            title,
            original_text,
            watch_kind,
            priority,
            watch_for,
            personal_context,
            source_config,
            evaluation_rules,
            prompt_config,
            surface_when,
            event_date,
        )
    ):
        if watch_kind is None:
            row.watch_kind = infer_watch_kind(row.title, row.watch_for or [])
        if priority is None:
            row.priority = row.priority or "watch_only"
        if personal_context is None:
            row.personal_context = personal_context_for(
                row.title,
                row.original_text,
                row.watch_for or [],
                **(row.personal_context or {}),
            )
        if source_config is None:
            row.source_config = source_config_for(
                row.watch_for or [], **(row.source_config or {})
            )
        if evaluation_rules is None:
            row.evaluation_rules = evaluation_rules_for(
                row.surface_when or [],
                (row.evaluation_rules or {}).get("suppress_when"),
                primary_focus_allowed=(row.evaluation_rules or {}).get(
                    "primary_focus_allowed", row.priority == "primary_allowed"
                ),
            )
        if personal_state is None:
            row.personal_state = personal_state_for(
                row.title,
                row.original_text,
                row.watch_for or [],
                row.surface_when or [],
                row.event_date,
            )
        if external_state is None:
            row.external_state = external_state_for(
                row.title, row.watch_for or [], row.surface_when or []
            )
        if prompt_config is None:
            row.prompt_config = prompt_config_for(
                title=row.title,
                watch_kind=row.watch_kind,
                priority=row.priority,
                personal_context=row.personal_context or {},
                source_config=row.source_config or {},
                evaluation_rules=row.evaluation_rules or {},
                daily_prompt_override=(row.prompt_config or {}).get(
                    "daily_prompt_override"
                ),
            )

    row.last_evaluated_on = None
    db.commit()
    db.refresh(row)
    return row


def set_watch_item_status(db: Session, row: WatchItem, status: str) -> WatchItem:
    return update_watch_item(db, row, status=status)


def remove_watch_item(db: Session, row: WatchItem) -> None:
    db.execute(delete(WatchEvaluation).where(WatchEvaluation.watch_item_id == row.id))
    db.delete(row)
    db.commit()


def watch_counts(db: Session) -> dict:
    rows = db.execute(
        select(WatchItem.status, func.count(WatchItem.id)).group_by(WatchItem.status)
    ).all()
    counts = {"active": 0, "completed": 0, "archived": 0, "total": 0}
    for status, count in rows:
        key = status if status in counts else "archived"
        counts[key] += count
        counts["total"] += count
    return counts


def serialize_watch_item(row: WatchItem, latest: WatchEvaluation | None = None) -> dict:
    watch_for = row.watch_for or []
    surface_when = row.surface_when or []
    inferred_kind = infer_watch_kind(row.title, watch_for)
    watch_kind = row.watch_kind if row.watch_kind in WATCH_KINDS else inferred_kind
    personal_state = row.personal_state or personal_state_for(
        row.title, row.original_text, watch_for, surface_when, row.event_date
    )
    external_state = row.external_state or external_state_for(
        row.title, watch_for, surface_when
    )
    priority = normalize_watch_priority(row.priority)
    personal_context = row.personal_context or personal_context_for(
        row.title, row.original_text, watch_for
    )
    source_config = row.source_config or source_config_for(watch_for)
    evaluation_rules = row.evaluation_rules or evaluation_rules_for(
        surface_when,
        suppression_rules_for(row),
        primary_focus_allowed=priority == "primary_allowed",
    )
    prompt_config = row.prompt_config or prompt_config_for(
        title=row.title,
        watch_kind=watch_kind,
        priority=priority,
        personal_context=personal_context,
        source_config=source_config,
        evaluation_rules=evaluation_rules,
    )
    personal_inputs = personal_state.get("inputs") or []
    external_sources = external_state.get("sources") or []
    return {
        "id": row.id,
        "source_watch_id": source_watch_id(row.title),
        "title": row.title,
        "original_text": row.original_text,
        "event_date": row.event_date.isoformat() if row.event_date else None,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        "check_frequency": row.check_frequency,
        "watch_kind": watch_kind,
        "priority": priority,
        "enabled": bool(row.enabled),
        "watch_for": watch_for,
        "conditions": watch_for,
        "source_inputs": source_inputs_for(watch_for),
        "personal_state": personal_state,
        "external_state": external_state,
        "personal_context": personal_context,
        "source_config": source_config,
        "evaluation_rules": evaluation_rules,
        "prompt_config": prompt_config,
        "personal_inputs": personal_inputs,
        "external_sources": external_sources,
        "personal_accounts": personal_context.get("accounts") or [],
        "personal_interests": personal_context.get("interests") or [],
        "connected_data_sources": source_config.get("connected_sources") or [],
        "missing_sources": source_config.get("missing_sources") or [],
        "manual_inputs": source_config.get("manual_inputs") or [],
        "validation_warnings": validation_warnings_for(row),
        "cadence": row.check_frequency,
        "surface_when": surface_when,
        "surface_rules": evaluation_rules.get("surface_when") or surface_when,
        "suppression_rules": suppression_rules_for(row),
        "briefing_posture": row.briefing_posture,
        "preferred_output": row.briefing_posture,
        "status": row.status,
        "last_evaluated_on": (
            row.last_evaluated_on.isoformat() if row.last_evaluated_on else None
        ),
        "latest_evaluation": serialize_watch_evaluation(latest) if latest else None,
        "why_today": latest.trigger_reason if latest else None,
    }


def serialize_watch_evaluation(row: WatchEvaluation) -> dict:
    return {
        "id": row.id,
        "watch_item_id": row.watch_item_id,
        "as_of": row.as_of.isoformat(),
        "title": row.title,
        "summary": row.summary,
        "category": row.category,
        "importance_score": row.importance_score,
        "actionability_score": row.actionability_score,
        "should_surface": row.should_surface,
        "trigger_reason": row.trigger_reason,
        "evidence": row.evidence or {},
        "generation_metadata": {
            "why_generated": row.trigger_reason,
            "what_changed": row.summary,
            "why_user_should_care": row.trigger_reason,
            "expiration_date": (
                row.as_of + timedelta(days=1 if row.category == "action" else 3)
            ).isoformat(),
        },
    }


def latest_watch_evaluation(db: Session, item_id: int) -> WatchEvaluation | None:
    return db.scalar(
        select(WatchEvaluation)
        .where(WatchEvaluation.watch_item_id == item_id)
        .order_by(WatchEvaluation.as_of.desc(), WatchEvaluation.created_at.desc())
        .limit(1)
    )


def archive_expired_watch_items(db: Session, today: date | None = None) -> int:
    today = today or date.today()
    rows = list(
        db.scalars(
            select(WatchItem).where(
                WatchItem.status == "active",
                WatchItem.expires_at.is_not(None),
                WatchItem.expires_at < today,
            )
        ).all()
    )
    for row in rows:
        row.status = "archived"
    if rows:
        db.commit()
    return len(rows)


def planning_dimensions(row: WatchItem) -> str:
    dimensions = row.watch_for or DEFAULT_WATCH_FOR
    if len(dimensions) == 1:
        return dimensions[0]
    return ", ".join(dimensions[:-1]) + f", and {dimensions[-1]}"


def quiet_summary_for_watch(row: WatchItem) -> str:
    title = row.title.lower()
    if "bitcoin" in title:
        return "No BTC accumulation trigger today. Price movement did not meet the review rule."
    if "trading systems" in title:
        return "No trading-system action. Liquidity still keeps this on hold."
    if "side project" in title or "focusos validation" in title:
        return "No project changed ship-or-stop posture today."
    if "big tech" in title or "ai, and major company" in title:
        return "No major tech release changed your workflow today."
    if "sports radar" in title:
        return "No major game, injury, playoff, or spoiler-safe recap item found."
    if "golf weather" in title:
        return "No better local golf window than the current watch-only item."
    if "shopping" in title:
        return "No saved shopping interest produced a high-confidence match."
    if "media" in title or "watchlist radar" in title:
        return "No saved media interest produced a high-confidence match."
    if "life notes" in title:
        return "No dated reminder entered its action window."
    if "personal finance" in title:
        return "No liquidity or portfolio threshold crossed today."
    if "investing ideas" in title or "market pullbacks" in title:
        return "No tracked market move changed the review posture today."
    if row.event_date:
        days_until = (row.event_date - date.today()).days
        if days_until >= 0:
            return f"{days_until} days away. No planning trigger has opened yet."
        return "Event has passed with no recap item needed."
    return "No material change reached the briefing threshold today."


def evaluate_watch_item(row: WatchItem, today: date | None = None) -> dict:
    today = today or date.today()
    domain = watch_domain(row.title, row.watch_for or [])
    inferred_kind = infer_watch_kind(row.title, row.watch_for or [])
    watch_kind = row.watch_kind if row.watch_kind in WATCH_KINDS else inferred_kind
    evidence = {
        "watch_kind": watch_kind,
        "priority": row.priority,
        "watch_for": row.watch_for or [],
        "personal_state": row.personal_state or {},
        "external_state": row.external_state or {},
        "personal_context": row.personal_context or {},
        "source_config": row.source_config or {},
        "evaluation_rules": row.evaluation_rules or {},
        "surface_when": row.surface_when or [],
        "event_date": row.event_date.isoformat() if row.event_date else None,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        "domain": domain,
    }

    if row.event_date is None:
        return {
            "title": row.title,
            "summary": "No dated trigger has made this watch item briefing-worthy yet.",
            "category": "awareness",
            "importance_score": 30,
            "actionability_score": 0,
            "should_surface": False,
            "trigger_reason": "Waiting for a material update or dated decision point.",
            "evidence": evidence,
        }

    days_until = (row.event_date - today).days
    evidence["days_until_event"] = days_until

    if days_until < 0:
        days_since = abs(days_until)
        if days_since <= 1 and "summary" in (row.watch_for or []):
            return {
                "title": f"{row.title} happened yesterday",
                "summary": "A recap would now save effort, so this watch item should turn into a summary request.",
                "category": "awareness",
                "importance_score": 72,
                "actionability_score": 20,
                "should_surface": True,
                "trigger_reason": "The watched event has passed and the item asked for a useful summary.",
                "evidence": evidence,
            }
        return {
            "title": row.title,
            "summary": "The watched event has passed and no further update is needed.",
            "category": "awareness",
            "importance_score": 20,
            "actionability_score": 0,
            "should_surface": False,
            "trigger_reason": "Event has passed without a summary trigger.",
            "evidence": evidence,
        }

    if days_until == 0:
        return {
            "title": f"{row.title} is today",
            "summary": f"Check {planning_dimensions(row)} now because the watched event is inside today's decision window.",
            "category": "action",
            "importance_score": 90,
            "actionability_score": 82,
            "should_surface": True,
            "trigger_reason": "The watched event is today.",
            "evidence": evidence,
        }

    if days_until == 1:
        return {
            "title": f"{row.title} is tomorrow",
            "summary": f"Planning details are close enough to matter. Check {planning_dimensions(row)} before the window closes.",
            "category": "action",
            "importance_score": 84,
            "actionability_score": 74,
            "should_surface": True,
            "trigger_reason": "The watched event is one day away.",
            "evidence": evidence,
        }

    if 2 <= days_until <= 5:
        return {
            "title": f"{row.title} planning is starting to matter",
            "summary": f"The decision window is opening. Monitor {planning_dimensions(row)} now so this does not become last-minute.",
            "category": "opportunity",
            "importance_score": 76,
            "actionability_score": 56,
            "should_surface": True,
            "trigger_reason": "The watched event entered its planning window.",
            "evidence": evidence,
        }

    if days_until <= 7 and domain == "Technology":
        return {
            "title": f"{row.title} is coming up",
            "summary": "This is close enough to watch for agenda, timing, and post-event summary value.",
            "category": "awareness",
            "importance_score": 64,
            "actionability_score": 16,
            "should_surface": True,
            "trigger_reason": "A watched technology event is within a week.",
            "evidence": evidence,
        }

    return {
        "title": row.title,
        "summary": "The watch item is active, but it is not close enough or changed enough to brief today.",
        "category": "awareness",
        "importance_score": 30,
        "actionability_score": 0,
        "should_surface": False,
        "trigger_reason": "No meaningful update today.",
        "evidence": evidence,
    }


def evaluate_active_watch_items(
    db: Session, today: date | None = None
) -> list[WatchEvaluation]:
    today = today or date.today()
    archive_expired_watch_items(db, today=today)
    rows = list(
        db.scalars(
            select(WatchItem)
            .where(WatchItem.status == "active", WatchItem.enabled.is_(True))
            .order_by(WatchItem.created_at, WatchItem.id)
        ).all()
    )
    evaluations: list[WatchEvaluation] = []
    for row in rows:
        if row.last_evaluated_on == today:
            latest = latest_watch_evaluation(db, row.id)
            if latest:
                evaluations.append(latest)
            continue
        result = evaluate_watch_item(row, today=today)
        db.execute(
            delete(WatchEvaluation).where(
                WatchEvaluation.watch_item_id == row.id,
                WatchEvaluation.as_of == today,
            )
        )
        evaluation = WatchEvaluation(watch_item_id=row.id, as_of=today, **result)
        row.last_evaluated_on = today
        db.add(evaluation)
        evaluations.append(evaluation)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return list(
            db.scalars(
                select(WatchEvaluation)
                .join(WatchItem)
                .where(
                    WatchEvaluation.as_of == today,
                    WatchItem.status == "active",
                    WatchItem.enabled.is_(True),
                )
                .order_by(WatchEvaluation.id)
            ).all()
        )
    for evaluation in evaluations:
        db.refresh(evaluation)
    return evaluations


def surfaced_watch_evaluations(
    db: Session, today: date | None = None
) -> list[WatchEvaluation]:
    today = today or date.today()
    return list(
        db.scalars(
            select(WatchEvaluation)
            .where(
                WatchEvaluation.as_of == today,
                WatchEvaluation.should_surface.is_(True),
            )
            .order_by(
                WatchEvaluation.importance_score.desc(),
                WatchEvaluation.actionability_score.desc(),
                WatchEvaluation.id,
            )
        ).all()
    )


def active_watch_status(db: Session) -> list[dict]:
    rows = list(
        db.scalars(
            select(WatchItem)
            .where(WatchItem.status == "active", WatchItem.enabled.is_(True))
            .order_by(
                WatchItem.expires_at.is_(None),
                WatchItem.expires_at,
                WatchItem.created_at,
            )
        ).all()
    )
    statuses: list[dict] = []
    for row in rows:
        latest = latest_watch_evaluation(db, row.id)
        if latest and latest.should_surface:
            summary = latest.trigger_reason
        else:
            summary = quiet_summary_for_watch(row)
        statuses.append(
            {
                "id": row.id,
                "title": row.title,
                "summary": summary,
                "status": row.status,
                "watch_kind": row.watch_kind,
                "priority": row.priority,
                "domain": watch_domain(row.title, row.watch_for or []),
                "should_surface": bool(latest and latest.should_surface),
                "source_watch_ids": [source_watch_id(row.title)],
                "suppression_rule": (
                    "No material update today."
                    if not (latest and latest.should_surface)
                    else None
                ),
                "event_date": row.event_date.isoformat() if row.event_date else None,
                "detail_id": f"watch:{row.id}",
            }
        )
    return statuses[:5]


def watch_attention_items(evaluations: Iterable[WatchEvaluation]) -> list[dict]:
    items = []
    for row in evaluations:
        watch = row.watch_item
        domain = (
            watch_domain(watch.title, watch.watch_for or []) if watch else "Watchlist"
        )
        items.append(
            enrich_attention_item(
                {
                    "title": row.title,
                    "why_now": row.summary,
                    "action": "",
                    "priority": max(1, round(row.importance_score / 10)),
                    "detail_id": f"watch:{row.watch_item_id}",
                    "source": "watchlist",
                    "topic": "watchlist",
                    "domain": domain,
                    "vertical": domain,
                    "story_type": "focusos",
                    "suggested_posture": "Watch",
                    "attention_section": (
                        "Today"
                        if row.category in {"action", "opportunity"}
                        else "Around You"
                    ),
                    "situation": row.title,
                    "why_it_matters": row.trigger_reason,
                    "what_changed": row.trigger_reason,
                    "source_watch_ids": [f"watch:{row.watch_item_id}"],
                    "triggered_surface_rule": row.trigger_reason,
                    "suppressed_by": None,
                    "why_today": row.summary,
                    "watch_kind": watch.watch_kind if watch else None,
                    "watch_priority": watch.priority if watch else None,
                },
                category=row.category,
                importance_score=row.importance_score,
                actionability_score=row.actionability_score,
                expiration_hours=24 if row.category == "action" else 72,
                why_user_cares=row.trigger_reason,
            )
        )
    return items
