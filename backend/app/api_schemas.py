from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class WatchItemCreate(BaseModel):
    text: str | None = Field(default=None, min_length=1, max_length=4000)
    title: str | None = Field(default=None, min_length=1, max_length=240)
    original_text: str | None = Field(default=None, min_length=1, max_length=4000)
    watch_kind: str | None = Field(default=None, min_length=1, max_length=40)
    priority: str | None = Field(default=None, min_length=1, max_length=40)
    enabled: bool = True
    check_frequency: str | None = Field(default=None, min_length=1, max_length=40)
    watch_for: list[str] | None = None
    personal_context: dict | None = None
    source_config: dict | None = None
    evaluation_rules: dict | None = None
    prompt_config: dict | None = None


class WatchItemUpdate(BaseModel):
    text: str | None = Field(default=None, min_length=1, max_length=2000)
    title: str | None = Field(default=None, min_length=1, max_length=240)
    original_text: str | None = Field(default=None, min_length=1, max_length=2000)
    event_date: date | None = None
    expires_at: date | None = None
    check_frequency: str | None = Field(default=None, min_length=1, max_length=40)
    watch_kind: str | None = Field(default=None, min_length=1, max_length=40)
    priority: str | None = Field(default=None, min_length=1, max_length=40)
    enabled: bool | None = None
    watch_for: list[str] | None = None
    personal_state: dict | None = None
    external_state: dict | None = None
    personal_context: dict | None = None
    source_config: dict | None = None
    evaluation_rules: dict | None = None
    prompt_config: dict | None = None
    surface_when: list[str] | None = None
    status: str | None = None


class MockArchiveGenerate(BaseModel):
    days: int = Field(default=50, ge=1, le=365)
    replace: bool = False
