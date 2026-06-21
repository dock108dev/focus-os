from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Holding
from app.recommendations import recommendation_detail


class EmptySession:
    pass


def test_malformed_market_detail_returns_not_found_payload():
    detail = recommendation_detail(EmptySession(), "market:MSFT")

    assert detail["title"] == "Recommendation not found"
    assert detail["id"] == "market:MSFT"


def test_portfolio_review_detail_groups_active_thresholds():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        db.add_all(
            [
                Holding(
                    source="Fidelity",
                    account="Brokerage",
                    symbol="CASH",
                    name="Cash",
                    asset_class="Cash",
                    quantity=2500,
                    price=1,
                    market_value=2500,
                    cost_basis=2500,
                    as_of=date.today(),
                ),
                Holding(
                    source="Fidelity",
                    account="Brokerage",
                    symbol="MSFT",
                    name="Microsoft",
                    asset_class="Technology",
                    quantity=10,
                    price=700,
                    market_value=7000,
                    cost_basis=8000,
                    as_of=date.today(),
                ),
            ]
        )
        db.commit()

        detail = recommendation_detail(db, "portfolio:review")
    finally:
        db.close()

    assert detail["title"] == "Review portfolio positioning"
    assert "grouped into one review item" in detail["why_generated"][0]
    assert len(detail["raw_data"]["signals"]) >= 3
    assert (
        detail["suppressed_signals"][0]["reason"]
        == "Collapsed into Portfolio to preserve homepage diversity."
    )
