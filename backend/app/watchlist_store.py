from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .models import WatchEvaluation, WatchItem
from .watch_provenance import source_watch_id
from .watchlist_config import (
    evaluation_rules_for,
    external_state_for,
    normalize_watch_kind,
    normalize_watch_priority,
    personal_context_for,
    personal_state_for,
    prompt_config_for,
    source_config_for,
    suppression_rules_for,
    validation_warnings_for,
)
from .watchlist_parsing import (
    clean_title,
    extract_event_date,
    extract_watch_for,
    infer_watch_kind,
    source_inputs_for,
)
from .watchlist_rules import DEFAULT_SUPPRESS_WHEN, DEFAULT_SURFACE_WHEN, WATCH_KINDS

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
