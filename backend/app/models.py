from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Holding(Base):
    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(80), index=True)
    account: Mapped[str] = mapped_column(String(120), default="Manual")
    symbol: Mapped[str] = mapped_column(String(24), index=True)
    name: Mapped[str] = mapped_column(String(240), default="")
    asset_class: Mapped[str] = mapped_column(String(80), default="Unknown")
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0)
    market_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    cost_basis: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    as_of: Mapped[date] = mapped_column(Date, default=date.today)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    as_of: Mapped[date] = mapped_column(Date, index=True)
    total_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    cash_available: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=5)
    source_type: Mapped[str] = mapped_column(String(40), default="unstructured")
    category: Mapped[str] = mapped_column(String(80), default="General")
    refresh_frequency: Mapped[str] = mapped_column(String(40), default="daily")
    prompt: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    briefings: Mapped[list["TopicBriefing"]] = relationship(back_populates="topic")


class TopicBriefing(Base):
    __tablename__ = "topic_briefings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), index=True)
    as_of: Mapped[date] = mapped_column(Date, index=True)
    title: Mapped[str] = mapped_column(String(240))
    summary: Mapped[str] = mapped_column(Text)
    bullets: Mapped[list[str]] = mapped_column(JSON, default=list)
    action: Mapped[str] = mapped_column(String(240), default="")
    source_type: Mapped[str] = mapped_column(String(40), default="unstructured")
    priority: Mapped[int] = mapped_column(Integer, default=5)
    generated_by: Mapped[str] = mapped_column(String(80), default="fallback")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    topic: Mapped[Topic] = relationship(back_populates="briefings")


class MarketPrice(Base):
    __tablename__ = "market_prices"
    __table_args__ = (UniqueConstraint("symbol", "as_of", name="uq_market_price_symbol_as_of"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(24), index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0)
    previous_close: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0)
    five_day_high: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0)
    five_day_change_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0)
    as_of: Mapped[date] = mapped_column(Date, index=True)
    source: Mapped[str] = mapped_column(String(80), default="Yahoo Finance")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CryptoPrice(Base):
    __tablename__ = "crypto_prices"
    __table_args__ = (UniqueConstraint("asset_id", "as_of", name="uq_crypto_price_asset_as_of"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    asset_id: Mapped[str] = mapped_column(String(80), index=True)
    symbol: Mapped[str] = mapped_column(String(24), index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=0)
    change_24h_pct: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0)
    as_of: Mapped[date] = mapped_column(Date, index=True)
    source: Mapped[str] = mapped_column(String(80), default="CoinGecko")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class WeatherRecommendation(Base):
    __tablename__ = "weather_recommendations"
    __table_args__ = (UniqueConstraint("activity", "as_of", name="uq_weather_recommendation_activity_as_of"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    activity: Mapped[str] = mapped_column(String(80), index=True)
    location: Mapped[str] = mapped_column(String(160), default="Central New Jersey")
    recommended_date: Mapped[date] = mapped_column(Date)
    title: Mapped[str] = mapped_column(String(240))
    reason: Mapped[str] = mapped_column(Text)
    action: Mapped[str] = mapped_column(String(240), default="")
    score: Mapped[int] = mapped_column(Integer, default=0)
    as_of: Mapped[date] = mapped_column(Date, index=True)
    source: Mapped[str] = mapped_column(String(80), default="Open-Meteo")
    raw: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SourceStatus(Base):
    __tablename__ = "source_statuses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(40), default="unknown")
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    message: Mapped[str] = mapped_column(Text, default="")
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class JobRun(Base):
    __tablename__ = "job_runs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    status: Mapped[str] = mapped_column(String(40), default="queued")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    message: Mapped[str] = mapped_column(Text, default="")
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
