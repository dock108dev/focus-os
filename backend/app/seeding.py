from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from .attention import summarize
from .models import Holding, PortfolioSnapshot, WatchItem
from .topic_engine import seed_topic_briefings_if_empty, seed_topics_if_empty
from .watch_provenance import DEFAULT_MIKE_WATCHES, LEGACY_DEFAULT_WATCH_TITLES
from .watchlist import external_state_for, infer_watch_kind, personal_state_for
from .watchlist import prompt_config_for


LEGACY_SAMPLE_PORTFOLIO_SIGNATURE = {
    ("Fidelity", "Fidelity Brokerage", "MSFT", "Microsoft", "Technology", "7740.00", "8210.00"),
    ("SoFi", "SoFi Invest", "VTI", "Vanguard Total Stock Market ETF", "US Equity", "6710.00", "6200.00"),
    ("Fidelity", "Fidelity Brokerage", "NVDA", "Nvidia", "Technology", "4544.00", "3900.00"),
    ("Tastytrade", "Tastytrade", "CASH", "Cash", "Cash", "3200.00", "3200.00"),
    ("SoFi", "SoFi Crypto", "BTC", "Bitcoin", "Crypto", "3410.00", "3820.00"),
}


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


def holding_signature(row: Holding) -> tuple[str, str, str, str, str, str, str]:
    return (
        row.source,
        row.account,
        row.symbol,
        row.name,
        row.asset_class,
        f"{Decimal(row.market_value or 0):.2f}",
        f"{Decimal(row.cost_basis or 0):.2f}",
    )


def purge_legacy_sample_portfolio(db: Session) -> int:
    holdings = list(db.scalars(select(Holding)).all())
    if not holdings:
        return 0
    signatures = {holding_signature(row) for row in holdings}
    if signatures != LEGACY_SAMPLE_PORTFOLIO_SIGNATURE:
        return 0

    for row in holdings:
        db.delete(row)
    db.query(PortfolioSnapshot).delete()
    db.commit()
    return len(holdings)


def seed_default_watches(db: Session) -> int:
    existing_rows = list(db.scalars(select(WatchItem)).all())
    current_titles = {watch["title"] for watch in DEFAULT_MIKE_WATCHES}
    changed_existing = False
    for row in existing_rows:
        if row.title in LEGACY_DEFAULT_WATCH_TITLES and row.title not in current_titles:
            if row.status == "active" or row.enabled:
                row.status = "archived"
                row.enabled = False
                changed_existing = True
            continue
        matching_default = next(
            (watch for watch in DEFAULT_MIKE_WATCHES if watch["title"] == row.title),
            None,
        )
        if matching_default:
            if row.watch_kind != matching_default["watch_kind"]:
                row.watch_kind = matching_default["watch_kind"]
                changed_existing = True
            if row.priority != matching_default["priority"]:
                row.priority = matching_default["priority"]
                changed_existing = True
            if row.check_frequency != matching_default["cadence"]:
                row.check_frequency = matching_default["cadence"]
                changed_existing = True
            if row.watch_for != matching_default["watch_for"]:
                row.watch_for = matching_default["watch_for"]
                changed_existing = True
            if row.surface_when != matching_default["surface_when"]:
                row.surface_when = matching_default["surface_when"]
                changed_existing = True
            if not row.enabled or row.status != "active":
                row.enabled = True
                row.status = "active"
                changed_existing = True
            for key in (
                "personal_context",
                "source_config",
                "evaluation_rules",
            ):
                if getattr(row, key) != matching_default[key]:
                    setattr(row, key, matching_default[key])
                    changed_existing = True
            next_prompt = prompt_config_for(
                title=row.title,
                watch_kind=matching_default["watch_kind"],
                priority=matching_default["priority"],
                personal_context=matching_default["personal_context"],
                source_config=matching_default["source_config"],
                evaluation_rules=matching_default["evaluation_rules"],
                daily_prompt_override=(row.prompt_config or {}).get(
                    "daily_prompt_override"
                ),
            )
            if row.prompt_config != next_prompt:
                row.prompt_config = next_prompt
                changed_existing = True
            next_personal_state = personal_state_for(
                row.title,
                row.original_text,
                matching_default["watch_for"],
                matching_default["surface_when"],
                row.event_date,
            )
            next_external_state = external_state_for(
                row.title, matching_default["watch_for"], matching_default["surface_when"]
            )
            if row.personal_state != next_personal_state:
                row.personal_state = next_personal_state
                changed_existing = True
            if row.external_state != next_external_state:
                row.external_state = next_external_state
                changed_existing = True
            continue

        inferred_kind = infer_watch_kind(row.title, row.watch_for or [])
        if (
            not row.watch_kind
            or row.watch_kind == "personal_tracker"
            and inferred_kind != "personal_tracker"
        ):
            row.watch_kind = inferred_kind
            changed_existing = True
        if not row.personal_state:
            row.personal_state = personal_state_for(
                row.title,
                row.original_text,
                row.watch_for or [],
                row.surface_when or [],
                row.event_date,
            )
            changed_existing = True
        if not row.external_state:
            row.external_state = external_state_for(
                row.title, row.watch_for or [], row.surface_when or []
            )
            changed_existing = True
    if changed_existing:
        db.commit()

    existing_titles = {
        title
        for title in db.scalars(select(WatchItem.title)).all()
        if isinstance(title, str)
    }
    rows = []
    for watch in DEFAULT_MIKE_WATCHES:
        if watch["title"] in existing_titles:
            continue
        rows.append(
            WatchItem(
                title=watch["title"],
                original_text=watch["original_text"],
                event_date=None,
                expires_at=None,
                check_frequency=watch["cadence"],
                watch_kind=watch["watch_kind"],
                priority=watch["priority"],
                enabled=True,
                watch_for=watch["watch_for"],
                personal_state=personal_state_for(
                    watch["title"],
                    watch["original_text"],
                    watch["watch_for"],
                    watch["surface_when"],
                    None,
                ),
                external_state=external_state_for(
                    watch["title"], watch["watch_for"], watch["surface_when"]
                ),
                personal_context=watch["personal_context"],
                source_config=watch["source_config"],
                evaluation_rules=watch["evaluation_rules"],
                prompt_config=prompt_config_for(
                    title=watch["title"],
                    watch_kind=watch["watch_kind"],
                    priority=watch["priority"],
                    personal_context=watch["personal_context"],
                    source_config=watch["source_config"],
                    evaluation_rules=watch["evaluation_rules"],
                ),
                surface_when=watch["surface_when"],
                briefing_posture="briefing output",
                status="active",
            )
        )
    if not rows:
        return 0
    db.add_all(rows)
    db.commit()
    return len(rows)


def seed_if_empty(db: Session) -> None:
    seed_topics_if_empty(db)
    seed_default_watches(db)
    purge_legacy_sample_portfolio(db)
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

    seed_topic_briefings_if_empty(db)
