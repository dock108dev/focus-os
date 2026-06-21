from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import logging
from threading import Thread

from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .attention import build_attention, build_morning_attention_feed, build_opportunities, build_recommended_actions, summarize
from .database import Base, SessionLocal, engine, get_db
from .importer import CSVImportError, parse_holdings_csv
from .models import Holding, JobRun, PortfolioSnapshot, SourceStatus, Topic
from .recommendations import recommendation_detail
from .security import (
    apply_security_headers,
    configured_cors_origins,
    max_import_bytes,
    require_allowed_origin,
    require_internal_api_key,
    validate_csv_upload,
)
from .source_status import serialize_source_status
from .structured_sources import (
    crypto_attention_items,
    latest_crypto_prices,
    latest_market_prices,
    latest_weather_recommendations,
    market_attention_items,
    refresh_structured_sources,
    weather_attention_items,
)
from .topic_engine import (
    latest_topic_briefings,
    run_morning_briefing,
    seed_topic_briefings_if_empty,
    seed_topics_if_empty,
    serialize_briefing,
    serialize_topic,
    topic_attention_items,
)


app = FastAPI(title="FocusOS API")
logger = logging.getLogger(__name__)
ALLOWED_ORIGINS = configured_cors_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-FocusOS-Key"],
)


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    try:
        require_allowed_origin(request, ALLOWED_ORIGINS)
    except HTTPException as exc:
        response = JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        apply_security_headers(response)
        return response
    response = await call_next(request)
    apply_security_headers(response)
    return response


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


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
    snapshots = list(db.scalars(select(PortfolioSnapshot).order_by(PortfolioSnapshot.as_of)).all())
    if not snapshots:
        return summary

    current_value = Decimal(str(summary["current_value"]))
    yesterday = max((row for row in snapshots if row.as_of < today), key=lambda row: row.as_of, default=None)
    month_anchor = max(
        (row for row in snapshots if row.as_of <= today - timedelta(days=30)),
        key=lambda row: row.as_of,
        default=None,
    )

    if yesterday and yesterday.total_value:
        daily_change = current_value - Decimal(yesterday.total_value)
        summary["daily_change"] = float(daily_change)
        summary["daily_change_pct"] = float(daily_change / Decimal(yesterday.total_value) * 100)

    if month_anchor and month_anchor.total_value:
        monthly_change = current_value - Decimal(month_anchor.total_value)
        summary["monthly_change"] = float(monthly_change)
        summary["monthly_change_pct"] = float(monthly_change / Decimal(month_anchor.total_value) * 100)

    return summary


def create_job_run(db: Session, name: str) -> JobRun:
    job = JobRun(name=name, status="queued", message="Queued.")
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def update_job_run(
    db: Session,
    job_id: int,
    status: str,
    message: str,
    details: dict | None = None,
    completed: bool = False,
) -> None:
    job = db.get(JobRun, job_id)
    if not job:
        logger.warning("job_run_missing", extra={"job_id": job_id, "status": status})
        return
    job.status = status
    job.message = message
    if details is not None:
        job.details = details
    if status == "running" and job.started_at is None:
        job.started_at = datetime.now(timezone.utc)
    if completed:
        job.completed_at = datetime.now(timezone.utc)
    db.commit()


def run_morning_job_background(job_id: int) -> None:
    with SessionLocal() as db:
        try:
            update_job_run(db, job_id, "running", "Refreshing structured sources and topic briefings.")
            structured = refresh_structured_sources(db)
            briefings = run_morning_briefing(db)
            update_job_run(
                db,
                job_id,
                "succeeded",
                "Morning briefing generated.",
                {"structured": structured, "topic_briefings": len(briefings)},
                completed=True,
            )
        except Exception as exc:
            logger.exception("morning_briefing_job_failed", extra={"job_id": job_id})
            update_job_run(
                db,
                job_id,
                "failed",
                "Morning briefing failed.",
                {"error_type": type(exc).__name__},
                completed=True,
            )


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

    rows = [
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
            as_of=date.today(),
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
            as_of=date.today(),
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
            as_of=date.today(),
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
            as_of=date.today(),
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
            as_of=date.today(),
        ),
    ]
    db.add_all(rows)
    db.commit()
    summary = summarize(rows)
    seed_snapshots_if_empty(
        db,
        Decimal(str(summary["current_value"])),
        Decimal(str(summary["cash_available"])),
    )
    seed_topic_briefings_if_empty(db)


@app.on_event("startup")
def on_startup() -> None:
    create_tables()
    with SessionLocal() as db:
        seed_if_empty(db)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/briefing")
def briefing(db: Session = Depends(get_db)) -> dict:
    holdings = list(db.scalars(select(Holding).order_by(Holding.source, Holding.symbol)).all())
    summary = apply_snapshot_changes(db, summarize(holdings))
    financial_attention = build_attention(holdings, summary)
    market_attention = market_attention_items(latest_market_prices(db))
    crypto_attention = crypto_attention_items(latest_crypto_prices(db))
    weather_attention = weather_attention_items(latest_weather_recommendations(db))
    topic_briefings = latest_topic_briefings(db)
    attention_feed = build_morning_attention_feed(
        [
            market_attention,
            crypto_attention,
            weather_attention,
            topic_attention_items(topic_briefings),
        ],
        financial_attention,
    )
    opportunities = build_opportunities(holdings, summary, financial_attention)
    recommended_actions = build_recommended_actions(attention_feed, opportunities, topic_briefings)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "attention": attention_feed,
        "opportunities": opportunities,
        "recommended_actions": recommended_actions,
        "structured_attention": {
            "market": market_attention,
            "crypto": crypto_attention,
            "weather": weather_attention,
        },
        "topic_briefings": [serialize_briefing(row) for row in topic_briefings],
        "holdings_count": len(holdings),
        "sources": sorted({holding.source for holding in holdings}),
    }


@app.get("/api/topics")
def topics(db: Session = Depends(get_db)) -> dict:
    rows = list(db.scalars(select(Topic).order_by(Topic.priority.desc(), Topic.name)).all())
    return {"topics": [serialize_topic(topic) for topic in rows]}


@app.get("/api/recommendations/{detail_id:path}")
def recommendation(detail_id: str, db: Session = Depends(get_db)) -> dict:
    return recommendation_detail(db, detail_id)


@app.post("/api/jobs/morning-briefing", dependencies=[Depends(require_internal_api_key)])
def queue_morning_job(db: Session = Depends(get_db)) -> dict:
    job = create_job_run(db, "morning-briefing")
    Thread(target=run_morning_job_background, args=(job.id,), daemon=True).start()
    return {
        "status": "queued",
        "job_id": job.id,
        "queued_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/jobs/morning-briefing/{job_id}")
def morning_job_status(job_id: int, db: Session = Depends(get_db)) -> dict:
    job = db.get(JobRun, job_id)
    if job is None:
        return {"status": "missing", "job_id": job_id}
    return {
        "job_id": job.id,
        "name": job.name,
        "status": job.status,
        "message": job.message,
        "details": job.details or {},
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


@app.get("/api/internal/source-status", dependencies=[Depends(require_internal_api_key)])
def source_statuses(db: Session = Depends(get_db)) -> dict:
    rows = list(db.scalars(select(SourceStatus).order_by(SourceStatus.name)).all())
    return {"sources": [serialize_source_status(row) for row in rows]}


@app.post("/api/import/holdings")
async def import_holdings(
    source: str = Query(..., min_length=1, max_length=80),
    replace: bool = Query(True),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    raw = await file.read(max_import_bytes() + 1)
    validate_csv_upload(file.content_type, file.filename, len(raw), max_import_bytes())
    try:
        holdings = parse_holdings_csv(raw, source=source)
    except (CSVImportError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if replace:
        db.execute(delete(Holding).where(Holding.source == source))

    db.add_all(holdings)
    db.commit()
    all_holdings = list(db.scalars(select(Holding)).all())
    upsert_snapshot(db, summarize(all_holdings))

    return {
        "source": source,
        "imported": len(holdings),
        "replace": replace,
    }
