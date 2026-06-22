from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import logging
from threading import Thread

from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import delete, inspect, select, text
from sqlalchemy.orm import Session

from .api_schemas import MockArchiveGenerate, WatchItemCreate, WatchItemUpdate
from .attention import (
    build_assistant_briefing,
    build_attention,
    build_morning_attention_feed,
    build_opportunities,
    build_recommended_actions,
    summarize,
)
from .briefing_archive import (
    archive_metadata,
    get_archived_payload,
    seed_mock_archive,
    seed_mock_archive_if_empty,
    upsert_archived_briefing,
)
from .database import Base, SessionLocal, engine, get_db
from .daily_review import build_daily_review
from .importer import CSVImportError, parse_holdings_csv
from .models import Holding, JobRun, PortfolioSnapshot, SourceStatus, Topic, WatchItem
from .novelty import apply_novelty, record_displayed_stories
from .recommendations import recommendation_detail
from .registries import (
    GLOBAL_GUARDRAILS,
    KNOWN_MISSING_SOURCE_STATUSES,
    PERSONAL_ACCOUNT_REGISTRY,
    SOURCE_REGISTRY,
)
from .security import (
    apply_security_headers,
    configured_cors_origins,
    max_import_bytes,
    require_allowed_origin,
    require_internal_api_key,
    validate_csv_upload,
)
from .seeding import seed_if_empty
from .source_status import serialize_source_status
from .structured_sources import (
    crypto_attention_items,
    finance_symbol_preferences,
    github_attention_items,
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
    serialize_briefing,
    serialize_topic,
    topic_attention_items,
)
from .watchlist import (
    active_watch_status,
    create_configured_watch_item,
    create_watch_item,
    evaluate_active_watch_items,
    latest_watch_evaluation,
    remove_watch_item,
    serialize_watch_item,
    set_watch_item_status,
    surfaced_watch_evaluations,
    update_watch_item,
    watch_attention_items,
    watch_counts,
)


logger = logging.getLogger(__name__)
ALLOWED_ORIGINS = configured_cors_origins()


class JobRunMissingError(RuntimeError):
    """Raised when a background job can no longer persist status."""


@asynccontextmanager
async def lifespan(_app: FastAPI):
    create_tables()
    with SessionLocal() as db:
        seed_if_empty(db)
        seed_mock_archive_if_empty(db)
    yield


app = FastAPI(title="FocusOS API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-FocusOS-Key"],
)


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    try:
        require_allowed_origin(request, ALLOWED_ORIGINS)
    except HTTPException as exc:
        response = JSONResponse(
            status_code=exc.status_code, content={"detail": exc.detail}
        )
        apply_security_headers(response)
        return response
    response = await call_next(request)
    apply_security_headers(response)
    return response


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_watch_item_schema()


def ensure_watch_item_schema() -> None:
    dialect = engine.dialect.name
    if dialect not in {"sqlite", "postgresql"}:
        return

    with engine.begin() as connection:
        if dialect == "sqlite":
            columns = {
                row[1]
                for row in connection.exec_driver_sql("PRAGMA table_info(watch_items)")
            }
        else:
            inspector = inspect(connection)
            if "watch_items" not in inspector.get_table_names():
                return
            columns = {
                column["name"] for column in inspector.get_columns("watch_items")
            }
        if "watch_kind" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE watch_items "
                    "ADD COLUMN watch_kind VARCHAR(40) DEFAULT 'personal_tracker'"
                )
            )
        if "priority" not in columns:
            connection.execute(
                text("ALTER TABLE watch_items ADD COLUMN priority VARCHAR(40) DEFAULT 'watch_only'")
            )
        if "enabled" not in columns:
            enabled_default = "BOOLEAN DEFAULT TRUE" if dialect == "postgresql" else "BOOLEAN DEFAULT 1"
            connection.execute(text(f"ALTER TABLE watch_items ADD COLUMN enabled {enabled_default}"))
        if "personal_state" not in columns:
            json_default = "JSON DEFAULT '{}'::json" if dialect == "postgresql" else "JSON"
            connection.execute(
                text(f"ALTER TABLE watch_items ADD COLUMN personal_state {json_default}")
            )
            connection.execute(
                text(
                    "UPDATE watch_items SET personal_state = '{}' "
                    "WHERE personal_state IS NULL"
                )
            )
        if "external_state" not in columns:
            json_default = "JSON DEFAULT '{}'::json" if dialect == "postgresql" else "JSON"
            connection.execute(
                text(f"ALTER TABLE watch_items ADD COLUMN external_state {json_default}")
            )
            connection.execute(
                text(
                    "UPDATE watch_items SET external_state = '{}' "
                    "WHERE external_state IS NULL"
                )
            )
        for column_name in (
            "personal_context",
            "source_config",
            "evaluation_rules",
            "prompt_config",
        ):
            if column_name not in columns:
                json_default = "JSON DEFAULT '{}'::json" if dialect == "postgresql" else "JSON"
                connection.execute(
                    text(f"ALTER TABLE watch_items ADD COLUMN {column_name} {json_default}")
                )
                reset_statements = {
                    "personal_context": (
                        "UPDATE watch_items SET personal_context = '{}' "
                        "WHERE personal_context IS NULL"
                    ),
                    "source_config": (
                        "UPDATE watch_items SET source_config = '{}' "
                        "WHERE source_config IS NULL"
                    ),
                    "evaluation_rules": (
                        "UPDATE watch_items SET evaluation_rules = '{}' "
                        "WHERE evaluation_rules IS NULL"
                    ),
                    "prompt_config": (
                        "UPDATE watch_items SET prompt_config = '{}' "
                        "WHERE prompt_config IS NULL"
                    ),
                }
                connection.execute(text(reset_statements[column_name]))


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
        raise JobRunMissingError(f"Job run {job_id} is missing.")
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
            update_job_run(
                db,
                job_id,
                "running",
                "Refreshing structured sources and topic briefings.",
            )
            structured = refresh_structured_sources(db)
            briefings = run_morning_briefing(db)
            watch_evaluations = evaluate_active_watch_items(db)
            update_job_run(
                db,
                job_id,
                "succeeded",
                "Morning briefing generated.",
                {
                    "structured": structured,
                    "topic_briefings": len(briefings),
                    "watch_evaluations": len(watch_evaluations),
                },
                completed=True,
            )
        except Exception as exc:
            logger.exception("morning_briefing_job_failed", extra={"job_id": job_id})
            try:
                update_job_run(
                    db,
                    job_id,
                    "failed",
                    "Morning briefing failed.",
                    {"error_type": type(exc).__name__},
                    completed=True,
                )
            except JobRunMissingError:
                logger.error(
                    "morning_briefing_job_status_missing",
                    extra={"job_id": job_id, "original_error_type": type(exc).__name__},
                )
            except Exception:
                logger.exception(
                    "morning_briefing_job_failure_status_update_failed",
                    extra={"job_id": job_id, "original_error_type": type(exc).__name__},
                )


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


def build_current_briefing_payload(db: Session) -> dict:
    holdings = list(
        db.scalars(select(Holding).order_by(Holding.source, Holding.symbol)).all()
    )
    summary = apply_snapshot_changes(db, summarize(holdings))
    financial_attention = build_attention(holdings, summary)
    symbol_preferences = finance_symbol_preferences(db)
    market_attention = market_attention_items(
        latest_market_prices(db), symbol_preferences
    )
    crypto_attention = crypto_attention_items(
        latest_crypto_prices(db), symbol_preferences
    )
    weather_attention = weather_attention_items(latest_weather_recommendations(db))
    github_attention = github_attention_items(db)
    evaluate_active_watch_items(db)
    watch_attention = watch_attention_items(surfaced_watch_evaluations(db))
    watch_status = active_watch_status(db)
    topic_briefings = latest_topic_briefings(db)
    attention_feed = build_morning_attention_feed(
        [
            market_attention,
            crypto_attention,
            weather_attention,
            github_attention,
            watch_attention,
            topic_attention_items(topic_briefings),
        ],
        financial_attention,
    )
    attention_feed = apply_novelty(db, attention_feed)
    record_displayed_stories(db, attention_feed)
    opportunities = build_opportunities(holdings, summary, financial_attention)
    recommended_actions = build_recommended_actions(
        attention_feed, opportunities, topic_briefings
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "attention": attention_feed,
        "assistant_briefing": build_assistant_briefing(
            attention_feed, watch_status=watch_status
        ),
        "opportunities": opportunities,
        "recommended_actions": recommended_actions,
        "topic_briefings": [serialize_briefing(row) for row in topic_briefings],
        "holdings_count": len(holdings),
        "sources": sorted({holding.source for holding in holdings}),
    }


@app.get("/api/briefing")
def briefing(
    briefing_date: date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
) -> dict:
    today = date.today()
    selected_date = briefing_date or today
    if selected_date > today:
        raise HTTPException(
            status_code=400, detail="Future briefings are not available."
        )
    if selected_date < today:
        archived = get_archived_payload(db, selected_date)
        if archived is None:
            raise HTTPException(status_code=404, detail="Archived briefing not found.")
        return archived

    payload = build_current_briefing_payload(db)
    upsert_archived_briefing(db, today, payload, source="live")
    return archive_metadata(payload, today, "live")


@app.post(
    "/api/internal/briefing-archive/mock",
    dependencies=[Depends(require_internal_api_key)],
)
def generate_mock_archive(
    payload: MockArchiveGenerate | None = None,
    db: Session = Depends(get_db),
) -> dict:
    options = payload or MockArchiveGenerate()
    written = seed_mock_archive(db, total_days=options.days, replace=options.replace)
    return {
        "status": "ok",
        "written": written,
        "days": options.days,
        "replace": options.replace,
        "ends_on": date.today().isoformat(),
    }


@app.get("/api/watch-items")
def watch_items(db: Session = Depends(get_db)) -> dict:
    evaluate_active_watch_items(db)
    rows = list(
        db.scalars(
            select(WatchItem).order_by(
                WatchItem.status,
                WatchItem.expires_at.is_(None),
                WatchItem.expires_at,
                WatchItem.created_at.desc(),
            )
        ).all()
    )
    return {
        "active_count": watch_counts(db)["active"],
        "counts": watch_counts(db),
        "watch_items": [
            serialize_watch_item(row, latest_watch_evaluation(db, row.id))
            for row in rows
        ]
    }


@app.post("/api/watch-items")
def add_watch_item(payload: WatchItemCreate, db: Session = Depends(get_db)) -> dict:
    try:
        if payload.title:
            row = create_configured_watch_item(
                db,
                title=payload.title,
                original_text=payload.original_text or payload.text,
                watch_kind=payload.watch_kind,
                priority=payload.priority,
                enabled=payload.enabled,
                check_frequency=payload.check_frequency or "daily",
                watch_for=payload.watch_for,
                personal_context=payload.personal_context,
                source_config=payload.source_config,
                evaluation_rules=payload.evaluation_rules,
                prompt_config=payload.prompt_config,
            )
        elif payload.text:
            row = create_watch_item(db, payload.text)
        else:
            raise ValueError("Watch text or title is required.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    evaluate_active_watch_items(db)
    return {
        "active_count": watch_counts(db)["active"],
        "watch_item": serialize_watch_item(row, latest_watch_evaluation(db, row.id))
    }


@app.patch("/api/watch-items/{watch_item_id}")
def edit_watch_item(
    watch_item_id: int, payload: WatchItemUpdate, db: Session = Depends(get_db)
) -> dict:
    row = db.get(WatchItem, watch_item_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Watch item not found.")

    updates = payload.model_dump(exclude_unset=True)
    try:
        row = update_watch_item(db, row, **updates)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    evaluate_active_watch_items(db)
    return {
        "active_count": watch_counts(db)["active"],
        "watch_item": serialize_watch_item(row, latest_watch_evaluation(db, row.id)),
    }


@app.post("/api/watch-items/{watch_item_id}/complete")
def complete_watch_item(watch_item_id: int, db: Session = Depends(get_db)) -> dict:
    row = db.get(WatchItem, watch_item_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Watch item not found.")
    row = set_watch_item_status(db, row, "completed")
    return {
        "active_count": watch_counts(db)["active"],
        "watch_item": serialize_watch_item(row, latest_watch_evaluation(db, row.id)),
    }


@app.post("/api/watch-items/{watch_item_id}/archive")
def archive_watch_item(watch_item_id: int, db: Session = Depends(get_db)) -> dict:
    row = db.get(WatchItem, watch_item_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Watch item not found.")
    row = set_watch_item_status(db, row, "archived")
    return {
        "active_count": watch_counts(db)["active"],
        "watch_item": serialize_watch_item(row, latest_watch_evaluation(db, row.id)),
    }


@app.delete("/api/watch-items/{watch_item_id}")
def delete_watch_item(watch_item_id: int, db: Session = Depends(get_db)) -> dict:
    row = db.get(WatchItem, watch_item_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Watch item not found.")
    remove_watch_item(db, row)
    return {"status": "deleted", "active_count": watch_counts(db)["active"]}


@app.get("/api/topics")
def topics(db: Session = Depends(get_db)) -> dict:
    rows = list(
        db.scalars(select(Topic).order_by(Topic.priority.desc(), Topic.name)).all()
    )
    return {"topics": [serialize_topic(topic) for topic in rows]}


@app.get("/api/source-registry")
def source_registry() -> dict:
    return {
        "sources": SOURCE_REGISTRY,
        "global_guardrails": GLOBAL_GUARDRAILS,
    }


@app.get("/api/personal-accounts")
def personal_accounts() -> dict:
    return {"personal_accounts": PERSONAL_ACCOUNT_REGISTRY}


@app.get("/api/recommendations/{detail_id:path}")
def recommendation(detail_id: str, db: Session = Depends(get_db)) -> dict:
    return recommendation_detail(db, detail_id)


@app.post(
    "/api/jobs/morning-briefing", dependencies=[Depends(require_internal_api_key)]
)
def queue_morning_job(db: Session = Depends(get_db)) -> dict:
    job = create_job_run(db, "morning-briefing")
    Thread(target=run_morning_job_background, args=(job.id,), daemon=True).start()
    return {
        "status": "queued",
        "job_id": job.id,
        "queued_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get(
    "/api/jobs/morning-briefing/{job_id}",
    dependencies=[Depends(require_internal_api_key)],
)
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


@app.get(
    "/api/internal/source-status", dependencies=[Depends(require_internal_api_key)]
)
def source_statuses(db: Session = Depends(get_db)) -> dict:
    rows = list(db.scalars(select(SourceStatus).order_by(SourceStatus.name)).all())
    return {
        "sources": [serialize_source_status(row) for row in rows],
        "registry": SOURCE_REGISTRY,
        "missing_or_unavailable": [
            item
            for item in SOURCE_REGISTRY
            if item["auth_required"] or not item["available"]
        ],
        "known_missing": KNOWN_MISSING_SOURCE_STATUSES,
    }


@app.get(
    "/api/internal/daily-review", dependencies=[Depends(require_internal_api_key)]
)
def daily_review(
    review_date: date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
) -> dict:
    today = date.today()
    selected_date = review_date or today
    if selected_date > today:
        raise HTTPException(status_code=400, detail="Future reviews are not available.")

    payload = get_archived_payload(db, selected_date)
    if payload is None:
        if selected_date < today:
            raise HTTPException(status_code=404, detail="Daily review not found.")
        payload = archive_metadata(build_current_briefing_payload(db), today, "live")

    return build_daily_review(db, selected_date, payload)


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
