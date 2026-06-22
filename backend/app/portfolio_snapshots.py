from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .models import PortfolioSnapshot


def upsert_snapshot(db: Session, summary: dict) -> None:
    today = date.today()
    db.execute(delete(PortfolioSnapshot).where(PortfolioSnapshot.as_of == today))
    db.add(
        PortfolioSnapshot(
            as_of=today,
            total_value=Decimal(str(summary["current_value"])),
            cash_available=Decimal(str(summary["cash_available"])),
        )
    )
    db.commit()


def apply_snapshot_changes(db: Session, summary: dict) -> dict:
    today = date.today()
    snapshots = list(
        db.scalars(select(PortfolioSnapshot).order_by(PortfolioSnapshot.as_of)).all()
    )
    if not snapshots:
        return summary

    current_value = Decimal(str(summary["current_value"]))
    yesterday = max(
        (row for row in snapshots if row.as_of < today),
        key=lambda row: row.as_of,
        default=None,
    )
    month_anchor = max(
        (row for row in snapshots if row.as_of <= today - timedelta(days=30)),
        key=lambda row: row.as_of,
        default=None,
    )

    if yesterday and yesterday.total_value:
        daily_change = current_value - Decimal(yesterday.total_value)
        summary["daily_change"] = float(daily_change)
        summary["daily_change_pct"] = float(
            daily_change / Decimal(yesterday.total_value) * 100
        )

    if month_anchor and month_anchor.total_value:
        monthly_change = current_value - Decimal(month_anchor.total_value)
        summary["monthly_change"] = float(monthly_change)
        summary["monthly_change_pct"] = float(
            monthly_change / Decimal(month_anchor.total_value) * 100
        )

    return summary
