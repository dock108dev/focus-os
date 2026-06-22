from __future__ import annotations

from datetime import date

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Holding, PortfolioSnapshot, WatchItem
from app.seeding import purge_legacy_sample_portfolio, sample_holdings, seed_if_empty


def in_memory_sessionmaker():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def test_seed_if_empty_does_not_create_sample_portfolio():
    testing_session = in_memory_sessionmaker()

    with testing_session() as db:
        seed_if_empty(db)
        holdings = db.scalar(select(func.count()).select_from(Holding))
        snapshots = db.scalar(select(func.count()).select_from(PortfolioSnapshot))
        watches = db.scalar(select(func.count()).select_from(WatchItem))

    assert holdings == 0
    assert snapshots == 0
    assert watches == 12


def test_legacy_sample_portfolio_is_purged_only_when_exact_match():
    testing_session = in_memory_sessionmaker()

    with testing_session() as db:
        db.add_all(sample_holdings())
        db.add(
            PortfolioSnapshot(
                as_of=date.today(), total_value=25604, cash_available=3200
            )
        )
        db.commit()

        deleted = purge_legacy_sample_portfolio(db)
        holdings = db.scalar(select(func.count()).select_from(Holding))
        snapshots = db.scalar(select(func.count()).select_from(PortfolioSnapshot))

    assert deleted == 5
    assert holdings == 0
    assert snapshots == 0
