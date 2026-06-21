from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from .attention import summarize
from .models import Holding, PortfolioSnapshot
from .topic_engine import seed_topic_briefings_if_empty, seed_topics_if_empty


def seed_snapshots_if_empty(db: Session, total_value: Decimal, cash_available: Decimal) -> None:
    has_snapshots = db.scalar(select(PortfolioSnapshot.id).limit(1))
    if has_snapshots:
        return

    today = date.today()
    db.add_all(
        [
            PortfolioSnapshot(
                as_of=today - timedelta(days=30),
                total_value=total_value - Decimal("980"),
                cash_available=max(cash_available - Decimal("500"), Decimal("0")),
            ),
            PortfolioSnapshot(
                as_of=today - timedelta(days=1),
                total_value=total_value - Decimal("210"),
                cash_available=cash_available,
            ),
            PortfolioSnapshot(
                as_of=today,
                total_value=total_value,
                cash_available=cash_available,
            ),
        ]
    )
    db.commit()


def sample_holdings() -> list[Holding]:
    today = date.today()
    return [
        Holding(
            source="Fidelity",
            account="Fidelity Brokerage",
            symbol="MSFT",
            name="Microsoft",
            asset_class="Technology",
            quantity=18,
            price=430,
            market_value=7740,
            cost_basis=8210,
            as_of=today,
        ),
        Holding(
            source="SoFi",
            account="SoFi Invest",
            symbol="VTI",
            name="Vanguard Total Stock Market ETF",
            asset_class="US Equity",
            quantity=22,
            price=305,
            market_value=6710,
            cost_basis=6200,
            as_of=today,
        ),
        Holding(
            source="Fidelity",
            account="Fidelity Brokerage",
            symbol="NVDA",
            name="Nvidia",
            asset_class="Technology",
            quantity=32,
            price=142,
            market_value=4544,
            cost_basis=3900,
            as_of=today,
        ),
        Holding(
            source="Tastytrade",
            account="Tastytrade",
            symbol="CASH",
            name="Cash",
            asset_class="Cash",
            quantity=3200,
            price=1,
            market_value=3200,
            cost_basis=3200,
            as_of=today,
        ),
        Holding(
            source="SoFi",
            account="SoFi Crypto",
            symbol="BTC",
            name="Bitcoin",
            asset_class="Crypto",
            quantity=0.055,
            price=62000,
            market_value=3410,
            cost_basis=3820,
            as_of=today,
        ),
    ]


def seed_if_empty(db: Session) -> None:
    seed_topics_if_empty(db)
    has_holdings = db.scalar(select(Holding.id).limit(1))
    if has_holdings:
        holdings = list(db.scalars(select(Holding)).all())
        summary = summarize(holdings)
        seed_snapshots_if_empty(
            db,
            Decimal(str(summary["current_value"])),
            Decimal(str(summary["cash_available"])),
        )
        seed_topic_briefings_if_empty(db)
        return

    rows = sample_holdings()
    db.add_all(rows)
    db.commit()
    summary = summarize(rows)
    seed_snapshots_if_empty(
        db,
        Decimal(str(summary["current_value"])),
        Decimal(str(summary["cash_available"])),
    )
    seed_topic_briefings_if_empty(db)
