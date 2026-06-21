from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import SourceStatus


def record_source_status(
    db: Session,
    name: str,
    status: str,
    message: str = "",
    details: dict | None = None,
) -> None:
    row = db.scalar(select(SourceStatus).where(SourceStatus.name == name))
    if row is None:
        row = SourceStatus(name=name)
        db.add(row)

    row.status = status
    row.message = message
    row.details = details or {}
    row.last_run_at = datetime.now(timezone.utc)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def serialize_source_status(row: SourceStatus) -> dict:
    return {
        "name": row.name,
        "status": row.status,
        "last_run_at": row.last_run_at.isoformat() if row.last_run_at else None,
        "message": row.message,
        "details": row.details or {},
    }
